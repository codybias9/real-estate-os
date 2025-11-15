"""Email campaign API routes."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
import sys
sys.path.insert(0, '/home/user/real-estate-os')

from api.database import get_db
from api.schemas import Campaign, CampaignCreate, OutreachLog, CampaignStatus
from db.models import Campaign as CampaignModel, OutreachLog as OutreachModel

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])


@router.get("", response_model=List[Campaign])
def list_campaigns(
    status: CampaignStatus = Query(None, description="Filter by status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List all campaigns."""

    query = db.query(CampaignModel)

    if status:
        query = query.filter(CampaignModel.status == status)

    campaigns = query.order_by(CampaignModel.created_at.desc()).offset(skip).limit(limit).all()

    return [Campaign.model_validate(c) for c in campaigns]


@router.get("/{campaign_id}", response_model=Campaign)
def get_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
):
    """Get a single campaign."""

    campaign = db.query(CampaignModel).filter(CampaignModel.id == campaign_id).first()

    if not campaign:
        raise HTTPException(status_code=404, detail=f"Campaign {campaign_id} not found")

    return Campaign.model_validate(campaign)


@router.post("", response_model=Campaign, status_code=201)
def create_campaign(
    campaign_data: CampaignCreate,
    db: Session = Depends(get_db),
):
    """Create a new campaign."""

    campaign = CampaignModel(**campaign_data.model_dump())
    campaign.total_recipients = len(campaign_data.recipient_emails)

    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    return Campaign.model_validate(campaign)


@router.post("/{campaign_id}/send", status_code=202)
def send_campaign(
    campaign_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Send a campaign (simulated)."""

    campaign = db.query(CampaignModel).filter(CampaignModel.id == campaign_id).first()

    if not campaign:
        raise HTTPException(status_code=404, detail=f"Campaign {campaign_id} not found")

    if campaign.status not in ['draft', 'scheduled']:
        raise HTTPException(status_code=400, detail="Campaign has already been sent or is in progress")

    # Update campaign status
    campaign.status = 'sending'
    db.commit()

    # In production, trigger actual email sending
    return {
        "message": "Campaign send triggered",
        "campaign_id": campaign_id,
        "status": "sending",
        "total_recipients": campaign.total_recipients,
    }


@router.get("/{campaign_id}/logs", response_model=List[OutreachLog])
def get_campaign_logs(
    campaign_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Get outreach logs for a campaign."""

    # Check if campaign exists
    campaign = db.query(CampaignModel).filter(CampaignModel.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail=f"Campaign {campaign_id} not found")

    # Get logs
    logs = db.query(OutreachModel).filter(
        OutreachModel.campaign_id == campaign_id
    ).order_by(OutreachModel.created_at.desc()).offset(skip).limit(limit).all()

    return [OutreachLog.model_validate(log) for log in logs]


@router.get("/stats/overview")
def get_campaigns_overview(db: Session = Depends(get_db)):
    """Get overview statistics for all campaigns."""

    from sqlalchemy import func

    total_campaigns = db.query(func.count(CampaignModel.id)).scalar()

    total_sent = db.query(func.sum(CampaignModel.emails_sent)).scalar() or 0
    total_delivered = db.query(func.sum(CampaignModel.emails_delivered)).scalar() or 0
    total_opened = db.query(func.sum(CampaignModel.emails_opened)).scalar() or 0
    total_clicked = db.query(func.sum(CampaignModel.emails_clicked)).scalar() or 0
    total_replied = db.query(func.sum(CampaignModel.emails_replied)).scalar() or 0

    # Calculate rates
    delivery_rate = (total_delivered / total_sent * 100) if total_sent > 0 else 0
    open_rate = (total_opened / total_delivered * 100) if total_delivered > 0 else 0
    click_rate = (total_clicked / total_opened * 100) if total_opened > 0 else 0
    reply_rate = (total_replied / total_delivered * 100) if total_delivered > 0 else 0

    return {
        "total_campaigns": total_campaigns,
        "emails": {
            "sent": total_sent,
            "delivered": total_delivered,
            "opened": total_opened,
            "clicked": total_clicked,
            "replied": total_replied,
        },
        "rates": {
            "delivery_rate": round(delivery_rate, 2),
            "open_rate": round(open_rate, 2),
            "click_rate": round(click_rate, 2),
            "reply_rate": round(reply_rate, 2),
        },
    }
