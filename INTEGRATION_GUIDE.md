# Integration Guide

This guide explains every field returned by the Metadata Extractor API, what it means, and how to use it in your application.

## Quick Start

### Making Your First Request

```bash
curl -X POST "http://localhost:8000/api/v1/media/upload" \
  -F "file=@photo.jpg"
```

### Response Structure

Every response contains four main sections:

```json
{
  "filename": "photo.jpg",
  "file_size": 1024000,
  "metadata": { ... },
  "analysis": { ... }
}
```

---

## Metadata Section

The `metadata` section contains all extracted information from the file.

### File Info (`metadata.file_info`)

| Field | Type | Description |
|-------|------|-------------|
| `filename` | string | Original filename as uploaded |
| `size` | integer | File size in bytes |
| `extension` | string | File extension (e.g., ".jpg", ".mp4") |
| `modified` | float | Unix timestamp of file modification (null if STRIP_TIMESTAMPS=true) |

**Example:**
```json
{
  "filename": "vacation_photo.jpg",
  "size": 2456789,
  "extension": ".jpg",
  "modified": 1699876543.0
}
```

**Usage Notes:**
- Use `size` to validate file size limits
- Use `extension` to determine file type without trusting the content-type header
- `modified` comes from filesystem, not EXIF - it may not match when the photo was actually taken

---

### EXIF Data (`metadata.exif`)

This contains all EXIF metadata extracted from the image. Below is every field with its meaning:

#### Location Fields (GPS)

| Field | Type | Description | Privacy |
|-------|------|-------------|---------|
| `GPSLatitude` | string/float | Latitude coordinate | SENSITIVE |
| `GPSLongitude` | string/float | Longitude coordinate | SENSITIVE |
| `GPSAltitude` | float | Altitude in meters | SENSITIVE |
| `GPSLatitudeRef` | string | "N" or "S" (North/South) | SENSITIVE |
| `GPSLongitudeRef` | string | "E" or "W" (East/West) | SENSITIVE |
| `GPSAltitudeRef` | string | "0" = above sea level, "1" = below | SENSITIVE |
| `GPSDateStamp` | string | GPS date (format: "YYYY:MM:DD") | SENSITIVE |
| `GPSTimeStamp` | string | GPS time (format: "HH:MM:SS") | SENSITIVE |

**Example:**
```json
{
  "GPSLatitude": 37.7749,
  "GPSLongitude": -122.4194,
  "GPSAltitude": 10.5
}
```

**Usage Notes:**
- If all GPS fields are missing, the user may have stripped location data or uploaded via social media
- GPS coordinates can be faked - don't trust them for critical location verification
- Combine with `analysis.spoofing` to check reliability

---

#### Date/Time Fields

| Field | Type | Description | Privacy |
|-------|------|-------------|---------|
| `DateTimeOriginal` | string | When photo was actually taken (format: "YYYY:MM:DD HH:MM:SS") | SENSITIVE |
| `DateTime` | string | File modification time in EXIF | SENSITIVE |
| `DateTimeDigitized` | string | When photo was digitized | SENSITIVE |

**Example:**
```json
{
  "DateTimeOriginal": "2023:10:15 14:30:00"
}
```

**Usage Notes:**
- `DateTimeOriginal` is the most accurate timestamp - it's when the photo was taken
- These can be easily spoofed - check `analysis.spoofing` for anomalies
- In screenshots, these fields are typically absent

---

#### Device Information

| Field | Type | Description | Privacy |
|-------|------|-------------|---------|
| `Make` | string | Camera/phone manufacturer | SAFE |
| `Model` | string | Camera/phone model | SAFE |
| `Software` | string | Software used to process image | SAFE |
| `LensModel` | string | Lens model (cameras only) | SAFE |
| `LensMake` | string | Lens manufacturer | SAFE |
| `BodySerialNumber` | string | Camera body serial number | SENSITIVE |
| `LensSerialNumber` | string | Lens serial number | SENSITIVE |
| `CameraSerialNumber` | string | Camera serial number | SENSITIVE |
| `ImageUniqueID` | string | Unique identifier for image | SENSITIVE |

**Example:**
```json
{
  "Make": "Apple",
  "Model": "iPhone 14 Pro",
  "Software": "iOS 16.6.1",
  "BodySerialNumber": "[REDACTED]"
}
```

