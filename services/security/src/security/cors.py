"""
CORS configuration for frontend integration
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def configure_cors(app: FastAPI, allowed_origins: list[str] | None = None):
    """
    Configure CORS middleware for FastAPI app.

    Allows frontend applications to make requests to the API.

    Args:
        app: FastAPI application instance
        allowed_origins: List of allowed origins (from env if not provided)

    Example:
        configure_cors(app, ["http://localhost:3000", "https://app.example.com"])
    """
    # Default allowed origins from environment
    if allowed_origins is None:
        env_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000")
        allowed_origins = [origin.strip() for origin in env_origins.split(",")]

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "X-Request-ID",
            "X-Correlation-ID",
        ],
        expose_headers=[
            "X-Request-ID",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
        ],
        max_age=3600,  # Cache preflight requests for 1 hour
    )

    return app


def get_cors_config() -> dict:
    """
    Get current CORS configuration.

    Returns:
        Dictionary with CORS settings
    """
    env_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000")
    allowed_origins = [origin.strip() for origin in env_origins.split(",")]

    return {
        "allowed_origins": allowed_origins,
        "allow_credentials": True,
        "allowed_methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        "allowed_headers": [
            "Authorization",
            "Content-Type",
            "X-Request-ID",
            "X-Correlation-ID",
        ],
        "exposed_headers": [
            "X-Request-ID",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
        ],
        "max_age": 3600,
    }
