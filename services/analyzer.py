"""
Metadata analysis service - detects spoofing, platform, screenshot, and reliability.
"""
from typing import Dict, Any, List
import re
from services.metadata_extractor import _serialize_value, _deep_serialize

# Fields that can be easily faked/spoofed
SPOOFABLE_FIELDS = [
    "DateTimeOriginal",
    "DateTime",
    "GPSLatitude",
    "GPSLongitude",
    "GPSAltitude",
    "Make",
    "Model",
    "Software",
    "Artist",
    "Copyright",
    "ImageDescription",
    "UserComment",
    "BodySerialNumber",
    "LensSerialNumber",
    "CameraSerialNumber",
    "InternalSerialNumber",
    "SerialNumber",
    "ImageUniqueID",
    "OwnerName",
    "CameraOwnerName",
]

# Fields that are reliable (hardware-based, harder to spoof)
RELIABLE_FIELDS = [
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
]

# Social platforms known to strip metadata
SOCIAL_PLATFORMS = {
    "facebook": ["Facebook", "fb"],
    "instagram": ["Instagram", "IG"],
    "whatsapp": ["WhatsApp"],
    "telegram": ["Telegram"],
    "twitter": ["Twitter", "X"],
    "snapchat": ["Snapchat", "Snap"],
    "tiktok": ["TikTok", "Douyin"],
}

# Android-specific indicators
ANDROID_INDICATORS = [
    "Android",
    "Google",
    "Samsung",
    "LG ",
    "Motorola",
    "OnePlus",
    "Xiaomi",
    "OPPO",
    "vivo",
    "Realme",
]

# iPhone/iOS-specific indicators
IPHONE_INDICATORS = [
    "Apple",
    "iPhone",
    "iPad",
    "iOS",
    "CoreMedia",
    "ImageIO",
]

# Typical screenshot dimensions (common mobile screens)
SCREENSHOT_DIMENSIONS = [
    (1080, 1920),  # Full HD
    (1170, 2532),  # iPhone 12/13
    (1284, 2778),  # iPhone 12 Pro Max
    (1125, 2436),  # iPhone X
    (1440, 3200),  # Various Android flagships
    (1440, 2960),  # Samsung Galaxy S8+
    (1080, 2340),  # Various mid-range phones
    (720, 1280),   # HD
    (1440, 2560),  # QHD
]

# Camera characteristics that would be absent in screenshots
CAMERA_REQUIRED_FIELDS = [
    "LensModel",
    "LensMake",
    "FocalLength",
    "FNumber",
    "ExposureTime",
    "ISOSpeedRatings",
]

