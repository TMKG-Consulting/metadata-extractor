# Privacy Considerations

## Overview

This document outlines the privacy implications of metadata in media files and how the Metadata Extractor system handles sensitive information.

## What Metadata Can Be Extracted

### Location Data (HIGH SENSITIVITY)
- GPS coordinates (Latitude, Longitude, Altitude)
- GPS timestamps and processing methods
- Location names (reverse geocoded)

### Device Identifiers (HIGH SENSITIVITY)
- Camera serial numbers
- Lens serial numbers
- Body serial numbers
- Device unique IDs
- Owner names

### Temporal Data (MEDIUM SENSITIVITY)
- DateTimeOriginal (when photo was taken)
- DateTimeDigitized
- DateTime (file modification)
- GPS timestamps

### Personal Information (MEDIUM SENSITIVITY)
- Artist/Creator name
- Copyright holder
- Image descriptions
- User comments
- XP metadata (Windows-specific)

## What Can Be Faked/Spoofed

### Easily Spoofable
1. **Timestamps**: Any date/time field can be changed
2. **GPS Coordinates**: Can be set to any location
3. **Camera Make/Model**: Just text strings in EXIF
4. **Software**: Shows editing tools used
5. **Serial Numbers**: Can be forged

### Harder to Spoof (But Not Impossible)
1. **Exposure Settings**: Requires actual camera settings
2. **Lens Information**: Lens model, focal length
3. **Sensor Data**: Some hardware-based readings

## Metadata Stripping by Platform

When users upload media to social platforms, metadata is typically stripped:

| Platform | GPS | Timestamps | Camera Info | All EXIF |
|----------|-----|------------|-------------|----------|
| Facebook | ❌ | ❌ | ❌ | ❌ |
| Instagram | ❌ | ❌ | ❌ | ❌ |
| WhatsApp | ❌ | ❌ | ❌ | ❌ |
| Telegram | ❌ | Partial | Partial | ❌ |
| Twitter | ❌ | ❌ | ❌ | ❌ |

**Implication**: If you receive media with no metadata, it likely passed through a social platform.

## Android vs iPhone Differences

### iPhone Indicators
- Make: "Apple"
- Software: "iOS X.X" or "iPhone OS"
- Often has Apple-specific tags (LensSpecification)
- Consistent timestamp format

### Android Indicators
- Make: "Samsung", "Google", "OnePlus", etc.
- Software: "Android X.X"
- May have manufacturer-specific tags
- More varied metadata structures

## Screenshots vs Camera Captures

### Screenshot Characteristics
- No camera EXIF (ExposureTime, FNumber, etc.)
- Dimensions match common screen sizes
- May have "Screenshot" in software field
- No lens information
- Often PNG format

### Camera Capture Characteristics
- Camera-specific EXIF present
- Lens model information
- Hardware settings recorded
- May have location data
- Usually JPEG

## Privacy Implications

### For Platform Operators
1. **Data Minimization**: Only collect necessary metadata
2. **User Consent**: Inform users about metadata collection
3. **Storage Security**: Protect stored metadata
4. **Access Controls**: Limit who can view metadata
5. **Retention Policies**: Delete old metadata

### For End Users
1. **Before Sharing**: Remove metadata from sensitive photos
2. **Use AirDrop/Local Sharing**: Preserves less metadata
3. **Screenshots**: Safer for sharing (less metadata)
4. **Social Platforms**: Assume ALL metadata will be stripped

## How This System Handles Privacy

### Configurable Protections
```python
STRIP_GPS_DATA = True      # Remove all GPS coordinates
STRIP_TIMESTAMPS = False   # Keep timestamps (configurable)
ANONYMIZE_DEVICE_ID = True # Redact serial numbers
```

### Automatic Redaction
The system automatically redacts:
- All GPS-related fields
- Device serial numbers
- Owner names
- User comments
- Maker notes

### Audit Trail
The system logs privacy actions:
- Which fields were stripped
- What was anonymized
- Compliance status

## Recommendations

### For High-Privacy Applications
1. Enable all privacy protections
2. Strip all EXIF except necessary technical fields
3. Implement data retention policies
4. Provide user-facing metadata controls

### For Analysis Applications
1. Keep technical fields (exposure, aperture)
2. Strip personal identifiers
3. Anonymize device serial numbers
4. Consider keeping timestamps for analytics

### For Forensic Applications
1. Disable privacy stripping
2. Extract all available metadata
3. Maintain chain of custody
4. Document all findings

## Compliance Notes

### GDPR
- Lawful basis required for processing
- Data minimization principle
- Right to erasure consideration
- Privacy by design implemented

### CCPA
- Consumer rights awareness
- Opt-out mechanisms
- Data deletion capabilities

## Best Practices

1. **Default to Privacy**: Strip sensitive data unless explicitly needed
2. **User Control**: Allow users to control metadata retention
3. **Transparent**: Inform users what metadata is collected
4. **Secure**: Protect metadata with same rigor as content
5. **Audit**: Regular privacy reviews and updates

---

## Integrator Checklist

### Before Processing User Uploads

- [ ] Decide whether to strip GPS data (`STRIP_GPS_DATA`)
- [ ] Decide whether to strip timestamps (`STRIP_TIMESTAMPS`)
- [ ] Decide whether to anonymize device IDs (`ANONYMIZE_DEVICE_ID`)
- [ ] Set file size limits appropriate for your use case

### When Handling Metadata in Your App

- [ ] Never log GPS coordinates without explicit user consent
- [ ] Don't display device serial numbers to other users
- [ ] Consider timestamp as personal data under GDPR
- [ ] Implement data retention policies (delete old metadata)
- [ ] Provide users with ability to delete their metadata

### For Compliance

- [ ] Document what metadata you collect
- [ ] Provide privacy policy disclosure
- [ ] Implement data subject access requests (DSAR)
- [ ] Set up data deletion/erasure workflows
- [ ] Conduct privacy impact assessments for new features

---

## Decision Matrix: When to Use What

| Use Case | Keep GPS | Keep Timestamps | Keep Device ID | Notes |
|----------|----------|-----------------|----------------|-------|
| Photo forensics | Yes | Yes | Yes | Preserve all data |
| Content moderation | No | Yes | Yes | Need timestamp for reports |
| User analytics | No | Yes | No | Anonymize devices |
| Location verification | Yes | Maybe | Maybe | Depends on trust level |
| Social sharing | No | No | No | Strip everything |
| Print services | No | Yes | No | Need timestamp for quality |

---

## Field Sensitivity Reference

| Field Category | Sensitivity | Default Action | Can Be Used For |
|----------------|-------------|----------------|-----------------|
| GPS Coordinates | HIGH | Strip | Only with explicit consent |
| Serial Numbers | HIGH | Anonymize | Never display to users |
| Timestamps | MEDIUM | Keep | Analytics, forensics |
| Camera Settings | LOW | Keep | Technical analysis |
| Image Dimensions | LOW | Keep | UI rendering |
| Device Make/Model | LOW | Keep | Analytics, support |
