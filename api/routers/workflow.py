"""
Workflow Automation Router
Next Best Actions, Smart Lists, and One-Click Tasking
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from typing import List, Optional
from datetime import datetime, timedelta

from api.database import get_db
from api import schemas
from db.models import (
    Property, NextBestAction, SmartList, Task, TaskStatus, TaskPriority,
    Communication, PropertyTimeline, PropertyStage, Team
)

router = APIRouter(prefix="/workflow", tags=["Workflow"])

# ============================================================================
# NEXT BEST ACTION (NBA) PANEL
# ============================================================================

def _generate_nba_rules(db: Session, property: Property) -> List[NextBestAction]:
    """
    Apply rule-based logic to generate Next Best Actions

    5 intelligent rules:
    1. Outreach with no reply > 7 days → "Send follow-up" (priority: 0.8)
    2. High score (>0.7) with no memo → "Generate memo" (priority: 0.9)
    3. Negotiation without packet → "Send packet" (priority: 0.95)
    4. Warm replies in last 48h → "Respond to warm lead" (priority: 1.0)
    5. Stalled in stage > 14 days → "Move or archive" (priority: 0.6)
    """
    nbas = []
    now = datetime.utcnow()

    # Rule 1: Outreach with no reply > 7 days
    if property.current_stage == PropertyStage.OUTREACH:
        if property.last_contact_date:
            days_since_contact = (now - property.last_contact_date).days
            if days_since_contact >= 7 and property.reply_count == 0:
                nbas.append(NextBestAction(
                    property_id=property.id,
                    action_type="send_follow_up",
                    action_title="Send Follow-Up Email",
                    action_description=f"No reply in {days_since_contact} days. Try a different angle or channel.",
                    priority=0.8,
                    rule_name="outreach_no_reply_7d",
                    reasoning=f"Property in Outreach stage for {days_since_contact} days with no reply",
                    action_params={"suggested_channel": "email", "template_type": "follow_up"}
                ))

    # Rule 2: High score (>0.7) with no memo
    if property.bird_dog_score and property.bird_dog_score > 0.7:
        if not property.memo_url:
            nbas.append(NextBestAction(
                property_id=property.id,
                action_type="generate_memo",
                action_title="Generate Investment Memo",
                action_description=f"High-value property (score: {property.bird_dog_score:.2f}) needs memo for investor pitch",
                priority=0.9,
                rule_name="high_score_no_memo",
                reasoning=f"Bird dog score of {property.bird_dog_score:.2f} indicates high potential",
                action_params={"score": property.bird_dog_score}
            ))

    # Rule 3: Negotiation without packet
    if property.current_stage == PropertyStage.NEGOTIATION:
        if not property.packet_url:
            nbas.append(NextBestAction(
                property_id=property.id,
                action_type="send_packet",
                action_title="Send Deal Packet",
                action_description="Property in negotiation needs complete deal packet",
                priority=0.95,
                rule_name="negotiation_no_packet",
                reasoning="Properties in negotiation should have complete documentation",
                action_params={"required_docs": ["memo", "comps", "inspection", "disclosures"]}
            ))

    # Rule 4: Warm replies in last 48h
    if property.last_reply_date:
        hours_since_reply = (now - property.last_reply_date).total_seconds() / 3600
        if hours_since_reply <= 48:
            nbas.append(NextBestAction(
                property_id=property.id,
                action_type="respond_to_warm_lead",
                action_title="🔥 Respond to Warm Lead",
                action_description=f"Owner replied {int(hours_since_reply)} hours ago - strike while hot!",
                priority=1.0,
                rule_name="warm_reply_48h",
                reasoning="Recent engagement indicates high interest",
                action_params={"hours_since_reply": hours_since_reply},
                expires_at=now + timedelta(hours=24)
            ))

    # Rule 5: Stalled in stage > 14 days
    if property.stage_changed_at:
        days_in_stage = (now - property.stage_changed_at).days
        if days_in_stage >= 14 and property.current_stage not in [PropertyStage.CLOSED_WON, PropertyStage.CLOSED_LOST, PropertyStage.ARCHIVED]:
            nbas.append(NextBestAction(
                property_id=property.id,
                action_type="move_or_archive",
                action_title="Review Stalled Property",
                action_description=f"In {property.current_stage.value} for {days_in_stage} days. Time to move forward or archive?",
                priority=0.6,
                rule_name="stalled_14d",
                reasoning=f"No stage progression in {days_in_stage} days",
                action_params={"days_in_stage": days_in_stage, "current_stage": property.current_stage.value}
            ))

    return nbas

@router.post("/next-best-actions/generate")
def generate_next_best_actions(
    request: schemas.GenerateNBARequest,
    db: Session = Depends(get_db)
):
    """
    Generate Next Best Actions for properties

    Applies rule-based intelligence to surface the one thing to do next

    If property_ids provided: Generate for those specific properties
    If team_id provided: Generate for all active properties in team

    Returns count of NBAs created
    """
    # Get properties to analyze
    if request.property_ids:
        properties = db.query(Property).filter(
            Property.id.in_(request.property_ids),
            Property.archived_at.is_(None)
        ).all()
    elif request.team_id:
        properties = db.query(Property).filter(
            Property.team_id == request.team_id,
            Property.archived_at.is_(None)
        ).all()
    else:
        raise HTTPException(status_code=400, detail="Must provide either property_ids or team_id")

    # Clear existing NBAs for these properties
    if request.property_ids:
        db.query(NextBestAction).filter(
            NextBestAction.property_id.in_(request.property_ids),
            NextBestAction.is_completed == False
        ).delete(synchronize_session=False)

    nba_count = 0

    # Generate NBAs for each property
    for property in properties:
        nbas = _generate_nba_rules(db, property)
        for nba in nbas:
            db.add(nba)
            nba_count += 1

    db.commit()

    return {"generated_count": nba_count, "properties_analyzed": len(properties)}

@router.get("/next-best-actions", response_model=List[schemas.NextBestActionResponse])
def list_next_best_actions(
    property_id: Optional[int] = Query(None),
    team_id: Optional[int] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """
    Get Next Best Actions, sorted by priority

    Filters:
    - property_id: Get NBAs for specific property
    - team_id: Get NBAs for all properties in team
    - limit: Max results
    """
    query = db.query(NextBestAction).filter(
        NextBestAction.is_completed == False,
        NextBestAction.dismissed_at.is_(None),
        or_(
            NextBestAction.expires_at.is_(None),
            NextBestAction.expires_at > datetime.utcnow()
        )
    )

    if property_id:
        query = query.filter(NextBestAction.property_id == property_id)
    elif team_id:
        # Join with Property to filter by team
        query = query.join(Property).filter(Property.team_id == team_id)

    nbas = query.order_by(NextBestAction.priority.desc()).limit(limit).all()

    return nbas

@router.post("/next-best-actions/{nba_id}/complete")
def complete_next_best_action(
    nba_id: int,
    db: Session = Depends(get_db)
):
    """
    Mark NBA as completed
    """
    nba = db.query(NextBestAction).filter(NextBestAction.id == nba_id).first()
    if not nba:
        raise HTTPException(status_code=404, detail="NBA not found")

    nba.is_completed = True
    nba.completed_at = datetime.utcnow()

    db.commit()

    return {"status": "completed"}

# ============================================================================
# SMART LISTS (SAVED QUERIES)
# ============================================================================

@router.post("/smart-lists", response_model=schemas.SmartListResponse, status_code=201)
def create_smart_list(
    smart_list_data: schemas.SmartListCreate,
    user_id: int,  # In production, get from auth token
    db: Session = Depends(get_db)
):
    """
    Create a Smart List (saved query with intent)

    Examples of filters:
    - {"bird_dog_score__gte": 0.7, "memo_url__is_null": true}  # High Score & No Memo
    - {"last_reply_date__gte": "2025-11-01T00:00:00Z"}  # Warm Replies Last 48h
    - {"current_stage": "outreach", "last_contact_days_ago_gte": 7}  # Stalled in Outreach

    Smart Lists auto-refresh and track property counts
    """
    smart_list = SmartList(
        team_id=smart_list_data.team_id,
        created_by_user_id=user_id,
        name=smart_list_data.name,
        description=smart_list_data.description,
        filters=smart_list_data.filters,
        is_dynamic=smart_list_data.is_dynamic
    )

    db.add(smart_list)
    db.commit()
    db.refresh(smart_list)

    return smart_list

@router.get("/smart-lists", response_model=List[schemas.SmartListResponse])
def list_smart_lists(
    team_id: int,
    db: Session = Depends(get_db)
):
    """
    List all Smart Lists for a team
    """
    smart_lists = (
        db.query(SmartList)
        .filter(SmartList.team_id == team_id)
        .order_by(SmartList.created_at.desc())
        .all()
    )

    return smart_lists

@router.get("/smart-lists/{smart_list_id}/properties", response_model=List[schemas.PropertyResponse])
def get_smart_list_properties(
    smart_list_id: int,
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """
    Execute Smart List query and return matching properties

    Applies saved filters dynamically
    """
    smart_list = db.query(SmartList).filter(SmartList.id == smart_list_id).first()
    if not smart_list:
        raise HTTPException(status_code=404, detail="Smart List not found")

    # Build query from filters
    query = db.query(Property).filter(
        Property.team_id == smart_list.team_id,
        Property.archived_at.is_(None)
    )

    filters = smart_list.filters

    # Apply filters (simplified version - in production, make this more robust)
    if "bird_dog_score__gte" in filters:
        query = query.filter(Property.bird_dog_score >= filters["bird_dog_score__gte"])

    if "bird_dog_score__lte" in filters:
        query = query.filter(Property.bird_dog_score <= filters["bird_dog_score__lte"])

    if "memo_url__is_null" in filters:
        if filters["memo_url__is_null"]:
            query = query.filter(Property.memo_url.is_(None))
        else:
            query = query.filter(Property.memo_url.isnot(None))

    if "current_stage" in filters:
        query = query.filter(Property.current_stage == filters["current_stage"])

    if "last_contact_days_ago_gte" in filters:
        cutoff = datetime.utcnow() - timedelta(days=filters["last_contact_days_ago_gte"])
        query = query.filter(
            or_(
                Property.last_contact_date.is_(None),
                Property.last_contact_date <= cutoff
            )
        )

    if "last_reply_date__gte" in filters:
        cutoff_date = datetime.fromisoformat(filters["last_reply_date__gte"].replace("Z", "+00:00"))
        query = query.filter(Property.last_reply_date >= cutoff_date)

    if "assigned_user_id" in filters:
        query = query.filter(Property.assigned_user_id == filters["assigned_user_id"])

    # Execute and update cached count
    properties = query.limit(limit).all()

    smart_list.cached_count = len(properties)
    smart_list.last_refreshed_at = datetime.utcnow()
    db.commit()

    return properties

# ============================================================================
# ONE-CLICK TASKING
# ============================================================================

@router.post("/create-task-from-event", response_model=schemas.TaskResponse, status_code=201)
def create_task_from_event(
    request: schemas.CreateTaskFromEventRequest,
    user_id: int,  # In production, get from auth token
    db: Session = Depends(get_db)
):
    """
    One-Click Tasking: Convert any timeline event into a task

    Common use cases:
    - Email reply → "Respond to inquiry" task
    - Call logged → "Follow up on call" task
    - Memo viewed → "Check investor interest" task

    Automatically sets SLA and priority based on event type
    """
    # Get property
    property = db.query(Property).filter(Property.id == request.property_id).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    # Get communication if provided
    communication = None
    source_event_type = None

    if request.communication_id:
        communication = db.query(Communication).filter(Communication.id == request.communication_id).first()
        if communication:
            source_event_type = f"{communication.direction.value}_{communication.type.value}"

    # Create task
    task = Task(
        property_id=request.property_id,
        assigned_user_id=property.assigned_user_id or user_id,
        created_by_user_id=user_id,
        title=request.title,
        description=request.description,
        status=TaskStatus.PENDING,
        priority=request.priority.value,
        sla_hours=request.sla_hours,
        due_at=datetime.utcnow() + timedelta(hours=request.sla_hours),
        source_event_type=source_event_type,
        source_communication_id=request.communication_id
    )

    db.add(task)
    db.flush()

    # Create timeline event
    timeline_event = PropertyTimeline(
        property_id=property.id,
        event_type="task_created",
        event_title="Task Created from Event",
        event_description=request.title,
        task_id=task.id,
        communication_id=request.communication_id,
        user_id=user_id
    )
    db.add(timeline_event)

    db.commit()
    db.refresh(task)

    return task
