"""Health check endpoints for monitoring."""

from typing import Dict, Any
from datetime import datetime
import time

from fastapi import APIRouter, status, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from redis import Redis
from redis.exceptions import RedisError

from .database import get_db
from .config import settings

router = APIRouter(tags=["Health"])


def check_database(db: Session) -> Dict[str, Any]:
    """Check database connectivity and health."""
    try:
        start_time = time.time()
        result = db.execute(text("SELECT 1")).scalar()
        response_time = time.time() - start_time

        return {
            "status": "healthy" if result == 1 else "unhealthy",
            "response_time_ms": round(response_time * 1000, 2),
            "details": {
                "connection": "ok",
                "query_test": "passed"
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "response_time_ms": None,
            "details": {
                "error": str(e),
                "connection": "failed"
            }
        }


def check_redis() -> Dict[str, Any]:
    """Check Redis connectivity and health."""
    try:
        redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
        start_time = time.time()

        # Test ping
        ping_result = redis_client.ping()
        response_time = time.time() - start_time

        # Get some stats
        info = redis_client.info()

        redis_client.close()

        return {
            "status": "healthy" if ping_result else "unhealthy",
            "response_time_ms": round(response_time * 1000, 2),
            "details": {
                "ping": "ok",
                "connected_clients": info.get("connected_clients", 0),
                "used_memory_human": info.get("used_memory_human", "unknown"),
                "uptime_days": info.get("uptime_in_days", 0),
            }
        }
    except RedisError as e:
        return {
            "status": "unhealthy",
            "response_time_ms": None,
            "details": {
                "error": str(e),
                "connection": "failed"
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "response_time_ms": None,
            "details": {
                "error": str(e),
                "connection": "failed"
            }
        }


def check_celery() -> Dict[str, Any]:
    """Check Celery worker connectivity."""
    try:
        from .tasks.celery_app import celery_app

        # Get active workers
        inspect = celery_app.control.inspect(timeout=1.0)
        active_workers = inspect.active()

        if active_workers:
            worker_count = len(active_workers)
            return {
                "status": "healthy",
                "details": {
                    "workers": worker_count,
                    "worker_names": list(active_workers.keys())
                }
            }
        else:
            return {
                "status": "degraded",
                "details": {
                    "workers": 0,
                    "message": "No active Celery workers found"
                }
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "details": {
                "error": str(e),
                "workers": 0
            }
        }


def check_storage() -> Dict[str, Any]:
    """Check storage service (MinIO) health."""
    try:
        from .services.storage import storage_service

        # Try to list buckets to verify connectivity
        start_time = time.time()
        buckets = storage_service.client.list_buckets()
        response_time = time.time() - start_time

        return {
            "status": "healthy",
            "response_time_ms": round(response_time * 1000, 2),
            "details": {
                "connection": "ok",
                "buckets": len(buckets),
                "default_bucket": settings.MINIO_BUCKET
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "response_time_ms": None,
            "details": {
                "error": str(e),
                "connection": "failed"
            }
        }


@router.get("/healthz", status_code=status.HTTP_200_OK)
async def health_check():
    """
    Basic health check endpoint.
    Returns 200 if the service is running.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION
    }


@router.get("/health", status_code=status.HTTP_200_OK)
async def detailed_health_check(db: Session = Depends(get_db)):
    """
    Detailed health check endpoint.
    Checks all critical dependencies and returns detailed status.
    """
    start_time = time.time()

    # Check all services
    checks = {
        "database": check_database(db),
        "redis": check_redis(),
        "celery": check_celery(),
        "storage": check_storage(),
    }

    # Determine overall status
    all_healthy = all(
        check["status"] == "healthy"
        for check in checks.values()
    )

    any_degraded = any(
        check["status"] == "degraded"
        for check in checks.values()
    )

    any_unhealthy = any(
        check["status"] == "unhealthy"
        for check in checks.values()
    )

    if all_healthy:
        overall_status = "healthy"
        http_status = status.HTTP_200_OK
    elif any_unhealthy:
        overall_status = "unhealthy"
        http_status = status.HTTP_503_SERVICE_UNAVAILABLE
    elif any_degraded:
        overall_status = "degraded"
        http_status = status.HTTP_200_OK
    else:
        overall_status = "unknown"
        http_status = status.HTTP_500_INTERNAL_SERVER_ERROR

    total_time = time.time() - start_time

    response = {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "uptime": "available",  # TODO: Calculate actual uptime
        "checks": checks,
        "response_time_ms": round(total_time * 1000, 2)
    }

    return response


@router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_check(db: Session = Depends(get_db)):
    """
    Readiness check endpoint.
    Returns 200 if the service is ready to accept traffic (database is available).
    """
    db_check = check_database(db)

    if db_check["status"] == "healthy":
        return {
            "status": "ready",
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {
                "database": db_check
            }
        }
    else:
        return {
            "status": "not_ready",
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {
                "database": db_check
            }
        }


@router.get("/live", status_code=status.HTTP_200_OK)
async def liveness_check():
    """
    Liveness check endpoint.
    Returns 200 if the service is alive (can respond to requests).
    Used by Kubernetes liveness probes.
    """
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/metrics")
async def metrics():
    """
    Basic metrics endpoint.
    Returns application metrics for monitoring.
    """
    # TODO: Implement Prometheus metrics
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "metrics": {
            "requests_total": "not_implemented",
            "requests_duration_seconds": "not_implemented",
            "active_connections": "not_implemented"
        },
        "message": "Metrics endpoint available. Prometheus integration coming soon."
    }
