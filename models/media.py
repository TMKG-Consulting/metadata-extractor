"""
Data models for the Metadata Extractor API.
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

class FileInfo(BaseModel):
    """Basic file information."""
    filename: str
    size: int
    extension: str
    modified: Optional[float] = None

class MetadataExif(BaseModel):
    """EXIF metadata model."""
    pass  # Dynamic fields

class Location(BaseModel):
    """GPS location data."""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    altitude: Optional[float] = None
    source: str = "exif"

class MetadataResponse(BaseModel):
    """Response model for metadata extraction."""
    filename: str
    file_size: int
    location: Optional[Location] = None
    metadata: Dict[str, Any]
    analysis: Dict[str, Any]

class AnalysisSpoofing(BaseModel):
    """Spoofing detection results."""
    is_spoofed: bool
    spoofed_fields: List[str] = []
    spoof_indicators: List[str] = []
    confidence: str = "low"

class AnalysisReliability(BaseModel):
    """Metadata reliability assessment."""
    overall_score: float
    reliable_fields: List[str] = []
    unreliable_fields: List[str] = []
    missing_critical: List[str] = []

class AnalysisPlatform(BaseModel):
    """Platform detection results."""
    detected_platform: str
    confidence: str
    indicators: List[str] = []

class AnalysisScreenshot(BaseModel):
    """Screenshot detection results."""
    is_screenshot: bool
    confidence: str
    indicators: List[str] = []

class AnalysisSocial(BaseModel):
    """Social platform detection results."""
    platform: str
    is_stripped: bool
    indicators: List[str] = []

class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    timestamp: datetime
    version: str = "1.0.0"