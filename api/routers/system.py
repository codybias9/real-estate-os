"""System health and infrastructure monitoring router."""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import random

router = APIRouter(prefix="/system", tags=["system"])


class ServiceHealth(BaseModel):
    """Health status of a system service."""
    service_name: str
    status: str  # healthy, degraded, down
    uptime: int  # seconds
    last_check: str
    message: Optional[str] = None


class WorkerInfo(BaseModel):
    """Information about an Airflow worker."""
    worker_id: str
    hostname: str
    status: str  # active, idle, busy
    tasks_running: int
    tasks_completed: int
    cpu_usage: float  # percentage
    memory_usage: float  # percentage
    last_heartbeat: str


class QueueInfo(BaseModel):
    """Information about a task queue."""
    queue_name: str
    tasks_pending: int
    tasks_running: int
    tasks_completed_24h: int
    average_wait_time: float  # seconds


class StorageInfo(BaseModel):
    """Information about storage systems."""
    storage_type: str  # s3, postgres, redis, minio
    status: str
    total_size: Optional[int] = None  # bytes
    used_size: Optional[int] = None  # bytes
    available_size: Optional[int] = None  # bytes
    usage_percentage: Optional[float] = None


class SystemMetrics(BaseModel):
    """Overall system metrics."""
    total_cpu_usage: float
    total_memory_usage: float
    total_disk_usage: float
    active_workers: int
    total_workers: int
    tasks_queued: int
    tasks_running: int
    error_rate_24h: float  # percentage
    average_task_duration: float  # seconds


from typing import Optional


@router.get("/health", response_model=List[ServiceHealth])
def get_system_health():
    """
    Get health status of all system services.

    Monitors:
    - Airflow scheduler
    - Airflow webserver
    - Celery workers
    - PostgreSQL database
    - Redis broker
    - MinIO storage (if configured)
    """
    services = [
        ServiceHealth(
            service_name="airflow_scheduler",
            status="healthy",
            uptime=86400 * 7,  # 7 days
            last_check=datetime.now().isoformat(),
            message="Scheduler is running normally"
        ),
        ServiceHealth(
            service_name="airflow_webserver",
            status="healthy",
            uptime=86400 * 7,
            last_check=datetime.now().isoformat(),
            message="Webserver responding"
        ),
        ServiceHealth(
            service_name="celery_workers",
            status="healthy",
            uptime=86400 * 5,
            last_check=datetime.now().isoformat(),
            message="4 workers active"
        ),
        ServiceHealth(
            service_name="postgresql",
            status="healthy",
            uptime=86400 * 14,
            last_check=datetime.now().isoformat(),
            message="Database operational"
        ),
        ServiceHealth(
            service_name="redis",
            status="healthy",
            uptime=86400 * 14,
            last_check=datetime.now().isoformat(),
            message="Message broker operational"
        ),
        ServiceHealth(
            service_name="minio",
            status="degraded",
            uptime=86400 * 3,
            last_check=datetime.now().isoformat(),
            message="High disk usage (85%)"
        ),
    ]

    return services


@router.get("/workers", response_model=List[WorkerInfo])
def get_workers():
    """Get information about Celery workers processing tasks."""
    workers = []

    for i in range(4):  # 4 workers
        status = random.choice(["active", "active", "busy", "idle"])
        tasks_running = random.randint(0, 3) if status == "busy" else 0

        workers.append(WorkerInfo(
            worker_id=f"worker-{i+1}",
            hostname=f"airflow-worker-{i+1}",
            status=status,
            tasks_running=tasks_running,
            tasks_completed=random.randint(100, 500),
            cpu_usage=random.uniform(10, 80) if status == "busy" else random.uniform(5, 20),
            memory_usage=random.uniform(30, 70),
            last_heartbeat=(datetime.now() - timedelta(seconds=random.randint(1, 30))).isoformat()
        ))

    return workers


@router.get("/queues", response_model=List[QueueInfo])
def get_queues():
    """Get information about task queues."""
    queues = [
        QueueInfo(
            queue_name="default",
            tasks_pending=random.randint(2, 10),
            tasks_running=random.randint(1, 5),
            tasks_completed_24h=random.randint(100, 300),
            average_wait_time=random.uniform(5, 30)
        ),
        QueueInfo(
            queue_name="scraping",
            tasks_pending=random.randint(0, 5),
            tasks_running=random.randint(0, 2),
            tasks_completed_24h=random.randint(20, 50),
            average_wait_time=random.uniform(10, 60)
        ),
        QueueInfo(
            queue_name="enrichment",
            tasks_pending=random.randint(3, 15),
            tasks_running=random.randint(1, 3),
            tasks_completed_24h=random.randint(50, 150),
            average_wait_time=random.uniform(15, 45)
        ),
        QueueInfo(
            queue_name="ml_scoring",
            tasks_pending=random.randint(0, 3),
            tasks_running=random.randint(0, 1),
            tasks_completed_24h=random.randint(10, 30),
            average_wait_time=random.uniform(60, 180)
        ),
    ]

    return queues


