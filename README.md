# Metadata Extractor

Enterprise-grade metadata extraction system for handling uploaded media from thousands of users in a mobile ecosystem.

## Quick Links

- **[INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md)** - Complete field-by-field reference for integrators
- **[PRIVACY_CONSIDERATIONS.md](PRIVACY_CONSIDERATIONS.md)** - Privacy implications and compliance
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System design documentation

## Features

- **Metadata Extraction**: Extract EXIF, IPTC, XMP, and file system metadata from images and videos
- **Spoofing Detection**: Identify potentially faked or manipulated metadata fields
- **Platform Detection**: Differentiate between Android and iPhone captured media
- **Screenshot Detection**: Identify screenshots vs camera captures
- **Social Platform Detection**: Detect when metadata has been stripped by social platforms
- **Privacy Protection**: GDPR/CCPA compliant data handling with configurable protections

## Requirements

- Python 3.9+
- PostgreSQL (optional, for production)
- Redis (optional, for caching)

## Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Configuration

Copy `.env.example` to `.env` and configure:

```env
DATABASE_URL=postgresql://user:password@localhost/metadata_db
REDIS_URL=redis://localhost:6379
STRIP_GPS_DATA=true
STRIP_TIMESTAMPS=false
ANONYMIZE_DEVICE_ID=true
MAX_UPLOAD_SIZE=10485760
```

## Running

### Local Development

```bash
python main.py
```

The API will be available at `http://localhost:8000`
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Using Docker

```bash
docker-compose up -d
```

## Quick Integration Example

```python
import requests

# Upload a file
with open("photo.jpg", "rb") as f:
    response = requests.post(
        "http://localhost:8000/api/v1/media/upload",
        files={"file": f}
    )

data = response.json()

# Check if it's a real camera photo (not screenshot, not spoofed)
is_authentic = (
    data["analysis"]["screenshot"]["is_screenshot"] == False and
    data["analysis"]["spoofing"]["is_spoofed"] == False and
    data["analysis"]["reliability"]["overall_score"] >= 70
)

# Get device platform
platform = data["analysis"]["platform"]["detected_platform"]  # "iphone" or "android"

# Check if metadata was stripped (uploaded via social media)
was_stripped = data["analysis"]["social_platform"]["is_stripped"]

print(f"Authentic: {is_authentic}, Platform: {platform}, Stripped: {was_stripped}")
```

## API Endpoints

### POST /api/v1/media/upload

Upload an image or video for metadata extraction.

**Request:**
- `file`: The media file (JPEG, PNG, GIF, BMP, MP4, AVI, MOV)

**Response:**
```json
{
  "filename": "photo.jpg",
  "file_size": 1024000,
  "metadata": {
    "exif": {...},
    "file_info": {...}
  },
  "analysis": {
    "spoofing": {...},
    "reliability": {...},
    "platform": {...},
    "screenshot": {...}
  }
}
```

### GET /

Health check endpoint.

## Metadata Reliability Guide

### Spoofable Fields
These fields can be easily modified/faked:
- DateTimeOriginal, DateTime
- GPS coordinates (Latitude, Longitude, Altitude)
- Make, Model
- Software
- Device serial numbers

### Reliable Fields
These are hardware-based and harder to spoof:
- ExposureTime
- FNumber
- ISOSpeedRatings
- FocalLength

### Metadata Stripping by Platform
Social platforms strip most metadata:
- **Facebook/Instagram**: Strips all EXIF except some basic info
- **WhatsApp**: Removes nearly all metadata
- **Telegram**: Strips GPS but may keep some camera info

### Android vs iPhone
- **iPhone**: Uses "Apple" in Make, has consistent timestamp formats
- **Android**: Uses manufacturer names, "Android" in Software field

### Screenshots vs Camera
Screenshots typically:
- Lack camera-specific EXIF (ExposureTime, FNumber, etc.)
- Have dimensions matching common phone screens
- May have "Screenshot" in software field

## Testing

```bash
pytest tests/
```

## Production Deployment

See `docker-compose.yml` for a production-ready setup with:
- API service
- PostgreSQL database
- Redis cache

## License

MIT
