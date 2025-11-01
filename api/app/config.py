"""Application configuration using Pydantic Settings

Loads configuration from environment variables.
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """
    Application settings

    All settings are loaded from environment variables or .env file
    """

    # Application
    app_name: str = "Real Estate OS API"
    app_version: str = "1.0.0"
    debug: bool = False

    # Database
    database_url: str
    db_pool_size: int = 10
    db_max_overflow: int = 20

    # Authentication
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:8000"]

    # MinIO
    minio_endpoint: str = "minio:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_secure: bool = False

    # Qdrant
    qdrant_url: str = "http://qdrant:6333"

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
