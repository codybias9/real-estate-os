"""
Property scoring and ML model endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime, timedelta

from ..database import get_db
from ..models import PropertyScore, Property


router = APIRouter(prefix="/scoring", tags=["Scoring"])


@router.get("/scores")
async def list_property_scores(
    db: Session = Depends(get_db),
    min_score: Optional[float] = Query(None, ge=0, le=100),
    max_score: Optional[float] = Query(None, ge=0, le=100),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """
    List property scores with optional filters
    """
    try:
        query = db.query(PropertyScore)

        if min_score is not None:
            query = query.filter(PropertyScore.overall_score >= min_score)
        if max_score is not None:
            query = query.filter(PropertyScore.overall_score <= max_score)

        total = query.count()
        scores = query.order_by(desc(PropertyScore.overall_score))\
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
                    "id": score.id,
                    "property_id": score.property_id,
                    "dag_run_id": score.dag_run_id,
                    "overall_score": score.overall_score,
                    "investment_score": score.investment_score,
                    "risk_score": score.risk_score,
                    "roi_estimate": score.roi_estimate,
                    "model_version": score.model_version,
                    "created_at": score.created_at.isoformat() if score.created_at else None
                }
                for score in scores
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scores/{score_id}")
async def get_property_score(
    score_id: int,
    db: Session = Depends(get_db)
):
    """
    Get detailed score information including breakdown
    """
    try:
        score = db.query(PropertyScore).filter(PropertyScore.id == score_id).first()

        if not score:
            raise HTTPException(status_code=404, detail=f"Score {score_id} not found")

        return {
            "status": "success",
            "data": {
                "id": score.id,
                "property_id": score.property_id,
                "dag_run_id": score.dag_run_id,
                "overall_score": score.overall_score,
                "investment_score": score.investment_score,
                "risk_score": score.risk_score,
                "roi_estimate": score.roi_estimate,
                "score_components": score.score_components,
                "model_version": score.model_version,
                "features_used": score.features_used,
                "created_at": score.created_at.isoformat() if score.created_at else None,
                "updated_at": score.updated_at.isoformat() if score.updated_at else None
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/properties/{property_id}/scores")
async def get_property_scores_history(
    property_id: int,
    db: Session = Depends(get_db)
):
    """
    Get all scores for a specific property (historical)
    """
    try:
        scores = db.query(PropertyScore)\
            .filter(PropertyScore.property_id == property_id)\
            .order_by(desc(PropertyScore.created_at))\
            .all()

        if not scores:
            raise HTTPException(status_code=404, detail=f"No scores found for property {property_id}")

        return {
            "status": "success",
            "property_id": property_id,
            "data": [
                {
                    "id": score.id,
                    "overall_score": score.overall_score,
                    "investment_score": score.investment_score,
                    "risk_score": score.risk_score,
                    "roi_estimate": score.roi_estimate,
                    "model_version": score.model_version,
                    "created_at": score.created_at.isoformat() if score.created_at else None
                }
                for score in scores
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/top-properties")
async def get_top_scored_properties(
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=100)
):
    """
    Get top-scored properties with property details
    """
    try:
        # Get latest score for each property
        subquery = db.query(
            PropertyScore.property_id,
            func.max(PropertyScore.id).label("max_id")
        ).group_by(PropertyScore.property_id).subquery()

        # Join with PropertyScore and Property to get full details
        results = db.query(PropertyScore, Property)\
            .join(subquery, PropertyScore.id == subquery.c.max_id)\
            .join(Property, PropertyScore.property_id == Property.id)\
            .order_by(desc(PropertyScore.overall_score))\
            .limit(limit)\
            .all()

        return {
            "status": "success",
            "data": [
                {
                    "score_id": score.id,
                    "property_id": score.property_id,
                    "overall_score": score.overall_score,
                    "investment_score": score.investment_score,
                    "risk_score": score.risk_score,
                    "roi_estimate": score.roi_estimate,
                    "property": {
                        "address": prop.address,
                        "city": prop.city,
                        "state": prop.state,
                        "property_type": prop.property_type,
                        "bedrooms": prop.bedrooms,
                        "bathrooms": prop.bathrooms,
                        "sqft": prop.sqft,
                        "price": prop.price,
                        "estimated_value": prop.estimated_value
                    },
                    "created_at": score.created_at.isoformat() if score.created_at else None
                }
                for score, prop in results
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/overview")
async def get_scoring_stats(db: Session = Depends(get_db)):
    """
    Get overall scoring statistics
    """
    try:
        total_scores = db.query(func.count(PropertyScore.id)).scalar() or 0
        properties_scored = db.query(func.count(func.distinct(PropertyScore.property_id))).scalar() or 0

        if total_scores == 0:
            return {
                "status": "success",
                "data": {
                    "total_scores": 0,
                    "properties_scored": 0,
                    "score_distribution": {},
                    "averages": {}
                }
            }

        # Score averages
        avg_overall = db.query(func.avg(PropertyScore.overall_score)).scalar() or 0
        avg_investment = db.query(func.avg(PropertyScore.investment_score)).scalar() or 0
        avg_risk = db.query(func.avg(PropertyScore.risk_score)).scalar() or 0
        avg_roi = db.query(func.avg(PropertyScore.roi_estimate)).scalar() or 0

        # Score distribution (buckets)
        score_ranges = [
            ("0-20", 0, 20),
            ("20-40", 20, 40),
            ("40-60", 40, 60),
            ("60-80", 60, 80),
            ("80-100", 80, 100)
        ]

        distribution = {}
        for label, min_val, max_val in score_ranges:
            count = db.query(func.count(PropertyScore.id))\
                .filter(PropertyScore.overall_score >= min_val)\
                .filter(PropertyScore.overall_score < max_val)\
                .scalar() or 0
            distribution[label] = count

        # Recent activity (last 24 hours)
        last_24h = datetime.utcnow() - timedelta(hours=24)
        recent_scores = db.query(func.count(PropertyScore.id))\
            .filter(PropertyScore.created_at >= last_24h)\
            .scalar() or 0

        # Model versions in use
        model_versions = db.query(
            PropertyScore.model_version,
            func.count(PropertyScore.id).label("count")
        ).group_by(PropertyScore.model_version).all()

        return {
            "status": "success",
            "data": {
                "total_scores": total_scores,
                "properties_scored": properties_scored,
                "averages": {
                    "overall_score": round(float(avg_overall), 2),
                    "investment_score": round(float(avg_investment), 2),
                    "risk_score": round(float(avg_risk), 2),
                    "roi_estimate": round(float(avg_roi), 2)
                },
                "score_distribution": distribution,
                "recent_activity": {
                    "last_24h_scores": recent_scores
                },
                "model_versions": [
                    {"version": version, "count": count}
                    for version, count in model_versions
                ]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/trends")
async def get_scoring_trends(
    db: Session = Depends(get_db),
    days: int = Query(30, ge=1, le=90)
):
    """
    Get scoring trends over time
    """
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Daily scoring statistics
        daily_stats = db.query(
            func.date(PropertyScore.created_at).label("date"),
            func.count(PropertyScore.id).label("scores_created"),
            func.avg(PropertyScore.overall_score).label("avg_score")
        ).filter(
            PropertyScore.created_at >= cutoff_date
        ).group_by(
            func.date(PropertyScore.created_at)
        ).order_by(
            func.date(PropertyScore.created_at)
        ).all()

        return {
            "status": "success",
            "data": [
                {
                    "date": stat.date.isoformat() if stat.date else None,
                    "scores_created": stat.scores_created,
                    "average_score": round(float(stat.avg_score), 2) if stat.avg_score else 0
                }
                for stat in daily_stats
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
