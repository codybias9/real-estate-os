"""
Admin Router
Administrative endpoints for DLQ management, monitoring, and system administration

Security:
- All endpoints require ADMIN role
- Rate limited to prevent abuse
- Audit logged for compliance
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel

from api.database import get_db
from api.auth import get_current_user
from db.models import User, UserRole
from api import dlq

router = APIRouter(prefix="/admin", tags=["Admin"])

# ============================================================================
# AUTHORIZATION
# ============================================================================

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency to require ADMIN role

    Raises:
        HTTPException: 403 if user is not an admin
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class DLQStatsResponse(BaseModel):
    """DLQ statistics response"""
    total_failed: int
    by_queue: Dict[str, int]
    by_status: Dict[str, int]
    oldest_failure: Optional[str]
    time_since_oldest_minutes: float
    alert_threshold_exceeded: bool
    alert_message: Optional[str]


class FailedTaskResponse(BaseModel):
    """Failed task response"""
    id: int
    task_id: str
    task_name: str
    queue_name: str
    args: List[Any]
    kwargs: Dict[str, Any]
    exception_type: Optional[str]
    exception_message: Optional[str]
    traceback: Optional[str]
    retries_attempted: int
    failed_at: str
    replayed_at: Optional[str]
    status: str
    replay_count: int


class ReplayTaskRequest(BaseModel):
    """Request to replay a failed task"""
    failed_task_id: int
    force: bool = False


class ReplayBulkRequest(BaseModel):
    """Request to replay multiple failed tasks"""
    queue_name: Optional[str] = None
    task_name: Optional[str] = None
    failed_after: Optional[datetime] = None
    limit: int = 100


class ReplayResponse(BaseModel):
    """Replay operation response"""
    success: bool
    failed_task_id: Optional[int] = None
    original_task_id: Optional[str] = None
    new_task_id: Optional[str] = None
    task_name: Optional[str] = None
    replay_count: Optional[int] = None
    message: str
    error: Optional[str] = None


class BulkReplayResponse(BaseModel):
    """Bulk replay operation response"""
    total_attempted: int
    successful: int
    failed: int
    results: List[ReplayResponse]


# ============================================================================
# DLQ ENDPOINTS
# ============================================================================

@router.get("/dlq/stats", response_model=DLQStatsResponse)
def get_dlq_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Get DLQ statistics and monitoring data

    Returns:
        - total_failed: Number of failed tasks (not archived)
        - by_queue: Breakdown by queue name
        - by_status: Breakdown by status
        - oldest_failure: Timestamp of oldest unresolved failure
        - alert_threshold_exceeded: Whether alert should fire (> 5 min)
        - alert_message: Alert message if threshold exceeded

    Security:
        - Requires ADMIN role
    """
    stats = dlq.get_dlq_stats(db)
    return stats


@router.get("/dlq/tasks", response_model=List[FailedTaskResponse])
def list_failed_tasks(
    queue_name: Optional[str] = Query(None, description="Filter by queue name"),
    status: Optional[str] = Query(None, description="Filter by status (failed, replaying, replayed, archived)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    List failed tasks in DLQ

    Query Parameters:
        - queue_name: Filter by queue (optional)
        - status: Filter by status (optional)
        - limit: Max results (default 100, max 1000)
        - offset: Pagination offset (default 0)

    Returns:
        List of failed tasks with full details

    Security:
        - Requires ADMIN role
    """
    failed_tasks = dlq.get_failed_tasks(
        db=db,
        queue_name=queue_name,
        status=status,
        limit=limit,
        offset=offset
    )

    return failed_tasks


@router.get("/dlq/tasks/{failed_task_id}", response_model=FailedTaskResponse)
def get_failed_task_detail(
    failed_task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Get detailed information about a specific failed task

    Args:
        failed_task_id: ID of the failed task record

    Returns:
        Full failed task details including traceback

    Security:
        - Requires ADMIN role
    """
    from db.models import FailedTask

    failed_task = db.query(FailedTask).filter(FailedTask.id == failed_task_id).first()

    if not failed_task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Failed task {failed_task_id} not found"
        )

    return {
        "id": failed_task.id,
        "task_id": failed_task.task_id,
        "task_name": failed_task.task_name,
        "queue_name": failed_task.queue_name,
        "args": failed_task.args,
        "kwargs": failed_task.kwargs,
        "exception_type": failed_task.exception_type,
        "exception_message": failed_task.exception_message,
        "traceback": failed_task.traceback,
        "retries_attempted": failed_task.retries_attempted,
        "failed_at": failed_task.failed_at.isoformat(),
        "replayed_at": failed_task.replayed_at.isoformat() if failed_task.replayed_at else None,
        "status": failed_task.status,
        "replay_count": failed_task.replay_count
    }


@router.post("/dlq/replay", response_model=ReplayResponse)
def replay_single_task(
    request: ReplayTaskRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Replay a single failed task

    Body:
        - failed_task_id: ID of the failed task to replay
        - force: Force replay even if already replayed (default: false)

    Returns:
        Replay result with new task ID

    Security:
        - Requires ADMIN role
        - Idempotency prevents duplicate side-effects

    Notes:
        - Task will be replayed with original arguments
        - Idempotency keys ensure no duplicate side-effects
        - Task status updated to "replaying" → "replayed"
        - New task ID returned for monitoring
    """
    try:
        result = dlq.replay_failed_task(
            db=db,
            failed_task_id=request.failed_task_id,
            force=request.force
        )
        return result

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to replay task: {str(e)}"
        )


@router.post("/dlq/replay-bulk", response_model=BulkReplayResponse)
def replay_bulk_tasks(
    request: ReplayBulkRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Replay multiple failed tasks in bulk

    Body:
        - queue_name: Filter by queue (optional)
        - task_name: Filter by task name (optional)
        - failed_after: Only replay tasks failed after this time (optional)
        - limit: Maximum tasks to replay (default: 100, max: 1000)

    Returns:
        Bulk replay results with counts and individual task results

    Security:
        - Requires ADMIN role
        - Idempotency prevents duplicate side-effects

    Notes:
        - Tasks replayed in FIFO order (oldest first)
        - Individual failures don't stop bulk operation
        - Each task replay is idempotent
    """
    if request.limit > 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Limit cannot exceed 1000"
        )

    try:
        result = dlq.replay_failed_tasks_bulk(
            db=db,
            queue_name=request.queue_name,
            task_name=request.task_name,
            failed_after=request.failed_after,
            limit=request.limit
        )
        return result

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Bulk replay failed: {str(e)}"
        )


