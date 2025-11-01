"""Authentication configuration

Environment variables required:
- JWT_SECRET_KEY: Secret key for signing JWT tokens (use secrets.token_urlsafe(32))
- JWT_ALGORITHM: Algorithm for JWT (default: HS256)
- JWT_EXPIRATION_MINUTES: Token expiration time (default: 30)
- OIDC_PROVIDER_URL: OpenID Connect provider URL (optional, for Keycloak/Auth0)
- OIDC_CLIENT_ID: OAuth2 client ID (optional)
- OIDC_CLIENT_SECRET: OAuth2 client secret (optional)
- CORS_ORIGINS: Comma-separated list of allowed origins (production)
- RATE_LIMIT_PER_MINUTE: Rate limit per IP (default: 60)
- RATE_LIMIT_PER_TENANT_MINUTE: Rate limit per tenant (default: 100)
"""

import os
from typing import List

# JWT Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
if not JWT_SECRET_KEY:
    raise ValueError("JWT_SECRET_KEY environment variable must be set")

JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRATION_MINUTES = int(os.getenv("JWT_EXPIRATION_MINUTES", "30"))

# OIDC Configuration (optional)
OIDC_PROVIDER_URL = os.getenv("OIDC_PROVIDER_URL", "")
OIDC_CLIENT_ID = os.getenv("OIDC_CLIENT_ID", "")
OIDC_CLIENT_SECRET = os.getenv("OIDC_CLIENT_SECRET", "")

# CORS Configuration
CORS_ORIGINS_STR = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000")
CORS_ORIGINS: List[str] = [origin.strip() for origin in CORS_ORIGINS_STR.split(",")]

# Rate Limiting
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
RATE_LIMIT_PER_TENANT_MINUTE = int(os.getenv("RATE_LIMIT_PER_TENANT_MINUTE", "100"))

# Security Headers
ENABLE_HSTS = os.getenv("ENABLE_HSTS", "false").lower() == "true"
ENABLE_CSRF_PROTECTION = os.getenv("ENABLE_CSRF_PROTECTION", "true").lower() == "true"
