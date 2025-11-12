"""
Scraping jobs monitoring endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, Integer
from datetime import datetime, timedelta

from ..database import get_db
from ..models import ScrapingJob, ProspectQueue, JobStatus


router = APIRouter(prefix="/scraping", tags=["Scraping"])


@router.get("/jobs")
async def list_scraping_jobs(
    db: Session = Depends(get_db),
    status: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """
    List scraping jobs with optional filters
    """
    try:
        query = db.query(ScrapingJob)

        if status:
            query = query.filter(ScrapingJob.status == status)
        if source:
            query = query.filter(ScrapingJob.source == source)

        total = query.count()
        jobs = query.order_by(desc(ScrapingJob.created_at))\
            .limit(limit)\
            .offset(offset)\
            .all()

        return {
            "status": "success",
            "total": total,
            "limit": limit,
            "offset": offset,
            "data": [
                {
                    "id": job.id,
                    "dag_id": job.dag_id,
                    "dag_run_id": job.dag_run_id,
                    "source": job.source,
                    "status": job.status.value if job.status else None,
                    "items_scraped": job.items_scraped,
                    "items_failed": job.items_failed,
                    "started_at": job.started_at.isoformat() if job.started_at else None,
                    "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                    "created_at": job.created_at.isoformat() if job.created_at else None
                }
                for job in jobs
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/{job_id}")
async def get_scraping_job(
    job_id: int,
    db: Session = Depends(get_db)
):
    """
    Get details for a specific scraping job
    """
    try:
        job = db.query(ScrapingJob).filter(ScrapingJob.id == job_id).first()

        if not job:
            raise HTTPException(status_code=404, detail=f"Scraping job {job_id} not found")

        return {
            "status": "success",
            "data": {
                "id": job.id,
                "dag_id": job.dag_id,
                "dag_run_id": job.dag_run_id,
                "source": job.source,
                "status": job.status.value if job.status else None,
                "items_scraped": job.items_scraped,
                "items_failed": job.items_failed,
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "config": job.config,
                "error_log": job.error_log,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "updated_at": job.updated_at.isoformat() if job.updated_at else None
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/queue")
async def get_prospect_queue(
    db: Session = Depends(get_db),
    status: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """
    Get items from the prospect queue (scraped data)
    """
    try:
        query = db.query(ProspectQueue)

        if status:
            query = query.filter(ProspectQueue.status == status)
        if source:
            query = query.filter(ProspectQueue.source == source)

        total = query.count()
        prospects = query.order_by(desc(ProspectQueue.created_at))\
            .limit(limit)\
            .offset(offset)\
            .all()

        return {
            "status": "success",
            "total": total,
            "limit": limit,
            "offset": offset,
            "data": [
                {
                    "id": prospect.id,
                    "source": prospect.source,
                    "source_id": prospect.source_id,
                    "url": prospect.url,
                    "status": prospect.status,
                    "created_at": prospect.created_at.isoformat() if prospect.created_at else None,
                    "updated_at": prospect.updated_at.isoformat() if prospect.updated_at else None,
                    "payload": prospect.payload
                }
                for prospect in prospects
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/overview")
async def get_scraping_stats(db: Session = Depends(get_db)):
    """
    Get overall scraping statistics
    """
    try:
        # Job statistics
        total_jobs = db.query(func.count(ScrapingJob.id)).scalar() or 0
        running_jobs = db.query(func.count(ScrapingJob.id))\
            .filter(ScrapingJob.status == JobStatus.RUNNING)\
            .scalar() or 0
        queued_jobs = db.query(func.count(ScrapingJob.id))\
            .filter(ScrapingJob.status == JobStatus.QUEUED)\
            .scalar() or 0

        # Success/failure rates
        successful_jobs = db.query(func.count(ScrapingJob.id))\
            .filter(ScrapingJob.status == JobStatus.SUCCESS)\
            .scalar() or 0
        failed_jobs = db.query(func.count(ScrapingJob.id))\
            .filter(ScrapingJob.status == JobStatus.FAILED)\
            .scalar() or 0

        # Prospect queue statistics
        total_prospects = db.query(func.count(ProspectQueue.id)).scalar() or 0
        new_prospects = db.query(func.count(ProspectQueue.id))\
            .filter(ProspectQueue.status == "new")\
            .scalar() or 0
        processed_prospects = db.query(func.count(ProspectQueue.id))\
            .filter(ProspectQueue.status.in_(["enriched", "scored"]))\
            .scalar() or 0

        # Items scraped (total)
        total_items_scraped = db.query(func.sum(ScrapingJob.items_scraped)).scalar() or 0
        total_items_failed = db.query(func.sum(ScrapingJob.items_failed)).scalar() or 0

        # Recent activity (last 24 hours)
        last_24h = datetime.utcnow() - timedelta(hours=24)
        recent_prospects = db.query(func.count(ProspectQueue.id))\
            .filter(ProspectQueue.created_at >= last_24h)\
            .scalar() or 0

        # Source breakdown
        sources = db.query(
            ProspectQueue.source,
            func.count(ProspectQueue.id).label("count")
        ).group_by(ProspectQueue.source).all()

        return {
            "status": "success",
            "data": {
                "jobs": {
                    "total": total_jobs,
                    "running": running_jobs,
                    "queued": queued_jobs,
                    "successful": successful_jobs,
                    "failed": failed_jobs,
                    "success_rate": round((successful_jobs / total_jobs * 100) if total_jobs > 0 else 0, 2)
                },
                "prospects": {
                    "total": total_prospects,
                    "new": new_prospects,
                    "processed": processed_prospects,
                    "processing_rate": round((processed_prospects / total_prospects * 100) if total_prospects > 0 else 0, 2)
                },
                "items": {
                    "scraped": total_items_scraped,
                    "failed": total_items_failed,
                    "success_rate": round((total_items_scraped / (total_items_scraped + total_items_failed) * 100) if (total_items_scraped + total_items_failed) > 0 else 0, 2)
                },
                "recent_activity": {
                    "last_24h_prospects": recent_prospects
                },
                "sources": [
                    {"source": source, "count": count}
                    for source, count in sources
                ]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/daily")
async def get_daily_scraping_stats(
    db: Session = Depends(get_db),
    days: int = Query(7, ge=1, le=30)
):
    """
    Get daily scraping statistics
    """
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Daily prospect counts
        daily_stats = db.query(
            func.date(ProspectQueue.created_at).label("date"),
            func.count(ProspectQueue.id).label("prospects_scraped"),
            ProspectQueue.source
        ).filter(
            ProspectQueue.created_at >= cutoff_date
        ).group_by(
            func.date(ProspectQueue.created_at),
            ProspectQueue.source
        ).all()

        # Format the data
        stats_by_date = {}
        for stat in daily_stats:
            date_str = stat.date.isoformat() if stat.date else None
            if date_str not in stats_by_date:
                stats_by_date[date_str] = {
                    "date": date_str,
                    "total": 0,
                    "by_source": {}
                }
            stats_by_date[date_str]["total"] += stat.prospects_scraped
            stats_by_date[date_str]["by_source"][stat.source] = stat.prospects_scraped

        return {
            "status": "success",
            "data": list(stats_by_date.values())
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