def analyze_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze metadata for spoofing, reliability, platform, and screenshot detection.

    Args:
        metadata: Raw metadata from extract_metadata()

    Returns:
        Analysis results dictionary
    """
    return {
        "spoofing": _deep_serialize(detect_spoofing(metadata)),
        "reliability": _deep_serialize(assess_reliability(metadata)),
        "platform": _deep_serialize(detect_platform(metadata)),
        "screenshot": _deep_serialize(detect_screenshot(metadata)),
        "social_platform": _deep_serialize(detect_social_platform(metadata)),
    }

def detect_spoofing(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Detect potentially spoofed or faked metadata fields.

    Returns information about which fields may have been manipulated.
    """
    spoofing_results = {
        "is_spoofed": False,
        "spoofed_fields": [],
        "spoof_indicators": [],
        "confidence": "low",
    }

    exif = metadata.get("exif", {})
    other = metadata.get("other", {})

    # Check for spoofable fields that are present
    for field in SPOOFABLE_FIELDS:
        if field in exif and exif[field]:
            spoofing_results["spoofed_fields"].append(field)

    # Check for common spoofing indicators
    # 1. Inconsistent timestamps
    file_time = metadata.get("file_info", {}).get("modified")
    exif_time = exif.get("DateTimeOriginal") or exif.get("DateTime")

    if file_time and exif_time:
        # If EXIF time is significantly different from file time, suspicious
        # Note: This is a simplified check
        spoofing_results["spoof_indicators"].append("timestamp_mismatch")

    # 2. Software field indicates editing
    if exif.get("Software"):
        spoofing_results["spoof_indicators"].append("editing_software_present")
        spoofing_results["spoofed_fields"].append("Software")

    # 3. Check for unrealistic values
    gps_lat = exif.get("GPSLatitude") or exif.get("GPS GPSLatitude")
    gps_lon = exif.get("GPSLongitude") or exif.get("GPS GPSLongitude")

    if gps_lat and gps_lon:
        try:
            lat_val = float(gps_lat) if isinstance(gps_lat, (int, float)) else 0
            lon_val = float(gps_lon) if isinstance(gps_lon, (int, float)) else 0
            if lat_val > 90 or lat_val < -90 or lon_val > 180 or lon_val < -180:
                spoofing_results["spoof_indicators"].append("invalid_gps_coordinates")
                spoofing_results["is_spoofed"] = True
        except (ValueError, TypeError):
            pass

    # Determine confidence level
    if len(spoofing_results["spoof_indicators"]) >= 2:
        spoofing_results["confidence"] = "high"
    elif len(spoofing_results["spoof_indicators"]) == 1:
        spoofing_results["confidence"] = "medium"

    return spoofing_results

