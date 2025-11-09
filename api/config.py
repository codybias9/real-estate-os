"""
Application Configuration & Feature Flags

Manages application mode (mock vs production) and provider selection.
Enables fully self-contained development/staging without external dependencies.
"""
import os
from enum import Enum
from typing import Optional
from pydantic_settings import BaseSettings


class AppMode(str, Enum):
    """Application runtime mode"""
    MOCK = "mock"      # Local development with mock providers
    STAGING = "staging"  # Staging environment (may use real or mock)
    PRODUCTION = "production"  # Production with real providers


class AppConfig(BaseSettings):
    """
    Application configuration with safe defaults for development.

    Mock Mode (default):
    - Uses MailHog for email (SMTP localhost:1025)
    - Uses Mock Twilio service (localhost:4010)
    - Uses MinIO for storage (localhost:9000)
    - Uses Gotenberg for PDF (localhost:3000)
    - Uses deterministic templates (no LLM calls)
    - Enforces rate limiting and webhook signatures

    Production Mode:
    - Uses SendGrid for email
    - Uses Twilio for SMS
    - Uses AWS S3 for storage
    - Uses WeasyPrint/DocRaptor for PDF
    - Uses OpenAI/Claude for LLM
    """

    # ============================================================================
    # CORE APPLICATION SETTINGS
    # ============================================================================

    APP_MODE: AppMode = AppMode.MOCK
    APP_NAME: str = "Real Estate OS"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # ============================================================================
    # FEATURE FLAGS
    # ============================================================================

    # External communication flags
    FEATURE_EXTERNAL_SENDS: bool = False  # Actually send emails/SMS externally
    FEATURE_USE_LLM: bool = False  # Use real LLM APIs
    FEATURE_RATE_LIMIT: bool = True  # Enable rate limiting
    FEATURE_WEBHOOK_SIGNATURES: bool = True  # Enforce webhook signatures
    FEATURE_CACHE_RESPONSES: bool = True  # Enable response caching

    # ============================================================================
    # DATABASE SETTINGS
    # ============================================================================

    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/real_estate_os"
    DATABASE_ECHO: bool = False  # Set to True for SQL logging

    # ============================================================================
    # REDIS SETTINGS
    # ============================================================================

    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CACHE_DB: int = 1
    REDIS_RATE_LIMIT_DB: int = 2

    # ============================================================================
    # CELERY SETTINGS
    # ============================================================================

    CELERY_BROKER_URL: str = "amqp://guest:guest@localhost:5672//"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/3"

    # ============================================================================
    # EMAIL PROVIDER SETTINGS
    # ============================================================================

    # Mock mode (MailHog)
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 1025
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "noreply@realtor-demo.com"

    # Production mode (SendGrid)
    SENDGRID_API_KEY: Optional[str] = None
    SENDGRID_SIGNING_SECRET: str = "mock-sendgrid-secret-for-dev"

    # ============================================================================
    # SMS PROVIDER SETTINGS
    # ============================================================================

    # Mock mode
    MOCK_TWILIO_URL: str = "http://localhost:4010"
    MOCK_TWILIO_SECRET: str = "mock-twilio-secret-for-dev"

    # Production mode (Twilio)
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_FROM_PHONE: str = "+15555551234"

    # ============================================================================
    # STORAGE PROVIDER SETTINGS
    # ============================================================================

    # Mock mode (MinIO)
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "memos"
    MINIO_SECURE: bool = False

    # Production mode (AWS S3)
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_S3_BUCKET: Optional[str] = None
    AWS_S3_REGION: str = "us-east-1"

    # ============================================================================
    # PDF PROVIDER SETTINGS
    # ============================================================================

    # Mock mode (Gotenberg)
    GOTENBERG_URL: str = "http://localhost:3000"

    # Production mode (WeasyPrint local or DocRaptor)
    DOCRAPTOR_API_KEY: Optional[str] = None

    # ============================================================================
    # LLM PROVIDER SETTINGS
    # ============================================================================

    # Production mode
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None

    # ============================================================================
    # RATE LIMITING SETTINGS
    # ============================================================================

    RATE_LIMIT_AUTH_LOGIN: str = "10/minute"  # Failed login attempts
    RATE_LIMIT_JOB_ENQUEUE: str = "30/minute"  # Job creation
    RATE_LIMIT_API_GENERAL: str = "100/minute"  # General API calls

    # ============================================================================
    # SECURITY SETTINGS
    # ============================================================================

    SECRET_KEY: str = "dev-secret-key-change-in-production"
    JWT_SECRET: str = "jwt-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 60

    # Security headers (production)
    SECURITY_HEADERS_ENABLED: bool = True
    CORS_ORIGINS: list = ["http://localhost:3000", "http://localhost:8000"]

    # ============================================================================
    # SSE SETTINGS
    # ============================================================================

    SSE_HEARTBEAT_INTERVAL: int = 20  # seconds
    SSE_TOKEN_EXPIRATION: int = 300  # 5 minutes

    # ============================================================================
    # WEBHOOK SETTINGS
    # ============================================================================

    WEBHOOK_TIMESTAMP_TOLERANCE: int = 300  # 5 minutes for timestamp skew

    # ============================================================================
    # ARTIFACT & LOGGING SETTINGS
    # ============================================================================

    AUDIT_ARTIFACTS_DIR: str = "./audit_artifacts"
    LOG_LEVEL: str = "INFO"
    LOG_SQL: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = True


# Global config instance
config = AppConfig()


def get_config() -> AppConfig:
    """Get application configuration"""
    return config


def is_mock_mode() -> bool:
    """Check if running in mock mode"""
    return config.APP_MODE == AppMode.MOCK


def is_production_mode() -> bool:
    """Check if running in production mode"""
    return config.APP_MODE == AppMode.PRODUCTION


def get_provider_info() -> dict:
    """
    Get current provider configuration for status endpoint

    Returns:
        Dict with provider types currently active
    """
    mode = config.APP_MODE

    providers = {
        "app_mode": mode.value,
        "email": "mailhog-smtp" if is_mock_mode() else "sendgrid",
        "sms": "mock-twilio" if is_mock_mode() else "twilio",
        "storage": "minio-local" if is_mock_mode() else "aws-s3",
        "pdf": "gotenberg-local" if is_mock_mode() else "weasyprint",
        "llm": "deterministic-templates" if is_mock_mode() or not config.FEATURE_USE_LLM else "openai",
        "features": {
            "external_sends": config.FEATURE_EXTERNAL_SENDS,
            "use_llm": config.FEATURE_USE_LLM,
            "rate_limit": config.FEATURE_RATE_LIMIT,
            "webhook_signatures": config.FEATURE_WEBHOOK_SIGNATURES,
            "cache_responses": config.FEATURE_CACHE_RESPONSES,
        }
    }

    return providers
