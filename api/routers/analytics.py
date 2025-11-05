"""Analytics and reporting router."""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta, date
from decimal import Decimal

from ..database import get_db
from ..dependencies import get_current_user, require_permission
from ..models import (
    User,
    Property,
    Lead,
    Deal,
    Campaign,
    Transaction,
)
from ..models.property import PropertyStatus, PropertyType
from ..models.lead import LeadStatus, LeadSource
from ..models.deal import DealStage, DealType
from ..models.campaign import CampaignStatus

router = APIRouter(prefix="/analytics", tags=["analytics"])


class DashboardMetrics(BaseModel):
    """Dashboard metrics response."""
    total_properties: int
    total_leads: int
    total_deals: int
    total_deal_value: Decimal
    active_campaigns: int
    properties_by_status: Dict[str, int]
    leads_by_status: Dict[str, int]
    deals_by_stage: Dict[str, int]
    recent_activity_count: int


class PropertyMetrics(BaseModel):
    """Property metrics response."""
    total_properties: int
    by_type: Dict[str, int]
    by_status: Dict[str, int]
    avg_price: Decimal
    total_value: Decimal
    cities: List[Dict[str, Any]]


class LeadMetrics(BaseModel):
    """Lead metrics response."""
    total_leads: int
    by_status: Dict[str, int]
    by_source: Dict[str, int]
    avg_score: float
    conversion_rate: float
    new_leads_last_30_days: int


class DealMetrics(BaseModel):
    """Deal metrics response."""
    total_deals: int
    by_stage: Dict[str, int]
    by_type: Dict[str, int]
    total_value: Decimal
    avg_value: Decimal
    win_rate: float
    expected_revenue: Decimal


class CampaignMetrics(BaseModel):
    """Campaign metrics response."""
    total_campaigns: int
    active_campaigns: int
    total_sent: int
    total_delivered: int
    total_opened: int
    delivery_rate: float
    open_rate: float
    click_rate: float


class RevenueMetrics(BaseModel):
    """Revenue metrics response."""
    total_revenue: Decimal
    total_expenses: Decimal
    net_revenue: Decimal
    revenue_by_month: List[Dict[str, Any]]
    revenue_by_deal_type: Dict[str, Decimal]


from pydantic import BaseModel


@router.get("/dashboard", response_model=DashboardMetrics)
def get_dashboard_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("analytics:read")),
):
    """Get high-level dashboard metrics."""
    org_id = current_user.organization_id

    # Count totals
    total_properties = db.query(func.count(Property.id)).filter(
        Property.organization_id == org_id,
        Property.deleted_at.is_(None),
    ).scalar()

    total_leads = db.query(func.count(Lead.id)).filter(
        Lead.organization_id == org_id,
        Lead.deleted_at.is_(None),
    ).scalar()

    total_deals = db.query(func.count(Deal.id)).filter(
        Deal.organization_id == org_id,
        Deal.deleted_at.is_(None),
    ).scalar()

    total_deal_value = db.query(func.sum(Deal.value)).filter(
        Deal.organization_id == org_id,
        Deal.deleted_at.is_(None),
    ).scalar() or Decimal("0")

    active_campaigns = db.query(func.count(Campaign.id)).filter(
        Campaign.organization_id == org_id,
        Campaign.status.in_([CampaignStatus.IN_PROGRESS, CampaignStatus.SCHEDULED]),
    ).scalar()

    # Properties by status
    properties_by_status = {}
    for status in PropertyStatus:
        count = db.query(func.count(Property.id)).filter(
            Property.organization_id == org_id,
            Property.status == status,
            Property.deleted_at.is_(None),
        ).scalar()
        properties_by_status[status.value] = count

    # Leads by status
    leads_by_status = {}
    for status in LeadStatus:
        count = db.query(func.count(Lead.id)).filter(
            Lead.organization_id == org_id,
            Lead.status == status,
            Lead.deleted_at.is_(None),
        ).scalar()
        leads_by_status[status.value] = count

    # Deals by stage
    deals_by_stage = {}
    for stage in DealStage:
        count = db.query(func.count(Deal.id)).filter(
            Deal.organization_id == org_id,
            Deal.stage == stage,
            Deal.deleted_at.is_(None),
        ).scalar()
        deals_by_stage[stage.value] = count

    # Recent activity (last 7 days)
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    recent_activity_count = (
        db.query(func.count(Property.id)).filter(
            Property.organization_id == org_id,
            Property.created_at >= seven_days_ago,
        ).scalar()
        + db.query(func.count(Lead.id)).filter(
            Lead.organization_id == org_id,
            Lead.created_at >= seven_days_ago,
        ).scalar()
        + db.query(func.count(Deal.id)).filter(
            Deal.organization_id == org_id,
            Deal.created_at >= seven_days_ago,
        ).scalar()
    )

    return {
        "total_properties": total_properties,
        "total_leads": total_leads,
        "total_deals": total_deals,
        "total_deal_value": total_deal_value,
        "active_campaigns": active_campaigns,
        "properties_by_status": properties_by_status,
        "leads_by_status": leads_by_status,
        "deals_by_stage": deals_by_stage,
        "recent_activity_count": recent_activity_count,
    }


