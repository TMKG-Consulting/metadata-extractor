"""
Platform detection utilities - differentiate between Android and iOS.
"""
from typing import Dict, Any, Optional, Tuple
import re

# Common device identifiers
ANDROID_PATTERNS = [
    r"Android\s*[\d.]+",
    r"Samsung\s+Galaxy",
    r"SM-[A-Z0-9]+",
    r"Google\s+Pixel",
    r"OnePlus\s+[A-Z0-9]+",
    r"Xiaomi\s+[A-Z0-9]+",
    r"Redmi\s+[A-Z0-9]+",
    r"POCO\s+[A-Z0-9]+",
    r"OPPO\s+[A-Z0-9]+",
    r"vivo\s+[A-Z0-9]+",
    r"Realme\s+[A-Z0-9]+",
    r"Motorola\s+[A-Z0-9]+",
    r"Nokia\s+[A-Z0-9]+",
    r"Sony\s+Xperia",
    r"LGE\s+[A-Z0-9]+",
    r"HTC\s+[A-Z0-9]+",
    r"Asus\s+ZenFone",
]

IPHONE_PATTERNS = [
    r"iPhone\s+[\d]+",
    r"iPhone\s+[\d]+\s+Pro",
    r"iPhone\s+[\d]+\s+Pro\s+Max",
    r"iPhone\s+[\d]+\s+Plus",
    r"iPhone\s+[\d]+\s+mini",
    r"iPad\s+Pro",
    r"iPad\s+Air",
    r"iPad\s+mini",
    r"iPad\s+\([A-Za-z0-9\s]+\)",
    r"iOS\s+[\d.]+",
    r"CFNetwork",
    r"CoreMedia",
    r"ImageIO",
]

# Typical aspect ratios for each platform
ANDROID_ASPECT_RATIOS = [
    16/9,    # Most Android phones
    18/9,    # Older 18:9 phones
    19.5/9,  # Modern tall phones
    20/9,    # Newer tall phones
    21/9,    # Ultra-wide phones
]

IPHONE_ASPECT_RATIOS = [
    19.5/9,  # iPhone X, 11, 12 mini, 13 mini
    9/19.5,  # Alternative representation
    9/20,    # iPhone 12, 13, 14
    9/21,    # iPhone 14 Pro Max, 15 Pro Max
]

def detect_platform_from_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Detect platform from metadata with detailed analysis.

    Returns:
        Dictionary with platform detection results
    """
    result = {
        "platform": "unknown",
        "confidence": "low",
        "details": {},
    }

    exif = metadata.get("exif", {})
    other = metadata.get("other", {})

    make = exif.get("Make", "")
    model = exif.get("Model", "")
    software = exif.get("Software", "")

    # Combine for checking
    combined = f"{make} {model} {software}".lower()

    # Check Android patterns
    android_matches = []
    for pattern in ANDROID_PATTERNS:
        if re.search(pattern, combined, re.IGNORECASE):
            android_matches.append(pattern)

    # Check iPhone patterns
    iphone_matches = []
    for pattern in IPHONE_PATTERNS:
        if re.search(pattern, combined, re.IGNORECASE):
            iphone_matches.append(pattern)

    # Analyze dimensions
    dimensions = other.get("size")
    if dimensions:
        width, height = dimensions if isinstance(dimensions, tuple) else (0, 0)
        if width and height:
            aspect = width / height if height > 0 else 0

            # Check against known ratios
            for ratio in IPHONE_ASPECT_RATIOS:
                if 0.99 * ratio <= aspect <= 1.01 * ratio:
                    result["details"]["aspect_ratio"] = f"iphone_{ratio}"
                    if not iphone_matches:  # Give a small boost if no direct pattern
                        iphone_matches.append("aspect_ratio_match")

    # Determine platform
    if iphone_matches and not android_matches:
        result["platform"] = "iphone"
        result["confidence"] = "high"
        result["details"]["matches"] = iphone_matches
    elif android_matches and not iphone_matches:
        result["platform"] = "android"
        result["confidence"] = "high"
        result["details"]["matches"] = android_matches
    elif iphone_matches and android_matches:
        # Both matched - need more analysis
        if len(iphone_matches) > len(android_matches):
            result["platform"] = "iphone"
            result["confidence"] = "medium"
        else:
            result["platform"] = "android"
            result["confidence"] = "medium"
        result["details"]["matches"] = {
            "iphone": iphone_matches,
            "android": android_matches
        }

    return result

def get_device_info(metadata: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Extract device information from metadata."""
    exif = metadata.get("exif", {})
    other = metadata.get("other", {})

    device = {
        "make": exif.get("Make"),
        "model": exif.get("Model"),
        "software": exif.get("Software"),
        "os_version": None,
        "camera_info": {},
    }

    # Extract OS version from software string
    software = device.get("software", "")
    if software:
        # Try to extract version numbers
        android_match = re.search(r"Android\s+([\d.]+)", software, re.IGNORECASE)
        if android_match:
            device["os_version"] = android_match.group(1)
            device["os"] = "Android"

        ios_match = re.search(r"iOS\s+([\d.]+)", software, re.IGNORECASE)
        if ios_match:
            device["os_version"] = ios_match.group(1)
            device["os"] = "iOS"

    # Camera info
    if "LensModel" in exif:
        device["camera_info"]["lens"] = exif["LensModel"]
    if "LensMake" in exif:
        device["camera_info"]["lens_make"] = exif["LensMake"]

    return device if any(device.values()) else None