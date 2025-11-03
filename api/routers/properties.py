"""
Property management API endpoints.

Handles property CRUD, stage management, and property-related queries.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func
from typing import List, Optional
from datetime import datetime, timedelta

from api.database import get_db
from api import schemas
from db import models

router = APIRouter(prefix="/properties", tags=["Properties"])


@router.get("/", response_model=schemas.PropertyListResponse)
def list_properties(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    current_stage: Optional[List[str]] = Query(None),
    assigned_user_id: Optional[int] = None,
    bird_dog_score_gte: Optional[float] = None,
    bird_dog_score_lte: Optional[float] = None,
    has_memo: Optional[bool] = None,
    has_reply: Optional[bool] = None,
    last_contact_days_ago_gte: Optional[int] = None,
    search: Optional[str] = None,
    tags: Optional[List[str]] = Query(None),
    sort_by: str = "created_at",
    sort_desc: bool = True,
    db: Session = Depends(get_db)
):
    """
    List properties with filtering, pagination, and sorting.

    Filters:
    - current_stage: Filter by pipeline stage(s)
    - assigned_user_id: Filter by assigned user
    - bird_dog_score_gte/lte: Score range
    - has_memo: Properties with/without memo
    - has_reply: Properties with/without reply
    - last_contact_days_ago_gte: Properties not contacted in X days
    - search: Full-text search in address, owner name
    - tags: Filter by tags

    Pagination:
    - page: Page number (1-indexed)
    - page_size: Items per page

    Sorting:
    - sort_by: Field to sort by
    - sort_desc: Sort descending if true
    """

    query = db.query(models.Property)

    # Apply filters
    if current_stage:
        query = query.filter(models.Property.current_stage.in_(current_stage))

    if assigned_user_id:
        query = query.filter(models.Property.assigned_user_id == assigned_user_id)

    if bird_dog_score_gte is not None:
        query = query.filter(models.Property.bird_dog_score >= bird_dog_score_gte)

    if bird_dog_score_lte is not None:
        query = query.filter(models.Property.bird_dog_score <= bird_dog_score_lte)

    if has_memo is not None:
        if has_memo:
            query = query.filter(models.Property.memo_url.isnot(None))
        else:
            query = query.filter(models.Property.memo_url.is_(None))

    if has_reply is not None:
        if has_reply:
            query = query.filter(models.Property.reply_count > 0)
        else:
            query = query.filter(models.Property.reply_count == 0)

    if last_contact_days_ago_gte is not None:
        cutoff_date = datetime.utcnow() - timedelta(days=last_contact_days_ago_gte)
        query = query.filter(
            or_(
                models.Property.last_contact_date.is_(None),
                models.Property.last_contact_date < cutoff_date
            )
        )

    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                models.Property.address.ilike(search_pattern),
                models.Property.owner_name.ilike(search_pattern),
                models.Property.city.ilike(search_pattern)
            )
        )

    if tags:
        # Filter properties that have any of the specified tags
        query = query.filter(models.Property.tags.op("?|")(tags))

    # Get total count before pagination
    total = query.count()

    # Apply sorting
    if sort_desc:
        query = query.order_by(getattr(models.Property, sort_by).desc())
    else:
        query = query.order_by(getattr(models.Property, sort_by).asc())

    # Apply pagination
    offset = (page - 1) * page_size
    items = query.offset(offset).limit(page_size).all()

    pages = (total + page_size - 1) // page_size

    return schemas.PropertyListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages
    )


@router.get("/{property_id}", response_model=schemas.PropertyResponse)
def get_property(property_id: int, db: Session = Depends(get_db)):
    """Get a single property by ID"""
    property = db.query(models.Property).filter(models.Property.id == property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")
    return property


@router.post("/", response_model=schemas.PropertyResponse, status_code=201)
def create_property(
    property_data: schemas.PropertyCreate,
    db: Session = Depends(get_db)
):
    """Create a new property"""
    property = models.Property(**property_data.model_dump())
    db.add(property)
    db.commit()
    db.refresh(property)

    # Create timeline event
    timeline_event = models.TimelineEvent(
        property_id=property.id,
        event_type="property_created",
        title="Property created",
        description=f"Property added to pipeline in {property.current_stage} stage"
    )
    db.add(timeline_event)
    db.commit()

    return property


@router.patch("/{property_id}", response_model=schemas.PropertyResponse)
def update_property(
    property_id: int,
    property_data: schemas.PropertyUpdate,
    db: Session = Depends(get_db)
):
    """Update a property"""
    property = db.query(models.Property).filter(models.Property.id == property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    # Update fields
    update_data = property_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(property, field, value)

    db.commit()
    db.refresh(property)
    return property


@router.post("/{property_id}/stage", response_model=schemas.PropertyResponse)
def update_property_stage(
    property_id: int,
    stage_update: schemas.StageUpdateRequest,
    user_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Update property pipeline stage.

    This creates a stage history record and updates the property.
    """
    property = db.query(models.Property).filter(models.Property.id == property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    from_stage = property.current_stage
    to_stage = stage_update.to_stage

    # Create stage history record
    stage_history = models.PropertyStageHistory(
        property_id=property_id,
        from_stage=from_stage,
        to_stage=to_stage,
        changed_by_id=user_id,
        reason=stage_update.reason
    )
    db.add(stage_history)

    # Update property stage
    property.current_stage = to_stage
    property.updated_at = datetime.utcnow()

    # Create timeline event
    timeline_event = models.TimelineEvent(
        property_id=property_id,
        event_type="stage_changed",
        title=f"Stage changed: {from_stage} → {to_stage}",
        description=stage_update.reason,
        user_id=user_id,
        metadata={"from_stage": from_stage, "to_stage": to_stage}
    )
    db.add(timeline_event)

    db.commit()
    db.refresh(property)
    return property


@router.delete("/{property_id}", status_code=204)
def delete_property(property_id: int, db: Session = Depends(get_db)):
    """Delete a property (soft delete by archiving)"""
    property = db.query(models.Property).filter(models.Property.id == property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    property.archived_at = datetime.utcnow()
    property.current_stage = "archived"
    db.commit()
    return None


@router.get("/{property_id}/timeline", response_model=List[dict])
def get_property_timeline(
    property_id: int,
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """
    Get property activity timeline.

    Returns a chronological list of all activity on a property.
    """
    property = db.query(models.Property).filter(models.Property.id == property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    events = db.query(models.TimelineEvent)\
        .filter(models.TimelineEvent.property_id == property_id)\
        .order_by(models.TimelineEvent.created_at.desc())\
        .limit(limit)\
        .all()

    return [
        {
            "id": event.id,
            "event_type": event.event_type,
            "title": event.title,
            "description": event.description,
            "user_id": event.user_id,
            "metadata": event.metadata,
            "created_at": event.created_at
        }
        for event in events
    ]


@router.get("/{property_id}/stage-history", response_model=List[dict])
def get_property_stage_history(
    property_id: int,
    db: Session = Depends(get_db)
):
    """Get stage transition history for a property"""
    property = db.query(models.Property).filter(models.Property.id == property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    history = db.query(models.PropertyStageHistory)\
        .filter(models.PropertyStageHistory.property_id == property_id)\
        .order_by(models.PropertyStageHistory.created_at.desc())\
        .all()

    return [
        {
            "id": h.id,
            "from_stage": h.from_stage,
            "to_stage": h.to_stage,
            "changed_by_id": h.changed_by_id,
            "reason": h.reason,
            "created_at": h.created_at
        }
        for h in history
    ]


@router.get("/stats/pipeline", response_model=schemas.PipelineStatsResponse)
def get_pipeline_stats(db: Session = Depends(get_db)):
    """
    Get pipeline overview statistics.

    Returns:
    - Total properties
    - Count by stage
    - Average days in each stage
    - Conversion rates
    """

    # Total properties
    total = db.query(func.count(models.Property.id))\
        .filter(models.Property.archived_at.is_(None))\
        .scalar()

    # Count by stage
    by_stage_query = db.query(
        models.Property.current_stage,
        func.count(models.Property.id)
    ).filter(models.Property.archived_at.is_(None))\
     .group_by(models.Property.current_stage)\
     .all()

    by_stage = {stage: count for stage, count in by_stage_query}

    # Average days in stage (simplified - uses created_at)
    avg_days_query = db.query(
        models.Property.current_stage,
        func.avg(func.extract('epoch', func.now() - models.Property.created_at) / 86400)
    ).filter(models.Property.archived_at.is_(None))\
     .group_by(models.Property.current_stage)\
     .all()

    avg_days_in_stage = {stage: float(days) if days else 0 for stage, days in avg_days_query}

    # Conversion rates (simplified)
    conversion_rates = {}
    if by_stage.get("prospect", 0) > 0:
        conversion_rates["prospect_to_outreach"] = by_stage.get("outreach", 0) / by_stage["prospect"]
    if by_stage.get("outreach", 0) > 0:
        conversion_rates["outreach_to_contact"] = by_stage.get("contact_made", 0) / by_stage["outreach"]

    return schemas.PipelineStatsResponse(
        total_properties=total,
        by_stage=by_stage,
        avg_days_in_stage=avg_days_in_stage,
        conversion_rates=conversion_rates
    )
