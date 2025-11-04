"""
Workflow automation API endpoints.

P0 Features:
- Next Best Action (NBA) - The ONE thing to do next
- Smart Lists - Saved intents with dynamic filtering
- One-Click Tasking - Convert events to tasks with SLA
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func, case
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from api.database import get_db
from api import schemas
from db import models

router = APIRouter(prefix="/workflow", tags=["Workflow"])


# ============================================================================
# NEXT BEST ACTION (NBA) - P0 Feature
# ============================================================================

@router.get("/next-best-actions", response_model=List[schemas.NextBestActionResponse])
def list_next_best_actions(
    property_id: Optional[int] = None,
    is_completed: bool = False,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    Get Next Best Action recommendations.

    Returns AI-generated recommendations for what to do next on each property,
    driven by stage, freshness, and recent activity.
    """

    query = db.query(models.NextBestAction).filter(
        models.NextBestAction.is_completed == is_completed,
        models.NextBestAction.dismissed_at.is_(None)
    )

    if property_id:
        query = query.filter(models.NextBestAction.property_id == property_id)

    actions = query.order_by(
        models.NextBestAction.priority_score.desc(),
        models.NextBestAction.created_at.desc()
    ).limit(limit).all()

    return actions


@router.post("/next-best-actions/generate", response_model=Dict[str, Any])
def generate_next_best_actions(
    property_id: Optional[int] = None,
    force_regenerate: bool = False,
    db: Session = Depends(get_db)
):
    """
    Generate Next Best Action recommendations for properties.

    Logic for NBA generation:
    1. Properties in outreach with no reply > 7 days → "Send follow-up"
    2. High score properties with no memo → "Generate memo"
    3. Properties in negotiation without packet → "Send packet"
    4. Warm replies in last 48h → "Respond to warm lead"
    5. Properties stalled in stage > 14 days → "Move to next stage or archive"

    Args:
        property_id: Generate for specific property only
        force_regenerate: Clear existing NBAs and regenerate
    """

    if property_id:
        properties = db.query(models.Property).filter(
            models.Property.id == property_id,
            models.Property.archived_at.is_(None)
        ).all()
    else:
        properties = db.query(models.Property).filter(
            models.Property.archived_at.is_(None)
        ).all()

    if force_regenerate:
        # Clear existing uncompleted NBAs
        db.query(models.NextBestAction).filter(
            models.NextBestAction.property_id.in_([p.id for p in properties]),
            models.NextBestAction.is_completed == False
        ).delete(synchronize_session=False)

    generated_count = 0
    now = datetime.utcnow()

    for property in properties:
        actions_to_create = []

        # Rule 1: Outreach with no reply > 7 days
        if property.current_stage == "outreach":
            if property.last_contact_date:
                days_since_contact = (now - property.last_contact_date).days
                if days_since_contact >= 7 and property.reply_count == 0:
                    actions_to_create.append({
                        "action_type": "send_followup",
                        "title": "Send follow-up email",
                        "description": f"{days_since_contact} days since last contact with no reply",
                        "reasoning": "Property has been in outreach for a week with no response. A follow-up may re-engage the owner.",
                        "priority_score": 0.8,
                        "signals": {
                            "stage": "outreach",
                            "days_since_contact": days_since_contact,
                            "reply_count": 0
                        }
                    })

        # Rule 2: High score with no memo
        if property.bird_dog_score and property.bird_dog_score >= 0.7:
            if not property.memo_url:
                actions_to_create.append({
                    "action_type": "generate_memo",
                    "title": "Generate investor memo",
                    "description": f"High-scoring property (score: {property.bird_dog_score:.2f}) without memo",
                    "reasoning": "This property scored highly and needs an investor memo generated to share with potential buyers.",
                    "priority_score": 0.9,
                    "signals": {
                        "score": property.bird_dog_score,
                        "has_memo": False
                    }
                })

        # Rule 3: Negotiation without packet
        if property.current_stage == "negotiation":
            if not property.packet_url:
                actions_to_create.append({
                    "action_type": "send_packet",
                    "title": "Send deal packet",
                    "description": "Property in negotiation needs full packet sent",
                    "reasoning": "Property has moved to negotiation stage but packet hasn't been sent to investor yet.",
                    "priority_score": 0.95,
                    "signals": {
                        "stage": "negotiation",
                        "has_packet": False
                    }
                })

        # Rule 4: Warm replies in last 48h
        if property.last_reply_date:
            hours_since_reply = (now - property.last_reply_date).total_seconds() / 3600
            if hours_since_reply <= 48:
                actions_to_create.append({
                    "action_type": "respond_to_reply",
                    "title": "Respond to warm lead",
                    "description": f"Owner replied {int(hours_since_reply)} hours ago",
                    "reasoning": "Recent reply indicates warm interest. Respond quickly to maintain momentum.",
                    "priority_score": 1.0,  # Highest priority
                    "signals": {
                        "hours_since_reply": hours_since_reply,
                        "reply_count": property.reply_count
                    }
                })

        # Rule 5: Stalled in stage > 14 days
        days_in_stage = (now - property.created_at).days  # Simplified - should use stage history
        if days_in_stage >= 14 and property.current_stage not in ["won", "lost", "archived"]:
            actions_to_create.append({
                "action_type": "move_or_archive",
                "title": "Move to next stage or archive",
                "description": f"Property stuck in {property.current_stage} for {days_in_stage} days",
                "reasoning": "Property hasn't progressed. Consider moving forward or archiving if no longer viable.",
                "priority_score": 0.6,
                "signals": {
                    "stage": property.current_stage,
                    "days_in_stage": days_in_stage
                }
            })

        # Create NBA records
        for action_data in actions_to_create:
            nba = models.NextBestAction(
                property_id=property.id,
                **action_data
            )
            db.add(nba)
            generated_count += 1

    db.commit()

    return {
        "success": True,
        "properties_processed": len(properties),
        "actions_generated": generated_count
    }


