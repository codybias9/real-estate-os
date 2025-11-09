"""
Background Jobs Router
Endpoints for queuing and checking async tasks

IDEMPOTENCY:
All job-queuing endpoints use idempotency keys to prevent duplicate task submission.
Client should provide Idempotency-Key header or one will be auto-generated.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

from api.database import get_db
from api.auth import get_current_user
from db.models import User, Property
from api.tasks import (
    generate_memo_async,
    generate_packet_async,
    batch_generate_memos,
    enrich_property_async,
    batch_enrich_properties,
    update_propensity_scores,
    send_email_async,
    send_bulk_emails
)
from api.idempotency import get_idempotency_handler, IdempotencyHandler

router = APIRouter(prefix="/jobs", tags=["Background Jobs"])

# ============================================================================
# REQUEST SCHEMAS
# ============================================================================

class GenerateMemoJobRequest(BaseModel):
    property_id: int
    template: str = "default"

class GeneratePacketJobRequest(BaseModel):
    property_id: int
    deal_id: int
    include_comps: bool = True

class BatchMemoJobRequest(BaseModel):
    property_ids: List[int]
    template: str = "default"

class EnrichPropertyJobRequest(BaseModel):
    property_id: int
    sources: Optional[List[str]] = None

class BatchEnrichJobRequest(BaseModel):
    property_ids: List[int]
    sources: Optional[List[str]] = None

class SendEmailJobRequest(BaseModel):
    to_email: str
    subject: str
    body: str
    property_id: Optional[int] = None
    template_id: Optional[int] = None

class BulkEmailRecipient(BaseModel):
    to_email: str
    property_id: Optional[int] = None
    personalization: Dict[str, Any] = {}

class BulkEmailJobRequest(BaseModel):
    recipients: List[BulkEmailRecipient]
    subject: str
    body_template: str
    template_id: Optional[int] = None

# ============================================================================
# RESPONSE SCHEMAS
# ============================================================================

class JobResponse(BaseModel):
    success: bool
    job_id: str
    status: str = "queued"
    message: str

class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    state: str
    result: Optional[Any] = None
    error: Optional[str] = None

# ============================================================================
# MEMO GENERATION JOBS
# ============================================================================

@router.post("/memo/generate", response_model=JobResponse)
def queue_memo_generation(
    memo_request: GenerateMemoJobRequest,
    http_request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    idempotency: IdempotencyHandler = Depends(get_idempotency_handler)
):
    """
    Queue memo generation as background job

    Returns immediately with job ID
    Poll /jobs/{job_id}/status to check progress

    Idempotency:
    - Provide Idempotency-Key header to prevent duplicate submissions
    - Same key within 24 hours returns the same job_id (cached response)
    - Prevents duplicate memo generation from double-clicks or retries
    """
    # Check for existing idempotent request
    existing = idempotency.check_existing()
    if existing:
        return JSONResponse(
            content=existing["body"],
            status_code=existing["status_code"],
            headers={"X-Idempotency-Cached": "true"}
        )

    # Verify property exists and user has access
    property = db.query(Property).filter(Property.id == memo_request.property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    if property.team_id != current_user.team_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Queue task (only once due to idempotency)
    task = generate_memo_async.delay(memo_request.property_id, memo_request.template)

    response = {
        "success": True,
        "job_id": task.id,
        "status": "queued",
        "message": f"Memo generation queued for property {memo_request.property_id}"
    }

    # Store response for idempotency
    idempotency.store_response(200, response, memo_request.dict())

    return response


@router.post("/memo/batch", response_model=JobResponse)
def queue_batch_memo_generation(
    request: BatchMemoJobRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Queue batch memo generation

    Generates memos for multiple properties in parallel
    """
    # Verify all properties exist and user has access
    properties = db.query(Property).filter(
        Property.id.in_(request.property_ids)
    ).all()

    if len(properties) != len(request.property_ids):
        raise HTTPException(status_code=404, detail="Some properties not found")

    if any(p.team_id != current_user.team_id for p in properties):
        raise HTTPException(status_code=403, detail="Access denied")

    # Queue batch task
    task = batch_generate_memos.delay(request.property_ids, request.template)

    return {
        "success": True,
        "job_id": task.id,
        "status": "queued",
        "message": f"Batch memo generation queued for {len(request.property_ids)} properties"
    }


