"""
Data quality and platform metrics endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta

from ..database import get_db
from ..models import (
    DataQualityMetric,
    ProspectQueue,
    Property,
    PropertyScore,
    ScrapingJob,
    EnrichmentJob,
    PipelineRun,
    JobStatus
)


router = APIRouter(prefix="/metrics", tags=["Metrics"])


@router.get("/overview")
async def get_platform_metrics_overview(db: Session = Depends(get_db)):
    """
    Get high-level platform metrics overview
    """
    try:
        # Data pipeline metrics
        total_prospects = db.query(func.count(ProspectQueue.id)).scalar() or 0
        total_properties = db.query(func.count(Property.id)).scalar() or 0
        total_scores = db.query(func.count(PropertyScore.id)).scalar() or 0

        # Pipeline execution metrics
        total_pipeline_runs = db.query(func.count(PipelineRun.id)).scalar() or 0
        successful_runs = db.query(func.count(PipelineRun.id))\
            .filter(PipelineRun.status == "success")\
            .scalar() or 0

        # Active jobs
        active_scraping_jobs = db.query(func.count(ScrapingJob.id))\
            .filter(ScrapingJob.status.in_([JobStatus.RUNNING, JobStatus.QUEUED]))\
            .scalar() or 0
        active_enrichment_jobs = db.query(func.count(EnrichmentJob.id))\
            .filter(EnrichmentJob.status.in_([JobStatus.RUNNING, JobStatus.QUEUED]))\
            .scalar() or 0

        # Data flow metrics
        new_prospects = db.query(func.count(ProspectQueue.id))\
            .filter(ProspectQueue.status == "new")\
            .scalar() or 0
        enriched_properties = db.query(func.count(Property.id))\
            .filter(Property.enrichment_data.isnot(None))\
            .scalar() or 0

        # Recent activity (last 24 hours)
        last_24h = datetime.utcnow() - timedelta(hours=24)
        recent_prospects = db.query(func.count(ProspectQueue.id))\
            .filter(ProspectQueue.created_at >= last_24h)\
            .scalar() or 0
        recent_enrichments = db.query(func.count(Property.id))\
            .filter(Property.created_at >= last_24h)\
            .scalar() or 0
        recent_scores = db.query(func.count(PropertyScore.id))\
            .filter(PropertyScore.created_at >= last_24h)\
            .scalar() or 0

        return {
            "status": "success",
            "data": {
                "data_pipeline": {
                    "total_prospects": total_prospects,
                    "total_properties": total_properties,
                    "total_scores": total_scores,
                    "new_prospects_pending": new_prospects,
                    "enriched_properties": enriched_properties
                },
                "pipeline_execution": {
                    "total_runs": total_pipeline_runs,
                    "successful_runs": successful_runs,
                    "success_rate": round((successful_runs / total_pipeline_runs * 100) if total_pipeline_runs > 0 else 0, 2)
                },
                "active_jobs": {
                    "scraping": active_scraping_jobs,
                    "enrichment": active_enrichment_jobs,
                    "total": active_scraping_jobs + active_enrichment_jobs
                },
                "recent_activity_24h": {
                    "prospects_scraped": recent_prospects,
                    "properties_enriched": recent_enrichments,
                    "properties_scored": recent_scores
                },
                "data_flow": {
                    "conversion_rate": round((total_properties / total_prospects * 100) if total_prospects > 0 else 0, 2),
                    "scoring_rate": round((total_scores / total_properties * 100) if total_properties > 0 else 0, 2)
                }
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quality")
async def get_data_quality_metrics(
    db: Session = Depends(get_db),
    metric_type: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000)
):
    """
    Get data quality metrics
    """
    try:
        query = db.query(DataQualityMetric)

        if metric_type:
            query = query.filter(DataQualityMetric.metric_type == metric_type)

        metrics = query.order_by(DataQualityMetric.measured_at.desc())\
            .limit(limit)\
            .all()

        return {
            "status": "success",
            "total": len(metrics),
            "data": [
                {
                    "id": metric.id,
                    "metric_type": metric.metric_type,
                    "metric_name": metric.metric_name,
                    "value": metric.value,
                    "threshold": metric.threshold,
                    "is_passing": metric.is_passing,
                    "entity_type": metric.entity_type,
                    "entity_id": metric.entity_id,
                    "details": metric.details,
                    "measured_at": metric.measured_at.isoformat() if metric.measured_at else None
                }
                for metric in metrics
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/throughput")
async def get_throughput_metrics(
    db: Session = Depends(get_db),
    days: int = Query(7, ge=1, le=30)
):
    """
    Get data processing throughput metrics
    """
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Daily throughput for each stage
        scraping_throughput = db.query(
            func.date(ProspectQueue.created_at).label("date"),
            func.count(ProspectQueue.id).label("count")
        ).filter(
            ProspectQueue.created_at >= cutoff_date
        ).group_by(
            func.date(ProspectQueue.created_at)
        ).all()

        enrichment_throughput = db.query(
            func.date(Property.created_at).label("date"),
            func.count(Property.id).label("count")
        ).filter(
            Property.created_at >= cutoff_date
        ).group_by(
            func.date(Property.created_at)
        ).all()

        scoring_throughput = db.query(
            func.date(PropertyScore.created_at).label("date"),
            func.count(PropertyScore.id).label("count")
        ).filter(
            PropertyScore.created_at >= cutoff_date
        ).group_by(
            func.date(PropertyScore.created_at)
        ).all()

        # Combine into daily metrics
        daily_metrics = {}

        for stat in scraping_throughput:
            date_str = stat.date.isoformat() if stat.date else None
            if date_str not in daily_metrics:
                daily_metrics[date_str] = {"date": date_str, "scraped": 0, "enriched": 0, "scored": 0}
            daily_metrics[date_str]["scraped"] = stat.count

        for stat in enrichment_throughput:
            date_str = stat.date.isoformat() if stat.date else None
            if date_str not in daily_metrics:
                daily_metrics[date_str] = {"date": date_str, "scraped": 0, "enriched": 0, "scored": 0}
            daily_metrics[date_str]["enriched"] = stat.count

        for stat in scoring_throughput:
            date_str = stat.date.isoformat() if stat.date else None
            if date_str not in daily_metrics:
                daily_metrics[date_str] = {"date": date_str, "scraped": 0, "enriched": 0, "scored": 0}
            daily_metrics[date_str]["scored"] = stat.count

        return {
            "status": "success",
            "days": days,
            "data": sorted(daily_metrics.values(), key=lambda x: x["date"])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance")
async def get_performance_metrics(db: Session = Depends(get_db)):
    """
    Get pipeline performance metrics
    """
    try:
        # Average processing times
        avg_scraping_duration = db.query(
            func.avg(
                func.extract('epoch', ScrapingJob.completed_at - ScrapingJob.started_at)
            )
        ).filter(
            ScrapingJob.status == JobStatus.SUCCESS,
            ScrapingJob.started_at.isnot(None),
            ScrapingJob.completed_at.isnot(None)
        ).scalar() or 0

        avg_enrichment_duration = db.query(
            func.avg(
                func.extract('epoch', EnrichmentJob.completed_at - EnrichmentJob.started_at)
            )
        ).filter(
            EnrichmentJob.status == JobStatus.SUCCESS,
            EnrichmentJob.started_at.isnot(None),
            EnrichmentJob.completed_at.isnot(None)
        ).scalar() or 0

        avg_pipeline_duration = db.query(
            func.avg(PipelineRun.duration_seconds)
        ).filter(
            PipelineRun.status == "success",
            PipelineRun.duration_seconds.isnot(None)
        ).scalar() or 0

        # Error rates
        total_scraping_jobs = db.query(func.count(ScrapingJob.id)).scalar() or 0
        failed_scraping_jobs = db.query(func.count(ScrapingJob.id))\
            .filter(ScrapingJob.status == JobStatus.FAILED)\
            .scalar() or 0

        total_enrichment_jobs = db.query(func.count(EnrichmentJob.id)).scalar() or 0
        failed_enrichment_jobs = db.query(func.count(EnrichmentJob.id))\
            .filter(EnrichmentJob.status == JobStatus.FAILED)\
            .scalar() or 0

        return {
            "status": "success",
            "data": {
                "average_durations": {
                    "scraping_seconds": round(float(avg_scraping_duration), 2),
                    "enrichment_seconds": round(float(avg_enrichment_duration), 2),
                    "pipeline_seconds": round(float(avg_pipeline_duration), 2)
                },
                "error_rates": {
                    "scraping": {
                        "total": total_scraping_jobs,
                        "failed": failed_scraping_jobs,
                        "rate_percent": round((failed_scraping_jobs / total_scraping_jobs * 100) if total_scraping_jobs > 0 else 0, 2)
                    },
                    "enrichment": {
                        "total": total_enrichment_jobs,
                        "failed": failed_enrichment_jobs,
                        "rate_percent": round((failed_enrichment_jobs / total_enrichment_jobs * 100) if total_enrichment_jobs > 0 else 0, 2)
                    }
                }
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/funnel")
async def get_data_funnel_metrics(db: Session = Depends(get_db)):
    """
    Get data processing funnel metrics (conversion through pipeline stages)
    """
    try:
        # Count items at each stage
        stage_1_prospects = db.query(func.count(ProspectQueue.id)).scalar() or 0
        stage_2_processing = db.query(func.count(ProspectQueue.id))\
            .filter(ProspectQueue.status == "processing")\
            .scalar() or 0
        stage_3_enriched = db.query(func.count(Property.id)).scalar() or 0
        stage_4_scored = db.query(func.count(PropertyScore.id)).scalar() or 0

        # Calculate conversion rates
        prospect_to_property = round((stage_3_enriched / stage_1_prospects * 100) if stage_1_prospects > 0 else 0, 2)
        property_to_scored = round((stage_4_scored / stage_3_enriched * 100) if stage_3_enriched > 0 else 0, 2)
        overall_conversion = round((stage_4_scored / stage_1_prospects * 100) if stage_1_prospects > 0 else 0, 2)

        # Failed/dropped items
        failed_prospects = db.query(func.count(ProspectQueue.id))\
            .filter(ProspectQueue.status == "failed")\
            .scalar() or 0

        return {
            "status": "success",
            "data": {
                "stages": {
                    "1_scraped": stage_1_prospects,
                    "2_processing": stage_2_processing,
                    "3_enriched": stage_3_enriched,
                    "4_scored": stage_4_scored
                },
                "conversion_rates": {
                    "prospect_to_property_percent": prospect_to_property,
                    "property_to_scored_percent": property_to_scored,
                    "overall_conversion_percent": overall_conversion
                },
                "dropped": {
                    "failed_prospects": failed_prospects,
                    "drop_rate_percent": round((failed_prospects / stage_1_prospects * 100) if stage_1_prospects > 0 else 0, 2)
                }
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
