from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import os
import shutil
from pathlib import Path

from services.metadata_extractor import extract_metadata, _serialize_value, _deep_serialize
from services.analyzer import analyze_metadata
from utils.privacy_utils import apply_privacy_protections
from config.settings import settings
from models.media import Location
from typing import Optional

router = APIRouter()

@router.post("/upload")
async def upload_media(
    file: UploadFile = File(...),
    strip_sensitive: bool = True,
):
    """
    Upload an image or video file for metadata extraction and analysis.

    If strip_sensitive=false, the endpoint returns raw metadata without privacy redaction.
    """
    # Validate file type
    allowed_extensions = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".mp4", ".avi", ".mov"}
    file_extension = Path(file.filename).suffix.lower()
    if file_extension not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {file_extension}")

    # Validate file size
    contents = await file.read()
    if len(contents) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="File too large")

    # Save the file temporarily
    temp_dir = Path(settings.UPLOAD_DIR)
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_file_path = temp_dir / file.filename

    try:
        with open(temp_file_path, "wb") as buffer:
            buffer.write(contents)

        # Extract metadata
        raw_metadata = extract_metadata(temp_file_path)

        # Analyze metadata (spoofing, reliability, platform, screenshot)
        analysis_results = analyze_metadata(raw_metadata)

        # Apply privacy protections (strip/anonymize sensitive data)
        if strip_sensitive:
            protected_metadata = apply_privacy_protections(raw_metadata, analysis_results)
        else:
            protected_metadata = raw_metadata.copy()
            protected_metadata["_privacy"] = {
                "gps_stripped": False,
                "timestamps_modified": False,
                "device_anonymized": False,
                "sensitive_fields_removed": 0,
                "note": "privacy stripping bypassed"
            }

        # Extract location data if available
        location = _extract_location(protected_metadata)

        # Prepare response
        response = {
            "filename": file.filename,
            "file_size": len(contents),
            "location": location,
            "metadata": protected_metadata,
            "analysis": analysis_results,
        }

        # Ensure all values in the response are JSON-serializable
        response = _deep_serialize(response)

        return JSONResponse(content=response)

    finally:
        # Clean up the temporary file
        if temp_file_path.exists():
            os.remove(temp_file_path)

def _extract_location(metadata: dict) -> Optional[dict]:
    """Extract location data from protected metadata."""
    exif = metadata.get("exif", {})
    
    # Check for decimal GPS coordinates (preferred)
    gps_decimal = exif.get("GPS_Decimal")
    if gps_decimal:
        lat = gps_decimal.get("latitude")
        lon = gps_decimal.get("longitude")
        if lat is not None and lon is not None:
            location_data = {
                "latitude": _deep_serialize(lat),
                "longitude": _deep_serialize(lon),
                "altitude": _deep_serialize(exif.get("GPSAltitude")),
                "source": "exif"
            }
            return location_data
    
    return None