"""Pipelines router for data processing workflow management."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from enum import Enum
import random

router = APIRouter(prefix="/pipelines", tags=["pipelines"])


class DAGStatus(str, Enum):
    """DAG execution status."""
    running = "running"
    success = "success"
    failed = "failed"
    queued = "queued"


class PipelineType(str, Enum):
    """Type of data pipeline."""
    scraping = "scraping"
    enrichment = "enrichment"
    scoring = "scoring"
    document_generation = "document_generation"
    discovery = "discovery"


class DAGRunInfo(BaseModel):
    """Information about a DAG run."""
    dag_id: str
    run_id: str
    status: DAGStatus
    start_date: str
    end_date: Optional[str]
    duration: Optional[int]  # seconds
    tasks_total: int
    tasks_succeeded: int
    tasks_failed: int
    tasks_running: int


class DAGInfo(BaseModel):
    """Information about a DAG."""
    dag_id: str
    description: str
    schedule_interval: Optional[str]
    is_paused: bool
    is_active: bool
    last_run: Optional[DAGRunInfo]
    next_run: Optional[str]
    tags: List[str]
    pipeline_type: PipelineType


class PipelineMetrics(BaseModel):
    """Overall pipeline metrics."""
    total_dags: int
    active_dags: int
    paused_dags: int
    running_tasks: int
    queued_tasks: int
    failed_tasks_24h: int
    successful_runs_24h: int
    average_duration: float  # seconds
    total_properties_processed_24h: int
    total_properties_enriched_24h: int
    total_documents_generated_24h: int


class ScrapingJobInfo(BaseModel):
    """Information about a scraping job."""
    job_id: str
    spider_name: str
    status: DAGStatus
    start_time: str
    end_time: Optional[str]
    items_scraped: int
    items_dropped: int
    pages_crawled: int
    errors: int


class EnrichmentJobInfo(BaseModel):
    """Information about an enrichment job."""
    job_id: str
    status: DAGStatus
    start_time: str
    end_time: Optional[str]
    properties_processed: int
    properties_enriched: int
    enrichment_sources: List[str]
    errors: int


# Mock data for DAGs based on actual DAGs in the codebase
MOCK_DAGS = [
    DAGInfo(
        dag_id="scrape_book_listings",
        description="Scrape book listings from books.toscrape.com for demonstration",
        schedule_interval="0 0 * * *",  # Daily at midnight
        is_paused=False,
        is_active=True,
        last_run=DAGRunInfo(
            dag_id="scrape_book_listings",
            run_id="manual__2025-11-12T00:00:00",
            status=DAGStatus.success,
            start_date=(datetime.now() - timedelta(hours=2)).isoformat(),
            end_date=(datetime.now() - timedelta(hours=1, minutes=45)).isoformat(),
            duration=900,
            tasks_total=1,
            tasks_succeeded=1,
            tasks_failed=0,
            tasks_running=0
        ),
        next_run=(datetime.now() + timedelta(hours=22)).isoformat(),
        tags=["scraping", "data-ingestion"],
        pipeline_type=PipelineType.scraping
    ),
    DAGInfo(
        dag_id="discovery_offmarket",
        description="Scrape off-market leads and put JSON rows into prospect_queue",
        schedule_interval="@hourly",
        is_paused=False,
        is_active=True,
        last_run=DAGRunInfo(
            dag_id="discovery_offmarket",
            run_id="scheduled__2025-11-12T16:00:00",
            status=DAGStatus.running,
            start_date=(datetime.now() - timedelta(minutes=15)).isoformat(),
            end_date=None,
            duration=None,
            tasks_total=1,
            tasks_succeeded=0,
            tasks_failed=0,
            tasks_running=1
        ),
        next_run=(datetime.now() + timedelta(minutes=45)).isoformat(),
        tags=["pipeline", "discovery"],
        pipeline_type=PipelineType.discovery
    ),
    DAGInfo(
        dag_id="enrichment_property",
        description="Join assessor API data onto prospect_queue",
        schedule_interval="@hourly",
        is_paused=False,
        is_active=True,
        last_run=DAGRunInfo(
            dag_id="enrichment_property",
            run_id="scheduled__2025-11-12T15:00:00",
            status=DAGStatus.success,
            start_date=(datetime.now() - timedelta(hours=1, minutes=10)).isoformat(),
            end_date=(datetime.now() - timedelta(hours=1)).isoformat(),
            duration=600,
            tasks_total=1,
            tasks_succeeded=1,
            tasks_failed=0,
            tasks_running=0
        ),
        next_run=(datetime.now() + timedelta(minutes=50)).isoformat(),
        tags=["pipeline", "enrichment"],
        pipeline_type=PipelineType.enrichment
    ),
    DAGInfo(
        dag_id="score_master",
        description="Vector embed + LightGBM score properties",
        schedule_interval="@hourly",
        is_paused=True,
        is_active=False,
        last_run=DAGRunInfo(
            dag_id="score_master",
            run_id="scheduled__2025-11-12T14:00:00",
            status=DAGStatus.success,
            start_date=(datetime.now() - timedelta(hours=2, minutes=5)).isoformat(),
            end_date=(datetime.now() - timedelta(hours=1, minutes=50)).isoformat(),
            duration=900,
            tasks_total=1,
            tasks_succeeded=1,
            tasks_failed=0,
            tasks_running=0
        ),
        next_run=None,
        tags=["pipeline", "ml", "scoring"],
        pipeline_type=PipelineType.scoring
    ),
    DAGInfo(
        dag_id="docgen_packet",
        description="Render Investor Memo PDF into MinIO",
        schedule_interval="@hourly",
        is_paused=True,
        is_active=False,
        last_run=DAGRunInfo(
            dag_id="docgen_packet",
            run_id="scheduled__2025-11-12T14:00:00",
            status=DAGStatus.success,
            start_date=(datetime.now() - timedelta(hours=2, minutes=15)).isoformat(),
            end_date=(datetime.now() - timedelta(hours=2)).isoformat(),
            duration=900,
            tasks_total=1,
            tasks_succeeded=1,
            tasks_failed=0,
            tasks_running=0
        ),
        next_run=None,
        tags=["pipeline", "documents"],
        pipeline_type=PipelineType.document_generation
    ),
    DAGInfo(
        dag_id="property_processing_pipeline",
        description="End-to-end property processing workflow",
        schedule_interval=None,  # Manual trigger only
        is_paused=False,
        is_active=True,
        last_run=None,
        next_run=None,
        tags=["pipeline"],
        pipeline_type=PipelineType.enrichment
    ),
]


@router.get("/dags", response_model=List[DAGInfo])
def list_dags(
    pipeline_type: Optional[PipelineType] = None,
    active_only: bool = Query(False, description="Show only active DAGs")
):
    """
    List all Airflow DAGs with their current status.

    This endpoint provides information about all data processing pipelines
    including scraping jobs, enrichment workflows, and ML scoring.
    """
    filtered_dags = MOCK_DAGS

    if pipeline_type:
        filtered_dags = [dag for dag in filtered_dags if dag.pipeline_type == pipeline_type]

    if active_only:
        filtered_dags = [dag for dag in filtered_dags if dag.is_active]

    return filtered_dags


@router.get("/dags/{dag_id}", response_model=DAGInfo)
def get_dag(dag_id: str):
    """Get detailed information about a specific DAG."""
    for dag in MOCK_DAGS:
        if dag.dag_id == dag_id:
            return dag

    raise HTTPException(status_code=404, detail=f"DAG '{dag_id}' not found")


@router.get("/dags/{dag_id}/runs", response_model=List[DAGRunInfo])
def get_dag_runs(
    dag_id: str,
    limit: int = Query(10, ge=1, le=100)
):
    """Get recent runs for a specific DAG."""
    # Check if DAG exists
    dag_exists = any(dag.dag_id == dag_id for dag in MOCK_DAGS)
    if not dag_exists:
        raise HTTPException(status_code=404, detail=f"DAG '{dag_id}' not found")

    # Generate mock run history
    runs = []
    for i in range(limit):
        status = random.choice([DAGStatus.success, DAGStatus.success, DAGStatus.success, DAGStatus.failed])
        start = datetime.now() - timedelta(hours=i*2)
        end = start + timedelta(minutes=random.randint(10, 60))

        runs.append(DAGRunInfo(
            dag_id=dag_id,
            run_id=f"scheduled__{start.isoformat()}",
            status=status,
            start_date=start.isoformat(),
            end_date=end.isoformat(),
            duration=int((end - start).total_seconds()),
            tasks_total=random.randint(1, 5),
            tasks_succeeded=random.randint(1, 5),
            tasks_failed=0 if status == DAGStatus.success else random.randint(1, 2),
            tasks_running=0
        ))

    return runs


@router.get("/metrics", response_model=PipelineMetrics)
def get_pipeline_metrics():
    """
    Get overall metrics for all data processing pipelines.

    This provides a high-level overview of the platform's data processing health.
    """
    return PipelineMetrics(
        total_dags=len(MOCK_DAGS),
        active_dags=sum(1 for dag in MOCK_DAGS if dag.is_active),
        paused_dags=sum(1 for dag in MOCK_DAGS if dag.is_paused),
        running_tasks=2,
        queued_tasks=5,
        failed_tasks_24h=3,
        successful_runs_24h=48,
        average_duration=720.5,
        total_properties_processed_24h=1247,
        total_properties_enriched_24h=1189,
        total_documents_generated_24h=342
    )


@router.get("/scraping/jobs", response_model=List[ScrapingJobInfo])
def get_scraping_jobs(limit: int = Query(10, ge=1, le=100)):
    """Get recent scraping jobs with their statistics."""
    jobs = []
    for i in range(limit):
        status = random.choice([DAGStatus.success, DAGStatus.success, DAGStatus.running, DAGStatus.failed])
        start = datetime.now() - timedelta(hours=i)
        end = None if status == DAGStatus.running else start + timedelta(minutes=random.randint(15, 45))

        jobs.append(ScrapingJobInfo(
            job_id=f"scrape_{start.strftime('%Y%m%d_%H%M%S')}",
            spider_name="listings",
            status=status,
            start_time=start.isoformat(),
            end_time=end.isoformat() if end else None,
            items_scraped=random.randint(50, 500) if status != DAGStatus.running else random.randint(10, 100),
            items_dropped=random.randint(0, 5),
            pages_crawled=random.randint(10, 50),
            errors=0 if status == DAGStatus.success else random.randint(1, 3)
        ))

    return jobs


@router.get("/enrichment/jobs", response_model=List[EnrichmentJobInfo])
def get_enrichment_jobs(limit: int = Query(10, ge=1, le=100)):
    """Get recent enrichment jobs with their statistics."""
    jobs = []
    for i in range(limit):
        status = random.choice([DAGStatus.success, DAGStatus.success, DAGStatus.running, DAGStatus.failed])
        start = datetime.now() - timedelta(hours=i)
        end = None if status == DAGStatus.running else start + timedelta(minutes=random.randint(10, 30))

        processed = random.randint(50, 200)
        enriched = processed - random.randint(0, 10) if status == DAGStatus.success else processed - random.randint(10, 50)

        jobs.append(EnrichmentJobInfo(
            job_id=f"enrich_{start.strftime('%Y%m%d_%H%M%S')}",
            status=status,
            start_time=start.isoformat(),
            end_time=end.isoformat() if end else None,
            properties_processed=processed,
            properties_enriched=enriched,
            enrichment_sources=["assessor_api", "zillow", "redfin", "county_records"],
            errors=processed - enriched
        ))

    return jobs


@router.post("/dags/{dag_id}/trigger")
def trigger_dag(dag_id: str, config: Optional[Dict[str, Any]] = None):
    """
    Trigger a DAG run manually.

    In a real implementation, this would call the Airflow API to trigger the DAG.
    For demo purposes, this returns a mock response.
    """
    dag_exists = any(dag.dag_id == dag_id for dag in MOCK_DAGS)
    if not dag_exists:
        raise HTTPException(status_code=404, detail=f"DAG '{dag_id}' not found")

    run_id = f"manual__{datetime.now().isoformat()}"

    return {
        "message": f"DAG '{dag_id}' triggered successfully",
        "run_id": run_id,
        "dag_id": dag_id,
        "execution_date": datetime.now().isoformat()
    }


@router.post("/dags/{dag_id}/pause")
def pause_dag(dag_id: str):
    """Pause a DAG (prevent new runs from being scheduled)."""
    dag_exists = any(dag.dag_id == dag_id for dag in MOCK_DAGS)
    if not dag_exists:
        raise HTTPException(status_code=404, detail=f"DAG '{dag_id}' not found")

    return {
        "message": f"DAG '{dag_id}' paused successfully",
        "dag_id": dag_id,
        "is_paused": True
    }


@router.post("/dags/{dag_id}/unpause")
def unpause_dag(dag_id: str):
    """Unpause a DAG (resume scheduled runs)."""
    dag_exists = any(dag.dag_id == dag_id for dag in MOCK_DAGS)
    if not dag_exists:
        raise HTTPException(status_code=404, detail=f"DAG '{dag_id}' not found")

    return {
        "message": f"DAG '{dag_id}' unpaused successfully",
        "dag_id": dag_id,
        "is_paused": False
    }