**Usage Notes:**
- Use `Make` + `Model` to detect platform (Apple = iPhone, Samsung/Google/etc = Android)
- `Software` often reveals if image was edited (e.g., "Photoshop", "Snapseed")
- Serial numbers are redacted when `ANONYMIZE_DEVICE_ID=true`

---

#### Camera Settings (Technical)

| Field | Type | Description | Reliability |
|-------|------|-------------|-------------|
| `ExposureTime` | string | Shutter speed (e.g., "1/120") | HIGH |
| `FNumber` | string | Aperture (e.g., "1.8") | HIGH |
| `ISOSpeedRatings` | string/int | ISO sensitivity | HIGH |
| `FocalLength` | string | Focal length (e.g., "4.25mm") | HIGH |
| `FocalLengthIn35mmFilm` | int | Equivalent 35mm focal length | HIGH |
| `MeteringMode` | string | Metering mode used | HIGH |
| `Flash` | string | Flash fired (Yes/No) | HIGH |
| `WhiteBalance` | string | White balance setting | HIGH |
| `ExposureProgram` | string | Exposure program (Manual, Auto, etc.) | HIGH |
| `ExposureMode` | string | Exposure mode | HIGH |
| `SceneCaptureType` | string | Scene type (Standard, Portrait, Landscape) | HIGH |
| `DigitalZoomRatio` | float | Digital zoom used | MEDIUM |
| `Contrast` | string | Contrast setting | MEDIUM |
| `Saturation` | string | Saturation setting | MEDIUM |
| `Sharpness` | string | Sharpness setting | MEDIUM |

**Example:**
```json
{
  "ExposureTime": "1/120",
  "FNumber": "1.8",
  "ISOSpeedRatings": "100",
  "FocalLength": "4.25mm"
}
```

**Usage Notes:**
- These fields are hardware-based and difficult to spoof - they're RELIABLE
- If these are missing but the image has EXIF, it may indicate a screenshot
- High reliability score in `analysis.reliability` confirms these are present

---

#### Image Properties

| Field | Type | Description |
|-------|------|-------------|
| `ImageWidth` | int | Image width in pixels |
| `ImageLength` | int | Image height in pixels |
| `BitsPerSample` | int | Bits per color channel |
| `Compression` | int | Compression method |
| `PhotometricInterpretation` | int | Color space |
| `XResolution` | int | X resolution (dpi) |
| `YResolution` | int | Y resolution (dpi) |
| `ResolutionUnit` | int | Resolution unit (1=none, 2=inch, 3=cm) |
| `ColorSpace` | int | Color space |

**Example:**
```json
{
  "ImageWidth": 4032,
  "ImageLength": 3024,
  "XResolution": 72,
  "YResolution": 72
}
```

---

### Video Metadata (`metadata.video`)

For video files, metadata is extracted differently using hachoir:

| Field | Type | Description |
|-------|------|-------------|
| `width` | int | Video width in pixels |
| `height` | int | Video height in pixels |
| `duration` | float | Duration in seconds |
| `bit_rate` | int | Bit rate in bps |
| `codec` | string | Video codec |
| `frame_rate` | float | Frames per second |
| `audio_codec` | string | Audio codec (if present) |

**Example:**
```json
{
  "width": 1920,
  "height": 1080,
  "duration": 30.5,
  "bit_rate": 5000000,
  "codec": "AVC"
}
```

---

## Analysis Section

The `analysis` section provides interpreted results about the metadata.

### Spoofing Detection (`analysis.spoofing`)

| Field | Type | Description |
|-------|------|-------------|
| `is_spoofed` | boolean | True if metadata appears manipulated |
| `spoofed_fields` | array | List of fields that can be spoofed |
| `spoof_indicators` | array | Specific indicators found |
| `confidence` | string | "low", "medium", or "high" |

**Example:**
```json
{
  "is_spoofed": false,
  "spoofed_fields": ["DateTimeOriginal", "Make", "Model"],
  "spoof_indicators": ["editing_software_present"],
  "confidence": "medium"
}
```

**How to Use:**
- `is_spoofed = true`: Metadata may be fake - don't use for verification
- `confidence = "high"`: Strong indicator, act on it
- `confidence = "low"`: May be legitimate, no strong evidence either way
- `spoof_indicators` tells you what raised the alarm:
  - `timestamp_mismatch`: EXIF time differs significantly from file time
  - `editing_software_present`: Software field shows editing tool
  - `invalid_gps_coordinates`: GPS values out of valid range

---

### Reliability Assessment (`analysis.reliability`)

