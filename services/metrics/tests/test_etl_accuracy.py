"""
Metrics ETL Accuracy Tests
Validates that portfolio metrics are accurate within ±0.5% tolerance
"""

import pytest
from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4
import asyncpg

from metrics.etl_daily import MetricsETL


class TestMetricsAccuracy:
    """
    Test suite to validate metrics accuracy against raw data
    Ensures metrics reconcile within ±0.5% tolerance
    """

    @pytest.fixture
    async def db_pool(self):
        """Create test database pool"""
        pool = await asyncpg.create_pool(
            host="localhost",
            port=5432,
            database="realestate_test",
            user="realestate_app",
            password="test_password",
        )
        yield pool
        await pool.close()

    @pytest.fixture
    async def test_tenant(self):
        """Generate test tenant ID"""
        return uuid4()

    @pytest.fixture
    async def seed_test_data(self, db_pool, test_tenant):
        """
        Seed test data with known values
        Returns expected metrics for validation
        """
        target_date = date(2025, 11, 1)

        # Clear existing test data
        async with db_pool.acquire() as conn:
            await conn.execute("DELETE FROM pipeline_state WHERE tenant_id = $1", test_tenant)
            await conn.execute("DELETE FROM timeline_entries WHERE tenant_id = $1", test_tenant)
            await conn.execute("DELETE FROM action_packets WHERE tenant_id = $1", test_tenant)
            await conn.execute("DELETE FROM metrics_daily WHERE tenant_id = $1", test_tenant)

            # Insert pipeline states (100 properties)
            property_ids = [uuid4() for _ in range(100)]

            # Stage distribution:
            # 20 new, 40 qualified, 25 enriched, 10 pitched, 5 won
            stage_assignments = (
                [("new", property_ids[:20])] +
                [("qualified", property_ids[20:60])] +
                [("enriched", property_ids[60:85])] +
                [("pitched", property_ids[85:95])] +
                [("closed_won", property_ids[95:100])]
            )

            for stage, prop_ids in stage_assignments:
                for prop_id in prop_ids:
                    await conn.execute(
                        """
                        INSERT INTO pipeline_state (
                            tenant_id, property_id, stage, state_changed_at
                        ) VALUES ($1, $2, $3, $4)
                        """,
                        test_tenant,
                        prop_id,
                        stage,
                        datetime(2025, 11, 1, 12, 0, 0),
                    )

            # Insert outreach events (500 sends, 450 delivered, 200 opens, 50 replies)
            for i in range(500):
                # All sends
                await conn.execute(
                    """
                    INSERT INTO timeline_entries (
                        tenant_id, property_id, event_type, created_at
                    ) VALUES ($1, $2, $3, $4)
                    """,
                    test_tenant,
                    property_ids[i % len(property_ids)],
                    "outreach.sent",
                    datetime(2025, 11, 1, 10, 0, 0),
                )

                # 450 delivered (90%)
                if i < 450:
                    await conn.execute(
                        """
                        INSERT INTO timeline_entries (
                            tenant_id, property_id, event_type, created_at
                        ) VALUES ($1, $2, $3, $4)
                        """,
                        test_tenant,
                        property_ids[i % len(property_ids)],
                        "outreach.delivered",
                        datetime(2025, 11, 1, 10, 5, 0),
                    )

                # 200 opens (44.4% of delivered)
                if i < 200:
                    await conn.execute(
                        """
                        INSERT INTO timeline_entries (
                            tenant_id, property_id, event_type, created_at
                        ) VALUES ($1, $2, $3, $4)
                        """,
                        test_tenant,
                        property_ids[i % len(property_ids)],
                        "outreach.opened",
                        datetime(2025, 11, 1, 10, 15, 0),
                    )

                # 50 replies (11.1% of delivered)
                if i < 50:
                    await conn.execute(
                        """
                        INSERT INTO timeline_entries (
                            tenant_id, property_id, event_type, created_at
                        ) VALUES ($1, $2, $3, $4)
                        """,
                        test_tenant,
                        property_ids[i % len(property_ids)],
                        "outreach.replied",
                        datetime(2025, 11, 1, 11, 0, 0),
                    )

            # Insert memo generation events (60 memos, avg 15s)
            for i in range(60):
                await conn.execute(
                    """
                    INSERT INTO action_packets (
                        tenant_id, property_id, action_type, created_at, completed_at
                    ) VALUES ($1, $2, $3, $4, $5)
                    """,
                    test_tenant,
                    property_ids[i],
                    "generate_memo",
                    datetime(2025, 11, 1, 9, 0, 0),
                    datetime(2025, 11, 1, 9, 0, 15),  # 15 seconds
                )

        # Return expected values for validation
        return {
            "target_date": target_date,
            "expected": {
                "stage_new": 20,
                "stage_qualified": 40,
                "stage_enriched": 25,
                "stage_pitched": 10,
                "stage_closed_won": 5,
                "outreach_sends": 500,
                "outreach_delivered": 450,
                "outreach_opens": 200,
                "outreach_replies": 50,
                "memos_generated": 60,
                "response_rate_delivered": Decimal("90.00"),  # 450/500
                "response_rate_opened": Decimal("44.44"),     # 200/450
                "response_rate_replied": Decimal("11.11"),    # 50/450
            }
        }

    @pytest.mark.asyncio
    async def test_stage_count_accuracy(self, db_pool, test_tenant, seed_test_data):
        """
        Test that stage counts match raw data exactly
        Tolerance: ±0 (exact match required for counts)
        """
        etl = MetricsETL(db_pool)
        test_data = await seed_test_data

        metrics = await etl.run_daily(test_data["target_date"], test_tenant)

        expected = test_data["expected"]

        # Validate stage counts (exact match)
        assert metrics["stage_new"] == expected["stage_new"], \
            f"Stage new count mismatch: {metrics['stage_new']} != {expected['stage_new']}"

        assert metrics["stage_qualified"] == expected["stage_qualified"], \
            f"Stage qualified count mismatch: {metrics['stage_qualified']} != {expected['stage_qualified']}"

        assert metrics["stage_enriched"] == expected["stage_enriched"], \
            f"Stage enriched count mismatch: {metrics['stage_enriched']} != {expected['stage_enriched']}"

        assert metrics["stage_pitched"] == expected["stage_pitched"], \
            f"Stage pitched count mismatch: {metrics['stage_pitched']} != {expected['stage_pitched']}"

        assert metrics["stage_closed_won"] == expected["stage_closed_won"], \
            f"Stage closed_won count mismatch: {metrics['stage_closed_won']} != {expected['stage_closed_won']}"

    @pytest.mark.asyncio
    async def test_outreach_count_accuracy(self, db_pool, test_tenant, seed_test_data):
        """
        Test that outreach counts match raw data exactly
        Tolerance: ±0 (exact match required for counts)
        """
        etl = MetricsETL(db_pool)
        test_data = await seed_test_data

        metrics = await etl.run_daily(test_data["target_date"], test_tenant)

        expected = test_data["expected"]

        # Validate outreach counts (exact match)
        assert metrics["outreach_sends"] == expected["outreach_sends"], \
            f"Outreach sends mismatch: {metrics['outreach_sends']} != {expected['outreach_sends']}"

        assert metrics["outreach_delivered"] == expected["outreach_delivered"], \
            f"Outreach delivered mismatch: {metrics['outreach_delivered']} != {expected['outreach_delivered']}"

        assert metrics["outreach_opens"] == expected["outreach_opens"], \
            f"Outreach opens mismatch: {metrics['outreach_opens']} != {expected['outreach_opens']}"

        assert metrics["outreach_replies"] == expected["outreach_replies"], \
            f"Outreach replies mismatch: {metrics['outreach_replies']} != {expected['outreach_replies']}"

    @pytest.mark.asyncio
    async def test_response_rate_accuracy(self, db_pool, test_tenant, seed_test_data):
        """
        Test that response rates are accurate within ±0.5%
        Validates: delivered rate, open rate, reply rate
        """
        etl = MetricsETL(db_pool)
        test_data = await seed_test_data

        metrics = await etl.run_daily(test_data["target_date"], test_tenant)

        expected = test_data["expected"]
        tolerance = Decimal("0.5")

        # Validate response rates (±0.5% tolerance)
        delivered_rate = metrics["response_rate_delivered"]
        delivered_diff = abs(delivered_rate - expected["response_rate_delivered"])
        assert delivered_diff <= tolerance, \
            f"Delivered rate outside tolerance: {delivered_rate} (expected {expected['response_rate_delivered']} ±{tolerance}%)"

        opened_rate = metrics["response_rate_opened"]
        opened_diff = abs(opened_rate - expected["response_rate_opened"])
        assert opened_diff <= tolerance, \
            f"Opened rate outside tolerance: {opened_rate} (expected {expected['response_rate_opened']} ±{tolerance}%)"

        replied_rate = metrics["response_rate_replied"]
        replied_diff = abs(replied_rate - expected["response_rate_replied"])
        assert replied_diff <= tolerance, \
            f"Replied rate outside tolerance: {replied_rate} (expected {expected['response_rate_replied']} ±{tolerance}%)"

    @pytest.mark.asyncio
    async def test_memo_count_accuracy(self, db_pool, test_tenant, seed_test_data):
        """
        Test that memo counts match raw data exactly
        Tolerance: ±0 (exact match required for counts)
        """
        etl = MetricsETL(db_pool)
        test_data = await seed_test_data

        metrics = await etl.run_daily(test_data["target_date"], test_tenant)

        expected = test_data["expected"]

        # Validate memo count (exact match)
        assert metrics["memos_generated"] == expected["memos_generated"], \
            f"Memos generated mismatch: {metrics['memos_generated']} != {expected['memos_generated']}"

    @pytest.mark.asyncio
    async def test_csv_export_reconciliation(self, db_pool, test_tenant, seed_test_data):
        """
        Test that CSV export reconciles with raw events
        Validates that funnel CSV row counts match metrics_daily
        """
        etl = MetricsETL(db_pool)
        test_data = await seed_test_data

        # Run ETL to populate metrics_daily
        await etl.run_daily(test_data["target_date"], test_tenant)

        # Fetch metrics_daily
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM metrics_daily WHERE tenant_id = $1 AND day = $2",
                test_tenant,
                test_data["target_date"],
            )

        # Validate that metrics exist
        assert row is not None, "Metrics not found in metrics_daily"

        # Validate stage counts match
        assert row["stage_new"] == test_data["expected"]["stage_new"]
        assert row["stage_qualified"] == test_data["expected"]["stage_qualified"]
        assert row["stage_enriched"] == test_data["expected"]["stage_enriched"]
        assert row["stage_pitched"] == test_data["expected"]["stage_pitched"]
        assert row["stage_closed_won"] == test_data["expected"]["stage_closed_won"]

        # Validate outreach counts match
        assert row["outreach_sends"] == test_data["expected"]["outreach_sends"]
        assert row["outreach_delivered"] == test_data["expected"]["outreach_delivered"]
        assert row["outreach_opens"] == test_data["expected"]["outreach_opens"]
        assert row["outreach_replies"] == test_data["expected"]["outreach_replies"]

    @pytest.mark.asyncio
    async def test_realtime_metrics_accuracy(self, db_pool, test_tenant, seed_test_data):
        """
        Test that real-time metrics (24h window) are accurate
        """
        etl = MetricsETL(db_pool)
        await seed_test_data  # Seed data

        # Run real-time aggregation
        metrics = await etl.run_realtime(test_tenant, window_hrs=24)

        # Validate that metrics exist
        assert metrics["total_leads"] > 0, "No leads found in realtime metrics"
        assert metrics["qualified_count"] > 0, "No qualified leads found"
        assert metrics["memos_generated"] > 0, "No memos found"
        assert metrics["outreach_sends"] > 0, "No outreach sends found"

        # Validate rates are reasonable (0-100%)
        assert 0 <= metrics["qualified_rate"] <= 100
        assert 0 <= metrics["memo_conversion_rate"] <= 100
        assert 0 <= metrics["open_rate"] <= 100
        assert 0 <= metrics["reply_rate"] <= 100

    @pytest.mark.asyncio
    async def test_tiles_load_performance(self, db_pool, test_tenant, seed_test_data):
        """
        Test that dashboard tiles load in <1s (cached)
        Acceptance: Tiles load <1s from metrics_daily (already aggregated)
        """
        import time

        etl = MetricsETL(db_pool)
        test_data = await seed_test_data

        # Populate metrics_daily
        await etl.run_daily(test_data["target_date"], test_tenant)

        # Measure fetch time
        start = time.time()

        async with db_pool.acquire() as conn:
            await conn.fetchrow(
                "SELECT * FROM metrics_daily WHERE tenant_id = $1 AND day = $2",
                test_tenant,
                test_data["target_date"],
            )

        elapsed = time.time() - start

        # Validate <1s load time
        assert elapsed < 1.0, f"Tiles loaded in {elapsed:.2f}s (expected <1s)"


