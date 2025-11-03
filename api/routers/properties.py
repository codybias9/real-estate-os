"""
Property Management Router
Handles CRUD operations, filtering, timeline, and pipeline stats
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
from typing import List, Optional
from datetime import datetime, timedelta

from api.database import get_db
from api import schemas
from api.idempotency import IdempotencyHandler, get_idempotency_handler
from db.models import Property, PropertyTimeline, PropertyStage, Team, User
from api.cache import cache_response_with_etag, invalidate_property_cache

router = APIRouter(prefix="/properties", tags=["Properties"])

# ============================================================================
# CRUD OPERATIONS
# ============================================================================

@router.post("", response_model=schemas.PropertyResponse, status_code=201)
def create_property(
    property_data: schemas.PropertyCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new property in the pipeline

    Creates timeline event and initializes tracking fields
    """
    # Verify team exists
    team = db.query(Team).filter(Team.id == property_data.team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Verify assigned user if provided
    if property_data.assigned_user_id:
        user = db.query(User).filter(User.id == property_data.assigned_user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="Assigned user not found")

    # Create property
    property_dict = property_data.model_dump()
    db_property = Property(**property_dict)
    db_property.current_stage = PropertyStage.NEW
    db_property.stage_changed_at = datetime.utcnow()

    db.add(db_property)
    db.flush()

    # Create timeline event
    timeline_event = PropertyTimeline(
        property_id=db_property.id,
        event_type="property_created",
        event_title="Property Added to Pipeline",
        event_description=f"Added {property_data.address}"
    )
    db.add(timeline_event)

    db.commit()
    db.refresh(db_property)

    return db_property

@router.get("", response_model=List[schemas.PropertyResponse])
@cache_response_with_etag("properties_list", ttl=60, vary_on=["team_id", "stage", "assigned_user_id"])
def list_properties(
    request: Request,
    team_id: Optional[int] = Query(None),
    stage: Optional[schemas.PropertyStageEnum] = Query(None),
    assigned_user_id: Optional[int] = Query(None),
    bird_dog_score__gte: Optional[float] = Query(None, ge=0.0, le=1.0),
    bird_dog_score__lte: Optional[float] = Query(None, ge=0.0, le=1.0),
    has_memo: Optional[bool] = Query(None),
    has_reply: Optional[bool] = Query(None),
    last_contact_days_ago_gte: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    tags: Optional[List[str]] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """
    List properties with advanced filtering

    Filters:
    - team_id: Filter by team
    - stage: Filter by pipeline stage
    - assigned_user_id: Filter by assigned user
    - bird_dog_score__gte: Minimum bird dog score
    - bird_dog_score__lte: Maximum bird dog score
    - has_memo: Filter properties with/without memo
    - has_reply: Filter properties with/without reply
    - last_contact_days_ago_gte: Filter by days since last contact
    - search: Full-text search (address, owner, city)
    - tags: Filter by tags (AND logic)
    - skip: Pagination offset
    - limit: Pagination limit

    Caching:
    - Server-side: Redis cache for 60 seconds
    - Client-side: ETag support for conditional requests (304 Not Modified)
    """
    query = db.query(Property).filter(Property.archived_at.is_(None))

    # Apply filters
    if team_id:
        query = query.filter(Property.team_id == team_id)

    if stage:
        query = query.filter(Property.current_stage == stage.value)

    if assigned_user_id:
        query = query.filter(Property.assigned_user_id == assigned_user_id)

    if bird_dog_score__gte is not None:
        query = query.filter(Property.bird_dog_score >= bird_dog_score__gte)

    if bird_dog_score__lte is not None:
        query = query.filter(Property.bird_dog_score <= bird_dog_score__lte)

    if has_memo is not None:
        if has_memo:
            query = query.filter(Property.memo_url.isnot(None))
        else:
            query = query.filter(Property.memo_url.is_(None))

    if has_reply is not None:
        if has_reply:
            query = query.filter(Property.reply_count > 0)
        else:
            query = query.filter(Property.reply_count == 0)

    if last_contact_days_ago_gte is not None:
        cutoff_date = datetime.utcnow() - timedelta(days=last_contact_days_ago_gte)
        query = query.filter(
            or_(
                Property.last_contact_date.is_(None),
                Property.last_contact_date <= cutoff_date
            )
        )

    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                Property.address.ilike(search_pattern),
                Property.owner_name.ilike(search_pattern),
                Property.city.ilike(search_pattern),
                Property.zip_code.ilike(search_pattern)
            )
        )

    if tags:
        for tag in tags:
            query = query.filter(Property.tags.contains([tag]))

    # Order by score (high to low), then created date (newest first)
    query = query.order_by(
        desc(Property.bird_dog_score.nullslast()),
        desc(Property.created_at)
    )

    # Pagination
    properties = query.offset(skip).limit(limit).all()

    return properties