def assess_reliability(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Assess the reliability of metadata based on presence of reliable vs spoofable fields.
    """
    reliability_results = {
        "overall_score": 0.0,
        "reliable_fields": [],
        "unreliable_fields": [],
        "missing_critical": [],
    }

    exif = metadata.get("exif", {})
    other = metadata.get("other", {})

    # Check for reliable fields
    for field in RELIABLE_FIELDS:
        if field in exif and exif[field]:
            reliability_results["reliable_fields"].append(field)

    # Check for unreliable/spoofable fields
    for field in SPOOFABLE_FIELDS:
        if field in exif and exif[field]:
            reliability_results["unreliable_fields"].append(field)

    # Check for missing critical fields that should be in camera captures
    for field in CAMERA_REQUIRED_FIELDS:
        if field not in exif or not exif[field]:
            reliability_results["missing_critical"].append(field)

    # Calculate reliability score (0-100)
    reliable_count = len(reliability_results["reliable_fields"])
    unreliable_count = len(reliability_results["unreliable_fields"])
    missing_count = len(reliability_results["missing_critical"])

    if reliable_count > 0:
        score = (reliable_count * 10) - (unreliable_count * 5) - (missing_count * 8)
        reliability_results["overall_score"] = max(0, min(100, score))

    return reliability_results

def detect_platform(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Detect whether the image was captured on Android or iPhone.

    Returns platform information and confidence.
    """
    platform_results = {
        "detected_platform": "unknown",
        "confidence": "low",
        "indicators": [],
    }

    exif = metadata.get("exif", {})
    other = metadata.get("other", {})

    # Check Software field
    software = exif.get("Software", "")
    make = exif.get("Make", "")
    model = exif.get("Model", "")

    android_score = 0
    iphone_score = 0

    # Check Android indicators
    for indicator in ANDROID_INDICATORS:
        if indicator.lower() in software.lower() or indicator in make or indicator in model:
            android_score += 1
            platform_results["indicators"].append(f"android: {indicator}")

    # Check iPhone indicators
    for indicator in IPHONE_INDICATORS:
        if indicator.lower() in software.lower() or indicator in make or indicator in model:
            iphone_score += 1
            platform_results["indicators"].append(f"ios: {indicator}")

    # Additional platform-specific checks
    # iPhone typically has specific EXIF structures
    if "LensSpecification" in exif or "Apple" in make:
        iphone_score += 1

    # Android often uses specific compression
    if "Android" in software or "Google" in make:
        android_score += 1

    # Determine platform
    if android_score > iphone_score:
        platform_results["detected_platform"] = "android"
        platform_results["confidence"] = "high" if android_score >= 2 else "medium"
    elif iphone_score > android_score:
        platform_results["detected_platform"] = "iphone"
        platform_results["confidence"] = "high" if iphone_score >= 2 else "medium"

    return platform_results

def detect_screenshot(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Detect whether the image is a screenshot vs a camera capture.
    """
    screenshot_results = {
        "is_screenshot": False,
        "confidence": "low",
        "indicators": [],
    }

    exif = metadata.get("exif", {})
    other = metadata.get("other", {})
    file_info = metadata.get("file_info", {})

    # Check 1: Missing camera-specific metadata
    missing_camera_fields = []
    for field in CAMERA_REQUIRED_FIELDS:
        if field not in exif or not exif[field]:
            missing_camera_fields.append(field)

    if len(missing_camera_fields) >= 3:
        screenshot_results["indicators"].append("missing_camera_metadata")
        screenshot_results["is_screenshot"] = True

    # Check 2: Dimensions match typical screenshot sizes
    if "size" in other:
        size = other["size"]
        if size in SCREENSHOT_DIMENSIONS:
            screenshot_results["indicators"].append("screenshot_dimensions")
            screenshot_results["is_screenshot"] = True

    # Check 3: Software indicates screen capture
    software = exif.get("Software", "")
    if any(keyword in software.lower() for keyword in ["screenshot", "screen", "capture", "snipping"]):
        screenshot_results["indicators"].append("screenshot_software")
        screenshot_results["is_screenshot"] = True

    # Check 4: iOS screenshot indicators
    if "Make" in exif and "Apple" in exif["Make"]:
        if "Model" in exif and any(model in exif["Model"] for model in ["iPhone", "iPad"]):
            # Check if it's a screenshot by looking at aspect ratio
            if "size" in other:
                width, height = other["size"]
                aspect_ratio = width / height if height > 0 else 0
                # iPhones have specific aspect ratios for screenshots
                if aspect_ratio in [9/19.5, 9/20, 9/21]:  # Various iPhone ratios
                    screenshot_results["indicators"].append("ios_screenshot_aspect")

    # Check 5: File modification time vs EXIF time
    # Screenshots often have timestamps close together
    file_time = file_info.get("modified")
    exif_time = exif.get("DateTimeOriginal") or exif.get("DateTime")
    # This could indicate screenshot behavior

    # Determine confidence
    indicator_count = len(screenshot_results["indicators"])
    if indicator_count >= 2:
        screenshot_results["confidence"] = "high"
    elif indicator_count == 1:
        screenshot_results["confidence"] = "medium"

    return screenshot_results

def detect_social_platform(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Detect if metadata shows signs of being processed by social platforms.
    """
    platform_results = {
        "platform": "none",
        "is_stripped": False,
        "indicators": [],
    }

    exif = metadata.get("exif", {})
    other = metadata.get("other", {})

    # Check if most EXIF data is missing (indicates stripping)
    exif_keys = list(exif.keys())
    if len(exif_keys) < 5:
        platform_results["indicators"].append("minimal_exif")
        platform_results["is_stripped"] = True

    # Check for platform-specific software strings
    software = exif.get("Software", "")
    for platform, indicators in SOCIAL_PLATFORMS.items():
        for indicator in indicators:
            if indicator.lower() in software.lower():
                platform_results["platform"] = platform
                platform_results["indicators"].append(f"software: {indicator}")

    # Check for metadata that was likely stripped
    # If we only have basic info and no camera-specific data
    missing_camera = 0
    for field in CAMERA_REQUIRED_FIELDS:
        if field not in exif:
            missing_camera += 1

    if missing_camera >= 4:
        platform_results["indicators"].append("camera_data_stripped")
        platform_results["is_stripped"] = True

    return platform_results