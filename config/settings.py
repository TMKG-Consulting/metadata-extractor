import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # API settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Metadata Extractor"

    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database settings
    DATABASE_URL: str = "postgresql://user:password@localhost/metadata_db"

    # Redis settings
    REDIS_URL: str = "redis://localhost:6379"

    # File upload settings
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10 MB
    UPLOAD_DIR: str = "/tmp/uploads"

    # Privacy settings
    STRIP_GPS_DATA: bool = False
    STRIP_TIMESTAMPS: bool = False
    ANONYMIZE_DEVICE_ID: bool = True

    class Config:
        env_file = ".env"

settings = Settings()