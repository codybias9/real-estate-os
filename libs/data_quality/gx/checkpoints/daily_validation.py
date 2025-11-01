"""Great Expectations Checkpoints
Daily validation of all critical datasets

This runs as part of Airflow DAGs at phase boundaries:
- After ingest → before enrich
- After enrich → before score
- After score → before serve
"""

from great_expectations.checkpoint import Checkpoint
from great_expectations.data_context import DataContext
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class DataQualityCheckpoint:
    """Wrapper for Great Expectations checkpoint execution"""

    def __init__(self, context_root_dir: str = "libs/data_quality/gx"):
        self.context = DataContext(context_root_dir)

    def run_properties_validation(self) -> Dict:
        """Validate properties table"""
        checkpoint = Checkpoint(
            name="properties_checkpoint",
            data_context=self.context,
            config_version=1.0,
            class_name="Checkpoint",
            validations=[
                {
                    "batch_request": {
                        "datasource_name": "real_estate_postgres",
                        "data_connector_name": "properties_connector",
                        "data_asset_name": "property",
                    },
                    "expectation_suite_name": "properties_suite",
                }
            ],
            action_list=[
                {
                    "name": "store_validation_result",
                    "action": {"class_name": "StoreValidationResultAction"},
                },
                {
                    "name": "update_data_docs",
                    "action": {
                        "class_name": "UpdateDataDocsAction",
                        "site_names": ["local_site", "s3_site"],
                    },
                },
                {
                    "name": "send_slack_notification",
                    "action": {
                        "class_name": "SlackNotificationAction",
                        "slack_webhook": "${SLACK_WEBHOOK_URL}",
                        "notify_on": "failure",
                    },
                },
            ],
        )

        result = checkpoint.run()

        if not result["success"]:
            logger.error(f"Properties validation failed: {result}")
            # Raise to block downstream tasks in Airflow
            raise ValueError("Properties table failed data quality checks")

        return result

    def run_ownership_validation(self) -> Dict:
        """Validate ownership table"""
        checkpoint = Checkpoint(
            name="ownership_checkpoint",
            data_context=self.context,
            config_version=1.0,
            class_name="Checkpoint",
            validations=[
                {
                    "batch_request": {
                        "datasource_name": "real_estate_postgres",
                        "data_connector_name": "ownership_connector",
                        "data_asset_name": "ownership",
                    },
                    "expectation_suite_name": "ownership_suite",
                }
            ],
            action_list=[
                {
                    "name": "store_validation_result",
                    "action": {"class_name": "StoreValidationResultAction"},
                },
                {
                    "name": "update_data_docs",
                    "action": {"class_name": "UpdateDataDocsAction"},
                },
            ],
        )

        result = checkpoint.run()

        if not result["success"]:
            logger.error(f"Ownership validation failed: {result}")
            raise ValueError("Ownership table failed data quality checks")

        return result

    def run_outreach_validation(self) -> Dict:
        """Validate outreach tables"""
        checkpoint = Checkpoint(
            name="outreach_checkpoint",
            data_context=self.context,
            config_version=1.0,
            class_name="Checkpoint",
            validations=[
                {
                    "batch_request": {
                        "datasource_name": "real_estate_postgres",
                        "data_connector_name": "outreach_connector",
                        "data_asset_name": "outreach_campaign",
                    },
                    "expectation_suite_name": "outreach_suite",
                }
            ],
            action_list=[
                {
                    "name": "store_validation_result",
                    "action": {"class_name": "StoreValidationResultAction"},
                },
                {
                    "name": "update_data_docs",
                    "action": {"class_name": "UpdateDataDocsAction"},
                },
            ],
        )

        result = checkpoint.run()

        if not result["success"]:
            logger.error(f"Outreach validation failed: {result}")
            raise ValueError("Outreach tables failed data quality checks")

        return result

    def run_all_validations(self) -> Dict[str, Dict]:
        """Run all validation checkpoints"""
        results = {}

        try:
            results["properties"] = self.run_properties_validation()
            logger.info("✅ Properties validation passed")
        except ValueError as e:
            results["properties"] = {"success": False, "error": str(e)}

        try:
            results["ownership"] = self.run_ownership_validation()
            logger.info("✅ Ownership validation passed")
        except ValueError as e:
            results["ownership"] = {"success": False, "error": str(e)}

        try:
            results["outreach"] = self.run_outreach_validation()
            logger.info("✅ Outreach validation passed")
        except ValueError as e:
            results["outreach"] = {"success": False, "error": str(e)}

        # Overall success
        all_passed = all(r.get("success", False) for r in results.values())

        if not all_passed:
            failed = [k for k, v in results.items() if not v.get("success")]
            raise ValueError(f"Data quality checks failed for: {', '.join(failed)}")

        return results