@router.post("/next-best-actions/{action_id}/execute")
def execute_next_best_action(
    action_id: int,
    user_id: int = 1,  # TODO: Get from auth
    db: Session = Depends(get_db)
):
    """
    Execute a Next Best Action.

    This marks the action as completed and performs any associated automation.
    """

    nba = db.query(models.NextBestAction).filter(
        models.NextBestAction.id == action_id
    ).first()
    if not nba:
        raise HTTPException(status_code=404, detail="Next Best Action not found")

    # Mark as completed
    nba.is_completed = True
    nba.completed_at = datetime.utcnow()

    # Create timeline event
    timeline_event = models.TimelineEvent(
        property_id=nba.property_id,
        event_type="nba_executed",
        title=f"Executed: {nba.title}",
        description=nba.description,
        user_id=user_id,
        related_type="next_best_action",
        related_id=action_id
    )
    db.add(timeline_event)

    db.commit()

    return {
        "success": True,
        "action_id": action_id,
        "action_type": nba.action_type,
        "completed_at": nba.completed_at
    }


@router.post("/next-best-actions/{action_id}/dismiss")
def dismiss_next_best_action(
    action_id: int,
    db: Session = Depends(get_db)
):
    """Dismiss a Next Best Action without executing it"""

    nba = db.query(models.NextBestAction).filter(
        models.NextBestAction.id == action_id
    ).first()
    if not nba:
        raise HTTPException(status_code=404, detail="Next Best Action not found")

    nba.dismissed_at = datetime.utcnow()
    db.commit()

    return {
        "success": True,
        "action_id": action_id,
        "dismissed_at": nba.dismissed_at
    }


# ============================================================================
# SMART LISTS - P0 Feature
# ============================================================================

@router.get("/smart-lists", response_model=List[schemas.SmartListResponse])
def list_smart_lists(
    user_id: Optional[int] = None,
    include_shared: bool = True,
    db: Session = Depends(get_db)
):
    """
    Get all smart lists.

    Returns saved search criteria that create dynamic property lists.
    """

    query = db.query(models.SmartList)

    if user_id:
        if include_shared:
            query = query.filter(
                or_(
                    models.SmartList.created_by_id == user_id,
                    models.SmartList.is_shared == True
                )
            )
        else:
            query = query.filter(models.SmartList.created_by_id == user_id)

    smart_lists = query.order_by(
        models.SmartList.order_index.asc(),
        models.SmartList.created_at.desc()
    ).all()

    return smart_lists


@router.post("/smart-lists", response_model=schemas.SmartListResponse, status_code=201)
def create_smart_list(
    smart_list_data: schemas.SmartListCreate,
    user_id: int = 1,  # TODO: Get from auth
    db: Session = Depends(get_db)
):
    """
    Create a new smart list.

    Smart lists are saved filter configurations that create dynamic views.

    Examples:
    - "High score & no memo": {"bird_dog_score__gte": 0.7, "memo_url__is_null": true}
    - "Warm replies last 48h": {"last_reply_date__gte": "2025-11-01T00:00:00Z"}
    - "Stalled in Outreach 7+ days": {"current_stage": "outreach", "days_in_stage__gte": 7}
    """

    smart_list = models.SmartList(
        **smart_list_data.model_dump(),
        created_by_id=user_id
    )
    db.add(smart_list)
    db.commit()
    db.refresh(smart_list)

    # Refresh count
    count = _get_smart_list_count(smart_list.id, db)
    smart_list.property_count = count
    smart_list.last_refreshed_at = datetime.utcnow()
    db.commit()
    db.refresh(smart_list)

    return smart_list


@router.get("/smart-lists/{list_id}", response_model=schemas.SmartListResponse)
def get_smart_list(list_id: int, db: Session = Depends(get_db)):
    """Get a specific smart list"""

    smart_list = db.query(models.SmartList).filter(
        models.SmartList.id == list_id
    ).first()
    if not smart_list:
        raise HTTPException(status_code=404, detail="Smart list not found")

    return smart_list


