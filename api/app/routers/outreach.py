"""
Outreach Campaigns API Router

Wave 3.3 Part 4: REST API for campaign management

Endpoints:
- POST /outreach/campaigns - Create campaign
- GET /outreach/campaigns - List campaigns
- GET /outreach/campaigns/{id} - Get campaign details
- PATCH /outreach/campaigns/{id}/status - Start/pause/complete campaign
- POST /outreach/campaigns/{id}/recipients - Add recipients
- GET /outreach/campaigns/{id}/analytics - Get campaign analytics
- POST /outreach/templates - Create template
- GET /outreach/templates - List templates
"""

import logging
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from ..database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/outreach",
    tags=["outreach"],
    responses={404: {"description": "Not found"}},
)


# =============================================================================
# REQUEST/RESPONSE SCHEMAS
# =============================================================================

class TemplateCreate(BaseModel):
    name: str
    subject: str
    body_html: str
    body_text: Optional[str] = None
    variables: List[str] = []
    tags: List[str] = []


class TemplateResponse(BaseModel):
    id: str
    name: str
    subject: str
    body_html: str
    body_text: Optional[str]
    variables: List[str]
    tags: List[str]
    created_at: str


class CampaignStepCreate(BaseModel):
    template_id: str
    delay_days: int = 0
    delay_hours: int = 0
    send_time_hour: Optional[int] = None
    conditions: Optional[dict] = None


class CampaignCreate(BaseModel):
    name: str
    description: Optional[str] = None
    campaign_type: str  # seller_outreach, agent_networking, etc.
    from_email: str
    from_name: str
    reply_to: Optional[str] = None
    steps: List[CampaignStepCreate]
    tags: List[str] = []


class CampaignResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    campaign_type: str
    status: str
    from_email: str
    from_name: str
    reply_to: Optional[str]
    total_recipients: int
    emails_sent: int
    emails_delivered: int
    emails_opened: int
    emails_clicked: int
    replies_received: int
    unsubscribes: int
    tags: List[str]
    created_at: str
    updated_at: str


class RecipientCreate(BaseModel):
    email: str
    name: Optional[str] = None
    property_id: Optional[str] = None
    template_data: dict = {}
    tags: List[str] = []


class CampaignAnalyticsResponse(BaseModel):
    campaign_id: str
    total_recipients: int
    sent: int
    delivered: int
    opened: int
    clicked: int
    replied: int
    unsubscribed: int
    bounced: int
    delivery_rate: float
    open_rate: float
    click_rate: float
    reply_rate: float
    unsubscribe_rate: float
    bounce_rate: float
    step_metrics: List[dict]


# =============================================================================
# TEMPLATE ENDPOINTS
# =============================================================================

@router.post("/templates", response_model=TemplateResponse)
def create_template(
    template: TemplateCreate,
    tenant_id: UUID = Query(..., description="Tenant ID"),
    db: Session = Depends(get_db)
):
    """Create email template"""
    from db.models_outreach import EmailTemplate

    db_template = EmailTemplate(
        tenant_id=tenant_id,
        name=template.name,
        subject=template.subject,
        body_html=template.body_html,
        body_text=template.body_text,
        variables=template.variables,
        tags=template.tags
    )

    db.add(db_template)
    db.commit()
    db.refresh(db_template)

    return TemplateResponse(
        id=str(db_template.id),
        name=db_template.name,
        subject=db_template.subject,
        body_html=db_template.body_html,
        body_text=db_template.body_text,
        variables=db_template.variables,
        tags=db_template.tags,
        created_at=db_template.created_at.isoformat()
    )