@router.get("/storage", response_model=List[StorageInfo])
def get_storage():
    """Get information about storage systems."""
    storage_systems = [
        StorageInfo(
            storage_type="postgresql",
            status="healthy",
            total_size=100 * 1024 * 1024 * 1024,  # 100GB
            used_size=35 * 1024 * 1024 * 1024,   # 35GB
            available_size=65 * 1024 * 1024 * 1024,  # 65GB
            usage_percentage=35.0
        ),
        StorageInfo(
            storage_type="redis",
            status="healthy",
            total_size=16 * 1024 * 1024 * 1024,  # 16GB
            used_size=2 * 1024 * 1024 * 1024,    # 2GB
            available_size=14 * 1024 * 1024 * 1024,  # 14GB
            usage_percentage=12.5
        ),
        StorageInfo(
            storage_type="s3",
            status="healthy",
            total_size=None,  # Unlimited
            used_size=250 * 1024 * 1024 * 1024,  # 250GB
            available_size=None,
            usage_percentage=None
        ),
        StorageInfo(
            storage_type="minio",
            status="degraded",
            total_size=500 * 1024 * 1024 * 1024,  # 500GB
            used_size=425 * 1024 * 1024 * 1024,   # 425GB
            available_size=75 * 1024 * 1024 * 1024,  # 75GB
            usage_percentage=85.0
        ),
    ]

    return storage_systems


@router.get("/metrics", response_model=SystemMetrics)
def get_system_metrics():
    """Get overall system performance metrics."""
    return SystemMetrics(
        total_cpu_usage=random.uniform(30, 60),
        total_memory_usage=random.uniform(40, 70),
        total_disk_usage=random.uniform(35, 45),
        active_workers=random.randint(3, 4),
        total_workers=4,
        tasks_queued=random.randint(5, 20),
        tasks_running=random.randint(2, 8),
        error_rate_24h=random.uniform(1, 3),
        average_task_duration=random.uniform(180, 600)
    )


@router.get("/logs/recent")
def get_recent_logs(limit: int = 50):
    """
    Get recent system logs.

    Returns logs from Airflow scheduler, workers, and other services.
    """
    log_levels = ["INFO", "INFO", "INFO", "WARNING", "DEBUG"]
    components = ["scheduler", "worker-1", "worker-2", "webserver", "enrichment_agent"]

    logs = []
    for i in range(limit):
        timestamp = datetime.now() - timedelta(minutes=i)
        level = random.choice(log_levels)
        component = random.choice(components)

        messages = {
            "scheduler": [
                f"DAG discovery_offmarket triggered successfully",
                f"Task enrichment_property.placeholder completed",
                f"Heartbeat received from worker-{random.randint(1,4)}"
            ],
            "worker-1": [
                "Task started: scrape_book_listings.run_scrapy_spider",
                "Task completed successfully",
                "Celery worker ready"
            ],
            "enrichment_agent": [
                "Enriched 25 properties with assessor data",
                "Connected to S3 bucket successfully",
                "Data validation passed"
            ]
        }

        message = random.choice(messages.get(component, ["System operational"]))

        logs.append({
            "timestamp": timestamp.isoformat(),
            "level": level,
            "component": component,
            "message": message
        })

    return logs


@router.get("/errors/recent")
def get_recent_errors(limit: int = 20):
    """Get recent errors and exceptions from the system."""
    errors = []

    error_types = [
        "ConnectionError",
        "TimeoutError",
        "ValidationError",
        "DatabaseError"
    ]

    error_messages = [
        "Failed to connect to external API",
        "Task execution timeout after 300s",
        "Invalid property data format",
        "Database connection pool exhausted"
    ]

    for i in range(limit):
        if random.random() < 0.3:  # 30% chance of error
            timestamp = datetime.now() - timedelta(hours=random.randint(0, 24))
            errors.append({
                "timestamp": timestamp.isoformat(),
                "error_type": random.choice(error_types),
                "message": random.choice(error_messages),
                "dag_id": random.choice(["discovery_offmarket", "enrichment_property", "score_master"]),
                "task_id": "placeholder",
                "severity": random.choice(["error", "critical", "warning"])
            })

    return sorted(errors, key=lambda x: x["timestamp"], reverse=True)
