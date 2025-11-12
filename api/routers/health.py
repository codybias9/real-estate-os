"""
System health and monitoring endpoints
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
import psutil
import os

from ..database import get_db
from ..services.airflow_client import airflow_client


router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/")
async def health_check():
    """
    Basic health check endpoint
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "Real Estate OS API"
    }


@router.get("/database")
async def database_health(db: Session = Depends(get_db)):
    """
    Check database connectivity and health
    """
    try:
        # Try to execute a simple query
        result = db.execute(text("SELECT 1")).scalar()

        # Get connection pool info
        pool = db.get_bind().pool
        pool_size = pool.size()
        pool_checked_in = pool.checkedin()
        pool_checked_out = pool.checkedout()
        pool_overflow = pool.overflow()

        return {
            "status": "healthy",
            "database": "connected",
            "pool": {
                "size": pool_size,
                "checked_in": pool_checked_in,
                "checked_out": pool_checked_out,
                "overflow": pool_overflow
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "database": "disconnected",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.get("/airflow")
async def airflow_health():
    """
    Check Airflow connectivity and health
    """
    try:
        health = await airflow_client.get_health()
        return {
            "status": health.get("status"),
            "airflow": health,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "airflow": {
                "status": "unreachable",
                "error": str(e)
            },
            "timestamp": datetime.utcnow().isoformat()
        }


@router.get("/system")
async def system_health():
    """
    Get system resource metrics
    """
    try:
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()

        # Memory usage
        memory = psutil.virtual_memory()
        memory_total = memory.total
        memory_available = memory.available
        memory_percent = memory.percent

        # Disk usage
        disk = psutil.disk_usage('/')
        disk_total = disk.total
        disk_used = disk.used
        disk_free = disk.free
        disk_percent = disk.percent

        return {
            "status": "healthy",
            "system": {
                "cpu": {
                    "count": cpu_count,
                    "usage_percent": cpu_percent
                },
                "memory": {
                    "total_bytes": memory_total,
                    "available_bytes": memory_available,
                    "usage_percent": memory_percent
                },
                "disk": {
                    "total_bytes": disk_total,
                    "used_bytes": disk_used,
                    "free_bytes": disk_free,
                    "usage_percent": disk_percent
                }
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.get("/comprehensive")
async def comprehensive_health(db: Session = Depends(get_db)):
    """
    Comprehensive health check of all system components
    """
    components = {
        "api": {"status": "healthy"},
        "database": {"status": "unknown"},
        "airflow": {"status": "unknown"},
        "system": {"status": "unknown"}
    }

    overall_status = "healthy"

    # Check database
    try:
        db.execute(text("SELECT 1")).scalar()
        components["database"]["status"] = "healthy"
    except Exception as e:
        components["database"]["status"] = "unhealthy"
        components["database"]["error"] = str(e)
        overall_status = "degraded"

    # Check Airflow
    try:
        airflow_health = await airflow_client.get_health()
        components["airflow"]["status"] = airflow_health.get("status", "unknown")
        if airflow_health.get("status") != "healthy":
            overall_status = "degraded"
    except Exception as e:
        components["airflow"]["status"] = "unhealthy"
        components["airflow"]["error"] = str(e)
        overall_status = "degraded"

    # Check system resources
    try:
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        # Consider unhealthy if memory or disk usage is above 90%
        if memory.percent > 90 or disk.percent > 90:
            components["system"]["status"] = "warning"
            components["system"]["message"] = "High resource usage"
            overall_status = "degraded"
        else:
            components["system"]["status"] = "healthy"

        components["system"]["memory_percent"] = memory.percent
        components["system"]["disk_percent"] = disk.percent
    except Exception as e:
        components["system"]["status"] = "error"
        components["system"]["error"] = str(e)

    return {
        "status": overall_status,
        "components": components,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/ready")
async def readiness_check(db: Session = Depends(get_db)):
    """
    Kubernetes readiness probe endpoint
    """
    try:
        # Check database connection
        db.execute(text("SELECT 1")).scalar()

        return {
            "status": "ready",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "not ready",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.get("/live")
async def liveness_check():
    """
    Kubernetes liveness probe endpoint
    """
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat()
    }
