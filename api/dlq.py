"""
Dead Letter Queue (DLQ) Management and Monitoring

Handles failed Celery tasks with comprehensive retry and replay capabilities.

Features:
- Automatic DLQ routing via RabbitMQ Dead Letter Exchange (DLX)
- Failed task tracking in database
- Admin replay endpoints
- Monitoring and alerting
- Idempotency on replay
- Progressive backoff

DLQ Flow:
1. Task fails after max retries → sent to DLX
2. Consumer records failure in database
3. Admin inspects DLQ via API
4. Admin replays tasks (with idempotency)
5. Monitoring alerts if DLQ depth > 0 for > 5 minutes
"""
import os
import logging
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from celery import Task
from celery.exceptions import MaxRetriesExceededError

logger = logging.getLogger(__name__)

# ============================================================================
# RABBITMQ DLQ CONFIGURATION
# ============================================================================

# Dead Letter Exchange configuration for RabbitMQ
DLQ_EXCHANGE = "dlx"  # Dead Letter Exchange
DLQ_ROUTING_KEY = "dlq.#"  # Route all failed messages

# Queue-specific DLQ configuration
QUEUE_DLQ_CONFIG = {
    "memos": {
        "x-dead-letter-exchange": DLQ_EXCHANGE,
        "x-dead-letter-routing-key": "dlq.memos",
        "x-message-ttl": 86400000,  # 24 hours (milliseconds)
    },
    "enrichment": {
        "x-dead-letter-exchange": DLQ_EXCHANGE,
        "x-dead-letter-routing-key": "dlq.enrichment",
        "x-message-ttl": 86400000,
    },
    "emails": {
        "x-dead-letter-exchange": DLQ_EXCHANGE,
        "x-dead-letter-routing-key": "dlq.emails",
        "x-message-ttl": 86400000,
    },
    "maintenance": {
        "x-dead-letter-exchange": DLQ_EXCHANGE,
        "x-dead-letter-routing-key": "dlq.maintenance",
        "x-message-ttl": 86400000,
    },
}

# ============================================================================
# FAILED TASK TRACKING
# ============================================================================

def record_failed_task(
    db: Session,
    task_id: str,
    task_name: str,
    args: List[Any],
    kwargs: Dict[str, Any],
    exception: Exception,
    traceback: str,
    queue_name: str = "default",
    retries: int = 0
) -> int:
    """
    Record a failed task in the database

    Args:
        db: Database session
        task_id: Celery task ID
        task_name: Task name (e.g., "api.tasks.memo_tasks.generate_memo_async")
        args: Task positional arguments
        kwargs: Task keyword arguments
        exception: Exception that caused the failure
        traceback: Full traceback string
        queue_name: Queue where task was running
        retries: Number of retries attempted

    Returns:
        Failed task record ID
    """
    from db.models import FailedTask

    try:
        failed_task = FailedTask(
            task_id=task_id,
            task_name=task_name,
            queue_name=queue_name,
            args=args,
            kwargs=kwargs,
            exception_type=type(exception).__name__,
            exception_message=str(exception),
            traceback=traceback,
            retries_attempted=retries,
            failed_at=datetime.utcnow(),
            status="failed"
        )

        db.add(failed_task)
        db.commit()
        db.refresh(failed_task)

        logger.error(
            f"Recorded failed task {task_name} (ID: {task_id})",
            extra={
                "task_id": task_id,
                "task_name": task_name,
                "queue": queue_name,
                "exception": str(exception),
                "retries": retries
            }
        )

        return failed_task.id

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to record failed task: {str(e)}")
        raise


