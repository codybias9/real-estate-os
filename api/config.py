"""
Configuration for Real Estate OS API
"""
import os
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""

    # Database
    DB_DSN: str = os.getenv("DB_DSN", "postgresql://airflow:airflow@postgres:5432/airflow")

    # Airflow
    AIRFLOW_API_URL: str = os.getenv("AIRFLOW_API_URL", "http://airflow-apiserver:8080/api/v1")
    AIRFLOW_USERNAME: str = os.getenv("AIRFLOW_USERNAME", "airflow")
    AIRFLOW_PASSWORD: str = os.getenv("AIRFLOW_PASSWORD", "airflow")

    # API
    API_PREFIX: str = "/api"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # CORS
    CORS_ORIGINS: list = ["*"]  # Configure appropriately for production

    class Config:
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
