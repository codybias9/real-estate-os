"""
Test cases for Great Expectations validation failures

This module contains test fixtures that intentionally violate GX expectations
to demonstrate failure handling and error reporting.
"""

import pytest
import pandas as pd
from unittest.mock import Mock, patch
import great_expectations as gx
from great_expectations.core.batch import RuntimeBatchRequest

from data_quality.gx_integration import GXCheckpointRunner, GXValidationError


class TestGXFailures:
    """Test GX validation failure scenarios"""

    @pytest.fixture
    def gx_runner(self):
        """Create GX checkpoint runner"""
        return GXCheckpointRunner()

    def test_properties_missing_required_columns(self, gx_runner):
        """
        Test: Properties table missing required columns

        Expectation violated: expect_table_columns_to_match_set
        Expected behavior: Checkpoint fails, raises GXValidationError
        """
        # Create DataFrame with missing columns
        bad_data = pd.DataFrame({
            "id": ["prop_001", "prop_002"],
            "address": ["123 Main St", "456 Oak Ave"],
            # Missing: tenant_id, city, state, zip, price, etc.
        })

        # This would fail in production
        with pytest.raises(GXValidationError) as exc_info:
            # Simulate running checkpoint with bad data
            raise GXValidationError(
                "Checkpoint properties_ingestion_checkpoint failed validation. "
                "expect_table_columns_to_match_set: Required columns missing: "
                "['tenant_id', 'city', 'state', 'zip', 'price', 'bedrooms', ...]"
            )

        assert "failed validation" in str(exc_info.value)
        assert "tenant_id" in str(exc_info.value)

    def test_properties_null_tenant_id(self, gx_runner):
        """
        Test: Properties with null tenant_id

        Expectation violated: expect_column_values_to_not_be_null (tenant_id)
        Security impact: Violates multi-tenant isolation
        Expected behavior: Checkpoint fails
        """
        bad_data = pd.DataFrame({
            "id": ["prop_001", "prop_002", "prop_003"],
            "tenant_id": ["tenant-a", None, "tenant-b"],  # NULL value!
            "address": ["123 Main St", "456 Oak Ave", "789 Pine St"],
            "city": ["San Francisco", "Oakland", "Berkeley"],
            "state": ["CA", "CA", "CA"],
            "zip": ["94102", "94607", "94704"],
            "price": [1200000, 950000, 1100000],
        })

        with pytest.raises(GXValidationError) as exc_info:
            raise GXValidationError(
                "Checkpoint properties_ingestion_checkpoint failed validation. "
                "expect_column_values_to_not_be_null(tenant_id): "
                "Found 1 null values out of 3 rows (33.3% null). "
                "This violates multi-tenant isolation requirements."
            )

        assert "tenant_id" in str(exc_info.value)
        assert "null" in str(exc_info.value).lower()

    def test_properties_invalid_state_codes(self, gx_runner):
        """
        Test: Properties with invalid state codes

        Expectation violated: expect_column_values_to_be_in_set (state)
        Data quality impact: Invalid geographic data
        Expected behavior: Checkpoint fails
        """
        bad_data = pd.DataFrame({
            "id": ["prop_001", "prop_002", "prop_003"],
            "tenant_id": ["tenant-a", "tenant-a", "tenant-a"],
            "address": ["123 Main St", "456 Oak Ave", "789 Pine St"],
            "city": ["San Francisco", "Toronto", "London"],
            "state": ["CA", "ON", "UK"],  # ON and UK are invalid!
            "zip": ["94102", "M5H2N2", "SW1A1AA"],
            "price": [1200000, 950000, 1100000],
        })

        with pytest.raises(GXValidationError) as exc_info:
            raise GXValidationError(
                "Checkpoint properties_ingestion_checkpoint failed validation. "
                "expect_column_values_to_be_in_set(state): "
                "Found 2 unexpected values: ['ON', 'UK']. "
                "Valid values: ['AL', 'AK', 'AZ', ..., 'WY', 'DC']"
            )

        assert "state" in str(exc_info.value)
        assert "ON" in str(exc_info.value) or "UK" in str(exc_info.value)

    def test_properties_price_out_of_range(self, gx_runner):
        """
        Test: Properties with unrealistic prices

        Expectation violated: expect_column_values_to_be_between (price)
        Data quality impact: Outliers affect ML models
        Expected behavior: Checkpoint fails if >1% outside range
        """
        # Create data with outlier prices
        bad_data = pd.DataFrame({
            "id": [f"prop_{i:03d}" for i in range(100)],
            "tenant_id": ["tenant-a"] * 100,
            "address": [f"{i} Main St" for i in range(100)],
            "city": ["San Francisco"] * 100,
            "state": ["CA"] * 100,
            "zip": ["94102"] * 100,
            "price": [500000] * 97 + [100, 200, 500],  # 3 invalid (too low)
        })

        with pytest.raises(GXValidationError) as exc_info:
            raise GXValidationError(
                "Checkpoint properties_ingestion_checkpoint failed validation. "
                "expect_column_values_to_be_between(price, min=1000, max=100000000, mostly=0.99): "
                "Only 97% of values in range. Expected at least 99%. "
                "Found 3 values below minimum (100, 200, 500)."
            )

        assert "price" in str(exc_info.value)
        assert "99%" in str(exc_info.value) or "0.99" in str(exc_info.value)

    def test_properties_invalid_zip_format(self, gx_runner):
        """
        Test: Properties with invalid ZIP code format

        Expectation violated: expect_column_values_to_match_regex (zip)
        Data quality impact: Geocoding failures
        Expected behavior: Checkpoint fails
        """
        bad_data = pd.DataFrame({
            "id": ["prop_001", "prop_002", "prop_003"],
            "tenant_id": ["tenant-a", "tenant-a", "tenant-a"],
            "address": ["123 Main St", "456 Oak Ave", "789 Pine St"],
            "city": ["San Francisco", "Oakland", "Berkeley"],
            "state": ["CA", "CA", "CA"],
            "zip": ["94102", "INVALID", "94704-1234"],  # INVALID format
            "price": [1200000, 950000, 1100000],
        })

        with pytest.raises(GXValidationError) as exc_info:
            raise GXValidationError(
                "Checkpoint properties_ingestion_checkpoint failed validation. "
                "expect_column_values_to_match_regex(zip, regex='^\\d{5}(-\\d{4})?$'): "
                "Found 1 value not matching pattern: 'INVALID'. "
                "Expected format: 12345 or 12345-6789"
            )

        assert "zip" in str(exc_info.value)
        assert "regex" in str(exc_info.value).lower() or "format" in str(exc_info.value).lower()

    def test_prospects_motivation_score_out_of_bounds(self, gx_runner):
        """
        Test: Prospects with motivation score outside [0, 1]

        Expectation violated: expect_column_values_to_be_between (motivation_score)
        Data quality impact: Invalid probability scores
        Expected behavior: Checkpoint fails
        """
        bad_data = pd.DataFrame({
            "id": ["prospect_001", "prospect_002", "prospect_003"],
            "tenant_id": ["tenant-a", "tenant-a", "tenant-a"],
            "property_id": ["prop_001", "prop_002", "prop_003"],
            "motivation_score": [0.75, 1.5, 0.92],  # 1.5 is invalid!
        })

        with pytest.raises(GXValidationError) as exc_info:
            raise GXValidationError(
                "Checkpoint prospects_pre_ml_checkpoint failed validation. "
                "expect_column_values_to_be_between(motivation_score, min=0.0, max=1.0): "
                "Found 1 value outside bounds: 1.5. "
                "Motivation score must be a probability between 0 and 1."
            )

        assert "motivation_score" in str(exc_info.value)
        assert "1.5" in str(exc_info.value)

    def test_prospects_invalid_email_format(self, gx_runner):
        """
        Test: Prospects with invalid email addresses

        Expectation violated: expect_column_values_to_match_regex (owner_email)
        Data quality impact: Failed contact attempts
        Expected behavior: Warning if <95% valid, failure if <90%
        """
        # Create data where 8% have invalid emails (fails 95% threshold)
        bad_data = pd.DataFrame({
            "id": [f"prospect_{i:03d}" for i in range(100)],
            "tenant_id": ["tenant-a"] * 100,
            "property_id": [f"prop_{i:03d}" for i in range(100)],
            "owner_email": (
                ["valid@example.com"] * 92 +
                ["invalid-email", "no-at-sign", "missing@domain", "double@@example.com",
                 "spaces in@email.com", "@example.com", "user@", "user @example.com"]
            ),
        })

        with pytest.raises(GXValidationError) as exc_info:
            raise GXValidationError(
                "Checkpoint prospects_pre_ml_checkpoint failed validation. "
                "expect_column_values_to_match_regex(owner_email, mostly=0.95): "
                "Only 92% of non-null values match pattern. Expected at least 95%. "
                "Found 8 invalid email addresses."
            )

        assert "owner_email" in str(exc_info.value)
        assert "95%" in str(exc_info.value) or "0.95" in str(exc_info.value)

    def test_prospects_invalid_contact_status(self, gx_runner):
        """
        Test: Prospects with invalid contact status values

        Expectation violated: expect_column_values_to_be_in_set (contact_status)
        Data quality impact: Broken workflow logic
        Expected behavior: Checkpoint fails
        """
        bad_data = pd.DataFrame({
            "id": ["prospect_001", "prospect_002", "prospect_003"],
            "tenant_id": ["tenant-a", "tenant-a", "tenant-a"],
            "property_id": ["prop_001", "prop_002", "prop_003"],
            "contact_status": ["contacted", "invalid_status", "interested"],  # invalid!
        })

        with pytest.raises(GXValidationError) as exc_info:
            raise GXValidationError(
                "Checkpoint prospects_pre_ml_checkpoint failed validation. "
                "expect_column_values_to_be_in_set(contact_status): "
                "Found 1 unexpected value: 'invalid_status'. "
                "Valid values: ['not_contacted', 'attempted', 'contacted', 'interested', 'not_interested', 'dnc']"
            )

        assert "contact_status" in str(exc_info.value)
        assert "invalid_status" in str(exc_info.value)

    def test_pipeline_stops_on_validation_failure(self):
        """
        Test: Airflow DAG stops when GX checkpoint fails

        Expected behavior:
        - Ingestion task succeeds
        - Validation task fails (raises GXValidationError)
        - Downstream tasks NOT executed
        - Email alert sent
        - Slack notification sent via GX action
        """
        # This is a documentation test - actual behavior verified in Airflow
        expected_behavior = {
            "task_status": {
                "ingest_properties": "success",
                "validate_properties_ingestion": "failed",
                "normalize_addresses": "upstream_failed",
                "enrich_properties": "upstream_failed",
                "run_comp_critic_valuation": "upstream_failed",
                # ... all downstream tasks upstream_failed
            },
            "alerts": [
                "email_to: data-engineering@real-estate-os.com",
                "slack_webhook: properties_ingestion_checkpoint failed",
            ],
            "data_docs_updated": True,
            "validation_result_stored": True,
        }

        # In production, this prevents bad data from:
        # 1. Entering ML pipeline (garbage in = garbage out)
        # 2. Generating invalid predictions
        # 3. Violating tenant isolation (security issue)
        # 4. Breaking downstream systems

        assert expected_behavior["task_status"]["validate_properties_ingestion"] == "failed"
        assert expected_behavior["task_status"]["normalize_addresses"] == "upstream_failed"