| Field | Type | Description |
|-------|------|-------------|
| `overall_score` | float | Reliability score 0-100 |
| `reliable_fields` | array | Hardware-based fields present |
| `unreliable_fields` | array | Spoofable fields present |
| `missing_critical` | array | Expected camera fields that are missing |

**Example:**
```json
{
  "overall_score": 75.0,
  "reliable_fields": ["ExposureTime", "FNumber", "ISOSpeedRatings"],
  "unreliable_fields": ["DateTimeOriginal", "GPSLatitude"],
  "missing_critical": []
}
```

**How to Use:**
- `overall_score >= 70`: Metadata is likely trustworthy
- `overall_score 40-69`: Partially trustworthy, use with caution
- `overall_score < 40`: Likely manipulated or stripped
- High `missing_critical` count suggests screenshot or stripped metadata

---

### Platform Detection (`analysis.platform`)

| Field | Type | Description |
|-------|------|-------------|
| `detected_platform` | string | "android", "iphone", or "unknown" |
| `confidence` | string | "low", "medium", or "high" |
| `indicators` | array | What detected the platform |

**Example:**
```json
{
  "detected_platform": "iphone",
  "confidence": "high",
  "indicators": ["ios: Apple", "ios: iPhone 14 Pro"]
}
```

**How to Use:**
- Use `detected_platform` to filter/modify content based on device type
- Android images may have more varied EXIF structures
- iPhone has consistent EXIF format
- `confidence = "unknown"`: Not enough info to determine

---

### Screenshot Detection (`analysis.screenshot`)

| Field | Type | Description |
|-------|------|-------------|
| `is_screenshot` | boolean | True if appears to be a screenshot |
| `confidence` | string | "low", "medium", or "high" |
| `indicators` | array | Why it was classified this way |

**Example:**
```json
{
  "is_screenshot": true,
  "confidence": "high",
  "indicators": ["missing_camera_exif", "screenshot_dimensions", "no_lens_info"]
}
```

**How to Use:**
- `is_screenshot = true`: Original camera metadata was lost
- `confidence = "high"`: Multiple indicators present
- `indicators` tells you what was found:
  - `missing_camera_exif`: No ExposureTime, FNumber, etc.
  - `screenshot_dimensions`: Dimensions match known phone screens
  - `screenshot_software`: Software field mentions "screenshot"
  - `no_lens_info`: No lens model/make present

---

### Social Platform Detection (`analysis.social_platform`)

| Field | Type | Description |
|-------|------|-------------|
| `platform` | string | Detected platform ("facebook", "instagram", etc.) or "none" |
| `is_stripped` | boolean | True if metadata was significantly stripped |
| `indicators` | array | What indicated stripping |

**Example:**
```json
{
  "platform": "instagram",
  "is_stripped": true,
  "indicators": ["minimal_exif", "camera_data_stripped"]
}
```

**How to Use:**
- Use `is_stripped = true` to detect if user uploaded via social media
- `platform` may show which platform (not always reliable)
- If stripped, you cannot get: original GPS, exact timestamp, device info

---

## Privacy Section

When privacy protections are enabled, you'll see `_privacy` in metadata:

| Field | Type | Description |
|-------|------|-------------|
| `gps_stripped` | boolean | Whether GPS was removed |
| `timestamps_modified` | boolean | Whether timestamps were removed |
| `device_anonymized` | boolean | Whether device IDs were redacted |
| `sensitive_fields_removed` | int | Count of sensitive fields removed |

**Example:**
```json
{
  "_privacy": {
    "gps_stripped": true,
    "timestamps_modified": false,
    "device_anonymized": true,
    "sensitive_fields_removed": 8
  }
}
```

---

## Complete Response Example

