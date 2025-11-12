"""Jobs router for background job tracking and management."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from enum import Enum
import random

router = APIRouter(prefix="/jobs", tags=["jobs"])


# ============================================================================
# Enums
# ============================================================================

class JobStatus(str, Enum):
    """Status of a background job."""
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"
    retrying = "retrying"


class JobType(str, Enum):
    """Type of background job."""
    property_enrichment = "property_enrichment"
    batch_email_send = "batch_email_send"
    data_import = "data_import"
    report_generation = "report_generation"
    document_processing = "document_processing"
    scraping_job = "scraping_job"
    ml_scoring = "ml_scoring"
    image_processing = "image_processing"
    export_data = "export_data"
    bulk_update = "bulk_update"


class JobPriority(str, Enum):
    """Priority level for job execution."""
    low = "low"
    normal = "normal"
    high = "high"
    urgent = "urgent"


# ============================================================================
# Schemas
# ============================================================================

class BackgroundJob(BaseModel):
    """Background job information."""
    id: str
    job_type: JobType
    status: JobStatus
    priority: JobPriority
    title: str
    description: Optional[str]
    progress_percentage: float = Field(..., ge=0, le=100)
    items_total: Optional[int] = None
    items_processed: Optional[int] = None
    items_failed: Optional[int] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    estimated_completion: Optional[str] = None
    duration_seconds: Optional[float] = None
    worker_id: Optional[str] = None
    created_by: str
    created_at: str
    metadata: Optional[Dict[str, Any]] = None


class JobCreate(BaseModel):
    """Request to create a background job."""
    job_type: JobType
    priority: JobPriority = JobPriority.normal
    title: str
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class JobStats(BaseModel):
    """Statistics about background jobs."""
    total_jobs: int
    queued: int
    running: int
    completed_24h: int
    failed_24h: int
    average_duration: float
    jobs_by_type: Dict[str, int]
    jobs_by_priority: Dict[str, int]


class JobLogEntry(BaseModel):
    """Log entry for a job."""
    timestamp: str
    level: str  # info, warning, error
    message: str
    details: Optional[Dict[str, Any]] = None


# ============================================================================
# Mock Data Store
# ============================================================================

BACKGROUND_JOBS: Dict[str, Dict] = {
    "job_001": {
        "id": "job_001",
        "job_type": "batch_email_send",
        "status": "running",
        "priority": "high",
        "title": "Send batch emails - Monthly Newsletter",
        "description": "Sending newsletter to 342 contacts",
        "progress_percentage": 67.5,
        "items_total": 342,
        "items_processed": 231,
        "items_failed": 3,
        "started_at": datetime.now().replace(hour=9, minute=30, second=0).isoformat(),
        "completed_at": None,
        "estimated_completion": (datetime.now() + timedelta(minutes=15)).isoformat(),
        "duration_seconds": None,
        "worker_id": "worker-2",
        "created_by": "demo@realestateos.com",
        "created_at": (datetime.now() - timedelta(minutes=30)).isoformat(),
        "metadata": {
            "template_id": "tpl_001",
            "batch_id": "batch_20251112_093000"
        }
    },
    "job_002": {
        "id": "job_002",
        "job_type": "property_enrichment",
        "status": "running",
        "priority": "normal",
        "title": "Enrich imported properties",
        "description": "Enriching 125 properties from CSV import",
        "progress_percentage": 42.4,
        "items_total": 125,
        "items_processed": 53,
        "items_failed": 1,
        "started_at": (datetime.now() - timedelta(minutes=45)).isoformat(),
        "completed_at": None,
        "estimated_completion": (datetime.now() + timedelta(minutes=20)).isoformat(),
        "duration_seconds": None,
        "worker_id": "worker-3",
        "created_by": "demo@realestateos.com",
        "created_at": (datetime.now() - timedelta(hours=1)).isoformat(),
        "metadata": {
            "import_batch_id": "import_20251112_084500",
            "data_sources": ["county_assessor", "public_records", "third_party_api"]
        }
    },
    "job_003": {
        "id": "job_003",
        "job_type": "report_generation",
        "status": "queued",
        "priority": "low",
        "title": "Generate portfolio report",
        "description": "Monthly portfolio performance report",
        "progress_percentage": 0,
        "items_total": 1,
        "items_processed": 0,
        "items_failed": 0,
        "started_at": None,
        "completed_at": None,
        "estimated_completion": None,
        "duration_seconds": None,
        "worker_id": None,
        "created_by": "demo@realestateos.com",
        "created_at": (datetime.now() - timedelta(minutes=5)).isoformat(),
        "metadata": {
            "report_type": "portfolio_performance",
            "period": "2025-10"
        }
    },
    "job_004": {
        "id": "job_004",
        "job_type": "scraping_job",
        "status": "completed",
        "priority": "normal",
        "title": "Scrape property listings",
        "description": "Daily scraping run for new listings",
        "progress_percentage": 100,
        "items_total": 456,
        "items_processed": 456,
        "items_failed": 8,
        "started_at": (datetime.now() - timedelta(hours=2, minutes=30)).isoformat(),
        "completed_at": (datetime.now() - timedelta(minutes=45)).isoformat(),
        "estimated_completion": None,
        "duration_seconds": 6300,
        "worker_id": "worker-1",
        "created_by": "system",
        "created_at": (datetime.now() - timedelta(hours=3)).isoformat(),
        "metadata": {
            "spider_name": "listings_spider",
            "pages_crawled": 92,
            "items_saved": 448
        }
    },
    "job_005": {
        "id": "job_005",
        "job_type": "data_import",
        "status": "failed",
        "priority": "high",
        "title": "Import properties from MLS feed",
        "description": "Daily MLS data import",
        "progress_percentage": 23.5,
        "items_total": 850,
        "items_processed": 200,
        "items_failed": 200,
        "started_at": (datetime.now() - timedelta(hours=1, minutes=15)).isoformat(),
        "completed_at": (datetime.now() - timedelta(hours=1)).isoformat(),
        "estimated_completion": None,
        "duration_seconds": 900,
        "worker_id": "worker-4",
        "created_by": "system",
        "created_at": (datetime.now() - timedelta(hours=1, minutes=30)).isoformat(),
        "metadata": {
            "feed_url": "https://mls.example.com/feed.xml",
            "error": "Connection timeout after 200 records"
        }
    }
}


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/active", response_model=List[BackgroundJob])
def list_active_jobs(job_type: Optional[JobType] = None, priority: Optional[JobPriority] = None):
    """
    List all active (queued or running) background jobs.

    Shows current progress, estimated completion, and job details.
    Can filter by job type and priority.
    """
    # Filter for active jobs
    active_statuses = [JobStatus.queued.value, JobStatus.running.value, JobStatus.retrying.value]
    jobs = [
        job for job in BACKGROUND_JOBS.values()
        if job["status"] in active_statuses
    ]

    # Apply filters
    if job_type:
        jobs = [job for job in jobs if job["job_type"] == job_type.value]
    if priority:
        jobs = [job for job in jobs if job["priority"] == priority.value]

    # Sort by priority (urgent first) then by created_at
    priority_order = {"urgent": 0, "high": 1, "normal": 2, "low": 3}
    jobs.sort(key=lambda j: (priority_order[j["priority"]], j["created_at"]))

    return [BackgroundJob(**job) for job in jobs]


@router.get("/all", response_model=List[BackgroundJob])
def list_all_jobs(
    status: Optional[JobStatus] = None,
    job_type: Optional[JobType] = None,
    limit: int = 50,
    offset: int = 0
):
    """
    List all background jobs with optional filters.

    Includes completed, failed, and cancelled jobs.
    """
    jobs = list(BACKGROUND_JOBS.values())

    # Apply filters
    if status:
        jobs = [job for job in jobs if job["status"] == status.value]
    if job_type:
        jobs = [job for job in jobs if job["job_type"] == job_type.value]

    # Sort by created_at (most recent first)
    jobs.sort(key=lambda j: j["created_at"], reverse=True)

    # Pagination
    paginated = jobs[offset:offset + limit]

    return [BackgroundJob(**job) for job in paginated]


@router.get("/{job_id}", response_model=BackgroundJob)
def get_job(job_id: str):
    """
    Get details of a specific background job.

    Returns current status, progress, and metadata.
    """
    if job_id not in BACKGROUND_JOBS:
        raise HTTPException(status_code=404, detail="Job not found")

    return BackgroundJob(**BACKGROUND_JOBS[job_id])


@router.post("/", response_model=BackgroundJob, status_code=201)
def create_job(job_request: JobCreate):
    """
    Create a new background job.

    Queues the job for execution by workers.
    """
    # Generate new ID
    job_id = f"job_{str(len(BACKGROUND_JOBS) + 1).zfill(3)}"

    new_job = {
        "id": job_id,
        "job_type": job_request.job_type.value,
        "status": "queued",
        "priority": job_request.priority.value,
        "title": job_request.title,
        "description": job_request.description,
        "progress_percentage": 0,
        "items_total": None,
        "items_processed": 0,
        "items_failed": 0,
        "started_at": None,
        "completed_at": None,
        "estimated_completion": None,
        "duration_seconds": None,
        "worker_id": None,
        "created_by": "demo@realestateos.com",
        "created_at": datetime.now().isoformat(),
        "metadata": job_request.metadata or {}
    }

    BACKGROUND_JOBS[job_id] = new_job

    return BackgroundJob(**new_job)


@router.post("/{job_id}/cancel")
def cancel_job(job_id: str):
    """
    Cancel a running or queued job.

    Attempts to gracefully stop the job. May take a few moments
    for the worker to acknowledge the cancellation.
    """
    if job_id not in BACKGROUND_JOBS:
        raise HTTPException(status_code=404, detail="Job not found")

    job = BACKGROUND_JOBS[job_id]

    if job["status"] in ["completed", "failed", "cancelled"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel job with status: {job['status']}"
        )

    job["status"] = "cancelled"
    job["completed_at"] = datetime.now().isoformat()

    return {
        "job_id": job_id,
        "status": "cancelled",
        "message": "Job cancellation requested"
    }


@router.post("/{job_id}/retry")
def retry_job(job_id: str):
    """
    Retry a failed job.

    Creates a new job with the same parameters.
    """
    if job_id not in BACKGROUND_JOBS:
        raise HTTPException(status_code=404, detail="Job not found")

    original_job = BACKGROUND_JOBS[job_id]

    if original_job["status"] != "failed":
        raise HTTPException(
            status_code=400,
            detail="Can only retry failed jobs"
        )

    # Create new job
    new_job_id = f"job_{str(len(BACKGROUND_JOBS) + 1).zfill(3)}"

    new_job = {
        "id": new_job_id,
        "job_type": original_job["job_type"],
        "status": "queued",
        "priority": original_job["priority"],
        "title": f"{original_job['title']} (Retry)",
        "description": original_job["description"],
        "progress_percentage": 0,
        "items_total": original_job["items_total"],
        "items_processed": 0,
        "items_failed": 0,
        "started_at": None,
        "completed_at": None,
        "estimated_completion": None,
        "duration_seconds": None,
        "worker_id": None,
        "created_by": "demo@realestateos.com",
        "created_at": datetime.now().isoformat(),
        "metadata": {
            **original_job.get("metadata", {}),
            "retry_of": job_id
        }
    }

    BACKGROUND_JOBS[new_job_id] = new_job

    return {
        "original_job_id": job_id,
        "new_job_id": new_job_id,
        "message": "Job retry queued"
    }


@router.get("/{job_id}/logs", response_model=List[JobLogEntry])
def get_job_logs(job_id: str, limit: int = 100):
    """
    Get execution logs for a job.

    Returns log entries with timestamps, levels, and messages.
    """
    if job_id not in BACKGROUND_JOBS:
        raise HTTPException(status_code=404, detail="Job not found")

    job = BACKGROUND_JOBS[job_id]

    # Mock log entries
    logs = []
    base_time = datetime.fromisoformat(job["created_at"])

    # Generate mock logs based on job status
    if job["status"] in ["running", "completed"]:
        logs.append(JobLogEntry(
            timestamp=base_time.isoformat(),
            level="info",
            message="Job queued for execution",
            details={"priority": job["priority"]}
        ))

        if job["started_at"]:
            logs.append(JobLogEntry(
                timestamp=job["started_at"],
                level="info",
                message=f"Job started on worker {job['worker_id']}",
                details={"worker_id": job["worker_id"]}
            ))

            # Add progress logs
            if job["items_processed"] and job["items_processed"] > 0:
                logs.append(JobLogEntry(
                    timestamp=(datetime.fromisoformat(job["started_at"]) + timedelta(minutes=5)).isoformat(),
                    level="info",
                    message=f"Processed {job['items_processed']} of {job['items_total']} items",
                    details={
                        "processed": job["items_processed"],
                        "total": job["items_total"],
                        "progress": job["progress_percentage"]
                    }
                ))

            if job["items_failed"] and job["items_failed"] > 0:
                logs.append(JobLogEntry(
                    timestamp=(datetime.fromisoformat(job["started_at"]) + timedelta(minutes=10)).isoformat(),
                    level="warning",
                    message=f"{job['items_failed']} items failed processing",
                    details={"failed_count": job["items_failed"]}
                ))

        if job["status"] == "completed" and job["completed_at"]:
            logs.append(JobLogEntry(
                timestamp=job["completed_at"],
                level="info",
                message="Job completed successfully",
                details={
                    "duration_seconds": job["duration_seconds"],
                    "items_processed": job["items_processed"]
                }
            ))

    elif job["status"] == "failed":
        logs.append(JobLogEntry(
            timestamp=job["completed_at"] or datetime.now().isoformat(),
            level="error",
            message="Job failed with error",
            details=job.get("metadata", {}).get("error", "Unknown error")
        ))

    return logs[:limit]


@router.get("/stats/overview", response_model=JobStats)
def get_job_stats():
    """
    Get statistics about background jobs.

    Returns counts by status, type, and performance metrics.
    """
    jobs = list(BACKGROUND_JOBS.values())

    # Count by status
    queued = sum(1 for j in jobs if j["status"] == "queued")
    running = sum(1 for j in jobs if j["status"] == "running")

    # Count completed/failed in last 24h
    cutoff = (datetime.now() - timedelta(hours=24)).isoformat()
    completed_24h = sum(
        1 for j in jobs
        if j["status"] == "completed" and j.get("completed_at", "") > cutoff
    )
    failed_24h = sum(
        1 for j in jobs
        if j["status"] == "failed" and j.get("completed_at", "") > cutoff
    )

    # Calculate average duration
    durations = [j["duration_seconds"] for j in jobs if j.get("duration_seconds")]
    avg_duration = sum(durations) / len(durations) if durations else 0

    # Count by type
    jobs_by_type = {}
    for job in jobs:
        job_type = job["job_type"]
        jobs_by_type[job_type] = jobs_by_type.get(job_type, 0) + 1

    # Count by priority
    jobs_by_priority = {}
    for job in jobs:
        priority = job["priority"]
        jobs_by_priority[priority] = jobs_by_priority.get(priority, 0) + 1

    return JobStats(
        total_jobs=len(jobs),
        queued=queued,
        running=running,
        completed_24h=completed_24h,
        failed_24h=failed_24h,
        average_duration=round(avg_duration, 2),
        jobs_by_type=jobs_by_type,
        jobs_by_priority=jobs_by_priority
    )