# ============================================================================
# Airflow Integration Functions
# ============================================================================


def validate_after_ingest(**context):
    """Airflow task: Validate data after ingest phase"""
    checkpoint = DataQualityCheckpoint()
    results = checkpoint.run_all_validations()
    return results


def validate_after_enrich(**context):
    """Airflow task: Validate data after enrich phase"""
    checkpoint = DataQualityCheckpoint()
    results = checkpoint.run_all_validations()
    return results


def validate_after_score(**context):
    """Airflow task: Validate data after scoring phase"""
    checkpoint = DataQualityCheckpoint()
    results = checkpoint.run_all_validations()
    return results


def check_freshness(**context):
    """Check data freshness SLA"""
    from sqlalchemy import create_engine, text
    from datetime import datetime, timedelta
    import os

    engine = create_engine(os.getenv("DB_DSN"))

    with engine.connect() as conn:
        # Check max timestamp in source tables
        result = conn.execute(
            text(
                """
            SELECT
                max(updated_at) as latest_update,
                now() - max(updated_at) as lag
            FROM property
        """
            )
        ).fetchone()

        lag_seconds = result.lag.total_seconds()
        sla_seconds = 2 * 3600  # 2 hours

        if lag_seconds > sla_seconds:
            raise ValueError(
                f"Data freshness SLA violated: lag={lag_seconds/3600:.1f}h, SLA={sla_seconds/3600:.1f}h"
            )

        logger.info(f"✅ Data freshness OK: lag={lag_seconds/60:.0f}min")
        return {"lag_seconds": lag_seconds}


def check_schema_drift(**context):
    """Detect schema changes using Jaccard similarity"""
    from sqlalchemy import create_engine, inspect
    import os

    engine = create_engine(os.getenv("DB_DSN"))
    inspector = inspect(engine)

    # Expected schemas (from expectations)
    expected_schemas = {
        "property": set(
            [
                "id",
                "tenant_id",
                "address",
                "city",
                "state",
                "zip_code",
                "latitude",
                "longitude",
                "geom",
                "list_price",
                "sqft",
                "lot_size",
                "year_built",
                "bedrooms",
                "bathrooms",
                "property_type",
                "asset_type",
                "status",
                "mls_number",
                "dom",
                "created_at",
                "updated_at",
            ]
        ),
        "ownership": set(
            [
                "id",
                "tenant_id",
                "owner_name",
                "phone",
                "email",
                "entity_type",
                "created_at",
                "updated_at",
            ]
        ),
    }

    drift_results = {}

    for table_name, expected_cols in expected_schemas.items():
        actual_cols = set([col["name"] for col in inspector.get_columns(table_name)])

        # Jaccard similarity
        intersection = len(expected_cols & actual_cols)
        union = len(expected_cols | actual_cols)
        jaccard = intersection / union if union > 0 else 0

        drift_results[table_name] = {
            "jaccard_similarity": jaccard,
            "expected": list(expected_cols),
            "actual": list(actual_cols),
            "missing": list(expected_cols - actual_cols),
            "extra": list(actual_cols - expected_cols),
        }

        if jaccard < 0.95:  # Alert threshold
            logger.warning(
                f"⚠️  Schema drift detected in {table_name}: Jaccard={jaccard:.2f}"
            )

        if jaccard < 0.80:  # Block threshold
            raise ValueError(
                f"Severe schema drift in {table_name}: Jaccard={jaccard:.2f}"
            )

    return drift_results