@router.get("/properties", response_model=PropertyMetrics)
def get_property_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("analytics:read")),
):
    """Get property analytics."""
    org_id = current_user.organization_id

    properties = db.query(Property).filter(
        Property.organization_id == org_id,
        Property.deleted_at.is_(None),
    ).all()

    total_properties = len(properties)

    # By type
    by_type = {}
    for prop_type in PropertyType:
        count = sum(1 for p in properties if p.property_type == prop_type)
        by_type[prop_type.value] = count

    # By status
    by_status = {}
    for status in PropertyStatus:
        count = sum(1 for p in properties if p.status == status)
        by_status[status.value] = count

    # Calculate values
    prices = [p.price for p in properties if p.price]
    avg_price = sum(prices) / len(prices) if prices else Decimal("0")
    total_value = sum(prices)

    # Top cities
    city_counts = {}
    for p in properties:
        city_counts[p.city] = city_counts.get(p.city, 0) + 1

    cities = [
        {"city": city, "count": count}
        for city, count in sorted(city_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    ]

    return {
        "total_properties": total_properties,
        "by_type": by_type,
        "by_status": by_status,
        "avg_price": avg_price,
        "total_value": total_value,
        "cities": cities,
    }


@router.get("/leads", response_model=LeadMetrics)
def get_lead_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("analytics:read")),
):
    """Get lead analytics."""
    org_id = current_user.organization_id

    leads = db.query(Lead).filter(
        Lead.organization_id == org_id,
        Lead.deleted_at.is_(None),
    ).all()

    total_leads = len(leads)

    # By status
    by_status = {}
    for status in LeadStatus:
        count = sum(1 for lead in leads if lead.status == status)
        by_status[status.value] = count

    # By source
    by_source = {}
    for source in LeadSource:
        count = sum(1 for lead in leads if lead.source == source)
        by_source[source.value] = count

    # Calculate metrics
    avg_score = sum(lead.score for lead in leads) / total_leads if total_leads > 0 else 0.0

    converted = sum(1 for lead in leads if lead.status == LeadStatus.CONVERTED)
    conversion_rate = (converted / total_leads * 100) if total_leads > 0 else 0.0

    # New leads last 30 days
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    new_leads_last_30_days = sum(1 for lead in leads if lead.created_at >= thirty_days_ago)

    return {
        "total_leads": total_leads,
        "by_status": by_status,
        "by_source": by_source,
        "avg_score": avg_score,
        "conversion_rate": conversion_rate,
        "new_leads_last_30_days": new_leads_last_30_days,
    }


@router.get("/deals", response_model=DealMetrics)
def get_deal_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("analytics:read")),
):
    """Get deal analytics."""
    org_id = current_user.organization_id

    deals = db.query(Deal).filter(
        Deal.organization_id == org_id,
        Deal.deleted_at.is_(None),
    ).all()

    total_deals = len(deals)

    # By stage
    by_stage = {}
    for stage in DealStage:
        count = sum(1 for deal in deals if deal.stage == stage)
        by_stage[stage.value] = count

    # By type
    by_type = {}
    for deal_type in DealType:
        count = sum(1 for deal in deals if deal.deal_type == deal_type)
        by_type[deal_type.value] = count

    # Calculate values
    total_value = sum(deal.value for deal in deals)
    avg_value = total_value / total_deals if total_deals > 0 else Decimal("0")

    # Win rate
    won_deals = sum(1 for deal in deals if deal.stage == DealStage.CLOSED_WON)
    lost_deals = sum(1 for deal in deals if deal.stage == DealStage.CLOSED_LOST)
    closed_deals = won_deals + lost_deals
    win_rate = (won_deals / closed_deals * 100) if closed_deals > 0 else 0.0

    # Expected revenue (based on probability)
    expected_revenue = sum(
        deal.value * (deal.probability / 100)
        for deal in deals
        if deal.stage not in [DealStage.CLOSED_WON, DealStage.CLOSED_LOST]
    )

    return {
        "total_deals": total_deals,
        "by_stage": by_stage,
        "by_type": by_type,
        "total_value": total_value,
        "avg_value": avg_value,
        "win_rate": win_rate,
        "expected_revenue": expected_revenue,
    }