@router.get("/templates", response_model=List[TemplateResponse])
def list_templates(
    tenant_id: UUID = Query(..., description="Tenant ID"),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List email templates"""
    from db.models_outreach import EmailTemplate

    templates = db.query(EmailTemplate).filter(
        EmailTemplate.tenant_id == tenant_id
    ).order_by(EmailTemplate.created_at.desc()).limit(limit).all()

    return [
        TemplateResponse(
            id=str(t.id),
            name=t.name,
            subject=t.subject,
            body_html=t.body_html,
            body_text=t.body_text,
            variables=t.variables,
            tags=t.tags,
            created_at=t.created_at.isoformat()
        )
        for t in templates
    ]


# =============================================================================
# CAMPAIGN ENDPOINTS
# =============================================================================

@router.post("/campaigns", response_model=CampaignResponse)
def create_campaign(
    campaign: CampaignCreate,
    tenant_id: UUID = Query(..., description="Tenant ID"),
    db: Session = Depends(get_db)
):
    """Create new campaign"""
    from db.models_outreach import Campaign, CampaignStep

    # Create campaign
    db_campaign = Campaign(
        tenant_id=tenant_id,
        name=campaign.name,
        description=campaign.description,
        campaign_type=campaign.campaign_type,
        status="draft",
        from_email=campaign.from_email,
        from_name=campaign.from_name,
        reply_to=campaign.reply_to or campaign.from_email,
        tags=campaign.tags
    )

    db.add(db_campaign)
    db.flush()

    # Add steps
    for idx, step in enumerate(campaign.steps, start=1):
        db_step = CampaignStep(
            campaign_id=db_campaign.id,
            step_number=idx,
            template_id=UUID(step.template_id),
            delay_days=step.delay_days,
            delay_hours=step.delay_hours,
            send_time_hour=step.send_time_hour,
            conditions=step.conditions
        )
        db.add(db_step)

    db.commit()
    db.refresh(db_campaign)

    return CampaignResponse(
        id=str(db_campaign.id),
        name=db_campaign.name,
        description=db_campaign.description,
        campaign_type=db_campaign.campaign_type,
        status=db_campaign.status,
        from_email=db_campaign.from_email,
        from_name=db_campaign.from_name,
        reply_to=db_campaign.reply_to,
        total_recipients=0,
        emails_sent=0,
        emails_delivered=0,
        emails_opened=0,
        emails_clicked=0,
        replies_received=0,
        unsubscribes=0,
        tags=db_campaign.tags,
        created_at=db_campaign.created_at.isoformat(),
        updated_at=db_campaign.updated_at.isoformat()
    )


@router.get("/campaigns", response_model=List[CampaignResponse])
def list_campaigns(
    tenant_id: UUID = Query(..., description="Tenant ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List campaigns"""
    from db.models_outreach import Campaign

    query = db.query(Campaign).filter(Campaign.tenant_id == tenant_id)

    if status:
        query = query.filter(Campaign.status == status)

    campaigns = query.order_by(Campaign.created_at.desc()).limit(limit).all()

    return [
        CampaignResponse(
            id=str(c.id),
            name=c.name,
            description=c.description,
            campaign_type=c.campaign_type,
            status=c.status,
            from_email=c.from_email,
            from_name=c.from_name,
            reply_to=c.reply_to,
            total_recipients=c.total_recipients,
            emails_sent=c.emails_sent,
            emails_delivered=c.emails_delivered,
            emails_opened=c.emails_opened,
            emails_clicked=c.emails_clicked,
            replies_received=c.replies_received,
            unsubscribes=c.unsubscribes,
            tags=c.tags,
            created_at=c.created_at.isoformat(),
            updated_at=c.updated_at.isoformat()
        )
        for c in campaigns
    ]


@router.get("/campaigns/{campaign_id}", response_model=CampaignResponse)
def get_campaign(
    campaign_id: UUID,
    tenant_id: UUID = Query(..., description="Tenant ID"),
    db: Session = Depends(get_db)
):
    """Get campaign details"""
    from db.models_outreach import Campaign

    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.tenant_id == tenant_id
    ).first()

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    return CampaignResponse(
        id=str(campaign.id),
        name=campaign.name,
        description=campaign.description,
        campaign_type=campaign.campaign_type,
        status=campaign.status,
        from_email=campaign.from_email,
        from_name=campaign.from_name,
        reply_to=campaign.reply_to,
        total_recipients=campaign.total_recipients,
        emails_sent=campaign.emails_sent,
        emails_delivered=campaign.emails_delivered,
        emails_opened=campaign.emails_opened,
        emails_clicked=campaign.emails_clicked,
        replies_received=campaign.replies_received,
        unsubscribes=campaign.unsubscribes,
        tags=campaign.tags,
        created_at=campaign.created_at.isoformat(),
        updated_at=campaign.updated_at.isoformat()
    )


