"""
API v1 Router
"""

from fastapi import APIRouter
from .health import router as health_router
from .auth import router as auth_router
from .properties import router as properties_router

# v1 router without tags (endpoints define their own tags)
router = APIRouter(prefix="/v1")

# Include health endpoints
router.include_router(health_router)

# Include authentication endpoints
router.include_router(auth_router)

# Include property endpoints
router.include_router(properties_router)

__all__ = ["router"]