@router.get("/campaigns", response_model=CampaignMetrics)
def get_campaign_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("analytics:read")),
):
    """Get campaign analytics."""
    org_id = current_user.organization_id

    campaigns = db.query(Campaign).filter(
        Campaign.organization_id == org_id,
    ).all()

    total_campaigns = len(campaigns)

    active_campaigns = sum(
        1 for c in campaigns if c.status in [CampaignStatus.IN_PROGRESS, CampaignStatus.SCHEDULED]
    )

    total_sent = sum(c.sent_count for c in campaigns)
    total_delivered = sum(c.delivered_count for c in campaigns)
    total_opened = sum(c.opened_count for c in campaigns)

    delivery_rate = (total_delivered / total_sent * 100) if total_sent > 0 else 0.0
    open_rate = (total_opened / total_delivered * 100) if total_delivered > 0 else 0.0

    total_clicked = sum(c.clicked_count for c in campaigns)
    click_rate = (total_clicked / total_opened * 100) if total_opened > 0 else 0.0

    return {
        "total_campaigns": total_campaigns,
        "active_campaigns": active_campaigns,
        "total_sent": total_sent,
        "total_delivered": total_delivered,
        "total_opened": total_opened,
        "delivery_rate": delivery_rate,
        "open_rate": open_rate,
        "click_rate": click_rate,
    }


@router.get("/revenue", response_model=RevenueMetrics)
def get_revenue_metrics(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("analytics:read")),
):
    """Get revenue analytics."""
    org_id = current_user.organization_id

    query = db.query(Transaction).filter(
        Transaction.organization_id == org_id,
    )

    if start_date:
        query = query.filter(Transaction.transaction_date >= start_date)

    if end_date:
        query = query.filter(Transaction.transaction_date <= end_date)

    transactions = query.all()

    # Calculate totals
    from ..models.deal import TransactionType

    total_revenue = sum(
        t.amount
        for t in transactions
        if t.transaction_type in [TransactionType.SALE, TransactionType.COMMISSION, TransactionType.INCOME]
    )

    total_expenses = sum(
        t.amount for t in transactions if t.transaction_type == TransactionType.EXPENSE
    )

    net_revenue = total_revenue - total_expenses

    # Revenue by month
    monthly_revenue = {}
    for t in transactions:
        if t.transaction_type in [TransactionType.SALE, TransactionType.COMMISSION, TransactionType.INCOME]:
            month_key = t.transaction_date.strftime("%Y-%m")
            monthly_revenue[month_key] = monthly_revenue.get(month_key, Decimal("0")) + t.amount

    revenue_by_month = [
        {"month": month, "revenue": float(revenue)}
        for month, revenue in sorted(monthly_revenue.items())
    ]

    # Revenue by deal type
    revenue_by_deal_type = {}
    for deal_type in DealType:
        deals = db.query(Deal).filter(
            Deal.organization_id == org_id,
            Deal.deal_type == deal_type,
            Deal.stage == DealStage.CLOSED_WON,
        ).all()

        revenue = sum(
            sum(t.amount for t in deal.transactions if t.transaction_type in [
                TransactionType.SALE, TransactionType.COMMISSION, TransactionType.INCOME
            ])
            for deal in deals
        )

        revenue_by_deal_type[deal_type.value] = revenue

    return {
        "total_revenue": total_revenue,
        "total_expenses": total_expenses,
        "net_revenue": net_revenue,
        "revenue_by_month": revenue_by_month,
        "revenue_by_deal_type": revenue_by_deal_type,
    }