@router.patch("/campaigns/{campaign_id}/status")
def update_campaign_status(
    campaign_id: UUID,
    status: str = Body(..., embed=True, description="New status: draft/active/paused/completed/archived"),
    tenant_id: UUID = Query(..., description="Tenant ID"),
    db: Session = Depends(get_db)
):
    """Update campaign status (start, pause, complete, archive)"""
    from db.models_outreach import Campaign

    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.tenant_id == tenant_id
    ).first()

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    valid_statuses = ["draft", "active", "paused", "completed", "archived"]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")

    campaign.status = status
    campaign.updated_at = datetime.utcnow()

    if status == "active" and not campaign.start_date:
        campaign.start_date = datetime.utcnow()

    db.commit()

    return {"campaign_id": str(campaign_id), "status": status, "updated_at": campaign.updated_at.isoformat()}


@router.post("/campaigns/{campaign_id}/recipients")
def add_recipients(
    campaign_id: UUID,
    recipients: List[RecipientCreate],
    tenant_id: UUID = Query(..., description="Tenant ID"),
    db: Session = Depends(get_db)
):
    """Add recipients to campaign"""
    from db.models_outreach import Campaign, CampaignRecipient

    # Verify campaign exists
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.tenant_id == tenant_id
    ).first()

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Add recipients
    added = 0
    for recipient in recipients:
        db_recipient = CampaignRecipient(
            campaign_id=campaign_id,
            tenant_id=tenant_id,
            email=recipient.email,
            name=recipient.name,
            property_id=UUID(recipient.property_id) if recipient.property_id else None,
            template_data=recipient.template_data,
            tags=recipient.tags
        )
        db.add(db_recipient)
        added += 1

    # Update campaign recipient count
    campaign.total_recipients += added

    db.commit()

    return {
        "campaign_id": str(campaign_id),
        "added": added,
        "total_recipients": campaign.total_recipients
    }


@router.get("/campaigns/{campaign_id}/analytics", response_model=CampaignAnalyticsResponse)
def get_campaign_analytics(
    campaign_id: UUID,
    tenant_id: UUID = Query(..., description="Tenant ID"),
    db: Session = Depends(get_db)
):
    """Get campaign analytics and metrics"""
    from db.models_outreach import Campaign, CampaignRecipient
    from ml.models.outreach_campaigns import CampaignAnalytics

    # Get campaign
    campaign = db.query(Campaign).filter(
        Campaign.id == campaign_id,
        Campaign.tenant_id == tenant_id
    ).first()

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Get recipients
    recipients = db.query(CampaignRecipient).filter(
        CampaignRecipient.campaign_id == campaign_id,
        CampaignRecipient.tenant_id == tenant_id
    ).all()

    # Convert to domain objects for analytics
    from ml.models.outreach_campaigns import (
        CampaignRecipient as DomainRecipient,
        RecipientStatus,
        Campaign as DomainCampaign
    )

    domain_recipients = [
        DomainRecipient(
            id=str(r.id),
            campaign_id=str(r.campaign_id),
            email=r.email,
            name=r.name,
            status=RecipientStatus(r.status),
            current_step=r.current_step,
            last_email_sent_at=r.last_email_sent_at,
            last_opened_at=r.last_opened_at,
            last_clicked_at=r.last_clicked_at
        )
        for r in recipients
    ]

    domain_campaign = DomainCampaign(
        id=str(campaign.id),
        name=campaign.name,
        campaign_type=campaign.campaign_type,
        status=campaign.status
    )

    # Calculate metrics
    metrics = CampaignAnalytics.calculate_metrics(domain_campaign, domain_recipients)
    step_metrics = CampaignAnalytics.get_step_metrics(domain_campaign, domain_recipients)

    return CampaignAnalyticsResponse(
        campaign_id=str(campaign_id),
        total_recipients=metrics['total_recipients'],
        sent=metrics['sent'],
        delivered=metrics['delivered'],
        opened=metrics['opened'],
        clicked=metrics['clicked'],
        replied=metrics['replied'],
        unsubscribed=metrics['unsubscribed'],
        bounced=metrics['bounced'],
        delivery_rate=round(metrics['delivery_rate'], 3),
        open_rate=round(metrics['open_rate'], 3),
        click_rate=round(metrics['click_rate'], 3),
        reply_rate=round(metrics['reply_rate'], 3),
        unsubscribe_rate=round(metrics['unsubscribe_rate'], 3),
        bounce_rate=round(metrics['bounce_rate'], 3),
        step_metrics=step_metrics
    )
