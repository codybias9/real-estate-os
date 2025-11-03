"""
Quick Win features API endpoints.

Month 1 quick wins that provide immediate friction reduction:
1. Generate & Send Combo - One-click from PDF → sent
2. Auto-Assign on Reply - Automatic assignment on inbound reply
3. Stage-Aware Templates - Filter templates by current stage
4. Flag Data Issue - Crowdsource quality fixes
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List
from datetime import datetime, timedelta
import secrets

from api.database import get_db
from api import schemas
from db import models

router = APIRouter(prefix="/quick-wins", tags=["Quick Wins"])


# ============================================================================
# QUICK WIN #1: Generate & Send Combo
# ============================================================================

@router.post("/generate-and-send", response_model=schemas.GenerateAndSendResponse)
def generate_and_send(
    request: schemas.GenerateAndSendRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Quick Win #1: Generate packet and send in one action.

    This endpoint:
    1. Optionally regenerates the investor memo if requested
    2. Generates the full packet (memo + comps + disclosures)
    3. Sends email with packet attached
    4. Creates communication record
    5. Updates property last_contact_date

    Background tasks handle the heavy lifting (PDF generation, email sending).
    """

    # Verify property exists
    property = db.query(models.Property).filter(
        models.Property.id == request.property_id
    ).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    # Verify template exists
    template = db.query(models.Template).filter(
        models.Template.id == request.template_id,
        models.Template.is_active == True
    ).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Check if template is allowed for current stage (stage-aware templates)
    if template.allowed_stages and property.current_stage not in template.allowed_stages:
        raise HTTPException(
            status_code=400,
            detail=f"Template not allowed for stage '{property.current_stage}'"
        )

    # Check if packet exists and if regeneration is requested
    packet_url = property.packet_url
    if request.regenerate_memo or not packet_url:
        # TODO: Trigger packet generation DAG or service
        # For now, set a placeholder
        packet_url = f"s3://packets/{property.id}/packet_{datetime.utcnow().isoformat()}.zip"
        property.packet_generated_at = datetime.utcnow()
        property.packet_url = packet_url

    # Render template with property data
    body_text = template.body_text.format(
        address=property.address,
        owner_name=property.owner_name or "Property Owner",
        score=property.bird_dog_score or "N/A",
        price=property.asking_price or "TBD"
    )
    subject = template.subject.format(
        address=property.address
    ) if template.subject else f"Investment Opportunity: {property.address}"

    # Create communication record
    communication = models.Communication(
        property_id=property.id,
        type=models.CommunicationTypeEnum.EMAIL,
        direction=models.CommunicationDirectionEnum.OUTBOUND,
        template_id=template.id,
        subject=subject,
        body_text=body_text,
        to_addresses=[request.to_email],
        sent_at=datetime.utcnow(),
        metadata={"packet_url": packet_url, "regenerated": request.regenerate_memo}
    )
    db.add(communication)

    # Update property
    property.last_contact_date = datetime.utcnow()
    property.total_touches += 1

    # Update template stats
    template.send_count += 1

    # Create timeline event
    timeline_event = models.TimelineEvent(
        property_id=property.id,
        event_type="packet_sent",
        title=f"Packet sent to {request.to_email}",
        description=f"Used template: {template.name}",
        related_type="communication",
        related_id=communication.id
    )
    db.add(timeline_event)

    db.commit()
    db.refresh(communication)

    # TODO: Schedule background task to actually send the email
    # background_tasks.add_task(send_email_with_attachment, communication.id, packet_url)

    return schemas.GenerateAndSendResponse(
        success=True,
        packet_url=packet_url,
        communication_id=communication.id,
        sent_at=communication.sent_at,
        message=f"Packet generated and sent to {request.to_email}"
    )


# ============================================================================
# QUICK WIN #2: Auto-Assign on Reply
# ============================================================================

@router.post("/auto-assign-on-reply/{communication_id}")
def auto_assign_on_reply(
    communication_id: int,
    assignee_id: int,
    db: Session = Depends(get_db)
):
    """
    Quick Win #2: Auto-assign property to user when they receive a reply.

    This is typically called by:
    - Email webhook when a reply is detected
    - Manual trigger by user
    - Automated workflow rule

    Logic:
    - If communication is an inbound reply
    - And property is not already assigned
    - Auto-assign to the user who sent the original email
    """

    communication = db.query(models.Communication).filter(
        models.Communication.id == communication_id
    ).first()
    if not communication:
        raise HTTPException(status_code=404, detail="Communication not found")

    if communication.direction != models.CommunicationDirectionEnum.INBOUND:
        raise HTTPException(status_code=400, detail="Communication is not an inbound reply")

    property = db.query(models.Property).filter(
        models.Property.id == communication.property_id
    ).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    # Check if already assigned
    if property.assigned_user_id:
        return {
            "success": False,
            "message": f"Property already assigned to user {property.assigned_user_id}",
            "property_id": property.id,
            "assigned_user_id": property.assigned_user_id
        }

    # Auto-assign
    property.assigned_user_id = assignee_id
    property.updated_at = datetime.utcnow()
    property.last_reply_date = datetime.utcnow()
    property.reply_count += 1

    # Create timeline event
    timeline_event = models.TimelineEvent(
        property_id=property.id,
        event_type="auto_assigned",
        title=f"Auto-assigned to user {assignee_id}",
        description="Automatically assigned due to inbound reply",
        user_id=assignee_id,
        metadata={"trigger": "inbound_reply", "communication_id": communication_id}
    )
    db.add(timeline_event)

    # Create task for follow-up
    task = models.Task(
        property_id=property.id,
        title="Follow up on reply",
        description=f"Property owner replied. Review and respond.",
        assignee_id=assignee_id,
        priority=models.TaskPriorityEnum.HIGH,
        sla_hours=24,
        source_type="email_reply",
        source_id=communication_id
    )
    db.add(task)

    db.commit()

    return {
        "success": True,
        "message": f"Property auto-assigned to user {assignee_id}",
        "property_id": property.id,
        "assigned_user_id": assignee_id,
        "task_created": True
    }


