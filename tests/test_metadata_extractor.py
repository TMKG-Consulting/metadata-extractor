"""
Unit tests for the metadata extraction service.
"""
import pytest
from pathlib import Path
import tempfile
import os
from PIL import Image
import piexif

# Import the module we're testing
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.metadata_extractor import extract_metadata, _serialize_value

class TestMetadataExtractor:
    """Test cases for metadata extraction."""

    def test_extract_metadata_from_image(self, tmp_path):
        """Test extracting metadata from a simple image."""
        # Create a test image
        img_path = tmp_path / "test_image.jpg"
        img = Image.new('RGB', (100, 100), color='red')
        img.save(img_path)

        # Extract metadata
        metadata = extract_metadata(img_path)

        # Verify basic structure
        assert "file_info" in metadata
        assert "exif" in metadata
        assert metadata["file_info"]["filename"] == "test_image.jpg"
        assert metadata["file_info"]["extension"] == ".jpg"

    def test_extract_metadata_with_exif(self, tmp_path):
        """Test extracting EXIF data from an image."""
        # Create a test image with EXIF data
        img_path = tmp_path / "test_exif.jpg"

        # Create image with some EXIF-like data
        img = Image.new('RGB', (100, 100), color='blue')
        exif_dict = {
            "0th": {
                271: "TestMake",  # Make
                272: "TestModel",  # Model
            },
            "Exif": {
                36867: "2023:01:01 12:00:00",  # DateTimeOriginal
            }
        }
        img.save(img_path, exif=exif_dict)

        # Extract metadata
        metadata = extract_metadata(img_path)

        # Check that we got some metadata back
        assert "exif" in metadata

    def test_extract_metadata_with_gps(self, tmp_path):
        """Test extracting GPS coordinates from an image."""
        img_path = tmp_path / "test_gps.jpg"
        img = Image.new('RGB', (100, 100), color='green')

        gps_ifd = {
            piexif.GPSIFD.GPSLatitudeRef: 'N',
            piexif.GPSIFD.GPSLatitude: [(37, 1), (46, 1), (30, 1)],
            piexif.GPSIFD.GPSLongitudeRef: 'W',
            piexif.GPSIFD.GPSLongitude: [(122, 1), (25, 1), (0, 1)],
        }
        exif_dict = {"GPS": gps_ifd}
        exif_bytes = piexif.dump(exif_dict)
        img.save(img_path, exif=exif_bytes)

        metadata = extract_metadata(img_path)

        assert metadata["exif"]["GPSLatitude"] == [37, 46, 30]
        assert metadata["exif"]["GPSLongitude"] == [122, 25, 0]
        assert metadata["exif"]["GPSLatitudeRef"] == 'N'
        assert metadata["exif"]["GPSLongitudeRef"] == 'W'
        assert metadata["exif"]["GPS_Decimal"]["latitude"] == 37.775
        assert metadata["exif"]["GPS_Decimal"]["longitude"] == -122.41666666666667

    def test_serialize_value_bytes(self):
        """Test serializing bytes to string."""
        result = _serialize_value(b"test")
        assert result == "test"

    def test_serialize_value_fraction(self):
        """Test serializing fraction values."""
        # Create a mock fraction
        class MockFraction:
            def __init__(self, num, den):
                self.num = num
                self.den = den

        frac = MockFraction(1, 100)
        result = _serialize_value(frac)
        assert result == 0.01

    def test_serialize_value_tuple(self):
        """Test serializing tuple values."""
        result = _serialize_value((1, 2, 3))
        assert result == [1, 2, 3]

    def test_extract_metadata_nonexistent_file(self):
        """Test handling of nonexistent files."""
        with pytest.raises(Exception):
            extract_metadata(Path("/nonexistent/file.jpg"))

    def test_file_info_extraction(self, tmp_path):
        """Test file info extraction."""
        # Create a test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        metadata = extract_metadata(test_file)

        assert metadata["file_info"]["filename"] == "test.txt"
        assert metadata["file_info"]["extension"] == ".txt"
        assert metadata["file_info"]["size"] > 0