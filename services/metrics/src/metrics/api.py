"""
Portfolio Metrics API
Endpoints for dashboard tiles, CSV export, and template performance
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Optional
from uuid import UUID
import csv
import io

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
import asyncpg
import structlog

from .models import (
    PortfolioMetricsResponse,
    PortfolioTiles,
    TemplatePerformanceRow,
    MetricsDaily,
    MetricsWindow,
    FunnelCSVRow,
)
from .etl_daily import MetricsETL

logger = structlog.get_logger()
router = APIRouter(prefix="/v1/metrics", tags=["metrics"])


# ============================================================
# Dependencies
# ============================================================

async def get_db_pool():
    """Get database connection pool (injected by app)"""
    # This would be provided by the main FastAPI app
    # For now, placeholder
    raise NotImplementedError("Database pool must be provided by app")


async def get_current_user():
    """Get current authenticated user with tenant_id"""
    # This would come from JWT middleware
    # For now, placeholder
    raise NotImplementedError("Auth middleware must provide current_user")


# ============================================================
# Endpoints
# ============================================================

@router.get("/portfolio", response_model=PortfolioMetricsResponse)
async def get_portfolio_metrics(
    window: str = Query("7d", pattern="^(7d|30d|90d|365d)$"),
    db: asyncpg.Pool = Depends(get_db_pool),
    current_user = Depends(get_current_user),
):
    """
    Get portfolio metrics for dashboard

    Args:
        window: Time window (7d, 30d, 90d, 365d)

    Returns:
        PortfolioMetricsResponse with tiles, template performance, and daily metrics
    """
    tenant_id = current_user.tenant_id
    window_obj = MetricsWindow(window=window)
    days = window_obj.to_days()

    start_date = date.today() - timedelta(days=days)
    end_date = date.today()

    logger.info(
        "metrics.portfolio.get",
        tenant_id=str(tenant_id),
        window=window,
        start=str(start_date),
        end=str(end_date),
    )

    # Fetch daily metrics for the window
    daily_metrics = await _fetch_daily_metrics(db, tenant_id, start_date, end_date)

    # Fetch real-time metrics (latest 24h)
    etl = MetricsETL(db)
    realtime_metrics = await etl.run_realtime(tenant_id, window_hrs=24)

    # Fetch template performance
    template_performance = await _fetch_template_performance(
        db, tenant_id, start_date, end_date
    )

    # Calculate tiles from aggregated data
    tiles = _calculate_tiles_from_metrics(daily_metrics, realtime_metrics, window)

    response = PortfolioMetricsResponse(
        tiles=tiles,
        template_performance=template_performance,
        daily_metrics=daily_metrics,
    )

    logger.info(
        "metrics.portfolio.success",
        tenant_id=str(tenant_id),
        daily_count=len(daily_metrics),
        template_count=len(template_performance),
    )

    return response


@router.get("/portfolio/export")
async def export_portfolio_funnel(
    window: str = Query("7d", pattern="^(7d|30d|90d|365d)$"),
    db: asyncpg.Pool = Depends(get_db_pool),
    current_user = Depends(get_current_user),
):
    """
    Export portfolio funnel data as CSV

    Args:
        window: Time window (7d, 30d, 90d, 365d)

    Returns:
        CSV file with funnel metrics reconciled with raw events
    """
    tenant_id = current_user.tenant_id
    window_obj = MetricsWindow(window=window)
    days = window_obj.to_days()

    start_date = date.today() - timedelta(days=days)
    end_date = date.today()

    logger.info(
        "metrics.export.start",
        tenant_id=str(tenant_id),
        window=window,
    )

    # Fetch daily metrics
    daily_metrics = await _fetch_daily_metrics(db, tenant_id, start_date, end_date)

    # Generate CSV rows
    csv_rows = _generate_funnel_csv_rows(daily_metrics)

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "date",
            "stage",
            "count",
            "conversions",
            "conversion_rate",
            "avg_time_hrs",
            "cost_usd",
        ],
    )
    writer.writeheader()
    for row in csv_rows:
        writer.writerow(row.dict())

    # Return as streaming response
    csv_content = output.getvalue()
    output.close()

    return StreamingResponse(
        io.StringIO(csv_content),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=funnel_{window}_{date.today()}.csv"
        },
    )


@router.get("/templates", response_model=List[TemplatePerformanceRow])
async def get_template_performance(
    window: str = Query("30d", pattern="^(7d|30d|90d|365d)$"),
    db: asyncpg.Pool = Depends(get_db_pool),
    current_user = Depends(get_current_user),
):
    """
    Get template performance sorted by reply rate

    Args:
        window: Time window (7d, 30d, 90d, 365d)

    Returns:
        List of template performance rows sorted by reply_rate desc
    """
    tenant_id = current_user.tenant_id
    window_obj = MetricsWindow(window=window)
    days = window_obj.to_days()

    start_date = date.today() - timedelta(days=days)
    end_date = date.today()

    templates = await _fetch_template_performance(db, tenant_id, start_date, end_date)

    logger.info(
        "metrics.templates.get",
        tenant_id=str(tenant_id),
        count=len(templates),
    )

    return templates


@router.post("/refresh/{target_date}")
async def refresh_metrics(
    target_date: date,
    db: asyncpg.Pool = Depends(get_db_pool),
    current_user = Depends(get_current_user),
):
    """
    Manually trigger metrics refresh for a specific date
    Admin-only endpoint for backfilling or corrections

    Args:
        target_date: Date to refresh metrics for

    Returns:
        Success message with metrics summary
    """
    # Check admin role
    if current_user.role not in ["admin", "ops"]:
        raise HTTPException(status_code=403, detail="Admin access required")

    tenant_id = current_user.tenant_id

    logger.info(
        "metrics.refresh.start",
        tenant_id=str(tenant_id),
        date=str(target_date),
        user=current_user.email,
    )

    # Run ETL for target date
    etl = MetricsETL(db)
    metrics = await etl.run_daily(target_date, tenant_id)

    logger.info(
        "metrics.refresh.complete",
        tenant_id=str(tenant_id),
        date=str(target_date),
    )

    return {
        "status": "success",
        "date": str(target_date),
        "metrics": {
            "total_leads": metrics["stage_new"]
            + metrics["stage_qualified"]
            + metrics["stage_enriched"],
            "memos_generated": metrics["memos_generated"],
            "outreach_sends": metrics["outreach_sends"],
        },
    }


# ============================================================
# Helper Functions
# ============================================================

async def _fetch_daily_metrics(
    db: asyncpg.Pool, tenant_id: UUID, start_date: date, end_date: date
) -> List[MetricsDaily]:
    """Fetch daily metrics for date range"""
    query = """
    SELECT *
    FROM metrics_daily
    WHERE tenant_id = $1
      AND day >= $2
      AND day <= $3
    ORDER BY day DESC
    """
    rows = await db.fetch(query, tenant_id, start_date, end_date)
    return [MetricsDaily(**dict(row)) for row in rows]


async def _fetch_template_performance(
    db: asyncpg.Pool, tenant_id: UUID, start_date: date, end_date: date
) -> List[TemplatePerformanceRow]:
    """Fetch template performance aggregated over date range"""
    query = """
    SELECT
        template_id,
        template_name,
        channel,
        SUM(sends) as sends,
        AVG(delivery_rate) as delivery_rate,
        AVG(open_rate) as open_rate,
        AVG(click_rate) as click_rate,
        AVG(reply_rate) as reply_rate
    FROM metrics_template_performance
    WHERE tenant_id = $1
      AND day >= $2
      AND day <= $3
    GROUP BY template_id, template_name, channel
    ORDER BY reply_rate DESC NULLS LAST
    """
    rows = await db.fetch(query, tenant_id, start_date, end_date)
    return [
        TemplatePerformanceRow(
            template_id=row["template_id"],
            template_name=row["template_name"] or "Unknown",
            channel=row["channel"],
            sends=row["sends"] or 0,
            delivery_rate=Decimal(str(row["delivery_rate"] or 0)),
            open_rate=Decimal(str(row["open_rate"] or 0)),
            click_rate=Decimal(str(row["click_rate"] or 0)),
            reply_rate=Decimal(str(row["reply_rate"] or 0)),
        )
        for row in rows
    ]


def _calculate_tiles_from_metrics(
    daily_metrics: List[MetricsDaily], realtime_metrics: dict, window: str
) -> PortfolioTiles:
    """
    Calculate dashboard tiles from daily + realtime metrics
    Uses realtime for most recent values and daily for trends
    """
    # Use realtime for current values
    total_leads = realtime_metrics.get("total_leads", 0)
    qualified_rate = realtime_metrics.get("qualified_rate", Decimal("0.00"))
    memo_conversion_rate = realtime_metrics.get("memo_conversion_rate", Decimal("0.00"))
    open_rate = realtime_metrics.get("open_rate", Decimal("0.00"))
    reply_rate = realtime_metrics.get("reply_rate", Decimal("0.00"))

    # Calculate avg time to qualified from daily metrics
    time_to_qualified_values = [
        m.time_to_qualified_hrs
        for m in daily_metrics
        if m.time_to_qualified_hrs is not None
    ]
    avg_time_to_qualified = (
        Decimal(str(sum(time_to_qualified_values) / len(time_to_qualified_values)))
        if time_to_qualified_values
        else Decimal("0.00")
    )

    return PortfolioTiles(
        total_leads=total_leads,
        qualified_rate=qualified_rate,
        avg_time_to_qualified_hrs=avg_time_to_qualified,
        memo_conversion_rate=memo_conversion_rate,
        open_rate=open_rate,
        reply_rate=reply_rate,
        window=window,
        calculated_at=datetime.utcnow(),
    )


def _generate_funnel_csv_rows(daily_metrics: List[MetricsDaily]) -> List[FunnelCSVRow]:
    """
    Generate CSV rows from daily metrics
    One row per stage per day for reconciliation
    """
    rows = []

    for metric in daily_metrics:
        # Stages to include in funnel CSV
        stages = [
            ("new", metric.stage_new, None),
            ("qualified", metric.stage_qualified, metric.time_to_qualified_hrs),
            ("enriched", metric.stage_enriched, metric.time_to_enriched_hrs),
            ("pitched", metric.stage_pitched, metric.time_to_pitched_hrs),
            ("closed_won", metric.stage_closed_won, metric.time_to_closed_hrs),
        ]

        for stage_name, count, avg_time in stages:
            # Calculate conversions (next stage count)
            next_stage_count = 0
            conversion_rate = Decimal("0.00")

            if stage_name == "new":
                next_stage_count = metric.stage_qualified
                conversion_rate = metric.conversion_new_to_qualified or Decimal("0.00")
            elif stage_name == "qualified":
                next_stage_count = metric.stage_enriched
                conversion_rate = metric.conversion_qualified_to_enriched or Decimal("0.00")
            elif stage_name == "enriched":
                next_stage_count = metric.stage_pitched
                conversion_rate = metric.conversion_enriched_to_pitched or Decimal("0.00")
            elif stage_name == "pitched":
                next_stage_count = metric.stage_closed_won
                conversion_rate = metric.conversion_pitched_to_won or Decimal("0.00")

            rows.append(
                FunnelCSVRow(
                    date=str(metric.day),
                    stage=stage_name,
                    count=count,
                    conversions=next_stage_count,
                    conversion_rate=conversion_rate,
                    avg_time_hrs=avg_time,
                    cost_usd=metric.total_cost_usd,
                )
            )

    return rows