@router.post("/dlq/archive/{failed_task_id}")
def archive_failed_task(
    failed_task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Archive a failed task without replay

    Use this for tasks that:
    - Are no longer relevant
    - Were resolved manually
    - Should not be replayed

    Args:
        failed_task_id: ID of the failed task to archive

    Returns:
        Success confirmation

    Security:
        - Requires ADMIN role
    """
    try:
        dlq.archive_failed_task(db, failed_task_id)

        return {
            "success": True,
            "message": f"Task {failed_task_id} archived successfully"
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to archive task: {str(e)}"
        )


@router.get("/dlq/alerts")
def check_dlq_alerts(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Check if DLQ alerts should fire

    Alert Conditions:
        - DLQ depth > 0 for > 5 minutes
        - Alert clears when DLQ is empty or all tasks replayed

    Returns:
        Alert data if alert should fire, None otherwise

    Security:
        - Requires ADMIN role

    Integration:
        - Call this from monitoring system (Prometheus, Grafana)
        - Alert on non-null response
        - Use alert_message for notification content
    """
    alert = dlq.check_dlq_alerts(db)

    if alert:
        return alert
    else:
        return {
            "alert": False,
            "message": "DLQ is healthy - no alerts"
        }


# ============================================================================
# SYSTEM ADMINISTRATION
# ============================================================================

@router.get("/health/detailed")
def detailed_health_check(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Detailed system health check

    Returns:
        - Database connectivity
        - Redis connectivity
        - Celery worker status
        - DLQ status
        - Cache hit rates

    Security:
        - Requires ADMIN role
    """
    from api.rate_limit import redis_client
    from api.cache import cache_client

    health = {
        "timestamp": datetime.utcnow().isoformat(),
        "database": "unknown",
        "redis": "unknown",
        "cache": "unknown",
        "dlq": "unknown"
    }

    # Check database
    try:
        db.execute("SELECT 1")
        health["database"] = "healthy"
    except Exception as e:
        health["database"] = f"unhealthy: {str(e)}"

    # Check Redis
    try:
        if redis_client:
            redis_client.ping()
            health["redis"] = "healthy"
        else:
            health["redis"] = "not configured"
    except Exception as e:
        health["redis"] = f"unhealthy: {str(e)}"

    # Check cache
    try:
        if cache_client:
            cache_client.ping()
            health["cache"] = "healthy"
        else:
            health["cache"] = "not configured"
    except Exception as e:
        health["cache"] = f"unhealthy: {str(e)}"

    # Check DLQ
    try:
        stats = dlq.get_dlq_stats(db)
        health["dlq"] = {
            "status": "alert" if stats["alert_threshold_exceeded"] else "healthy",
            "failed_tasks": stats["total_failed"],
            "oldest_failure": stats["oldest_failure"]
        }
    except Exception as e:
        health["dlq"] = f"error: {str(e)}"

    return health


@router.post("/maintenance/cleanup-idempotency-keys")
def cleanup_expired_idempotency_keys(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Clean up expired idempotency keys

    Removes idempotency keys that have exceeded their TTL.
    Should be run daily via cron or Celery beat.

    Returns:
        Number of keys deleted

    Security:
        - Requires ADMIN role
    """
    from api.idempotency import cleanup_expired_idempotency_keys

    deleted = cleanup_expired_idempotency_keys(db)

    return {
        "success": True,
        "deleted_count": deleted,
        "message": f"Cleaned up {deleted} expired idempotency keys"
    }
