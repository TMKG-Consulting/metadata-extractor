# Architecture Documentation

## System Overview

The Metadata Extractor is a Python-based microservice for extracting, analyzing, and protecting metadata from media files in a high-volume mobile ecosystem.

## Architecture Layers

```
┌─────────────────────────────────────┐
│         API Layer (FastAPI)         │
│   /api/v1/media/upload endpoint     │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│      Service Layer                  │
│  ┌─────────────┐  ┌──────────────┐  │
│  │  Metadata   │  │   Analyzer   │  │
│  │  Extractor  │  │   Service    │  │
│  └─────────────┘  └──────────────┘  │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│       Privacy Layer                 │
│   Configurable data protection      │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│      Storage/Cache (Optional)       │
│     PostgreSQL + Redis              │
└─────────────────────────────────────┘
```

## Components

### API Layer (`api/v1/routes/media.py`)
- FastAPI router handling file uploads
- Request validation (file type, size)
- Response formatting

### Metadata Extraction (`services/metadata_extractor.py`)
- Extracts EXIF data using Pillow and piexif
- Extracts video metadata using hachoir
- Returns structured metadata dictionary

### Analysis Engine (`services/analyzer.py`)
- **Spoofing Detection**: Identifies faked/false metadata
- **Reliability Assessment**: Scores metadata trustworthiness
- **Platform Detection**: Determines Android vs iPhone
- **Screenshot Detection**: Identifies screenshots vs camera captures
- **Social Platform Detection**: Detects metadata stripping

### Privacy Utilities (`utils/privacy_utils.py`)
- GDPR/CCPA compliant data handling
- Configurable GPS/timestamp stripping
- Device identifier anonymization

## Data Flow

1. File uploaded to `/api/v1/media/upload`
2. File saved to temporary storage
3. Metadata extraction extracts raw metadata
4. Analysis service analyzes metadata
5. Privacy protections applied
6. Response returned with protected metadata + analysis

## Privacy Design

### Configurable Protections (via settings)
- `STRIP_GPS_DATA`: Remove all GPS coordinates
- `STRIP_TIMESTAMPS`: Remove datetime fields
- `ANONYMIZE_DEVICE_ID`: Redact serial numbers

### Sensitive Fields
The system automatically redacts 30+ fields containing:
- Location data (GPS)
- Timestamps
- Device identifiers
- User information

## Scalability Considerations

- **Async Processing**: Uses FastAPI for concurrent requests
- **Stateless**: No session state, scales horizontally
- **Redis Cache**: Optional caching layer
- **Database**: Optional PostgreSQL for persistence

## Security

- File type validation
- File size limits (default 10MB)
- Automatic file cleanup
- No sensitive data logged (with privacy settings enabled)

## Testing Strategy

- Unit tests for each service component
- Integration tests for API endpoints
- Mock-based testing for reproducibility

## Production Readiness

- Docker containerization
- Health check endpoint
- Configurable via environment variables
- Follows 12-factor app principles
