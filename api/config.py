"""
Configuration module for Real Estate OS API.
Handles environment variables, database connections, and service configurations.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, PostgresDsn, RedisDsn
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Application
    app_name: str = "Real Estate OS API"
    app_version: str = "0.1.0"
    environment: str = Field(default="development", pattern="^(development|staging|production)$")
    debug: bool = False
    api_prefix: str = "/api/v1"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4

    # Database
    database_url: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/real_estate_os",
        description="PostgreSQL connection string"
    )
    database_pool_size: int = 20
    database_max_overflow: int = 10
    database_pool_timeout: int = 30
    database_echo: bool = False

    # Redis
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection string"
    )
    redis_password: Optional[str] = None
    redis_max_connections: int = 50

    # Keycloak (OIDC)
    keycloak_server_url: str = Field(
        default="http://localhost:8080",
        description="Keycloak server URL"
    )
    keycloak_realm: str = Field(
        default="real-estate-os",
        description="Keycloak realm name"
    )
    keycloak_client_id: str = Field(
        default="api-client",
        description="Keycloak client ID for API"
    )
    keycloak_client_secret: Optional[str] = Field(
        default=None,
        description="Keycloak client secret (if confidential client)"
    )
    keycloak_admin_username: Optional[str] = None
    keycloak_admin_password: Optional[str] = None

    # JWT Settings
    jwt_algorithm: str = "RS256"
    jwt_audience: str = "api-client"
    jwt_issuer: Optional[str] = None  # Auto-detected from Keycloak

    # CORS
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="Allowed CORS origins"
    )
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
    cors_allow_headers: list[str] = ["*"]

    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_default_per_minute: int = 100
    rate_limit_burst_size: int = 20

    # Rate limits per endpoint (requests per minute)
    rate_limit_auth_login: int = 10
    rate_limit_auth_register: int = 5
    rate_limit_properties_list: int = 100
    rate_limit_properties_create: int = 20
    rate_limit_ml_valuation: int = 50
    rate_limit_analytics: int = 30

    # Qdrant
    qdrant_url: str = Field(
        default="http://localhost:6333",
        description="Qdrant vector database URL"
    )
    qdrant_api_key: Optional[str] = None
    qdrant_timeout: int = 30

    # MinIO
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_secure: bool = False
    minio_bucket_documents: str = "documents"
    minio_bucket_images: str = "images"

    # Observability
    sentry_dsn: Optional[str] = None
    sentry_environment: Optional[str] = None
    sentry_traces_sample_rate: float = 0.1

    otel_enabled: bool = False
    otel_exporter_otlp_endpoint: str = "http://localhost:4317"
    otel_service_name: str = "real-estate-os-api"

    prometheus_enabled: bool = True
    prometheus_port: int = 9090

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    # Feature Flags
    enable_swagger: bool = True
    enable_redoc: bool = True

    # Security
    allowed_hosts: list[str] = ["*"]

    @property
    def database_url_async(self) -> str:
        """Convert sync database URL to async (asyncpg)."""
        return self.database_url.replace("postgresql://", "postgresql+asyncpg://")

    @property
    def keycloak_well_known_url(self) -> str:
        """Keycloak OIDC well-known configuration URL."""
        return f"{self.keycloak_server_url}/realms/{self.keycloak_realm}/.well-known/openid-configuration"

    @property
    def keycloak_jwks_url(self) -> str:
        """Keycloak JWKS (JSON Web Key Set) URL."""
        return f"{self.keycloak_server_url}/realms/{self.keycloak_realm}/protocol/openid-connect/certs"

    @property
    def keycloak_token_url(self) -> str:
        """Keycloak token endpoint URL."""
        return f"{self.keycloak_server_url}/realms/{self.keycloak_realm}/protocol/openid-connect/token"

    @property
    def keycloak_userinfo_url(self) -> str:
        """Keycloak userinfo endpoint URL."""
        return f"{self.keycloak_server_url}/realms/{self.keycloak_realm}/protocol/openid-connect/userinfo"


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Uses lru_cache to ensure settings are loaded only once.
    """
    return Settings()


# Export settings instance
settings = get_settings()
