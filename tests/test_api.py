"""
Integration tests for the API endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import sys
import io
from PIL import Image
import piexif

sys.path.insert(0, str(Path(__file__).parent.parent))

from main import app

client = TestClient(app)

class TestMediaAPI:
    """Test cases for the media upload API."""

    def test_root_endpoint(self):
        """Test the root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        assert "message" in response.json()

    def test_upload_endpoint_missing_file(self):
        """Test upload endpoint with no file."""
        response = client.post("/api/v1/media/upload")
        assert response.status_code == 422  # Validation error

    def test_upload_invalid_extension(self):
        """Test upload with invalid file extension."""
        # Create a simple text file
        file_content = b"not an image"
        response = client.post(
            "/api/v1/media/upload",
            files={"file": ("test.txt", file_content, "text/plain")}
        )
        assert response.status_code == 400

    def test_upload_valid_image(self):
        """Test uploading a valid image."""
        # Create a test image in memory
        img = Image.new('RGB', (100, 100), color='red')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)

        response = client.post(
            "/api/v1/media/upload",
            files={"file": ("test.jpg", img_bytes, "image/jpeg")}
        )

        assert response.status_code == 200
        data = response.json()
        assert "filename" in data
        assert "metadata" in data
        assert "analysis" in data

    def test_upload_valid_image_with_gps(self):
        """Test uploading an image with GPS EXIF metadata."""
        img = Image.new('RGB', (100, 100), color='yellow')
        gps_ifd = {
            piexif.GPSIFD.GPSLatitudeRef: 'N',
            piexif.GPSIFD.GPSLatitude: [(37, 1), (46, 1), (30, 1)],
            piexif.GPSIFD.GPSLongitudeRef: 'W',
            piexif.GPSIFD.GPSLongitude: [(122, 1), (25, 1), (0, 1)],
        }
        exif_dict = {"GPS": gps_ifd}
        exif_bytes = piexif.dump(exif_dict)
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG', exif=exif_bytes)
        img_bytes.seek(0)

        response = client.post(
            "/api/v1/media/upload",
            files={"file": ("gps.jpg", img_bytes, "image/jpeg")}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["metadata"]["exif"]["GPSLatitude"] == [37, 46, 30]
        assert data["metadata"]["exif"]["GPSLongitude"] == [122, 25, 0]
        assert data["metadata"]["exif"]["GPSLatitudeRef"] == 'N'
        assert data["metadata"]["exif"]["GPSLongitudeRef"] == 'W'
        assert data["metadata"]["exif"]["GPS_Decimal"]["latitude"] == 37.775
        assert data["metadata"]["exif"]["GPS_Decimal"]["longitude"] == -122.41666666666667
        # Check top-level location field
        assert data["location"] is not None
        assert data["location"]["latitude"] == 37.775
        assert data["location"]["longitude"] == -122.41666666666667
        assert data["location"]["source"] == "exif"

    def test_upload_valid_image_without_privacy_stripping(self):
        """Test uploading an image without privacy redaction."""
        img = Image.new('RGB', (100, 100), color='blue')
        gps_ifd = {
            piexif.GPSIFD.GPSLatitudeRef: 'N',
            piexif.GPSIFD.GPSLatitude: [(37, 1), (46, 1), (30, 1)],
            piexif.GPSIFD.GPSLongitudeRef: 'W',
            piexif.GPSIFD.GPSLongitude: [(122, 1), (25, 1), (0, 1)],
        }
        exif_dict = {"GPS": gps_ifd}
        exif_bytes = piexif.dump(exif_dict)
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG', exif=exif_bytes)
        img_bytes.seek(0)

        response = client.post(
            "/api/v1/media/upload?strip_sensitive=false",
            files={"file": ("gps_no_privacy.jpg", img_bytes, "image/jpeg")}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["metadata"]["exif"]["GPSLatitude"] == [37, 46, 30]
        assert data["metadata"]["exif"]["GPSLongitude"] == [122, 25, 0]
        assert data["metadata"]["_privacy"]["note"] == "privacy stripping bypassed"

    def test_upload_file_too_large(self):
        """Test uploading a file that's too large."""
        # Create a large file (simulated)
        large_content = b"x" * (20 * 1024 * 1024)  # 20 MB

        response = client.post(
            "/api/v1/media/upload",
            files={"file": ("large.jpg", io.BytesIO(large_content), "image/jpeg")}
        )

        # Should get a 413 Payload Too Large
        assert response.status_code == 413