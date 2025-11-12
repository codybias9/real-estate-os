"""
Data enrichment pipeline endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime, timedelta

from ..database import get_db
from ..models import EnrichmentJob, Property, JobStatus


router = APIRouter(prefix="/enrichment", tags=["Enrichment"])


@router.get("/jobs")
async def list_enrichment_jobs(
    db: Session = Depends(get_db),
    status: Optional[str] = Query(None),
    enrichment_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """
    List enrichment jobs with optional filters
    """
    try:
        query = db.query(EnrichmentJob)

        if status:
            query = query.filter(EnrichmentJob.status == status)
        if enrichment_type:
            query = query.filter(EnrichmentJob.enrichment_type == enrichment_type)

        total = query.count()
        jobs = query.order_by(desc(EnrichmentJob.created_at))\
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
                    "property_id": job.property_id,
                    "status": job.status.value if job.status else None,
                    "enrichment_type": job.enrichment_type,
                    "started_at": job.started_at.isoformat() if job.started_at else None,
                    "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                    "data_sources_used": job.data_sources_used,
                    "fields_enriched": job.fields_enriched,
                    "created_at": job.created_at.isoformat() if job.created_at else None
                }
                for job in jobs
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/{job_id}")
async def get_enrichment_job(
    job_id: int,
    db: Session = Depends(get_db)
):
    """
    Get details for a specific enrichment job
    """
    try:
        job = db.query(EnrichmentJob).filter(EnrichmentJob.id == job_id).first()

        if not job:
            raise HTTPException(status_code=404, detail=f"Enrichment job {job_id} not found")

        return {
            "status": "success",
            "data": {
                "id": job.id,
                "dag_id": job.dag_id,
                "dag_run_id": job.dag_run_id,
                "property_id": job.property_id,
                "status": job.status.value if job.status else None,
                "enrichment_type": job.enrichment_type,
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "data_sources_used": job.data_sources_used,
                "fields_enriched": job.fields_enriched,
                "error_log": job.error_log,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "updated_at": job.updated_at.isoformat() if job.updated_at else None
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/properties")
async def list_enriched_properties(
    db: Session = Depends(get_db),
    city: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    property_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """
    List enriched properties with optional filters
    """
    try:
        query = db.query(Property)

        if city:
            query = query.filter(Property.city == city)
        if state:
            query = query.filter(Property.state == state)
        if property_type:
            query = query.filter(Property.property_type == property_type)

        total = query.count()
        properties = query.order_by(desc(Property.created_at))\
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
                    "id": prop.id,
                    "prospect_id": prop.prospect_id,
                    "address": prop.address,
                    "city": prop.city,
                    "state": prop.state,
                    "zip_code": prop.zip_code,
                    "property_type": prop.property_type,
                    "bedrooms": prop.bedrooms,
                    "bathrooms": prop.bathrooms,
                    "sqft": prop.sqft,
                    "lot_size": prop.lot_size,
                    "year_built": prop.year_built,
                    "price": prop.price,
                    "estimated_value": prop.estimated_value,
                    "enrichment_sources": prop.enrichment_sources,
                    "created_at": prop.created_at.isoformat() if prop.created_at else None,
                    "updated_at": prop.updated_at.isoformat() if prop.updated_at else None
                }
                for prop in properties
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/properties/{property_id}")
async def get_property_details(
    property_id: int,
    db: Session = Depends(get_db)
):
    """
    Get full details for a specific enriched property
    """
    try:
        prop = db.query(Property).filter(Property.id == property_id).first()

        if not prop:
            raise HTTPException(status_code=404, detail=f"Property {property_id} not found")

        return {
            "status": "success",
            "data": {
                "id": prop.id,
                "prospect_id": prop.prospect_id,
                "address": prop.address,
                "city": prop.city,
                "state": prop.state,
                "zip_code": prop.zip_code,
                "property_type": prop.property_type,
                "bedrooms": prop.bedrooms,
                "bathrooms": prop.bathrooms,
                "sqft": prop.sqft,
                "lot_size": prop.lot_size,
                "year_built": prop.year_built,
                "price": prop.price,
                "estimated_value": prop.estimated_value,
                "enrichment_data": prop.enrichment_data,
                "enrichment_sources": prop.enrichment_sources,
                "created_at": prop.created_at.isoformat() if prop.created_at else None,
                "updated_at": prop.updated_at.isoformat() if prop.updated_at else None
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/overview")
async def get_enrichment_stats(db: Session = Depends(get_db)):
    """
    Get overall enrichment statistics
    """
    try:
        # Job statistics
        total_jobs = db.query(func.count(EnrichmentJob.id)).scalar() or 0
        running_jobs = db.query(func.count(EnrichmentJob.id))\
            .filter(EnrichmentJob.status == JobStatus.RUNNING)\
            .scalar() or 0
        queued_jobs = db.query(func.count(EnrichmentJob.id))\
            .filter(EnrichmentJob.status == JobStatus.QUEUED)\
            .scalar() or 0
        successful_jobs = db.query(func.count(EnrichmentJob.id))\
            .filter(EnrichmentJob.status == JobStatus.SUCCESS)\
            .scalar() or 0
        failed_jobs = db.query(func.count(EnrichmentJob.id))\
            .filter(EnrichmentJob.status == JobStatus.FAILED)\
            .scalar() or 0

        # Property statistics
        total_properties = db.query(func.count(Property.id)).scalar() or 0

        # Recent activity (last 24 hours)
        last_24h = datetime.utcnow() - timedelta(hours=24)
        recent_enrichments = db.query(func.count(EnrichmentJob.id))\
            .filter(EnrichmentJob.created_at >= last_24h)\
            .scalar() or 0

        # Enrichment type breakdown
        enrichment_types = db.query(
            EnrichmentJob.enrichment_type,
            func.count(EnrichmentJob.id).label("count")
        ).group_by(EnrichmentJob.enrichment_type).all()

        # Data quality metrics
        properties_with_pricing = db.query(func.count(Property.id))\
            .filter(Property.price.isnot(None))\
            .scalar() or 0
        properties_with_details = db.query(func.count(Property.id))\
            .filter(Property.bedrooms.isnot(None))\
            .scalar() or 0

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
                "properties": {
                    "total": total_properties,
                    "with_pricing": properties_with_pricing,
                    "with_details": properties_with_details,
                    "completeness_rate": round((properties_with_details / total_properties * 100) if total_properties > 0 else 0, 2)
                },
                "recent_activity": {
                    "last_24h_enrichments": recent_enrichments
                },
                "enrichment_types": [
                    {"type": etype, "count": count}
                    for etype, count in enrichment_types
                ]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/data-quality")
async def get_data_quality_stats(db: Session = Depends(get_db)):
    """
    Get data quality metrics for enriched properties
    """
    try:
        total_properties = db.query(func.count(Property.id)).scalar() or 0

        if total_properties == 0:
            return {
                "status": "success",
                "data": {
                    "total_properties": 0,
                    "completeness": {}
                }
            }

        # Field completeness
        fields = {
            "address": Property.address,
            "city": Property.city,
            "state": Property.state,
            "zip_code": Property.zip_code,
            "property_type": Property.property_type,
            "bedrooms": Property.bedrooms,
            "bathrooms": Property.bathrooms,
            "sqft": Property.sqft,
            "lot_size": Property.lot_size,
            "year_built": Property.year_built,
            "price": Property.price,
            "estimated_value": Property.estimated_value
        }

        completeness = {}
        for field_name, field_col in fields.items():
            count = db.query(func.count(Property.id))\
                .filter(field_col.isnot(None))\
                .scalar() or 0
            completeness[field_name] = {
                "count": count,
                "percentage": round((count / total_properties * 100), 2)
            }

        # Overall completeness score (average of all fields)
        avg_completeness = sum(c["percentage"] for c in completeness.values()) / len(completeness)

        return {
            "status": "success",
            "data": {
                "total_properties": total_properties,
                "overall_completeness": round(avg_completeness, 2),
                "field_completeness": completeness
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
