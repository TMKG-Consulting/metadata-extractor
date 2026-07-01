"""
Unit tests for the metadata analyzer service.
"""
import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.analyzer import (
    analyze_metadata,
    detect_spoofing,
    assess_reliability,
    detect_platform,
    detect_screenshot,
    detect_social_platform,
    SPOOFABLE_FIELDS,
    RELIABLE_FIELDS,
)

class TestAnalyzer:
    """Test cases for metadata analysis."""

    def test_analyze_metadata_complete(self):
        """Test full metadata analysis."""
        metadata = {
            "file_info": {"filename": "test.jpg", "size": 1000, "modified": 1234567890, "extension": ".jpg"},
            "exif": {
                "Make": "Apple",
                "Model": "iPhone 13",
                "Software": "15.0",
                "DateTimeOriginal": "2023:01:01 12:00:00",
                "ExposureTime": "1/120",
                "FNumber": "1.8",
            },
            "other": {"size": (1170, 2532)},
        }

        result = analyze_metadata(metadata)

        assert "spoofing" in result
        assert "reliability" in result
        assert "platform" in result
        assert "screenshot" in result

    def test_detect_spoofing_with_indicators(self):
        """Test spoofing detection with indicators."""
        metadata = {
            "exif": {
                "DateTimeOriginal": "2099:01:01 12:00:00",  # Future date - suspicious
                "Software": "Photoshop",
                "GPSLatitude": 999,  # Invalid - spoofing indicator
            },
            "file_info": {"modified": 1234567890},
        }

        result = detect_spoofing(metadata)

        assert "is_spoofed" in result
        assert "spoof_indicators" in result

    def test_assess_reliability(self):
        """Test reliability assessment."""
        metadata = {
            "exif": {
                "ExposureTime": "1/120",
                "FNumber": "1.8",
                "ISOSpeedRatings": "100",
                "DateTimeOriginal": "2023:01:01",
                "Make": "Apple",
            },
        }

        result = assess_reliability(metadata)

        assert "overall_score" in result
        assert "reliable_fields" in result
        assert "unreliable_fields" in result

    def test_detect_platform_iphone(self):
        """Test iPhone platform detection."""
        metadata = {
            "exif": {
                "Make": "Apple",
                "Model": "iPhone 13",
                "Software": "iOS 15.0",
            },
            "other": {"size": (1170, 2532)},
        }

        result = detect_platform(metadata)

        assert result["detected_platform"] == "iphone"
        assert result["confidence"] in ["medium", "high"]

    def test_detect_platform_android(self):
        """Test Android platform detection."""
        metadata = {
            "exif": {
                "Make": "Samsung",
                "Model": "Galaxy S21",
                "Software": "Android 12",
            },
        }

        result = detect_platform(metadata)

        assert result["detected_platform"] == "android"

    def test_detect_screenshot(self):
        """Test screenshot detection."""
        metadata = {
            "exif": {
                "Software": "Screenshot",
            },
            "other": {
                "size": (1170, 2532),
            },
        }

        result = detect_screenshot(metadata)

        assert "is_screenshot" in result
        assert "confidence" in result
        assert "indicators" in result

    def test_detect_social_platform(self):
        """Test social platform detection."""
        metadata = {
            "exif": {},
            "other": {},
        }

        # When EXIF is minimal, likely stripped
        result = detect_social_platform(metadata)

        assert result["is_stripped"] == True

    def test_spoofable_fields_defined(self):
        """Test that spoofable fields are defined."""
        assert len(SPOOFABLE_FIELDS) > 0
        assert "DateTimeOriginal" in SPOOFABLE_FIELDS
        assert "GPSLatitude" in SPOOFABLE_FIELDS

    def test_reliable_fields_defined(self):
        """Test that reliable fields are defined."""
        assert len(RELIABLE_FIELDS) > 0
        assert "ExposureTime" in RELIABLE_FIELDS
        assert "FNumber" in RELIABLE_FIELDS