```json
{
  "filename": "photo.jpg",
  "file_size": 2048000,
  "metadata": {
    "file_info": {
      "filename": "photo.jpg",
      "size": 2048000,
      "extension": ".jpg",
      "modified": 1699876543.0
    },
    "exif": {
      "Make": "Apple",
      "Model": "iPhone 14 Pro",
      "Software": "iOS 16.6.1",
      "DateTimeOriginal": "2023:10:15 14:30:00",
      "ExposureTime": "1/120",
      "FNumber": "1.8",
      "ISOSpeedRatings": "100",
      "FocalLength": "4.25mm",
      "ImageWidth": 4032,
      "ImageLength": 3024
    },
    "other": {
      "format": "JPEG",
      "mode": "RGB",
      "size": [4032, 3024]
    },
    "_privacy": {
      "gps_stripped": true,
      "timestamps_modified": false,
      "device_anonymized": true,
      "sensitive_fields_removed": 3
    }
  },
  "analysis": {
    "spoofing": {
      "is_spoofed": false,
      "spoofed_fields": ["DateTimeOriginal"],
      "spoof_indicators": [],
      "confidence": "low"
    },
    "reliability": {
      "overall_score": 85.0,
      "reliable_fields": ["ExposureTime", "FNumber", "ISOSpeedRatings", "FocalLength"],
      "unreliable_fields": ["DateTimeOriginal"],
      "missing_critical": []
    },
    "platform": {
      "detected_platform": "iphone",
      "confidence": "high",
      "indicators": ["ios: Apple", "ios: iPhone 14 Pro"]
    },
    "screenshot": {
      "is_screenshot": false,
      "confidence": "high",
      "indicators": []
    },
    "social_platform": {
      "platform": "none",
      "is_stripped": false,
      "indicators": []
    }
  }
}
```

---

## Common Integration Patterns

### Pattern 1: Verify Photo Authenticity

```python
def is_photo_authentic(analysis):
    # Check reliability score
    if analysis["reliability"]["overall_score"] < 50:
        return False
    
    # Check for spoofing
    if analysis["spoofing"]["is_spoofed"]:
        return False
    
    # Verify it's a real camera capture
    if analysis["screenshot"]["is_screenshot"]:
        return False
    
    return True
```

### Pattern 2: Get Location (Safely)

```python
def get_location_if_safe(metadata, analysis):
    # Don't return GPS if stripped or spoofed
    if analysis["social_platform"]["is_stripped"]:
        return None
    
    if analysis["spoofing"]["is_spoofed"]:
        return None
    
    # Check for spoofing indicators on GPS
    gps_indicators = analysis["spoofing"]["spoof_indicators"]
    if "invalid_gps_coordinates" in gps_indicators:
        return None
    
    return metadata.get("exif", {}).get("GPSLatitude")
```

### Pattern 3: Detect Device Type

```python
def get_device_type(analysis):
    platform = analysis["platform"]["detected_platform"]
    
    if platform == "iphone":
        return "iOS"
    elif platform == "android":
        return "Android"
    else:
        return "Unknown"
```

### Pattern 4: Handle Social Uploads

```python
def handle_upload(metadata, analysis):
    if analysis["social_platform"]["is_stripped"]:
        # User uploaded via social media
        # Limited metadata available
        return {
            "has_location": False,
            "has_timestamp": False,
            "has_device_info": False,
            "is_screenshot": analysis["screenshot"]["is_screenshot"]
        }
    else:
        # Direct upload - full metadata available
        return {
            "has_location": "GPSLatitude" in metadata.get("exif", {}),
            "has_timestamp": "DateTimeOriginal" in metadata.get("exif", {}),
            "has_device_info": "Model" in metadata.get("exif", {}),
            "is_screenshot": analysis["screenshot"]["is_screenshot"]
        }
```

---

## Error Handling

| Status Code | Meaning | Cause |
|-------------|---------|-------|
| 400 | Bad Request | Invalid file type |
| 413 | Payload Too Large | File exceeds MAX_UPLOAD_SIZE |
| 422 | Validation Error | Missing required fields |
| 500 | Server Error | Internal processing error |

**Example Error Response:**
```json
{
  "detail": "Unsupported file type: .exe"
}
```

---

## Configuration Options

Set these as environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `STRIP_GPS_DATA` | true | Remove all GPS coordinates |
| `STRIP_TIMESTAMPS` | false | Remove date/time fields |
| `ANONYMIZE_DEVICE_ID` | true | Redact serial numbers |
| `MAX_UPLOAD_SIZE` | 10485760 | Max file size in bytes (10MB) |
| `DATABASE_URL` | - | PostgreSQL connection string |
| `REDIS_URL` | - | Redis connection string |

---

## Testing Your Integration

Use the included test images or create your own:

```python
# Test 1: Real camera photo (high reliability)
# - Has all camera EXIF
# - Has GPS if taken with location on
# - Platform detection should work

# Test 2: Screenshot
# - Missing camera EXIF
# - No lens info
# - Dimensions match phone screens

# Test 3: Edited image
# - Software field shows editing tool
# - May have timestamp mismatch
# - Reliability score may be lower

# Test 4: Social media upload
# - Most EXIF stripped
# - is_stripped = true
# - Limited analysis possible
```