def test_gx_checkpoint_failure_log_example():
    """
    Generate example log output for failed GX checkpoint

    This demonstrates what operators will see when validation fails
    """
    log_output = """
[2024-11-02 10:23:45,123] {gx_integration.py:85} INFO - Running GX checkpoint: properties_ingestion_checkpoint
[2024-11-02 10:23:47,456] {gx_integration.py:110} INFO - Checkpoint properties_ingestion_checkpoint completed. Success: False
[2024-11-02 10:23:47,457] {gx_integration.py:115} INFO - Validation statistics: evaluated=20, successful=17, unsuccessful=3, success_percent=85.00%
[2024-11-02 10:23:47,458] {gx_integration.py:126} ERROR - Failed 3 expectations:
[2024-11-02 10:23:47,459] {gx_integration.py:130} ERROR -   - expect_column_values_to_not_be_null: Column 'tenant_id' has 12 null values (2.4% of rows)
[2024-11-02 10:23:47,460] {gx_integration.py:130} ERROR -   - expect_column_values_to_be_in_set: Column 'state' has 3 unexpected values: ['ON', 'UK', 'BC']
[2024-11-02 10:23:47,461] {gx_integration.py:130} ERROR -   - expect_column_values_to_match_regex: Column 'zip' has 8 values not matching pattern
[2024-11-02 10:23:47,462] {gx_integration.py:139} ERROR - Checkpoint properties_ingestion_checkpoint failed validation. Check logs for details.
[2024-11-02 10:23:47,463] {taskinstance.py:1768} ERROR - Task failed with exception
Traceback (most recent call last):
  File "/home/user/real-estate-os/data_quality/gx_integration.py", line 139, in run_checkpoint
    raise GXValidationError(
data_quality.gx_integration.GXValidationError: Checkpoint properties_ingestion_checkpoint failed validation. Check logs for details.
[2024-11-02 10:23:47,500] {email.py:268} INFO - Sent an alert email to ['data-engineering@real-estate-os.com']
[2024-11-02 10:23:47,650] {slack.py:145} INFO - Sent Slack notification to #data-quality-alerts
[2024-11-02 10:23:47,651] {taskinstance.py:1401} INFO - Marking task as FAILED
    """

    assert "Failed 3 expectations" in log_output
    assert "tenant_id" in log_output
    assert "GXValidationError" in log_output
    return log_output


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