@router.get("/smart-lists/{list_id}/properties", response_model=schemas.PropertyListResponse)
def get_smart_list_properties(
    list_id: int,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db)
):
    """
    Get properties matching a smart list.

    Applies the saved filter criteria to return matching properties.
    """

    smart_list = db.query(models.SmartList).filter(
        models.SmartList.id == list_id
    ).first()
    if not smart_list:
        raise HTTPException(status_code=404, detail="Smart list not found")

    # Build query from filters
    query = db.query(models.Property).filter(
        models.Property.archived_at.is_(None)
    )

    # Apply filters
    filters = smart_list.filters
    query = _apply_smart_list_filters(query, filters)

    # Get total count
    total = query.count()

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


@router.post("/smart-lists/{list_id}/refresh")
def refresh_smart_list(list_id: int, db: Session = Depends(get_db)):
    """Refresh the property count for a smart list"""

    smart_list = db.query(models.SmartList).filter(
        models.SmartList.id == list_id
    ).first()
    if not smart_list:
        raise HTTPException(status_code=404, detail="Smart list not found")

    count = _get_smart_list_count(list_id, db)
    smart_list.property_count = count
    smart_list.last_refreshed_at = datetime.utcnow()
    db.commit()

    return {
        "success": True,
        "list_id": list_id,
        "property_count": count,
        "refreshed_at": smart_list.last_refreshed_at
    }


@router.delete("/smart-lists/{list_id}", status_code=204)
def delete_smart_list(list_id: int, db: Session = Depends(get_db)):
    """Delete a smart list"""

    smart_list = db.query(models.SmartList).filter(
        models.SmartList.id == list_id
    ).first()
    if not smart_list:
        raise HTTPException(status_code=404, detail="Smart list not found")

    db.delete(smart_list)
    db.commit()
    return None


# ============================================================================
# ONE-CLICK TASKING - P1 Feature
# ============================================================================

@router.post("/create-task-from-event", response_model=schemas.TaskResponse, status_code=201)
def create_task_from_event(
    event_type: str,
    event_id: int,
    assignee_id: int,
    sla_hours: int = 24,
    user_id: int = 1,  # TODO: Get from auth
    db: Session = Depends(get_db)
):
    """
    One-click task creation from events.

    Converts an event (reply, open, call note) into a task with SLA and assignee.

    Event types:
    - communication: Create task from email/call
    - timeline_event: Create task from timeline event
    """

    title = ""
    description = ""
    property_id = None

    if event_type == "communication":
        comm = db.query(models.Communication).filter(
            models.Communication.id == event_id
        ).first()
        if not comm:
            raise HTTPException(status_code=404, detail="Communication not found")

        property_id = comm.property_id
        title = f"Follow up on {comm.type.value}"
        description = f"Subject: {comm.subject or 'N/A'}\n\n{comm.body_text[:200] if comm.body_text else ''}"

    elif event_type == "timeline_event":
        event = db.query(models.TimelineEvent).filter(
            models.TimelineEvent.id == event_id
        ).first()
        if not event:
            raise HTTPException(status_code=404, detail="Timeline event not found")

        property_id = event.property_id
        title = f"Follow up on: {event.title}"
        description = event.description

    else:
        raise HTTPException(status_code=400, detail=f"Unsupported event type: {event_type}")

    # Calculate due date
    due_date = datetime.utcnow() + timedelta(hours=sla_hours)

    # Create task
    task = models.Task(
        property_id=property_id,
        title=title,
        description=description,
        assignee_id=assignee_id,
        created_by_id=user_id,
        priority=models.TaskPriorityEnum.HIGH,
        sla_hours=sla_hours,
        due_date=due_date,
        source_type=event_type,
        source_id=event_id
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    return task


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _apply_smart_list_filters(query, filters: Dict[str, Any]):
    """Apply smart list filters to a property query"""

    for key, value in filters.items():
        # Handle comparison operators
        if "__" in key:
            field_name, operator = key.rsplit("__", 1)
            field = getattr(models.Property, field_name, None)

            if field is None:
                continue

            if operator == "gte":
                query = query.filter(field >= value)
            elif operator == "lte":
                query = query.filter(field <= value)
            elif operator == "gt":
                query = query.filter(field > value)
            elif operator == "lt":
                query = query.filter(field < value)
            elif operator == "is_null":
                if value:
                    query = query.filter(field.is_(None))
                else:
                    query = query.filter(field.isnot(None))
            elif operator == "in":
                query = query.filter(field.in_(value))
            elif operator == "contains":
                query = query.filter(field.ilike(f"%{value}%"))
        else:
            # Direct equality
            field = getattr(models.Property, key, None)
            if field is not None:
                if isinstance(value, list):
                    query = query.filter(field.in_(value))
                else:
                    query = query.filter(field == value)

    return query


def _get_smart_list_count(list_id: int, db: Session) -> int:
    """Get the count of properties matching a smart list"""

    smart_list = db.query(models.SmartList).filter(
        models.SmartList.id == list_id
    ).first()
    if not smart_list:
        return 0

    query = db.query(func.count(models.Property.id)).filter(
        models.Property.archived_at.is_(None)
    )

    query = _apply_smart_list_filters(query, smart_list.filters)

    return query.scalar()
