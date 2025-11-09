"""
Metrics Data Models
Portfolio aggregation models for daily and real-time metrics
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Dict, Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class MetricsDaily(BaseModel):
    """Daily aggregated metrics per tenant"""

    id: Optional[UUID] = None
    tenant_id: UUID
    day: date

    # Stage counts (snapshot at end of day)
    stage_new: int = 0
    stage_qualified: int = 0
    stage_enriched: int = 0
    stage_pitched: int = 0
    stage_negotiating: int = 0
    stage_closed_won: int = 0
    stage_closed_lost: int = 0
    stage_archived: int = 0

    # Conversion rates (%)
    conversion_new_to_qualified: Optional[Decimal] = None
    conversion_qualified_to_enriched: Optional[Decimal] = None
    conversion_enriched_to_pitched: Optional[Decimal] = None
    conversion_pitched_to_won: Optional[Decimal] = None
    conversion_overall: Optional[Decimal] = None

    # Response rates (outreach)
    outreach_sends: int = 0
    outreach_delivered: int = 0
    outreach_opens: int = 0
    outreach_clicks: int = 0
    outreach_replies: int = 0
    response_rate_delivered: Optional[Decimal] = None
    response_rate_opened: Optional[Decimal] = None
    response_rate_replied: Optional[Decimal] = None

    # Time to stage (median hours)
    time_to_qualified_hrs: Optional[Decimal] = None
    time_to_enriched_hrs: Optional[Decimal] = None
    time_to_pitched_hrs: Optional[Decimal] = None
    time_to_closed_hrs: Optional[Decimal] = None

    # Memos generated
    memos_generated: int = 0
    memos_avg_duration_sec: Optional[Decimal] = None
    memos_p95_duration_sec: Optional[Decimal] = None

    # Cost tracking
    total_cost_usd: Decimal = Decimal("0.00")
    avg_cost_per_property: Optional[Decimal] = None

    # Metadata
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MetricsRealtime(BaseModel):
    """Rolling 24-hour metrics for real-time dashboard"""

    id: Optional[UUID] = None
    tenant_id: UUID
    window_hrs: int = 24

    # Counters (flexible JSON storage)
    counters: Dict[str, Any] = Field(default_factory=dict)

    # Quick access fields (denormalized)
    total_leads: int = 0
    qualified_count: int = 0
    memos_generated: int = 0
    outreach_sends: int = 0
    outreach_opens: int = 0
    outreach_replies: int = 0

    # Calculated rates
    qualified_rate: Optional[Decimal] = None
    memo_conversion_rate: Optional[Decimal] = None
    open_rate: Optional[Decimal] = None
    reply_rate: Optional[Decimal] = None

    # Metadata
    window_start: datetime
    window_end: datetime
    calculated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MetricsTemplatePerformance(BaseModel):
    """Per-template outreach performance metrics"""

    id: Optional[UUID] = None
    tenant_id: UUID
    template_id: str
    template_name: Optional[str] = None
    channel: str  # email, sms, postal

    # Daily stats
    day: date
    sends: int = 0
    delivered: int = 0
    opens: int = 0
    clicks: int = 0
    replies: int = 0
    bounces: int = 0
    unsubscribes: int = 0

    # Calculated rates
    delivery_rate: Optional[Decimal] = None
    open_rate: Optional[Decimal] = None
    click_rate: Optional[Decimal] = None
    reply_rate: Optional[Decimal] = None

    # Metadata
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============================================================
# API Response Models
# ============================================================

class PortfolioTiles(BaseModel):
    """Dashboard tiles for portfolio overview"""

    total_leads: int
    qualified_rate: Decimal  # %
    avg_time_to_qualified_hrs: Decimal
    memo_conversion_rate: Decimal  # %
    open_rate: Decimal  # %
    reply_rate: Decimal  # %

    # Additional context
    window: str  # "7d", "30d", "90d"
    calculated_at: datetime


class TemplatePerformanceRow(BaseModel):
    """Single row in template performance table"""

    template_id: str
    template_name: str
    channel: str
    sends: int
    delivery_rate: Decimal
    open_rate: Decimal
    click_rate: Decimal
    reply_rate: Decimal


class PortfolioMetricsResponse(BaseModel):
    """Complete portfolio metrics response"""

    tiles: PortfolioTiles
    template_performance: list[TemplatePerformanceRow]
    daily_metrics: list[MetricsDaily]

    class Config:
        from_attributes = True


class FunnelCSVRow(BaseModel):
    """CSV export row for funnel analysis"""

    date: str
    stage: str
    count: int
    conversions: int
    conversion_rate: Decimal
    avg_time_hrs: Optional[Decimal] = None
    cost_usd: Decimal


class MetricsWindow(BaseModel):
    """Time window for metrics queries"""

    window: str = Field(default="7d", pattern="^(7d|30d|90d|365d)$")
    start_date: Optional[date] = None
    end_date: Optional[date] = None

    def to_days(self) -> int:
        """Convert window string to number of days"""
        mapping = {"7d": 7, "30d": 30, "90d": 90, "365d": 365}
        return mapping.get(self.window, 7)
