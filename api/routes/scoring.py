"""Property scoring API routes."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
import sys
sys.path.insert(0, '/home/user/real-estate-os')

from api.database import get_db
from api.schemas import PropertyScore, ScoreCreate, Property
from db.models import PropertyScore as ScoreModel, Property as PropertyModel

router = APIRouter(prefix="/api/properties", tags=["scoring"])


@router.get("/{property_id}/score", response_model=PropertyScore)
def get_property_score(
    property_id: int,
    db: Session = Depends(get_db),
):
    """Get score for a property."""

    # Check if property exists
    property_obj = db.query(PropertyModel).filter(PropertyModel.id == property_id).first()
    if not property_obj:
        raise HTTPException(status_code=404, detail=f"Property {property_id} not found")

    # Get score
    score = db.query(ScoreModel).filter(ScoreModel.property_id == property_id).first()

    if not score:
        raise HTTPException(status_code=404, detail=f"Score not found for property {property_id}")

    return PropertyScore.model_validate(score)


@router.post("/{property_id}/score", status_code=202)
def trigger_scoring(
    property_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Trigger scoring for a property (async)."""

    # Check if property exists
    property_obj = db.query(PropertyModel).filter(PropertyModel.id == property_id).first()
    if not property_obj:
        raise HTTPException(status_code=404, detail=f"Property {property_id} not found")

    # In production, this would trigger scoring service
    return {
        "message": "Scoring triggered",
        "property_id": property_id,
        "status": "pending",
    }


@router.put("/{property_id}/score", response_model=PropertyScore)
def create_or_update_score(
    property_id: int,
    score_data: ScoreCreate,
    db: Session = Depends(get_db),
):
    """Create or update score for a property."""

    # Check if property exists
    property_obj = db.query(PropertyModel).filter(PropertyModel.id == property_id).first()
    if not property_obj:
        raise HTTPException(status_code=404, detail=f"Property {property_id} not found")

    # Check if score exists
    score = db.query(ScoreModel).filter(ScoreModel.property_id == property_id).first()

    if score:
        # Update existing
        update_data = score_data.model_dump(exclude_unset=True, exclude={'property_id'})
        for field, value in update_data.items():
            setattr(score, field, value)
    else:
        # Create new
        score_dict = score_data.model_dump()
        score_dict['property_id'] = property_id
        score = ScoreModel(**score_dict)
        db.add(score)

    # Update property status
    if property_obj.status in ['new', 'enriched']:
        property_obj.status = 'scored'

    db.commit()
    db.refresh(score)

    return PropertyScore.model_validate(score)


@router.get("/scores/top", response_model=List[Property])
def get_top_scored_properties(
    limit: int = Query(10, ge=1, le=100, description="Number of top properties"),
    min_score: int = Query(0, ge=0, le=100, description="Minimum score"),
    db: Session = Depends(get_db),
):
    """Get top scored properties."""

    # Join properties with scores and filter/sort
    query = db.query(PropertyModel).join(ScoreModel, PropertyModel.id == ScoreModel.property_id)

    if min_score > 0:
        query = query.filter(ScoreModel.total_score >= min_score)

    properties = query.order_by(ScoreModel.total_score.desc()).limit(limit).all()

    return [Property.model_validate(p) for p in properties]


@router.get("/scores/stats")
def get_score_statistics(db: Session = Depends(get_db)):
    """Get scoring statistics."""

    total_scored = db.query(func.count(ScoreModel.id)).scalar()

    avg_score = db.query(func.avg(ScoreModel.total_score)).scalar()
    min_score = db.query(func.min(ScoreModel.total_score)).scalar()
    max_score = db.query(func.max(ScoreModel.total_score)).scalar()

    recommendation_counts = db.query(
        ScoreModel.recommendation,
        func.count(ScoreModel.id)
    ).group_by(ScoreModel.recommendation).all()

    risk_counts = db.query(
        ScoreModel.risk_level,
        func.count(ScoreModel.id)
    ).group_by(ScoreModel.risk_level).all()

    return {
        "total_scored": total_scored,
        "score_stats": {
            "average": round(float(avg_score), 2) if avg_score else 0,
            "min": int(min_score) if min_score else 0,
            "max": int(max_score) if max_score else 0,
        },
        "by_recommendation": {rec: count for rec, count in recommendation_counts},
        "by_risk_level": {risk: count for risk, count in risk_counts},
    }
