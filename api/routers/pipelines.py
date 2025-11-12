"""
Pipeline monitoring endpoints - Airflow DAG status and execution
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, Integer
from datetime import datetime, timedelta
import httpx

from ..database import get_db
from ..models import PipelineRun, ScrapingJob, EnrichmentJob
from ..services.airflow_client import airflow_client


router = APIRouter(prefix="/pipelines", tags=["Pipelines"])


@router.get("/overview")
async def get_pipeline_overview():
    """
    Get high-level overview of all pipeline activity
    """
    try:
        stats = await airflow_client.get_dag_stats()
        return {
            "status": "success",
            "data": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dags")
async def list_dags(
    limit: int = Query(100, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """
    List all available DAGs
    """
    try:
        dags = await airflow_client.get_dags(limit=limit, offset=offset)
        return {
            "status": "success",
            "data": dags
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dags/{dag_id}")
async def get_dag_details(dag_id: str):
    """
    Get details for a specific DAG
    """
    try:
        dag = await airflow_client.get_dag(dag_id)
        return {
            "status": "success",
            "data": dag
        }
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"DAG {dag_id} not found")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dags/{dag_id}/runs")
async def get_dag_runs(
    dag_id: str,
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    state: Optional[str] = Query(None)
):
    """
    Get execution runs for a specific DAG
    """
    try:
        runs = await airflow_client.get_dag_runs(
            dag_id=dag_id,
            limit=limit,
            offset=offset,
            state=state
        )
        return {
            "status": "success",
            "data": runs
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dags/{dag_id}/runs/{dag_run_id}")
async def get_dag_run_details(dag_id: str, dag_run_id: str):
    """
    Get details for a specific DAG run
    """
    try:
        run = await airflow_client.get_dag_run(dag_id, dag_run_id)
        return {
            "status": "success",
            "data": run
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dags/{dag_id}/runs/{dag_run_id}/tasks")
async def get_dag_run_tasks(dag_id: str, dag_run_id: str):
    """
    Get task instances for a specific DAG run
    """
    try:
        tasks = await airflow_client.get_task_instances(dag_id, dag_run_id)
        return {
            "status": "success",
            "data": tasks
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dags/{dag_id}/trigger")
async def trigger_dag(
    dag_id: str,
    conf: Optional[Dict[str, Any]] = None
):
    """
    Trigger a DAG run
    """
    try:
        result = await airflow_client.trigger_dag(dag_id, conf)
        return {
            "status": "success",
            "message": f"DAG {dag_id} triggered successfully",
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/runs/recent")
async def get_recent_runs(
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=100)
):
    """
    Get recent pipeline runs from database
    """
    try:
        runs = db.query(PipelineRun)\
            .order_by(desc(PipelineRun.created_at))\
            .limit(limit)\
            .all()

        return {
            "status": "success",
            "data": [
                {
                    "id": run.id,
                    "dag_id": run.dag_id,
                    "dag_run_id": run.dag_run_id,
                    "status": run.status,
                    "execution_date": run.execution_date.isoformat() if run.execution_date else None,
                    "started_at": run.started_at.isoformat() if run.started_at else None,
                    "completed_at": run.completed_at.isoformat() if run.completed_at else None,
                    "duration_seconds": run.duration_seconds,
                    "tasks_total": run.tasks_total,
                    "tasks_success": run.tasks_success,
                    "tasks_failed": run.tasks_failed
                }
                for run in runs
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/daily")
async def get_daily_stats(
    db: Session = Depends(get_db),
    days: int = Query(7, ge=1, le=30)
):
    """
    Get daily pipeline execution statistics
    """
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Query pipeline runs grouped by day
        stats = db.query(
            func.date(PipelineRun.execution_date).label("date"),
            func.count(PipelineRun.id).label("total_runs"),
            func.sum(func.cast(PipelineRun.status == "success", Integer)).label("successful_runs"),
            func.sum(func.cast(PipelineRun.status == "failed", Integer)).label("failed_runs"),
            func.avg(PipelineRun.duration_seconds).label("avg_duration")
        ).filter(
            PipelineRun.execution_date >= cutoff_date
        ).group_by(
            func.date(PipelineRun.execution_date)
        ).all()

        return {
            "status": "success",
            "data": [
                {
                    "date": stat.date.isoformat() if stat.date else None,
                    "total_runs": stat.total_runs or 0,
                    "successful_runs": stat.successful_runs or 0,
                    "failed_runs": stat.failed_runs or 0,
                    "avg_duration_seconds": float(stat.avg_duration) if stat.avg_duration else 0
                }
                for stat in stats
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