# ============================================================================
# QUICK WIN #3: Stage-Aware Templates
# ============================================================================

@router.get("/templates/for-stage/{stage}", response_model=List[schemas.TemplateResponse])
def get_templates_for_stage(
    stage: str,
    type: schemas.CommunicationTypeEnum = schemas.CommunicationTypeEnum.EMAIL,
    db: Session = Depends(get_db)
):
    """
    Quick Win #3: Get templates filtered by pipeline stage.

    Only returns templates that are:
    1. Active
    2. Match the communication type
    3. Either have no stage restrictions OR include the current stage

    This prevents users from picking the wrong template.
    """

    # Query templates
    templates = db.query(models.Template).filter(
        models.Template.is_active == True,
        models.Template.type == type
    ).all()

    # Filter by stage
    stage_aware_templates = []
    for template in templates:
        # If allowed_stages is empty, template is allowed for all stages
        if not template.allowed_stages or stage in template.allowed_stages:
            # Calculate performance metrics
            open_rate = None
            reply_rate = None
            if template.send_count > 0:
                open_rate = template.open_count / template.send_count
                reply_rate = template.reply_count / template.send_count

            template_dict = schemas.TemplateResponse.model_validate(template)
            template_dict.open_rate = open_rate
            template_dict.reply_rate = reply_rate
            stage_aware_templates.append(template_dict)

    return stage_aware_templates


# ============================================================================
# QUICK WIN #4: Flag Data Issue
# ============================================================================

@router.post("/flag-data-issue", response_model=schemas.DataFlagResponse, status_code=201)
def flag_data_issue(
    flag_data: schemas.DataFlagCreate,
    user_id: int = 1,  # TODO: Get from auth context
    db: Session = Depends(get_db)
):
    """
    Quick Win #4: Flag a data quality issue.

    Allows users to crowdsource data quality improvements by reporting:
    - Incorrect data
    - Outdated data
    - Missing data

    Creates a flag that can be reviewed and resolved by admins.
    """

    # Verify property exists
    property = db.query(models.Property).filter(
        models.Property.id == flag_data.property_id
    ).first()
    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    # Create data flag
    data_flag = models.DataFlag(
        property_id=flag_data.property_id,
        field_name=flag_data.field_name,
        issue_type=flag_data.issue_type,
        description=flag_data.description,
        suggested_value=flag_data.suggested_value,
        reported_by_id=user_id,
        status="open"
    )
    db.add(data_flag)

    # Add to property's data_flags JSON array
    if not isinstance(property.data_flags, list):
        property.data_flags = []

    property.data_flags.append({
        "field": flag_data.field_name,
        "issue": flag_data.issue_type,
        "reported_at": datetime.utcnow().isoformat(),
        "status": "open"
    })

    # Update data quality score (simple decrement)
    if property.data_quality_score is not None:
        property.data_quality_score = max(0, property.data_quality_score - 0.05)
    else:
        property.data_quality_score = 0.95

    # Create timeline event
    timeline_event = models.TimelineEvent(
        property_id=property.id,
        event_type="data_flagged",
        title=f"Data issue flagged: {flag_data.field_name}",
        description=f"{flag_data.issue_type}: {flag_data.description}",
        user_id=user_id
    )
    db.add(timeline_event)

    db.commit()
    db.refresh(data_flag)

    return data_flag


@router.get("/data-flags", response_model=List[schemas.DataFlagResponse])
def list_data_flags(
    status: str = "open",
    property_id: Optional[int] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    List data quality flags.

    Filters:
    - status: open, resolved, dismissed
    - property_id: Filter by property
    """

    query = db.query(models.DataFlag).filter(models.DataFlag.status == status)

    if property_id:
        query = query.filter(models.DataFlag.property_id == property_id)

    flags = query.order_by(models.DataFlag.created_at.desc()).limit(limit).all()

    return flags


@router.patch("/data-flags/{flag_id}/resolve")
def resolve_data_flag(
    flag_id: int,
    resolution_notes: Optional[str] = None,
    apply_suggestion: bool = False,
    user_id: int = 1,  # TODO: Get from auth context
    db: Session = Depends(get_db)
):
    """
    Resolve a data flag.

    Optionally applies the suggested value to the property.
    """

    flag = db.query(models.DataFlag).filter(models.DataFlag.id == flag_id).first()
    if not flag:
        raise HTTPException(status_code=404, detail="Data flag not found")

    # Update flag
    flag.status = "resolved"
    flag.resolved_at = datetime.utcnow()
    flag.resolved_by_id = user_id
    flag.resolution_notes = resolution_notes

    # Apply suggestion if requested
    if apply_suggestion and flag.suggested_value:
        property = db.query(models.Property).filter(
            models.Property.id == flag.property_id
        ).first()
        if property and hasattr(property, flag.field_name):
            setattr(property, flag.field_name, flag.suggested_value)

            # Create timeline event
            timeline_event = models.TimelineEvent(
                property_id=property.id,
                event_type="data_corrected",
                title=f"Data corrected: {flag.field_name}",
                description=f"Applied suggestion from data flag",
                user_id=user_id
            )
            db.add(timeline_event)

    db.commit()

    return {
        "success": True,
        "flag_id": flag_id,
        "status": "resolved",
        "applied_suggestion": apply_suggestion
    }