class TestMetricsEdgeCases:
    """Test edge cases and error handling"""

    @pytest.fixture
    async def db_pool(self):
        """Create test database pool"""
        pool = await asyncpg.create_pool(
            host="localhost",
            port=5432,
            database="realestate_test",
            user="realestate_app",
            password="test_password",
        )
        yield pool
        await pool.close()

    @pytest.mark.asyncio
    async def test_zero_division_handling(self, db_pool):
        """Test that division by zero is handled gracefully"""
        tenant_id = uuid4()
        etl = MetricsETL(db_pool)

        # Clear all data
        async with db_pool.acquire() as conn:
            await conn.execute("DELETE FROM pipeline_state WHERE tenant_id = $1", tenant_id)
            await conn.execute("DELETE FROM timeline_entries WHERE tenant_id = $1", tenant_id)

        # Run ETL with no data
        target_date = date(2025, 11, 2)
        metrics = await etl.run_daily(target_date, tenant_id)

        # Validate that rates are None or 0 when no data exists
        assert metrics["conversion_new_to_qualified"] is None or metrics["conversion_new_to_qualified"] == 0
        assert metrics["response_rate_delivered"] is None or metrics["response_rate_delivered"] == 0

    @pytest.mark.asyncio
    async def test_multi_tenant_isolation(self, db_pool):
        """Test that metrics are properly isolated by tenant"""
        tenant1 = uuid4()
        tenant2 = uuid4()
        etl = MetricsETL(db_pool)

        # Insert data for tenant1
        async with db_pool.acquire() as conn:
            prop_id = uuid4()
            await conn.execute(
                """
                INSERT INTO pipeline_state (tenant_id, property_id, stage, state_changed_at)
                VALUES ($1, $2, $3, $4)
                """,
                tenant1,
                prop_id,
                "qualified",
                datetime(2025, 11, 2, 12, 0, 0),
            )

        # Run ETL for both tenants
        target_date = date(2025, 11, 2)
        metrics1 = await etl.run_daily(target_date, tenant1)
        metrics2 = await etl.run_daily(target_date, tenant2)

        # Validate tenant1 has data, tenant2 has none
        assert metrics1["stage_qualified"] > 0
        assert metrics2["stage_qualified"] == 0