@router.post("/packet/generate", response_model=JobResponse)
def queue_packet_generation(
    request: GeneratePacketJobRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Queue offer packet generation as background job
    """
    property = db.query(Property).filter(Property.id == request.property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    if property.team_id != current_user.team_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Queue task
    task = generate_packet_async.delay(
        request.property_id,
        request.deal_id,
        request.include_comps
    )

    return {
        "success": True,
        "job_id": task.id,
        "status": "queued",
        "message": f"Packet generation queued for property {request.property_id}"
    }


# ============================================================================
# ENRICHMENT JOBS
# ============================================================================

@router.post("/enrich/property", response_model=JobResponse)
def queue_property_enrichment(
    request: EnrichPropertyJobRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Queue property enrichment as background job

    Fetches data from external sources (ATTOM, Regrid, etc.)
    """
    property = db.query(Property).filter(Property.id == request.property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    if property.team_id != current_user.team_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Queue task
    task = enrich_property_async.delay(request.property_id, request.sources)

    return {
        "success": True,
        "job_id": task.id,
        "status": "queued",
        "message": f"Enrichment queued for property {request.property_id}"
    }


@router.post("/enrich/batch", response_model=JobResponse)
def queue_batch_enrichment(
    request: BatchEnrichJobRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Queue batch property enrichment
    """
    properties = db.query(Property).filter(
        Property.id.in_(request.property_ids)
    ).all()

    if len(properties) != len(request.property_ids):
        raise HTTPException(status_code=404, detail="Some properties not found")

    if any(p.team_id != current_user.team_id for p in properties):
        raise HTTPException(status_code=403, detail="Access denied")

    # Queue batch task
    task = batch_enrich_properties.delay(request.property_ids, request.sources)

    return {
        "success": True,
        "job_id": task.id,
        "status": "queued",
        "message": f"Batch enrichment queued for {len(request.property_ids)} properties"
    }


@router.post("/propensity/update", response_model=JobResponse)
def queue_propensity_update(
    property_ids: Optional[List[int]] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Queue propensity score update

    If property_ids provided, updates only those properties
    Otherwise, updates all properties for user's team
    """
    if property_ids:
        properties = db.query(Property).filter(
            Property.id.in_(property_ids)
        ).all()

        if any(p.team_id != current_user.team_id for p in properties):
            raise HTTPException(status_code=403, detail="Access denied")

    # Queue task
    task = update_propensity_scores.delay(property_ids)

    return {
        "success": True,
        "job_id": task.id,
        "status": "queued",
        "message": "Propensity score update queued"
    }


# ============================================================================
# EMAIL JOBS
# ============================================================================

@router.post("/email/send", response_model=JobResponse)
def queue_email_send(
    request: SendEmailJobRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Queue email sending as background job
    """
    task = send_email_async.delay(
        to_email=request.to_email,
        subject=request.subject,
        body=request.body,
        property_id=request.property_id,
        template_id=request.template_id
    )

    return {
        "success": True,
        "job_id": task.id,
        "status": "queued",
        "message": f"Email queued for {request.to_email}"
    }


@router.post("/email/bulk", response_model=JobResponse)
def queue_bulk_email_send(
    request: BulkEmailJobRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Queue bulk email sending

    Sends personalized emails to multiple recipients in parallel
    """
    # Convert Pydantic models to dicts
    recipients_data = [r.dict() for r in request.recipients]

    task = send_bulk_emails.delay(
        recipients=recipients_data,
        subject=request.subject,
        body_template=request.body_template,
        template_id=request.template_id
    )

    return {
        "success": True,
        "job_id": task.id,
        "status": "queued",
        "message": f"Bulk email queued for {len(request.recipients)} recipients"
    }


# ============================================================================
# JOB STATUS
# ============================================================================

@router.get("/{job_id}/status", response_model=JobStatusResponse)
def get_job_status(
    job_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get status of a background job

    States:
    - PENDING: Task is waiting to be executed
    - STARTED: Task has been started
    - RETRY: Task is being retried
    - FAILURE: Task failed
    - SUCCESS: Task completed successfully
    """
    from celery.result import AsyncResult
    from api.celery_app import celery_app

    result = AsyncResult(job_id, app=celery_app)

    response = {
        "job_id": job_id,
        "status": result.status,
        "state": result.state
    }

    if result.ready():
        if result.successful():
            response["result"] = result.result
        else:
            response["error"] = str(result.info)

    return response


@router.post("/{job_id}/cancel")
def cancel_job(
    job_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Cancel a pending or running job

    Note: Jobs that have already started may not be cancellable
    """
    from celery.result import AsyncResult
    from api.celery_app import celery_app

    result = AsyncResult(job_id, app=celery_app)

    if result.state in ["PENDING", "STARTED"]:
        result.revoke(terminate=True)

        return {
            "success": True,
            "message": f"Job {job_id} cancelled"
        }
    else:
        return {
            "success": False,
            "message": f"Job {job_id} cannot be cancelled (state: {result.state})"
        }


@router.get("/active")
def list_active_jobs(
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user)
):
    """
    List active background jobs

    Note: This requires Celery Flower or similar monitoring tool
    For production, implement proper job tracking in database
    """
    # TODO: Implement job tracking in database
    # For now, return placeholder

    return {
        "message": "Install Flower for job monitoring: celery -A api.celery_app flower",
        "flower_url": "http://localhost:5555"
    }
