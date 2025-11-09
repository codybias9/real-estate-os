"""
Introspection endpoint for verification
Exposes app.routes and provider configuration when ENV=VERIFY

Add to api/main.py temporarily for verification:

    from api.introspection import router as introspection_router
    if os.getenv("VERIFY_MODE") == "true":
        app.include_router(introspection_router)
"""
import os
from fastapi import APIRouter, HTTPException
from typing import Dict, List, Any

router = APIRouter(prefix="/__introspection", tags=["Introspection"])


@router.get("/routes")
def get_routes():
    """
    Return all mounted routes (for verification)
    Only enabled when VERIFY_MODE=true
    """
    if os.getenv("VERIFY_MODE") != "true":
        raise HTTPException(404, "Not found")

    from fastapi import FastAPI
    from api.main import app

    routes = []
    for route in app.routes:
        if hasattr(route, "path"):
            routes.append({
                "path": route.path,
                "methods": list(getattr(route, "methods", [])),
                "name": getattr(route, "name", None),
            })

    return {
        "total_routes": len(routes),
        "routes": sorted(routes, key=lambda r: r["path"]),
        "openapi_paths": len(app.openapi().get("paths", {})) if hasattr(app, "openapi") else 0,
    }


@router.get("/providers")
def get_providers():
    """
    Return provider configuration (mock vs real)
    """
    if os.getenv("VERIFY_MODE") != "true":
        raise HTTPException(404, "Not found")

    config = {
        "MOCK_MODE": os.getenv("MOCK_MODE"),
        "providers": {}
    }

    # Try to introspect provider factory
    try:
        from api.providers.factory import get_email_provider, get_sms_provider
        from api.integrations.factory import get_storage_client, get_pdf_generator

        email = get_email_provider()
        config["providers"]["email"] = type(email).__name__

        sms = get_sms_provider()
        config["providers"]["sms"] = type(sms).__name__

        storage = get_storage_client()
        config["providers"]["storage"] = type(storage).__name__

        pdf = get_pdf_generator()
        config["providers"]["pdf"] = type(pdf).__name__

    except ImportError:
        config["providers"]["error"] = "Factory not available"

    return config


@router.get("/health-detailed")
def health_detailed():
    """
    Detailed health check with component status
    """
    if os.getenv("VERIFY_MODE") != "true":
        raise HTTPException(404, "Not found")

    health = {
        "status": "ok",
        "components": {}
    }

    # Database
    try:
        from api.database import engine
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        health["components"]["database"] = "connected"
    except Exception as e:
        health["components"]["database"] = f"error: {str(e)}"
        health["status"] = "degraded"

    # Redis (if configured)
    try:
        import os
        if os.getenv("REDIS_URL"):
            import redis
            r = redis.from_url(os.getenv("REDIS_URL"))
            r.ping()
            health["components"]["redis"] = "connected"
    except:
        health["components"]["redis"] = "not configured"

    # Celery (if configured)
    try:
        from api.celery_app import celery_app
        health["components"]["celery"] = "configured"
    except ImportError:
        health["components"]["celery"] = "not configured"

    return health