def get_failed_tasks(
    db: Session,
    queue_name: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """
    Get failed tasks from database

    Args:
        db: Database session
        queue_name: Filter by queue (optional)
        status: Filter by status (failed, replaying, replayed, archived)
        limit: Maximum number of results
        offset: Offset for pagination

    Returns:
        List of failed task records
    """
    from db.models import FailedTask

    query = db.query(FailedTask)

    if queue_name:
        query = query.filter(FailedTask.queue_name == queue_name)

    if status:
        query = query.filter(FailedTask.status == status)

    # Order by most recent first
    query = query.order_by(FailedTask.failed_at.desc())

    # Apply pagination
    failed_tasks = query.offset(offset).limit(limit).all()

    return [
        {
            "id": task.id,
            "task_id": task.task_id,
            "task_name": task.task_name,
            "queue_name": task.queue_name,
            "args": task.args,
            "kwargs": task.kwargs,
            "exception_type": task.exception_type,
            "exception_message": task.exception_message,
            "traceback": task.traceback,
            "retries_attempted": task.retries_attempted,
            "failed_at": task.failed_at.isoformat(),
            "replayed_at": task.replayed_at.isoformat() if task.replayed_at else None,
            "status": task.status,
            "replay_count": task.replay_count
        }
        for task in failed_tasks
    ]


def get_dlq_stats(db: Session) -> Dict[str, Any]:
    """
    Get DLQ statistics

    Returns:
        Dict with DLQ metrics:
        - total_failed: Total failed tasks
        - by_queue: Breakdown by queue
        - by_status: Breakdown by status
        - oldest_failure: Timestamp of oldest unresolved failure
        - alert_threshold_exceeded: Whether alert should fire
    """
    from db.models import FailedTask
    from sqlalchemy import func

    # Total failed tasks (not archived)
    total_failed = db.query(func.count(FailedTask.id)).filter(
        FailedTask.status.in_(["failed", "replaying"])
    ).scalar()

    # Breakdown by queue
    by_queue = db.query(
        FailedTask.queue_name,
        func.count(FailedTask.id).label("count")
    ).filter(
        FailedTask.status.in_(["failed", "replaying"])
    ).group_by(FailedTask.queue_name).all()

    # Breakdown by status
    by_status = db.query(
        FailedTask.status,
        func.count(FailedTask.id).label("count")
    ).group_by(FailedTask.status).all()

    # Oldest unresolved failure
    oldest_failure = db.query(func.min(FailedTask.failed_at)).filter(
        FailedTask.status == "failed"
    ).scalar()

    # Check if alert threshold exceeded (> 5 minutes with failures)
    alert_threshold_exceeded = False
    if oldest_failure:
        time_since_oldest = datetime.utcnow() - oldest_failure
        alert_threshold_exceeded = time_since_oldest > timedelta(minutes=5)

    return {
        "total_failed": total_failed,
        "by_queue": {queue: count for queue, count in by_queue},
        "by_status": {status: count for status, count in by_status},
        "oldest_failure": oldest_failure.isoformat() if oldest_failure else None,
        "time_since_oldest_minutes": (
            (datetime.utcnow() - oldest_failure).total_seconds() / 60
            if oldest_failure else 0
        ),
        "alert_threshold_exceeded": alert_threshold_exceeded,
        "alert_message": (
            f"DLQ has {total_failed} failed tasks for {int((datetime.utcnow() - oldest_failure).total_seconds() / 60)} minutes"
            if alert_threshold_exceeded else None
        )
    }


# ============================================================================
# TASK REPLAY
# ============================================================================

def replay_failed_task(
    db: Session,
    failed_task_id: int,
    force: bool = False
) -> Dict[str, Any]:
    """
    Replay a single failed task

    Args:
        db: Database session
        failed_task_id: ID of failed task record
        force: Force replay even if already replayed

    Returns:
        Dict with replay result:
        - success: Whether replay was successful
        - new_task_id: New Celery task ID
        - message: Status message

    Raises:
        ValueError: If task not found or already replayed
    """
    from db.models import FailedTask
    from api.celery_app import celery_app

    # Get failed task
    failed_task = db.query(FailedTask).filter(FailedTask.id == failed_task_id).first()

    if not failed_task:
        raise ValueError(f"Failed task {failed_task_id} not found")

    # Check if already replayed (unless force=True)
    if failed_task.status == "replayed" and not force:
        raise ValueError(f"Task {failed_task_id} already replayed. Use force=True to replay again.")

    try:
        # Mark as replaying
        failed_task.status = "replaying"
        failed_task.replay_count += 1
        db.commit()

        # Get task from Celery registry
        task_name = failed_task.task_name

        try:
            task = celery_app.tasks[task_name]
        except KeyError:
            raise ValueError(f"Task {task_name} not found in Celery registry")

        # Replay task with original arguments
        # IMPORTANT: Idempotency keys will prevent duplicate side-effects
        logger.info(
            f"Replaying task {task_name} (failed_task_id={failed_task_id})",
            extra={
                "failed_task_id": failed_task_id,
                "task_name": task_name,
                "original_task_id": failed_task.task_id,
                "replay_count": failed_task.replay_count
            }
        )

        # Apply task with original args/kwargs
        result = task.apply_async(
            args=failed_task.args,
            kwargs=failed_task.kwargs,
            # Use high priority to process replays quickly
            priority=9
        )

        # Update record
        failed_task.status = "replayed"
        failed_task.replayed_at = datetime.utcnow()
        failed_task.replayed_task_id = result.id
        db.commit()

        logger.info(
            f"Task replayed successfully: {task_name} (new task_id={result.id})",
            extra={
                "failed_task_id": failed_task_id,
                "new_task_id": result.id
            }
        )

        return {
            "success": True,
            "failed_task_id": failed_task_id,
            "original_task_id": failed_task.task_id,
            "new_task_id": result.id,
            "task_name": task_name,
            "replay_count": failed_task.replay_count,
            "message": f"Task replayed successfully with ID {result.id}"
        }

    except Exception as e:
        # Revert status on failure
        failed_task.status = "failed"
        db.commit()

        logger.error(
            f"Failed to replay task {failed_task_id}: {str(e)}",
            extra={"failed_task_id": failed_task_id, "error": str(e)}
        )

        return {
            "success": False,
            "failed_task_id": failed_task_id,
            "error": str(e),
            "message": f"Replay failed: {str(e)}"
        }


def replay_failed_tasks_bulk(
    db: Session,
    queue_name: Optional[str] = None,
    task_name: Optional[str] = None,
    failed_after: Optional[datetime] = None,
    limit: int = 100
) -> Dict[str, Any]:
    """
    Replay multiple failed tasks in bulk

    Args:
        db: Database session
        queue_name: Filter by queue (optional)
        task_name: Filter by task name (optional)
        failed_after: Only replay tasks that failed after this time
        limit: Maximum number of tasks to replay

    Returns:
        Dict with bulk replay results:
        - total_attempted: Number of tasks attempted
        - successful: Number of successful replays
        - failed: Number of failed replays
        - results: List of individual results
    """
    from db.models import FailedTask

    # Build query
    query = db.query(FailedTask).filter(FailedTask.status == "failed")

    if queue_name:
        query = query.filter(FailedTask.queue_name == queue_name)

    if task_name:
        query = query.filter(FailedTask.task_name == task_name)

    if failed_after:
        query = query.filter(FailedTask.failed_at > failed_after)

    # Order by oldest first (FIFO replay)
    query = query.order_by(FailedTask.failed_at.asc())

    # Apply limit
    failed_tasks = query.limit(limit).all()

    results = {
        "total_attempted": len(failed_tasks),
        "successful": 0,
        "failed": 0,
        "results": []
    }

    for failed_task in failed_tasks:
        try:
            result = replay_failed_task(db, failed_task.id, force=False)

            if result["success"]:
                results["successful"] += 1
            else:
                results["failed"] += 1

            results["results"].append(result)

        except Exception as e:
            logger.error(f"Error replaying task {failed_task.id}: {str(e)}")
            results["failed"] += 1
            results["results"].append({
                "success": False,
                "failed_task_id": failed_task.id,
                "error": str(e)
            })

    logger.info(
        f"Bulk replay completed: {results['successful']} successful, {results['failed']} failed",
        extra=results
    )

    return results


def archive_failed_task(db: Session, failed_task_id: int) -> bool:
    """
    Archive a failed task (mark as resolved without replay)

    Useful for tasks that:
    - Are no longer relevant
    - Were resolved manually
    - Should not be replayed

    Args:
        db: Database session
        failed_task_id: ID of failed task record

    Returns:
        True if archived successfully
    """
    from db.models import FailedTask

    failed_task = db.query(FailedTask).filter(FailedTask.id == failed_task_id).first()

    if not failed_task:
        raise ValueError(f"Failed task {failed_task_id} not found")

    failed_task.status = "archived"
    failed_task.replayed_at = datetime.utcnow()
    db.commit()

    logger.info(f"Archived failed task {failed_task_id}")

    return True


# ============================================================================
# MONITORING & ALERTING
# ============================================================================

def check_dlq_alerts(db: Session) -> Optional[Dict[str, Any]]:
    """
    Check if DLQ alerts should fire

    Alert conditions:
    - DLQ depth > 0 for > 5 minutes
    - Alert clears when DLQ is empty or all tasks replayed

    Returns:
        Alert data if alert should fire, None otherwise
    """
    stats = get_dlq_stats(db)

    if stats["alert_threshold_exceeded"]:
        return {
            "alert": True,
            "severity": "warning",
            "title": "DLQ Has Failed Tasks",
            "message": stats["alert_message"],
            "total_failed": stats["total_failed"],
            "oldest_failure": stats["oldest_failure"],
            "time_since_oldest_minutes": stats["time_since_oldest_minutes"],
            "by_queue": stats["by_queue"],
            "recommended_action": "Review failed tasks and replay or archive them"
        }

    return None


# ============================================================================
# CELERY TASK BASE CLASS WITH DLQ
# ============================================================================

class DLQTask(Task):
    """
    Base task class with DLQ support

    Automatically records failures to database when task exhausts retries.
    """

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """
        Handle task failure - record to DLQ
        """
        from api.database import SessionLocal

        logger.error(
            f"Task {self.name} failed: {exc}",
            exc_info=einfo,
            extra={
                "task_id": task_id,
                "task_name": self.name,
                "exception": str(exc)
            }
        )

        # Record to database
        db = SessionLocal()
        try:
            # Determine queue name from task routing
            from api.celery_app import celery_app
            queue_name = "default"

            # Check task routes
            task_routes = celery_app.conf.get("task_routes", {})
            for pattern, route_config in task_routes.items():
                if pattern in self.name or pattern == "*":
                    queue_name = route_config.get("queue", "default")
                    break

            record_failed_task(
                db=db,
                task_id=task_id,
                task_name=self.name,
                args=list(args),
                kwargs=kwargs,
                exception=exc,
                traceback=str(einfo),
                queue_name=queue_name,
                retries=self.request.retries
            )

        except Exception as e:
            logger.error(f"Failed to record task failure to DLQ: {str(e)}")

        finally:
            db.close()

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """
        Handle task retry
        """
        logger.warning(
            f"Task {self.name} retrying (attempt {self.request.retries + 1}): {exc}",
            extra={
                "task_id": task_id,
                "task_name": self.name,
                "retry_count": self.request.retries,
                "exception": str(exc)
            }
        )
