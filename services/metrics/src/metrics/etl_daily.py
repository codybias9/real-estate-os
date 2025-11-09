"""
Portfolio Metrics ETL Pipeline
Daily aggregation job for metrics_daily table

This DAG runs daily at 00:30 UTC and aggregates:
- Pipeline stage snapshots
- Timeline entries (outreach status)
- Action packets (memos)
- Time-to-stage calculations
"""

from datetime import datetime, timedelta, date
from decimal import Decimal
from typing import Dict, Any, List, Optional
from uuid import UUID

import asyncpg
import structlog
from statistics import median

logger = structlog.get_logger()


class MetricsETL:
    """
    ETL pipeline for portfolio metrics
    Aggregates data from multiple sources into metrics_daily
    """

    def __init__(self, db_pool: asyncpg.Pool):
        self.db = db_pool

    async def run_daily(self, target_date: date, tenant_id: UUID) -> Dict[str, Any]:
        """
        Run full daily ETL for a specific tenant and date

        Args:
            target_date: Date to calculate metrics for
            tenant_id: Tenant to process

        Returns:
            Dictionary with aggregated metrics
        """
        logger.info("etl.daily.start", date=str(target_date), tenant_id=str(tenant_id))

        # Task 1: Snapshot pipeline_state by stage
        stage_counts = await self._snapshot_pipeline_stages(target_date, tenant_id)

        # Task 2: Aggregate timeline_entries (outreach status)
        outreach_stats = await self._aggregate_outreach_metrics(target_date, tenant_id)

        # Task 3: Aggregate action_packets (memos)
        memo_stats = await self._aggregate_memo_metrics(target_date, tenant_id)

        # Task 4: Compute time-to-stage medians
        time_to_stage = await self._calculate_time_to_stage(target_date, tenant_id)

        # Task 5: Calculate conversion rates
        conversions = self._calculate_conversion_rates(stage_counts)

        # Task 6: Calculate response rates
        response_rates = self._calculate_response_rates(outreach_stats)

        # Task 7: Calculate cost metrics
        cost_metrics = await self._calculate_cost_metrics(target_date, tenant_id)

        # Combine all metrics
        metrics = {
            "tenant_id": tenant_id,
            "day": target_date,
            **stage_counts,
            **conversions,
            **outreach_stats,
            **response_rates,
            **time_to_stage,
            **memo_stats,
            **cost_metrics,
        }

        # Task 8: Upsert into metrics_daily
        await self._upsert_metrics_daily(metrics)

        logger.info("etl.daily.complete", date=str(target_date), tenant_id=str(tenant_id))
        return metrics

    async def _snapshot_pipeline_stages(
        self, target_date: date, tenant_id: UUID
    ) -> Dict[str, int]:
        """
        Count properties in each stage at end of target_date
        Uses pipeline_state table with state_changed_at timestamp
        """
        query = """
        WITH latest_states AS (
            SELECT DISTINCT ON (property_id)
                property_id,
                stage
            FROM pipeline_state
            WHERE tenant_id = $1
              AND state_changed_at <= $2::DATE + INTERVAL '1 day'
            ORDER BY property_id, state_changed_at DESC
        )
        SELECT
            stage,
            COUNT(*) as count
        FROM latest_states
        GROUP BY stage
        """
        rows = await self.db.fetch(query, tenant_id, target_date)

        stage_counts = {
            "stage_new": 0,
            "stage_qualified": 0,
            "stage_enriched": 0,
            "stage_pitched": 0,
            "stage_negotiating": 0,
            "stage_closed_won": 0,
            "stage_closed_lost": 0,
            "stage_archived": 0,
        }

        for row in rows:
            stage_key = f"stage_{row['stage'].lower()}"
            if stage_key in stage_counts:
                stage_counts[stage_key] = row["count"]

        return stage_counts

    async def _aggregate_outreach_metrics(
        self, target_date: date, tenant_id: UUID
    ) -> Dict[str, int]:
        """
        Aggregate outreach metrics from timeline_entries
        Counts sends, delivered, opens, clicks, replies for the day
        """
        query = """
        SELECT
            COUNT(*) FILTER (WHERE event_type = 'outreach.sent') as sends,
            COUNT(*) FILTER (WHERE event_type = 'outreach.delivered') as delivered,
            COUNT(*) FILTER (WHERE event_type = 'outreach.opened') as opens,
            COUNT(*) FILTER (WHERE event_type = 'outreach.clicked') as clicks,
            COUNT(*) FILTER (WHERE event_type = 'outreach.replied') as replies
        FROM timeline_entries
        WHERE tenant_id = $1
          AND created_at::DATE = $2
          AND event_type LIKE 'outreach.%'
        """
        row = await self.db.fetchrow(query, tenant_id, target_date)

        return {
            "outreach_sends": row["sends"] or 0,
            "outreach_delivered": row["delivered"] or 0,
            "outreach_opens": row["opens"] or 0,
            "outreach_clicks": row["clicks"] or 0,
            "outreach_replies": row["replies"] or 0,
        }

    async def _aggregate_memo_metrics(
        self, target_date: date, tenant_id: UUID
    ) -> Dict[str, Any]:
        """
        Aggregate memo generation metrics from action_packets
        Calculates count, avg duration, p95 duration
        """
        query = """
        SELECT
            COUNT(*) as count,
            AVG(EXTRACT(EPOCH FROM (completed_at - created_at))) as avg_duration,
            PERCENTILE_CONT(0.95) WITHIN GROUP (
                ORDER BY EXTRACT(EPOCH FROM (completed_at - created_at))
            ) as p95_duration
        FROM action_packets
        WHERE tenant_id = $1
          AND action_type = 'generate_memo'
          AND created_at::DATE = $2
          AND completed_at IS NOT NULL
        """
        row = await self.db.fetchrow(query, tenant_id, target_date)

        return {
            "memos_generated": row["count"] or 0,
            "memos_avg_duration_sec": Decimal(str(row["avg_duration"] or 0)),
            "memos_p95_duration_sec": Decimal(str(row["p95_duration"] or 0)),
        }

    async def _calculate_time_to_stage(
        self, target_date: date, tenant_id: UUID
    ) -> Dict[str, Optional[Decimal]]:
        """
        Calculate median time-to-stage for properties that moved stages on target_date
        Uses pipeline_state history to calculate deltas
        """
        query = """
        WITH stage_transitions AS (
            SELECT
                property_id,
                stage,
                state_changed_at,
                LAG(state_changed_at) OVER (PARTITION BY property_id ORDER BY state_changed_at) as prev_time,
                LAG(stage) OVER (PARTITION BY property_id ORDER BY state_changed_at) as prev_stage
            FROM pipeline_state
            WHERE tenant_id = $1
              AND state_changed_at::DATE <= $2
        ),
        time_deltas AS (
            SELECT
                stage,
                EXTRACT(EPOCH FROM (state_changed_at - prev_time)) / 3600.0 as hours
            FROM stage_transitions
            WHERE prev_time IS NOT NULL
              AND state_changed_at::DATE = $2
        )
        SELECT
            stage,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY hours) as median_hrs
        FROM time_deltas
        GROUP BY stage
        """
        rows = await self.db.fetch(query, tenant_id, target_date)

        time_to_stage = {
            "time_to_qualified_hrs": None,
            "time_to_enriched_hrs": None,
            "time_to_pitched_hrs": None,
            "time_to_closed_hrs": None,
        }

        stage_mapping = {
            "qualified": "time_to_qualified_hrs",
            "enriched": "time_to_enriched_hrs",
            "pitched": "time_to_pitched_hrs",
            "closed_won": "time_to_closed_hrs",
        }

        for row in rows:
            stage_key = stage_mapping.get(row["stage"].lower())
            if stage_key and row["median_hrs"]:
                time_to_stage[stage_key] = Decimal(str(row["median_hrs"]))

        return time_to_stage

    def _calculate_conversion_rates(self, stage_counts: Dict[str, int]) -> Dict[str, Optional[Decimal]]:
        """
        Calculate conversion rates between stages
        """
        def safe_rate(numerator: int, denominator: int) -> Optional[Decimal]:
            if denominator == 0:
                return None
            return Decimal(str(round((numerator / denominator) * 100, 2)))

        new = stage_counts.get("stage_new", 0)
        qualified = stage_counts.get("stage_qualified", 0)
        enriched = stage_counts.get("stage_enriched", 0)
        pitched = stage_counts.get("stage_pitched", 0)
        won = stage_counts.get("stage_closed_won", 0)

        total_in_funnel = new + qualified + enriched + pitched
        total_converted = qualified + enriched + pitched + won

        return {
            "conversion_new_to_qualified": safe_rate(qualified, new + qualified),
            "conversion_qualified_to_enriched": safe_rate(enriched, qualified + enriched),
            "conversion_enriched_to_pitched": safe_rate(pitched, enriched + pitched),
            "conversion_pitched_to_won": safe_rate(won, pitched + won),
            "conversion_overall": safe_rate(won, total_in_funnel) if total_in_funnel > 0 else None,
        }

    def _calculate_response_rates(self, outreach_stats: Dict[str, int]) -> Dict[str, Optional[Decimal]]:
        """
        Calculate outreach response rates
        """
        def safe_rate(numerator: int, denominator: int) -> Optional[Decimal]:
            if denominator == 0:
                return None
            return Decimal(str(round((numerator / denominator) * 100, 2)))

        sends = outreach_stats.get("outreach_sends", 0)
        delivered = outreach_stats.get("outreach_delivered", 0)
        opens = outreach_stats.get("outreach_opens", 0)
        replies = outreach_stats.get("outreach_replies", 0)

        return {
            "response_rate_delivered": safe_rate(delivered, sends),
            "response_rate_opened": safe_rate(opens, delivered),
            "response_rate_replied": safe_rate(replies, delivered),
        }

    async def _calculate_cost_metrics(
        self, target_date: date, tenant_id: UUID
    ) -> Dict[str, Decimal]:
        """
        Calculate cost metrics from connector usage
        """
        query = """
        SELECT
            SUM(cost_usd) as total_cost,
            COUNT(DISTINCT property_id) as property_count
        FROM connector_usage_log
        WHERE tenant_id = $1
          AND created_at::DATE = $2
        """
        row = await self.db.fetchrow(query, tenant_id, target_date)

        total_cost = Decimal(str(row["total_cost"] or 0))
        property_count = row["property_count"] or 0

        avg_cost = (
            Decimal(str(round(total_cost / property_count, 2)))
            if property_count > 0
            else Decimal("0.00")
        )

        return {
            "total_cost_usd": total_cost,
            "avg_cost_per_property": avg_cost,
        }

    async def _upsert_metrics_daily(self, metrics: Dict[str, Any]) -> None:
        """
        Upsert metrics into metrics_daily table
        """
        query = """
        INSERT INTO metrics_daily (
            tenant_id, day,
            stage_new, stage_qualified, stage_enriched, stage_pitched,
            stage_negotiating, stage_closed_won, stage_closed_lost, stage_archived,
            conversion_new_to_qualified, conversion_qualified_to_enriched,
            conversion_enriched_to_pitched, conversion_pitched_to_won, conversion_overall,
            outreach_sends, outreach_delivered, outreach_opens, outreach_clicks, outreach_replies,
            response_rate_delivered, response_rate_opened, response_rate_replied,
            time_to_qualified_hrs, time_to_enriched_hrs, time_to_pitched_hrs, time_to_closed_hrs,
            memos_generated, memos_avg_duration_sec, memos_p95_duration_sec,
            total_cost_usd, avg_cost_per_property
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
            $11, $12, $13, $14, $15,
            $16, $17, $18, $19, $20,
            $21, $22, $23,
            $24, $25, $26, $27,
            $28, $29, $30,
            $31, $32
        )
        ON CONFLICT (tenant_id, day)
        DO UPDATE SET
            stage_new = EXCLUDED.stage_new,
            stage_qualified = EXCLUDED.stage_qualified,
            stage_enriched = EXCLUDED.stage_enriched,
            stage_pitched = EXCLUDED.stage_pitched,
            stage_negotiating = EXCLUDED.stage_negotiating,
            stage_closed_won = EXCLUDED.stage_closed_won,
            stage_closed_lost = EXCLUDED.stage_closed_lost,
            stage_archived = EXCLUDED.stage_archived,
            conversion_new_to_qualified = EXCLUDED.conversion_new_to_qualified,
            conversion_qualified_to_enriched = EXCLUDED.conversion_qualified_to_enriched,
            conversion_enriched_to_pitched = EXCLUDED.conversion_enriched_to_pitched,
            conversion_pitched_to_won = EXCLUDED.conversion_pitched_to_won,
            conversion_overall = EXCLUDED.conversion_overall,
            outreach_sends = EXCLUDED.outreach_sends,
            outreach_delivered = EXCLUDED.outreach_delivered,
            outreach_opens = EXCLUDED.outreach_opens,
            outreach_clicks = EXCLUDED.outreach_clicks,
            outreach_replies = EXCLUDED.outreach_replies,
            response_rate_delivered = EXCLUDED.response_rate_delivered,
            response_rate_opened = EXCLUDED.response_rate_opened,
            response_rate_replied = EXCLUDED.response_rate_replied,
            time_to_qualified_hrs = EXCLUDED.time_to_qualified_hrs,
            time_to_enriched_hrs = EXCLUDED.time_to_enriched_hrs,
            time_to_pitched_hrs = EXCLUDED.time_to_pitched_hrs,
            time_to_closed_hrs = EXCLUDED.time_to_closed_hrs,
            memos_generated = EXCLUDED.memos_generated,
            memos_avg_duration_sec = EXCLUDED.memos_avg_duration_sec,
            memos_p95_duration_sec = EXCLUDED.memos_p95_duration_sec,
            total_cost_usd = EXCLUDED.total_cost_usd,
            avg_cost_per_property = EXCLUDED.avg_cost_per_property,
            updated_at = NOW()
        """

        await self.db.execute(
            query,
            metrics["tenant_id"],
            metrics["day"],
            metrics["stage_new"],
            metrics["stage_qualified"],
            metrics["stage_enriched"],
            metrics["stage_pitched"],
            metrics["stage_negotiating"],
            metrics["stage_closed_won"],
            metrics["stage_closed_lost"],
            metrics["stage_archived"],
            metrics["conversion_new_to_qualified"],
            metrics["conversion_qualified_to_enriched"],
            metrics["conversion_enriched_to_pitched"],
            metrics["conversion_pitched_to_won"],
            metrics["conversion_overall"],
            metrics["outreach_sends"],
            metrics["outreach_delivered"],
            metrics["outreach_opens"],
            metrics["outreach_clicks"],
            metrics["outreach_replies"],
            metrics["response_rate_delivered"],
            metrics["response_rate_opened"],
            metrics["response_rate_replied"],
            metrics["time_to_qualified_hrs"],
            metrics["time_to_enriched_hrs"],
            metrics["time_to_pitched_hrs"],
            metrics["time_to_closed_hrs"],
            metrics["memos_generated"],
            metrics["memos_avg_duration_sec"],
            metrics["memos_p95_duration_sec"],
            metrics["total_cost_usd"],
            metrics["avg_cost_per_property"],
        )

    async def run_realtime(self, tenant_id: UUID, window_hrs: int = 24) -> Dict[str, Any]:
        """
        Calculate real-time metrics for rolling window
        Used by dashboard for live updates
        """
        window_start = datetime.utcnow() - timedelta(hours=window_hrs)
        window_end = datetime.utcnow()

        # Similar aggregation logic but with time window
        query = """
        WITH recent_leads AS (
            SELECT COUNT(DISTINCT property_id) as count
            FROM pipeline_state
            WHERE tenant_id = $1 AND state_changed_at >= $2
        ),
        recent_qualified AS (
            SELECT COUNT(DISTINCT property_id) as count
            FROM pipeline_state
            WHERE tenant_id = $1 AND stage = 'qualified' AND state_changed_at >= $2
        ),
        recent_memos AS (
            SELECT COUNT(*) as count
            FROM action_packets
            WHERE tenant_id = $1 AND action_type = 'generate_memo' AND created_at >= $2
        ),
        recent_outreach AS (
            SELECT
                COUNT(*) FILTER (WHERE event_type = 'outreach.sent') as sends,
                COUNT(*) FILTER (WHERE event_type = 'outreach.opened') as opens,
                COUNT(*) FILTER (WHERE event_type = 'outreach.replied') as replies
            FROM timeline_entries
            WHERE tenant_id = $1 AND created_at >= $2 AND event_type LIKE 'outreach.%'
        )
        SELECT
            (SELECT count FROM recent_leads) as total_leads,
            (SELECT count FROM recent_qualified) as qualified_count,
            (SELECT count FROM recent_memos) as memos_generated,
            (SELECT sends FROM recent_outreach) as outreach_sends,
            (SELECT opens FROM recent_outreach) as outreach_opens,
            (SELECT replies FROM recent_outreach) as outreach_replies
        """

        row = await self.db.fetchrow(query, tenant_id, window_start)

        total_leads = row["total_leads"] or 0
        qualified_count = row["qualified_count"] or 0
        memos_generated = row["memos_generated"] or 0
        outreach_sends = row["outreach_sends"] or 0
        outreach_opens = row["outreach_opens"] or 0
        outreach_replies = row["outreach_replies"] or 0

        # Calculate rates
        qualified_rate = (
            Decimal(str(round((qualified_count / total_leads) * 100, 2)))
            if total_leads > 0
            else Decimal("0.00")
        )
        memo_conversion_rate = (
            Decimal(str(round((memos_generated / qualified_count) * 100, 2)))
            if qualified_count > 0
            else Decimal("0.00")
        )
        open_rate = (
            Decimal(str(round((outreach_opens / outreach_sends) * 100, 2)))
            if outreach_sends > 0
            else Decimal("0.00")
        )
        reply_rate = (
            Decimal(str(round((outreach_replies / outreach_sends) * 100, 2)))
            if outreach_sends > 0
            else Decimal("0.00")
        )

        metrics = {
            "tenant_id": tenant_id,
            "window_hrs": window_hrs,
            "total_leads": total_leads,
            "qualified_count": qualified_count,
            "memos_generated": memos_generated,
            "outreach_sends": outreach_sends,
            "outreach_opens": outreach_opens,
            "outreach_replies": outreach_replies,
            "qualified_rate": qualified_rate,
            "memo_conversion_rate": memo_conversion_rate,
            "open_rate": open_rate,
            "reply_rate": reply_rate,
            "window_start": window_start,
            "window_end": window_end,
            "counters": {},
        }

        # Upsert into metrics_realtime
        await self._upsert_metrics_realtime(metrics)

        return metrics

    async def _upsert_metrics_realtime(self, metrics: Dict[str, Any]) -> None:
        """Upsert metrics into metrics_realtime table"""
        query = """
        INSERT INTO metrics_realtime (
            tenant_id, window_hrs, counters,
            total_leads, qualified_count, memos_generated,
            outreach_sends, outreach_opens, outreach_replies,
            qualified_rate, memo_conversion_rate, open_rate, reply_rate,
            window_start, window_end
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
        ON CONFLICT (tenant_id, window_hrs, window_start)
        DO UPDATE SET
            total_leads = EXCLUDED.total_leads,
            qualified_count = EXCLUDED.qualified_count,
            memos_generated = EXCLUDED.memos_generated,
            outreach_sends = EXCLUDED.outreach_sends,
            outreach_opens = EXCLUDED.outreach_opens,
            outreach_replies = EXCLUDED.outreach_replies,
            qualified_rate = EXCLUDED.qualified_rate,
            memo_conversion_rate = EXCLUDED.memo_conversion_rate,
            open_rate = EXCLUDED.open_rate,
            reply_rate = EXCLUDED.reply_rate,
            window_end = EXCLUDED.window_end,
            calculated_at = NOW()
        """
        await self.db.execute(
            query,
            metrics["tenant_id"],
            metrics["window_hrs"],
            metrics["counters"],
            metrics["total_leads"],
            metrics["qualified_count"],
            metrics["memos_generated"],
            metrics["outreach_sends"],
            metrics["outreach_opens"],
            metrics["outreach_replies"],
            metrics["qualified_rate"],
            metrics["memo_conversion_rate"],
            metrics["open_rate"],
            metrics["reply_rate"],
            metrics["window_start"],
            metrics["window_end"],
        )
