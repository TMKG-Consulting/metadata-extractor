"""
Privacy utilities for handling sensitive metadata.
Implements GDPR/CCPA compliance and configurable data protection.
"""
from typing import Dict, Any, List
from config.settings import settings
from services.metadata_extractor import _serialize_value, _deep_serialize

# Sensitive metadata fields that may contain personal data
SENSITIVE_FIELDS = [
    "GPSLatitude",
    "GPSLongitude",
    "GPSAltitude",
    "GPSLatitudeRef",
    "GPSLongitudeRef",
    "GPSAltitudeRef",
    "GPSDateStamp",
    "GPSTimeStamp",
    "GPSProcessingMethod",
    "GPSAreaInformation",
    "DateTimeOriginal",
    "DateTime",
    "DateTimeDigitized",
    "Artist",
    "Copyright",
    "ImageDescription",
    "UserComment",
    "XPComment",
    "XPAuthor",
    "BodySerialNumber",
    "LensSerialNumber",
    "CameraSerialNumber",
    "InternalSerialNumber",
    "SerialNumber",
    "ImageUniqueID",
    "OwnerName",
    "CameraOwnerName",
    "MakerNote",
    "UserNote",
    "XPKeywords",
    "XPSubject",
    "XPTitle",
    "ApplicationRecordVersion",
    "OwnerName",
    "SerialNumber",
    "CameraLabel",
    "ImageIdentifier",
    "OriginalImageID",
    "OriginalDocumentID",
    "History",
]

# Fields that can be safely retained
SAFE_FIELDS = [
    "ExposureTime",
    "FNumber",
    "ISOSpeedRatings",
    "FocalLength",
    "FocalLengthIn35mmFilm",
    "MeteringMode",
    "Flash",
    "WhiteBalance",
    "ExposureProgram",
    "ExposureMode",
    "SceneCaptureType",
    "DigitalZoomRatio",
    "Contrast",
    "Saturation",
    "Sharpness",
    "ImageWidth",
    "ImageLength",
    "BitsPerSample",
    "Compression",
    "PhotometricInterpretation",
    "SamplesPerPixel",
    "XResolution",
    "YResolution",
    "ResolutionUnit",
    "ColorSpace",
    "PixelXDimension",
    "PixelYDimension",
    "Format",
    "mode",
    "size",
]

def apply_privacy_protections(
    metadata: Dict[str, Any],
    analysis: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Apply privacy protections to metadata based on settings and analysis.

    Args:
        metadata: Raw metadata dictionary
        analysis: Analysis results from analyze_metadata()

    Returns:
        Protected metadata with sensitive data stripped or anonymized
    """
    protected = {}

    for key, value in metadata.items():
        if key == "file_info":
            # Handle file info
            protected[key] = _protect_file_info(value)
        elif key == "exif":
            # Handle EXIF data
            protected[key] = _protect_exif(value)
        elif key in ["iptc", "xmp", "video"]:
            # Handle other metadata sections
            protected[key] = _protect_generic(value)
        elif key == "location":
            protected[key] = None if settings.STRIP_GPS_DATA else value
        elif key == "capture_time":
            protected[key] = None if settings.STRIP_TIMESTAMPS else value
        else:
            # Pass through other sections
            protected[key] = value

    # Add privacy audit information
    protected["_privacy"] = {
        "gps_stripped": settings.STRIP_GPS_DATA,
        "timestamps_modified": settings.STRIP_TIMESTAMPS,
        "device_anonymized": settings.ANONYMIZE_DEVICE_ID,
        "sensitive_fields_removed": _count_sensitive_removed(metadata, protected),
    }

    return protected

def _protect_file_info(file_info: Dict[str, Any]) -> Dict[str, Any]:
    """Protect file information - keep safe fields only."""
    return {
        "filename": file_info.get("filename"),
        "size": file_info.get("size"),
        "extension": file_info.get("extension"),
        # Timestamps can be stripped based on settings
        "modified": file_info.get("modified") if not settings.STRIP_TIMESTAMPS else None,
    }

def _protect_exif(exif: Dict[str, Any]) -> Dict[str, Any]:
    """Protect EXIF data - strip/anonymize sensitive fields."""
    protected = {}

    for key, value in exif.items():
        # Skip GPS data if setting is enabled
        if settings.STRIP_GPS_DATA and key.startswith("GPS"):
            continue

        # Anonymize device identifiers
        if settings.ANONYMIZE_DEVICE_ID:
            if key in ["BodySerialNumber", "LensSerialNumber", "CameraSerialNumber",
                       "InternalSerialNumber", "SerialNumber", "OwnerName", "CameraOwnerName",
                       "ImageUniqueID", "Artist", "Copyright", "MakerNote"]:
                protected[key] = "[REDACTED]"
                continue

        # Strip timestamps if setting is enabled
        # if settings.STRIP_TIMESTAMPS:
        #     if key in ["DateTimeOriginal", "DateTime", "DateTimeDigitized", "GPSDateStamp"]:
        #         continue

        # Check if field is in sensitive list
        if key in SENSITIVE_FIELDS and key not in SAFE_FIELDS:
            # Remove or redact based on sensitivity level
            protected[key] = "[REDACTED]"
        else:
            # Deep serialize value to ensure it's JSON-compatible
            protected[key] = _deep_serialize(value)

    return protected

def _protect_generic(data: Dict[str, Any]) -> Dict[str, Any]:
    """Generic protection for IPTC, XMP, video metadata."""
    protected = {}

    for key, value in data.items():
        # Check if this is a sensitive field
        if key in SENSITIVE_FIELDS:
            protected[key] = "[REDACTED]"
        else:
            # Deep serialize value to ensure it's JSON-compatible
            protected[key] = _deep_serialize(value)

    return protected

def _count_sensitive_removed(original: Dict[str, Any], protected: Dict[str, Any]) -> int:
    """Count how many sensitive fields were removed."""
    count = 0

    for key in SENSITIVE_FIELDS:
        # Check in EXIF
        if key in original.get("exif", {}):
            if key not in protected.get("exif", {}) or protected["exif"].get(key) == "[REDACTED]":
                count += 1

    return count

def is_sensitive_field(field_name: str) -> bool:
    """Check if a field is considered sensitive."""
    return field_name in SENSITIVE_FIELDS

def redact_value(field_name: str, value: Any) -> Any:
    """
    Redact a value based on field sensitivity.

    Args:
        field_name: Name of the metadata field
        value: Current value

    Returns:
        Redacted value or original based on sensitivity
    """
    if is_sensitive_field(field_name):
        return "[REDACTED]"
    return value

def get_data_retention_policy() -> Dict[str, Any]:
    """
    Returns the current data retention policy configuration.
    Useful for compliance documentation.
    """
    return {
        "gps_data": "stripped" if settings.STRIP_GPS_DATA else "retained",
        "timestamps": "stripped" if settings.STRIP_TIMESTAMPS else "retained",
        "device_identifiers": "anonymized" if settings.ANONYMIZE_DEVICE_ID else "retained",
        "compliance_mode": "GDPR/CCPA compliant",
    }