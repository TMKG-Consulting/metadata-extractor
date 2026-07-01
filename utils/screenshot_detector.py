"""
Screenshot detection utilities - differentiate between screenshots and camera captures.
"""
from typing import Dict, Any, Tuple, List
import numpy as np

# Common screenshot dimensions (width, height)
SCREENSHOT_DIMENSIONS = [
    (640, 1136),   # iPhone 5/SE
    (750, 1334),   # iPhone 6/7/8
    (1125, 2436),  # iPhone X
    (1170, 2532),  # iPhone 12/13
    (1284, 2778),  # iPhone 12/13 Pro Max
    (1179, 2556),  # iPhone 14 Pro
    (1290, 2796),  # iPhone 14 Pro Max
    (1080, 1920),  # Full HD
    (1080, 2160),  # Full HD+
    (1080, 2340),  # Various mid-range
    (1440, 2560),  # QHD
    (1440, 2960),  # Samsung Galaxy S8+
    (1440, 3200),  # Various flagships
    (720, 1280),   # HD
    (1080, 2400),  # Various
    (1220, 2700),  # Various
]

# Dimensions that are unlikely for camera captures (too uniform)
COMMON_SCREENSHOT_DPI = [72, 96, 120, 144, 160]

# Camera required fields
CAMERA_REQUIRED_EXIF = [
    "ExposureTime",
    "FNumber",
    "ISOSpeedRatings",
    "FocalLength",
]

def detect_screenshot_advanced(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Advanced screenshot detection combining multiple signals.

    Returns:
        Dictionary with screenshot detection results
    """
    result = {
        "is_screenshot": False,
        "confidence": "low",
        "signals": [],
    }

    exif = metadata.get("exif", {})
    other = metadata.get("other", {})

    # Signal 1: Missing camera EXIF data
    missing_camera = 0
    for field in CAMERA_REQUIRED_EXIF:
        if field not in exif or not exif[field]:
            missing_camera += 1

    if missing_camera >= 3:
        result["signals"].append("missing_camera_exif")

    # Signal 2: Dimensions match screenshot sizes
    if "size" in other:
        size = other["size"]
        if size in SCREENSHOT_DIMENSIONS:
            result["signals"].append("screenshot_dimensions")
        elif isinstance(size, tuple):
            width, height = size
            # Check for unusual aspect ratios
            if height > 0:
                ratio = width / height
                if ratio > 0.4 and ratio < 0.6:  # Roughly 9:16 to 9:20
                    result["signals"].append("vertical_screen_aspect")

    # Signal 3: Screenshot indicators in software
    software = str(exif.get("Software", "")).lower()
    screenshot_keywords = [
        "screenshot", "screen capture", "snipping", "screen recorder",
        "print screen", "screen shot", "capture screen"
    ]
    if any(kw in software for kw in screenshot_keywords):
        result["signals"].append("screenshot_software")

    # Signal 4: No lens information (cameras always have this)
    if "LensModel" not in exif and "LensMake" not in exif:
        result["signals"].append("no_lens_info")

    # Signal 5: Very uniform compression (typical of screenshots)
    # This would require actual image analysis with OpenCV
    # For now, we check if it's a PNG (lossless, typical of screenshots)
    file_ext = metadata.get("file_info", {}).get("extension", "").lower()
    if file_ext == ".png":
        result["signals"].append("png_format")

    # Signal 6: iOS screenshot pattern
    make = exif.get("Make", "")
    model = exif.get("Model", "")
    if "Apple" in make:
        if "iPhone" in model or "iPad" in model:
            # Check dimensions for iOS screenshots
            if "size" in other:
                size = other["size"]
                if isinstance(size, tuple):
                    w, h = size
                    # iOS screenshots often have these common sizes
                    if w in [750, 1125, 1170, 1284] and h > 2000:
                        result["signals"].append("ios_screenshot_size")

    # Calculate confidence
    signal_count = len(result["signals"])
    if signal_count >= 3:
        result["is_screenshot"] = True
        result["confidence"] = "high"
    elif signal_count == 2:
        result["is_screenshot"] = True
        result["confidence"] = "medium"
    elif signal_count == 1:
        # Single signal is not enough - might be camera with minimal EXIF
        result["confidence"] = "low"

    return result

def get_image_characteristics(file_path: str) -> Dict[str, Any]:
    """
    Get additional image characteristics for analysis.
    Uses OpenCV for basic image analysis.

    Note: This is a placeholder - full implementation would use OpenCV
    to analyze image characteristics like:
    - Compression uniformity (screenshots are uniformly compressed)
    - Presence of UI elements
    - Lens distortion patterns
    - Noise patterns (cameras have sensor noise, screenshots don't)
    """
    characteristics = {
        "requires_cv_analysis": True,
        "analysis_methods": [
            "compression_uniformity",
            "ui_element_detection",
            "noise_analysis",
            "color_space_analysis",
        ],
    }

    return characteristics