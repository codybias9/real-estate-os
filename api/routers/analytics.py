"""Analytics router for dashboard metrics and reporting."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Dict
from datetime import datetime, timedelta

router = APIRouter(prefix="/analytics", tags=["analytics"])


class DashboardMetrics(BaseModel):
    """Schema for dashboard metrics response."""
    total_properties: int
    active_properties: int
    total_leads: int
    new_leads_this_week: int
    total_deals: int
    deals_in_progress: int
    closed_deals_this_month: int
    revenue_this_month: float
    conversion_rate: float


class PipelineStage(BaseModel):
    """Schema for pipeline stage."""
    stage: str
    count: int
    value: float


class RevenueData(BaseModel):
    """Schema for revenue data point."""
    date: str
    revenue: float
    deals_closed: int


@router.get("/dashboard", response_model=DashboardMetrics)
def get_dashboard_metrics():
    """
    Get dashboard metrics overview.
    Returns mock data for demonstration purposes.
    """
    return DashboardMetrics(
        total_properties=25,
        active_properties=18,
        total_leads=142,
        new_leads_this_week=12,
        total_deals=45,
        deals_in_progress=8,
        closed_deals_this_month=3,
        revenue_this_month=4350000.00,
        conversion_rate=0.317
    )


@router.get("/pipeline", response_model=List[PipelineStage])
def get_lead_pipeline():
    """
    Get lead pipeline breakdown by stage.
    Returns mock data for demonstration purposes.
    """
    return [
        PipelineStage(stage="new", count=42, value=15500000.00),
        PipelineStage(stage="contacted", count=35, value=12800000.00),
        PipelineStage(stage="qualified", count=28, value=10200000.00),
        PipelineStage(stage="negotiation", count=18, value=6900000.00),
        PipelineStage(stage="under_contract", count=12, value=4500000.00),
        PipelineStage(stage="closed", count=7, value=2650000.00),
    ]


@router.get("/revenue", response_model=List[RevenueData])
def get_revenue_trends(period: str = "30d"):
    """
    Get revenue trends over time.
    Returns mock data for demonstration purposes.

    Args:
        period: Time period (7d, 30d, 90d, 365d)
    """
    # Generate mock data for the last 30 days
    data = []
    today = datetime.now()

    for i in range(30, 0, -1):
        date = today - timedelta(days=i)
        # Mock revenue with some variation
        base_revenue = 150000 + (i % 7) * 50000
        deals = 1 if i % 5 == 0 else 0

        data.append(RevenueData(
            date=date.strftime("%Y-%m-%d"),
            revenue=base_revenue,
            deals_closed=deals
        ))

    return data
