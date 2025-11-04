"""
DLQ Admin API
Endpoints for DLQ management (admin/ops only)
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
import structlog

# Import DLQ tools
import sys
sys.path.append('/home/user/real-estate-os')
from ops.dlq.replay import DLQReplay
from infrastructure.rabbitmq.dlq_config import DLQConfigurator

logger = structlog.get_logger()
router = APIRouter(prefix="/v1/ops/dlq", tags=["ops", "dlq"])


# ============================================================
# Models
# ============================================================

class DLQDepth(BaseModel):
    """DLQ depth information"""
    subject: str
    queue: str
    message_count: int
    consumer_count: int


class DLQReplayRequest(BaseModel):
    """Request to replay messages from DLQ"""
    subject: str
    limit: Optional[int] = None
    dry_run: bool = False


class DLQReplayResponse(BaseModel):
    """Response from replay operation"""
    subject: str
    stats: dict
    report_path: Optional[str] = None


class DLQPurgeRequest(BaseModel):
    """Request to purge DLQ"""
    subject: str
    confirm: bool = False  # Safety flag


class DLQPurgeResponse(BaseModel):
    """Response from purge operation"""
    subject: str
    messages_purged: int


class DLQMessage(BaseModel):
    """DLQ message preview"""
    event_id: str
    type: str
    metadata: dict
    payload: dict


# ============================================================
# Dependencies
# ============================================================

async def get_current_user():
    """Get current authenticated user"""
    # This would come from JWT middleware
    raise NotImplementedError("Auth middleware must provide current_user")


async def require_admin(current_user = Depends(get_current_user)):
    """Require admin or ops role"""
    if current_user.role not in ["admin", "ops"]:
        raise HTTPException(
            status_code=403,
            detail="Admin or Ops role required for DLQ operations"
        )
    return current_user


def get_rabbitmq_url() -> str:
    """Get RabbitMQ connection URL from config"""
    # This would come from app config
    return "amqp://guest:guest@localhost:5672/"


# ============================================================
# Endpoints
# ============================================================

@router.get("/depths", response_model=List[DLQDepth])
async def get_dlq_depths(
    current_user = Depends(require_admin),
):
    """
    Get DLQ depths for all subjects

    Returns:
        List of DLQ depths with message counts
    """
    logger.info("dlq.api.depths.start", user=current_user.email)

    rabbitmq_url = get_rabbitmq_url()
    configurator = DLQConfigurator(rabbitmq_url)

    try:
        await configurator.connect()
        depths = await configurator.get_all_dlq_depths()

        logger.info(
            "dlq.api.depths.success",
            user=current_user.email,
            count=len(depths),
        )

        return [DLQDepth(**d) for d in depths]

    except Exception as e:
        logger.error("dlq.api.depths.failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        await configurator.close()


@router.get("/depths/{subject}", response_model=DLQDepth)
async def get_dlq_depth_for_subject(
    subject: str,
    current_user = Depends(require_admin),
):
    """
    Get DLQ depth for a specific subject

    Args:
        subject: Event subject (e.g., "property.created")

    Returns:
        DLQ depth information
    """
    logger.info("dlq.api.depth.start", subject=subject, user=current_user.email)

    rabbitmq_url = get_rabbitmq_url()
    configurator = DLQConfigurator(rabbitmq_url)

    try:
        await configurator.connect()
        depth = await configurator.get_dlq_depth(subject)

        logger.info(
            "dlq.api.depth.success",
            subject=subject,
            message_count=depth["message_count"],
        )

        return DLQDepth(**depth)

    except Exception as e:
        logger.error("dlq.api.depth.failed", subject=subject, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        await configurator.close()


@router.post("/replay", response_model=DLQReplayResponse)
async def replay_dlq_messages(
    request: DLQReplayRequest,
    current_user = Depends(require_admin),
):
    """
    Replay messages from DLQ back to main queue

    Args:
        request: Replay request with subject, limit, and dry_run flag

    Returns:
        Replay statistics
    """
    logger.info(
        "dlq.api.replay.start",
        subject=request.subject,
        limit=request.limit,
        dry_run=request.dry_run,
        user=current_user.email,
    )

    rabbitmq_url = get_rabbitmq_url()
    replayer = DLQReplay(rabbitmq_url)

    try:
        await replayer.connect()

        stats = await replayer.replay_messages(
            subject=request.subject,
            limit=request.limit,
            dry_run=request.dry_run,
        )

        logger.info(
            "dlq.api.replay.success",
            subject=request.subject,
            stats=stats,
        )

        # Generate report path
        from datetime import datetime
        import json

        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "subject": request.subject,
            "limit": request.limit,
            "dry_run": request.dry_run,
            "stats": stats,
            "user": current_user.email,
        }

        report_path = f"/home/user/real-estate-os/audit_artifacts/logs/dlq-replay-{request.subject}-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)

        return DLQReplayResponse(
            subject=request.subject,
            stats=stats,
            report_path=report_path,
        )

    except Exception as e:
        logger.error(
            "dlq.api.replay.failed",
            subject=request.subject,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        await replayer.close()


@router.post("/purge", response_model=DLQPurgeResponse)
async def purge_dlq(
    request: DLQPurgeRequest,
    current_user = Depends(require_admin),
):
    """
    Purge (delete all messages) from a DLQ

    **WARNING**: This is a destructive operation. Use with caution.

    Args:
        request: Purge request with subject and confirmation flag

    Returns:
        Number of messages purged
    """
    if not request.confirm:
        raise HTTPException(
            status_code=400,
            detail="Purge requires confirm=true. This is a destructive operation."
        )

    logger.warning(
        "dlq.api.purge.start",
        subject=request.subject,
        user=current_user.email,
    )

    rabbitmq_url = get_rabbitmq_url()
    configurator = DLQConfigurator(rabbitmq_url)

    try:
        await configurator.connect()
        purged_count = await configurator.purge_dlq(request.subject)

        logger.warning(
            "dlq.api.purge.success",
            subject=request.subject,
            purged=purged_count,
            user=current_user.email,
        )

        return DLQPurgeResponse(
            subject=request.subject,
            messages_purged=purged_count,
        )

    except Exception as e:
        logger.error(
            "dlq.api.purge.failed",
            subject=request.subject,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        await configurator.close()


@router.get("/messages/{subject}", response_model=List[DLQMessage])
async def peek_dlq_messages(
    subject: str,
    limit: int = Query(10, ge=1, le=100),
    current_user = Depends(require_admin),
):
    """
    Peek at messages in DLQ without removing them

    Args:
        subject: Event subject
        limit: Number of messages to peek (1-100)

    Returns:
        List of message previews
    """
    logger.info(
        "dlq.api.peek.start",
        subject=subject,
        limit=limit,
        user=current_user.email,
    )

    rabbitmq_url = get_rabbitmq_url()
    replayer = DLQReplay(rabbitmq_url)

    try:
        await replayer.connect()

        messages = await replayer.peek_messages(subject=subject, limit=limit)

        logger.info(
            "dlq.api.peek.success",
            subject=subject,
            count=len(messages),
        )

        # Convert to DLQMessage models
        result = []
        for msg in messages:
            result.append(
                DLQMessage(
                    event_id=msg.get("event_id", "unknown"),
                    type=msg.get("type", "unknown"),
                    metadata=msg.get("metadata", {}),
                    payload=msg,
                )
            )

        return result

    except Exception as e:
        logger.error("dlq.api.peek.failed", subject=subject, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        await replayer.close()


@router.get("/list", response_model=List[DLQDepth])
async def list_subjects_with_messages(
    current_user = Depends(require_admin),
):
    """
    List all subjects that have messages in their DLQ

    Returns:
        List of subjects with non-zero DLQ depth
    """
    logger.info("dlq.api.list.start", user=current_user.email)

    rabbitmq_url = get_rabbitmq_url()
    replayer = DLQReplay(rabbitmq_url)

    try:
        await replayer.connect()

        subjects = await replayer.list_subjects_with_dlq_messages()

        logger.info(
            "dlq.api.list.success",
            count=len(subjects),
        )

        return [DLQDepth(**s, consumer_count=0) for s in subjects]

    except Exception as e:
        logger.error("dlq.api.list.failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        await replayer.close()
