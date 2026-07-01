"""
Metadata extraction service for images and videos.
Supports EXIF, IPTC, XMP, and file system metadata.
"""
import os
import json
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
from PIL import Image
from PIL.ExifTags import TAGS as PIL_EXIF_TAGS
import piexif
import hachoir.parser
import hachoir.metadata
import numpy as np

logger = logging.getLogger(__name__)


def _log_raw(stage: str, data: Any, file_path: Path) -> None:
    """
    Dump raw extraction data to the logger at DEBUG level.

    Each stage emits a single JSON-serialisable log record so you can grep by
    stage name and pipe the output through `jq` without parsing mixed text.

    Usage:
        import logging
        logging.basicConfig(level=logging.DEBUG)
        # or to a file:
        logging.basicConfig(filename="metadata_debug.log", level=logging.DEBUG)
    """
    def _safe(obj: Any) -> Any:
        """Best-effort JSON-safe conversion — lossy but never raises."""
        if obj is None or isinstance(obj, (bool, int, float, str)):
            return obj
        if isinstance(obj, (bytes, bytearray)):
            try:
                return obj.decode("utf-8", errors="replace")
            except Exception:
                return repr(obj)
        if isinstance(obj, dict):
            return {str(k): _safe(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [_safe(i) for i in obj]
        # IFDRational and similar fraction-like objects
        if hasattr(obj, "numerator") and hasattr(obj, "denominator"):
            try:
                return float(obj.numerator) / float(obj.denominator) if obj.denominator else None
            except Exception:
                pass
        try:
            return str(obj)
        except Exception:
            return "<unserializable>"

    record = {
        "stage": stage,
        "file": str(file_path),
        "data": _safe(data),
    }
    logger.debug("RAW_METADATA | %s", json.dumps(record, ensure_ascii=False))


def extract_metadata(file_path: Path) -> Dict[str, Any]:
    """
    Extract metadata from an image or video file.

    Args:
        file_path: Path to the media file

    Returns:
        Dictionary containing extracted metadata
    """
    metadata = {
        "file_info": {},
        "exif": {},
        "iptc": {},
        "xmp": {},
        "other": {}
    }

    stat = file_path.stat()
    metadata["file_info"] = {
        "filename": file_path.name,
        "size": stat.st_size,
        "created": stat.st_ctime,
        "modified": stat.st_mtime,
        "extension": file_path.suffix.lower()
    }

    extension = file_path.suffix.lower()

    if extension in [".jpg", ".jpeg", ".png", ".tiff", ".webp"]:
        metadata.update(_extract_image_metadata(file_path))
    elif extension in [".mp4", ".avi", ".mov", ".mkv", ".flv", ".wmv"]:
        metadata.update(_extract_video_metadata(file_path))

    metadata["location"] = _build_location(metadata.get("exif", {}))
    metadata["capture_time"] = _extract_capture_time(metadata.get("exif", {}))

    metadata = _deep_serialize(metadata)

    return metadata


def _extract_image_metadata(file_path: Path) -> Dict[str, Any]:
    """Extract metadata from image files."""
    metadata = {"exif": {}, "iptc": {}, "xmp": {}, "other": {}}

    # --- PIL pass: non-GPS EXIF tags only ---
    try:
        with Image.open(file_path) as img:
            exif_data = img._getexif()
            _log_raw("pil_raw_exif", exif_data, file_path)
            if exif_data:
                for tag_id, value in exif_data.items():
                    # Skip the GPSInfo block (tag 34853); piexif handles GPS below.
                    if tag_id == 34853:
                        continue
                    tag = PIL_EXIF_TAGS.get(tag_id, tag_id)
                    key = str(tag) if isinstance(tag, int) else tag
                    metadata["exif"][key] = value

            metadata["other"]["format"] = img.format
            metadata["other"]["mode"] = img.mode
            metadata["other"]["size"] = img.size

    except Exception as e:
        metadata["other"]["pil_error"] = f"Failed to extract image metadata: {str(e)}"

    # --- piexif pass: authoritative source for GPS tags ---
    # FIX: piexif.TAGS[ifd] is the correct lookup for tag names, not piexif.GPSIFD.
    # We use this for all IFDs, including GPS, to get consistent human-readable keys.
    try:
        exif_dict = piexif.load(str(file_path))
        _log_raw("piexif_raw_dict", exif_dict, file_path)

        for ifd in ("0th", "Exif", "GPS", "1st", "Interop"):
            if ifd not in exif_dict:
                continue
            if ifd == "GPS":
                _log_raw("piexif_raw_gps_ifd", exif_dict["GPS"], file_path)
            ifd_tags = piexif.TAGS.get(ifd, {})
            for tag_id, value in exif_dict[ifd].items():
                tag_info = ifd_tags.get(tag_id, {})
                tag_name = tag_info.get("name", tag_id)
                key = str(tag_name) if isinstance(tag_name, int) else tag_name

                # GPS rational values arrive as tuples-of-tuples: ((d_num, d_den), …).
                # Convert to plain floats before storing so downstream code has a
                # uniform representation regardless of extraction path.
                if ifd == "GPS" and key in ("GPSLatitude", "GPSLongitude", "GPSAltitude"):
                    value = _rational_tuple_to_floats(value)

                metadata["exif"][key] = value

        # Normalise the GPS direction references to bare ASCII characters.
        # piexif returns them as bytes (b'N\x00'), which serialises to "N\x00" and
        # makes equality checks against 'N'/'S'/'E'/'W' silently fail.
        for ref_key in ("GPSLatitudeRef", "GPSLongitudeRef", "GPSAltitudeRef"):
            ref_val = metadata["exif"].get(ref_key)
            if isinstance(ref_val, (bytes, bytearray)):
                metadata["exif"][ref_key] = ref_val.rstrip(b"\x00").decode("ascii", errors="replace")
            elif isinstance(ref_val, str):
                metadata["exif"][ref_key] = ref_val.strip("\x00")

        _log_raw("piexif_resolved_gps_fields", {
            k: metadata["exif"][k]
            for k in ("GPSLatitude", "GPSLongitude", "GPSLatitudeRef",
                      "GPSLongitudeRef", "GPSAltitude", "GPSAltitudeRef",
                      "GPSTimeStamp", "GPSDateStamp", "GPSVersionID",
                      "GPSProcessingMethod")
            if k in metadata["exif"]
        }, file_path)

        _add_decimal_coordinates(metadata["exif"])
        _log_raw("computed_gps_decimal", metadata["exif"].get("GPS_Decimal"), file_path)

    except Exception as e:
        metadata["other"]["piexif_error"] = str(e)

    return metadata


def _rational_tuple_to_floats(value: Any) -> Any:
    """
    Convert piexif GPS rational tuples ((num, den), …) to a list of floats.

    piexif represents DMS values as a 3-tuple of (numerator, denominator) pairs.
    We collapse them to floats here so the rest of the pipeline deals with a
    single uniform type: [degrees_float, minutes_float, seconds_float].
    """
    if not isinstance(value, (tuple, list)):
        return value
    result = []
    for item in value:
        if isinstance(item, (tuple, list)) and len(item) == 2:
            num, den = item
            result.append(float(num) / float(den) if den != 0 else 0.0)
        else:
            try:
                result.append(float(item))
            except (TypeError, ValueError):
                result.append(item)
    return result


def _extract_video_metadata(file_path: Path) -> Dict[str, Any]:
    """Extract metadata from video files using hachoir."""
    metadata = {"video": {}, "other": {}}

    try:
        parser = hachoir.parser.createParser(str(file_path))
        if parser:
            hachoir_metadata = hachoir.metadata.extractMetadata(parser)
            if hachoir_metadata:
                for line in hachoir_metadata.exportPlaintext():
                    if ": " in line:
                        key, value = line.split(": ", 1)
                        metadata["video"][key.strip()] = value.strip()
            parser.close()
    except Exception as e:
        metadata["other"]["video_error"] = f"Failed to extract video metadata: {str(e)}"

    return metadata


def _serialize_value(value: Any) -> Any:
    """Convert metadata values to JSON-serializable format."""
    if value is None:
        return None

    if isinstance(value, np.generic):
        return _serialize_value(value.item())

    if hasattr(value, 'num') and hasattr(value, 'den'):
        try:
            return float(value.num) / float(value.den) if value.den != 0 else None
        except (TypeError, ZeroDivisionError, AttributeError):
            return str(value)
    elif hasattr(value, 'numerator') and hasattr(value, 'denominator'):
        try:
            return float(value.numerator) / float(value.denominator) if value.denominator != 0 else None
        except (TypeError, ZeroDivisionError, AttributeError):
            return str(value)
    elif isinstance(value, bytes):
        try:
            return value.decode('utf-8')
        except UnicodeDecodeError:
            return str(value)
    elif isinstance(value, tuple):
        return [_serialize_value(v) for v in value]
    elif isinstance(value, list):
        return [_serialize_value(v) for v in value]
    elif isinstance(value, dict):
        return {str(k) if isinstance(k, int) else k: _serialize_value(v) for k, v in value.items()}
    else:
        return value


def _deep_serialize(obj: Any) -> Any:
    """Recursively serialize all objects to JSON-safe types."""
    if isinstance(obj, dict):
        return {str(k) if isinstance(k, int) else k: _deep_serialize(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_deep_serialize(item) for item in obj]
    elif isinstance(obj, np.generic):
        return _serialize_value(obj)
    else:
        return _serialize_value(obj)


def _add_decimal_coordinates(exif: Dict[str, Any]) -> None:
    """
    Add decimal GPS coordinates to the exif dict if raw GPS data is present.

    Must be called BEFORE _deep_serialize so that the rational values are still
    in their native (already-floated by _rational_tuple_to_floats) form.
    """
    lat_dms = exif.get("GPSLatitude")
    lon_dms = exif.get("GPSLongitude")
    lat_ref = exif.get("GPSLatitudeRef", "")
    lon_ref = exif.get("GPSLongitudeRef", "")

    if not (lat_dms and lon_dms and lat_ref and lon_ref):
        return

    latitude = _convert_dms_to_decimal(lat_dms, lat_ref)
    longitude = _convert_dms_to_decimal(lon_dms, lon_ref)

    if latitude is not None and longitude is not None:
        exif["GPS_Decimal"] = {
            "latitude": latitude,
            "longitude": longitude,
        }


def _build_location(exif: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Construct a location object from EXIF GPS fields."""
    gps_decimal = exif.get("GPS_Decimal")
    if isinstance(gps_decimal, dict):
        lat = gps_decimal.get("latitude")
        lon = gps_decimal.get("longitude")
        if lat is not None and lon is not None:
            return {
                "latitude": lat,
                "longitude": lon,
                "altitude": exif.get("GPSAltitude"),
                "source": "exif",
            }

    # Fallback: attempt conversion from raw fields if GPS_Decimal is absent.
    lat_dms = exif.get("GPSLatitude")
    lon_dms = exif.get("GPSLongitude")
    lat_ref = exif.get("GPSLatitudeRef", "")
    lon_ref = exif.get("GPSLongitudeRef", "")

    if lat_dms and lon_dms and lat_ref and lon_ref:
        latitude = _convert_dms_to_decimal(lat_dms, lat_ref)
        longitude = _convert_dms_to_decimal(lon_dms, lon_ref)
        if latitude is not None and longitude is not None:
            return {
                "latitude": latitude,
                "longitude": longitude,
                "altitude": exif.get("GPSAltitude"),
                "source": "exif",
            }

    return None


def _extract_capture_time(exif: Dict[str, Any]) -> Optional[str]:
    """Extract the capture time from EXIF date/time fields."""
    for key in ("DateTimeOriginal", "DateTimeDigitized", "DateTime"):
        value = exif.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _convert_dms_to_decimal(dms: Any, ref: str) -> Optional[float]:
    """
    Convert degrees/minutes/seconds GPS values to decimal degrees.

    Accepts:
      - A list/tuple of three floats [deg, min, sec]  (post _rational_tuple_to_floats)
      - A dict keyed by 0/1/2 (piexif raw, if called before conversion)

    FIX: The original code used keys 1/2/3 for dict lookup; EXIF DMS dicts are
    keyed 0 (degrees), 1 (minutes), 2 (seconds).
    FIX: Strip null bytes from ref before comparing so b'N\\x00' → 'N' works.
    """
    # Normalise ref to a single ASCII character.
    if isinstance(ref, (bytes, bytearray)):
        ref = ref.rstrip(b"\x00").decode("ascii", errors="replace")
    ref = ref.strip("\x00").upper()

    # Normalise dms to a 3-element list.
    if isinstance(dms, dict):
        # Keys are 0, 1, 2 — not 1, 2, 3.
        dms = [dms.get(0), dms.get(1), dms.get(2)]

    if not isinstance(dms, (list, tuple)) or len(dms) != 3:
        return None

    try:
        degrees = float(dms[0])
        minutes = float(dms[1])
        seconds = float(dms[2])
    except (TypeError, ValueError):
        return None

    decimal = degrees + (minutes / 60.0) + (seconds / 3600.0)
    if ref in ("S", "W"):
        decimal = -decimal
    return decimal