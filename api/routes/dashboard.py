"""Dashboard API routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
import sys
sys.path.insert(0, '/home/user/real-estate-os')

from api.database import get_db
from db.models import (
    Property as PropertyModel,
    PropertyEnrichment as EnrichmentModel,
    PropertyScore as ScoreModel,
    GeneratedDocument as DocumentModel,
    Campaign as CampaignModel,
)

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats")
def get_dashboard_stats(db: Session = Depends(get_db)):
    """Get overall dashboard statistics."""

    # Property stats
    total_properties = db.query(func.count(PropertyModel.id)).scalar()

    new_properties = db.query(func.count(PropertyModel.id)).filter(
        PropertyModel.status == 'new'
    ).scalar()

    enriched_properties = db.query(func.count(PropertyModel.id)).filter(
        PropertyModel.status.in_(['enriched', 'scored', 'documented', 'campaigned'])
    ).scalar()

    scored_properties = db.query(func.count(ScoreModel.id)).scalar()

    documented_properties = db.query(func.count(DocumentModel.id)).filter(
        DocumentModel.status == 'completed'
    ).scalar()

    # Score stats
    avg_score = db.query(func.avg(ScoreModel.total_score)).scalar()

    high_score_properties = db.query(func.count(ScoreModel.id)).filter(
        ScoreModel.total_score >= 80
    ).scalar()

    # Campaign stats
    total_campaigns = db.query(func.count(CampaignModel.id)).scalar()
    active_campaigns = db.query(func.count(CampaignModel.id)).filter(
        CampaignModel.status.in_(['scheduled', 'sending'])
    ).scalar()

    # Recent property stats (last 30 days)
    from datetime import datetime, timedelta
    thirty_days_ago = datetime.now() - timedelta(days=30)

    recent_properties = db.query(func.count(PropertyModel.id)).filter(
        PropertyModel.created_at >= thirty_days_ago
    ).scalar()

    return {
        "properties": {
            "total": total_properties,
            "new": new_properties,
            "enriched": enriched_properties,
            "scored": scored_properties,
            "documented": documented_properties,
            "recent_30_days": recent_properties,
        },
        "scoring": {
            "total_scored": scored_properties,
            "average_score": round(float(avg_score), 2) if avg_score else 0,
            "high_score_count": high_score_properties,
        },
        "campaigns": {
            "total": total_campaigns,
            "active": active_campaigns,
        },
    }


@router.get("/pipeline")
def get_pipeline_status(db: Session = Depends(get_db)):
    """Get pipeline status showing properties in each stage."""

    # Count properties in each stage
    new_count = db.query(func.count(PropertyModel.id)).filter(
        PropertyModel.status == 'new'
    ).scalar()

    enriched_count = db.query(func.count(PropertyModel.id)).filter(
        PropertyModel.status == 'enriched'
    ).scalar()

    scored_count = db.query(func.count(PropertyModel.id)).filter(
        PropertyModel.status == 'scored'
    ).scalar()

    documented_count = db.query(func.count(PropertyModel.id)).filter(
        PropertyModel.status == 'documented'
    ).scalar()

    campaigned_count = db.query(func.count(PropertyModel.id)).filter(
        PropertyModel.status == 'campaigned'
    ).scalar()

    total = new_count + enriched_count + scored_count + documented_count + campaigned_count

    return {
        "stages": [
            {"name": "Discovery", "count": new_count, "percentage": round((new_count / total * 100) if total > 0 else 0, 1)},
            {"name": "Enrichment", "count": enriched_count, "percentage": round((enriched_count / total * 100) if total > 0 else 0, 1)},
            {"name": "Scoring", "count": scored_count, "percentage": round((scored_count / total * 100) if total > 0 else 0, 1)},
            {"name": "Documentation", "count": documented_count, "percentage": round((documented_count / total * 100) if total > 0 else 0, 1)},
            {"name": "Outreach", "count": campaigned_count, "percentage": round((campaigned_count / total * 100) if total > 0 else 0, 1)},
        ],
        "total": total,
    }


@router.get("/recent-activity")
def get_recent_activity(db: Session = Depends(get_db), limit: int = 10):
    """Get recent activity across all entities."""

    # Get recently added properties
    recent_properties = db.query(PropertyModel).order_by(
        PropertyModel.created_at.desc()
    ).limit(limit).all()

    # Get recently scored properties
    recent_scores = db.query(ScoreModel).order_by(
        ScoreModel.created_at.desc()
    ).limit(limit).all()

    # Get recently generated documents
    recent_docs = db.query(DocumentModel).order_by(
        DocumentModel.created_at.desc()
    ).limit(limit).all()

    # Build activity feed
    activities = []

    for prop in recent_properties:
        activities.append({
            "type": "property_added",
            "timestamp": prop.created_at.isoformat(),
            "description": f"New property added: {prop.address}, {prop.city}, {prop.state}",
            "property_id": prop.id,
        })

    for score in recent_scores:
        activities.append({
            "type": "property_scored",
            "timestamp": score.created_at.isoformat(),
            "description": f"Property scored: {score.total_score}/100 ({score.recommendation})",
            "property_id": score.property_id,
        })

    for doc in recent_docs:
        activities.append({
            "type": "document_generated",
            "timestamp": doc.created_at.isoformat(),
            "description": f"Document generated: {doc.document_type}",
            "property_id": doc.property_id,
        })

    # Sort by timestamp (most recent first)
    activities.sort(key=lambda x: x['timestamp'], reverse=True)

    return {
        "activities": activities[:limit],
        "total": len(activities),
    }


@router.get("/top-properties")
def get_top_properties(db: Session = Depends(get_db), limit: int = 10):
    """Get top scoring properties for dashboard."""

    from api.schemas import Property

    # Get properties with scores, ordered by score
    properties = db.query(PropertyModel).join(
        ScoreModel, PropertyModel.id == ScoreModel.property_id
    ).order_by(ScoreModel.total_score.desc()).limit(limit).all()

    return {
        "properties": [Property.model_validate(p) for p in properties],
        "count": len(properties),
    }
