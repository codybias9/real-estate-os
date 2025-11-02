"""
API v1 Router
"""

from fastapi import APIRouter
from .health import router as health_router

# v1 router without tags (endpoints define their own tags)
router = APIRouter(prefix="/v1")

# Include health endpoints
router.include_router(health_router)

__all__ = ["router"]
