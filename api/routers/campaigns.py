"""Campaign router."""

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func
from typing import Optional, List
from datetime import datetime

from ..database import get_db
from ..dependencies import get_current_user, require_permission
from ..models import (
    User,
    Campaign,
    CampaignTemplate,
    CampaignRecipient,
    Lead,
)
from ..models.campaign import CampaignType, CampaignStatus
from ..schemas.campaign import (
    CampaignCreate,
    CampaignUpdate,
    CampaignResponse,
    CampaignListResponse,
    CampaignStats,
    CampaignTemplateCreate,
    CampaignTemplateUpdate,
    CampaignTemplateResponse,
    CampaignSendRequest,
)

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


def send_campaign_messages(campaign_id: int, db: Session):
    """Background task to send campaign messages."""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        return

    campaign.status = CampaignStatus.IN_PROGRESS
    campaign.started_at = datetime.utcnow()
    db.commit()

    # Get pending recipients
    recipients = db.query(CampaignRecipient).filter(
        CampaignRecipient.campaign_id == campaign_id,
        CampaignRecipient.status == "pending",
    ).all()

    for recipient in recipients:
        try:
            # Mock sending logic - in production, integrate with email/SMS providers
            if campaign.campaign_type == CampaignType.EMAIL:
                print(f"Sending email to {recipient.email}: {campaign.subject}")
            elif campaign.campaign_type == CampaignType.SMS:
                print(f"Sending SMS to {recipient.phone}: {campaign.content[:100]}")

            # Update recipient status
            recipient.status = "sent"
            recipient.sent_at = datetime.utcnow()
            campaign.sent_count += 1

            # Simulate delivery (in production, webhooks would update this)
            recipient.status = "delivered"
            recipient.delivered_at = datetime.utcnow()
            campaign.delivered_count += 1

        except Exception as e:
            recipient.status = "failed"
            recipient.error_message = str(e)

        db.commit()

    # Mark campaign as completed
    campaign.status = CampaignStatus.COMPLETED
    campaign.completed_at = datetime.utcnow()
    db.commit()


@router.post("", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
def create_campaign(
    campaign: CampaignCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("campaign:create")),
):
    """Create a new campaign."""
    # Verify template if provided
    if campaign.template_id:
        template = db.query(CampaignTemplate).filter(
            CampaignTemplate.id == campaign.template_id,
            CampaignTemplate.organization_id == current_user.organization_id,
        ).first()

        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template not found",
            )

    db_campaign = Campaign(
        organization_id=current_user.organization_id,
        created_by=current_user.id,
        **campaign.model_dump(),
    )

    db.add(db_campaign)
    db.commit()
    db.refresh(db_campaign)

    return db_campaign


@router.get("", response_model=CampaignListResponse)
def list_campaigns(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    search: Optional[str] = None,
    campaign_type: Optional[CampaignType] = None,
    status: Optional[CampaignStatus] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("campaign:read")),
):
    """List campaigns with filtering and pagination."""
    query = db.query(Campaign).filter(
        Campaign.organization_id == current_user.organization_id,
    )

    # Apply filters
    if search:
        query = query.filter(
            or_(
                Campaign.name.ilike(f"%{search}%"),
                Campaign.description.ilike(f"%{search}%"),
                Campaign.subject.ilike(f"%{search}%"),
            )
        )

    if campaign_type:
        query = query.filter(Campaign.campaign_type == campaign_type)

    if status:
        query = query.filter(Campaign.status == status)

    # Get total count
    total = query.count()

    # Apply pagination
    offset = (page - 1) * page_size
    campaigns = query.order_by(Campaign.created_at.desc()).offset(offset).limit(page_size).all()

    return {
        "items": campaigns,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
    }


@router.get("/stats", response_model=CampaignStats)
def get_campaign_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("campaign:read")),
):
    """Get campaign statistics."""
    campaigns = db.query(Campaign).filter(
        Campaign.organization_id == current_user.organization_id,
    ).all()

    total_campaigns = len(campaigns)
    total_sent = sum(c.sent_count for c in campaigns)
    total_delivered = sum(c.delivered_count for c in campaigns)
    total_opened = sum(c.opened_count for c in campaigns)
    total_clicked = sum(c.clicked_count for c in campaigns)

    delivery_rate = (total_delivered / total_sent * 100) if total_sent > 0 else 0.0
    open_rate = (total_opened / total_delivered * 100) if total_delivered > 0 else 0.0
    click_rate = (total_clicked / total_opened * 100) if total_opened > 0 else 0.0

    # Group by status
    by_status = {}
    for status in CampaignStatus:
        count = sum(1 for c in campaigns if c.status == status)
        by_status[status.value] = count

    # Group by type
    by_type = {}
    for campaign_type in CampaignType:
        count = sum(1 for c in campaigns if c.campaign_type == campaign_type)
        by_type[campaign_type.value] = count

    return {
        "total_campaigns": total_campaigns,
        "total_sent": total_sent,
        "total_delivered": total_delivered,
        "total_opened": total_opened,
        "total_clicked": total_clicked,
        "delivery_rate": delivery_rate,
        "open_rate": open_rate,
        "click_rate": click_rate,
        "by_status": by_status,
        "by_type": by_type,
    }