@router.get("/{property_id}", response_model=schemas.PropertyResponse)
def get_property(property_id: int, db: Session = Depends(get_db)):
    """
    Get a single property by ID
    """
    property = db.query(Property).filter(Property.id == property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    return property

@router.patch("/{property_id}", response_model=schemas.PropertyResponse)
def update_property(
    property_id: int,
    property_update: schemas.PropertyUpdate,
    db: Session = Depends(get_db)
):
    """
    Update a property

    Tracks stage changes in timeline
    """
    property = db.query(Property).filter(Property.id == property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    # Track stage change
    old_stage = property.current_stage
    update_data = property_update.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(property, field, value)

    # If stage changed, update stage tracking and create timeline event
    if "current_stage" in update_data and update_data["current_stage"] != old_stage:
        property.previous_stage = old_stage
        property.stage_changed_at = datetime.utcnow()

        timeline_event = PropertyTimeline(
            property_id=property.id,
            event_type="stage_changed",
            event_title="Stage Changed",
            event_description=f"Moved from {old_stage.value} to {property.current_stage.value}",
            metadata={"old_stage": old_stage.value, "new_stage": property.current_stage.value}
        )
        db.add(timeline_event)

    property.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(property)

    # Invalidate cache for this property
    invalidate_property_cache(property.id, property.team_id)

    return property

@router.delete("/{property_id}", status_code=204)
def delete_property(property_id: int, db: Session = Depends(get_db)):
    """
    Archive a property (soft delete)
    """
    property = db.query(Property).filter(Property.id == property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    property.archived_at = datetime.utcnow()
    property.current_stage = PropertyStage.ARCHIVED

    # Create timeline event
    timeline_event = PropertyTimeline(
        property_id=property.id,
        event_type="property_archived",
        event_title="Property Archived",
        event_description="Property moved to archive"
    )
    db.add(timeline_event)

    db.commit()

    # Invalidate cache for this property
    invalidate_property_cache(property.id, property.team_id)

    return None

# ============================================================================
# STAGE MANAGEMENT
# ============================================================================

@router.post("/{property_id}/stage", response_model=schemas.PropertyResponse)
def change_property_stage(
    property_id: int,
    stage_change: schemas.PropertyStageChange,
    http_request: Request,
    db: Session = Depends(get_db),
    idempotency: IdempotencyHandler = Depends(get_idempotency_handler)
):
    """
    Change property pipeline stage

    Creates timeline event

    Idempotency:
    - Provide Idempotency-Key header to prevent duplicate stage changes
    - Same key within 24 hours returns cached response
    - Prevents duplicate timeline events and stage transitions
    """
    # Check for existing idempotent request
    existing = idempotency.check_existing()
    if existing:
        return JSONResponse(
            content=existing["body"],
            status_code=existing["status_code"],
            headers={"X-Idempotency-Cached": "true"}
        )

    property = db.query(Property).filter(Property.id == property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    old_stage = property.current_stage
    property.previous_stage = old_stage
    property.current_stage = stage_change.new_stage.value
    property.stage_changed_at = datetime.utcnow()
    property.updated_at = datetime.utcnow()

    # Create timeline event
    timeline_event = PropertyTimeline(
        property_id=property.id,
        event_type="stage_changed",
        event_title="Stage Changed",
        event_description=f"Moved from {old_stage.value} to {stage_change.new_stage.value}",
        metadata={"old_stage": old_stage.value, "new_stage": stage_change.new_stage.value}
    )
    db.add(timeline_event)

    db.commit()
    db.refresh(property)

    # Convert property to dict for idempotency storage
    from api.schemas import PropertyResponse
    property_dict = PropertyResponse.from_orm(property).dict()

    # Store response for idempotency
    idempotency.store_response(200, property_dict, stage_change.dict())

    return property

# ============================================================================
# TIMELINE
# ============================================================================

@router.get("/{property_id}/timeline", response_model=List[schemas.TimelineEvent])
def get_property_timeline(
    property_id: int,
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """
    Get property timeline (activity feed)

    Returns recent events in reverse chronological order
    """
    property = db.query(Property).filter(Property.id == property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    events = (
        db.query(PropertyTimeline)
        .filter(PropertyTimeline.property_id == property_id)
        .order_by(desc(PropertyTimeline.created_at))
        .limit(limit)
        .all()
    )

    return events

# ============================================================================
# PIPELINE STATS
# ============================================================================

@router.get("/stats/pipeline", response_model=List[schemas.PipelineStats])
def get_pipeline_stats(
    team_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Get pipeline statistics by stage

    Returns counts, total expected value, and average scores per stage
    """
    query = db.query(
        Property.current_stage,
        func.count(Property.id).label("count"),
        func.sum(Property.expected_value).label("total_value"),
        func.avg(Property.bird_dog_score).label("avg_score")
    ).filter(Property.archived_at.is_(None))

    if team_id:
        query = query.filter(Property.team_id == team_id)

    stats = (
        query
        .group_by(Property.current_stage)
        .all()
    )

    return [
        {
            "stage": stage,
            "count": count,
            "total_value": total_value or 0.0,
            "avg_score": avg_score
        }
        for stage, count, total_value, avg_score in stats
    ]