@router.get("/{campaign_id}", response_model=CampaignResponse)
def get_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("campaign:read")),
):
    """Get a specific campaign."""
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.organization_id == current_user.organization_id,
    ).first()

    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found",
        )

    return campaign


@router.put("/{campaign_id}", response_model=CampaignResponse)
def update_campaign(
    campaign_id: int,
    campaign_update: CampaignUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("campaign:update")),
):
    """Update a campaign."""
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.organization_id == current_user.organization_id,
    ).first()

    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found",
        )

    # Can only update draft campaigns
    if campaign.status != CampaignStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only update draft campaigns",
        )

    # Update campaign
    update_data = campaign_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(campaign, field, value)

    campaign.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(campaign)

    return campaign


@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("campaign:delete")),
):
    """Delete a campaign."""
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.organization_id == current_user.organization_id,
    ).first()

    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found",
        )

    # Can only delete draft campaigns
    if campaign.status != CampaignStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only delete draft campaigns",
        )

    db.delete(campaign)
    db.commit()


@router.post("/{campaign_id}/send", response_model=CampaignResponse)
def send_campaign(
    campaign_id: int,
    request: CampaignSendRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("campaign:send")),
):
    """Send a campaign to leads."""
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.organization_id == current_user.organization_id,
    ).first()

    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found",
        )

    if campaign.status not in [CampaignStatus.DRAFT, CampaignStatus.SCHEDULED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Campaign already sent or in progress",
        )

    # Get leads to send to
    leads = db.query(Lead).filter(
        Lead.organization_id == current_user.organization_id,
        Lead.deleted_at.is_(None),
    )

    if request.lead_ids:
        leads = leads.filter(Lead.id.in_(request.lead_ids))

    if request.filters:
        # Apply additional filters if provided
        if request.filters.get("status"):
            leads = leads.filter(Lead.status == request.filters["status"])
        if request.filters.get("source"):
            leads = leads.filter(Lead.source == request.filters["source"])

    leads = leads.all()

    if not leads:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No leads found matching criteria",
        )

    # Create recipients
    for lead in leads:
        recipient = CampaignRecipient(
            campaign_id=campaign_id,
            lead_id=lead.id,
            email=lead.email,
            phone=lead.phone,
            first_name=lead.first_name,
            last_name=lead.last_name,
            status="pending",
        )
        db.add(recipient)

    campaign.total_recipients = len(leads)
    campaign.status = CampaignStatus.SCHEDULED
    campaign.scheduled_at = request.send_at or datetime.utcnow()

    db.commit()
    db.refresh(campaign)

    # Schedule background task to send campaign
    if request.send_now:
        background_tasks.add_task(send_campaign_messages, campaign_id, db)

    return campaign


# ================== CAMPAIGN TEMPLATES ==================

@router.post("/templates", response_model=CampaignTemplateResponse, status_code=status.HTTP_201_CREATED)
def create_template(
    template: CampaignTemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("campaign:create")),
):
    """Create a campaign template."""
    db_template = CampaignTemplate(
        organization_id=current_user.organization_id,
        created_by=current_user.id,
        **template.model_dump(),
    )

    db.add(db_template)
    db.commit()
    db.refresh(db_template)

    return db_template


@router.get("/templates", response_model=List[CampaignTemplateResponse])
def list_templates(
    campaign_type: Optional[CampaignType] = None,
    is_active: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("campaign:read")),
):
    """List campaign templates."""
    query = db.query(CampaignTemplate).filter(
        CampaignTemplate.organization_id == current_user.organization_id,
        CampaignTemplate.is_active == is_active,
    )

    if campaign_type:
        query = query.filter(CampaignTemplate.campaign_type == campaign_type)

    templates = query.order_by(CampaignTemplate.created_at.desc()).all()

    return templates


@router.get("/templates/{template_id}", response_model=CampaignTemplateResponse)
def get_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("campaign:read")),
):
    """Get a specific template."""
    template = db.query(CampaignTemplate).filter(
        CampaignTemplate.id == template_id,
        CampaignTemplate.organization_id == current_user.organization_id,
    ).first()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )

    return template


@router.put("/templates/{template_id}", response_model=CampaignTemplateResponse)
def update_template(
    template_id: int,
    template_update: CampaignTemplateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("campaign:update")),
):
    """Update a template."""
    template = db.query(CampaignTemplate).filter(
        CampaignTemplate.id == template_id,
        CampaignTemplate.organization_id == current_user.organization_id,
    ).first()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )

    # Update template
    update_data = template_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(template, field, value)

    template.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(template)

    return template


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("campaign:delete")),
):
    """Delete a template."""
    template = db.query(CampaignTemplate).filter(
        CampaignTemplate.id == template_id,
        CampaignTemplate.organization_id == current_user.organization_id,
    ).first()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )

    db.delete(template)
    db.commit()
