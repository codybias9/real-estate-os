"""Evidently Drift Detection
Monitors feature and model drift for ML systems

Types of drift detected:
1. Feature drift (PSI, JS divergence)
2. Model drift (performance degradation)
3. Data quality issues
4. Prediction drift
"""

from evidently import ColumnMapping
from evidently.report import Report
from evidently.metric_preset import DataDriftPreset, DataQualityPreset, RegressionPreset
from evidently.test_suite import TestSuite
from evidently.tests import (
    TestNumberOfDriftedColumns,
    TestShareOfDriftedColumns,
    TestColumnDrift,
    TestMeanError,
    TestValueRange
)
import pandas as pd
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import logging
import json

logger = logging.getLogger(__name__)


class DriftDetector:
    """Detect drift in features and model performance"""

    def __init__(self):
        # Column mappings for property features
        self.column_mapping = ColumnMapping(
            target="target_score",  # If supervised
            prediction="prediction",  # Model predictions
            numerical_features=[
                "sqft",
                "lot_size",
                "year_built",
                "list_price",
                "price_per_sqft",
                "days_on_market",
                "cap_rate",
                "latitude",
                "longitude",
                "condition_score",
                "flood_risk",
                "wildfire_risk",
                "walk_score"
            ],
            categorical_features=[
                "asset_type",
                "property_type",
                "market",
                "status"
            ]
        )

    def detect_feature_drift(
        self,
        reference_data: pd.DataFrame,
        current_data: pd.DataFrame,
        save_path: Optional[str] = None
    ) -> Dict:
        """Detect feature drift using PSI and JS divergence

        Args:
            reference_data: Historical reference data (training set)
            current_data: Current production data
            save_path: Path to save HTML report

        Returns:
            Dict with drift metrics
        """

        # Create drift report
        report = Report(metrics=[
            DataDriftPreset(),
            DataQualityPreset()
        ])

        # Generate report
        report.run(
            reference_data=reference_data,
            current_data=current_data,
            column_mapping=self.column_mapping
        )

        # Save HTML report
        if save_path:
            report.save_html(save_path)
            logger.info(f"Drift report saved to: {save_path}")

        # Extract metrics
        metrics = report.as_dict()

        # Parse drift results
        drift_summary = self._parse_drift_results(metrics)

        return drift_summary

    def detect_model_drift(
        self,
        reference_data: pd.DataFrame,
        current_data: pd.DataFrame,
        save_path: Optional[str] = None
    ) -> Dict:
        """Detect model performance drift

        Requires:
        - target column (actual values)
        - prediction column (model predictions)

        Args:
            reference_data: Historical data with targets and predictions
            current_data: Current data with targets and predictions
            save_path: Path to save HTML report

        Returns:
            Dict with model drift metrics (MAE, R², etc.)
        """

        # Create regression performance report
        report = Report(metrics=[
            RegressionPreset()
        ])

        report.run(
            reference_data=reference_data,
            current_data=current_data,
            column_mapping=self.column_mapping
        )

        # Save HTML report
        if save_path:
            report.save_html(save_path)
            logger.info(f"Model drift report saved to: {save_path}")

        # Extract metrics
        metrics = report.as_dict()

        # Parse model performance
        model_summary = self._parse_model_drift(metrics)

        return model_summary

    def run_drift_tests(
        self,
        reference_data: pd.DataFrame,
        current_data: pd.DataFrame
    ) -> Dict:
        """Run drift test suite with pass/fail tests

        Args:
            reference_data: Reference dataset
            current_data: Current dataset

        Returns:
            Dict with test results and failures
        """

        # Create test suite
        tests = TestSuite(tests=[
            # Overall drift tests
            TestNumberOfDriftedColumns(lt=5),  # Fewer than 5 drifted columns
            TestShareOfDriftedColumns(lt=0.3),  # Less than 30% drift

            # Specific column drift tests
            TestColumnDrift(column_name="list_price"),
            TestColumnDrift(column_name="sqft"),
            TestColumnDrift(column_name="days_on_market"),

            # Data quality tests
            TestValueRange(column_name="list_price", left=0, right=10000000),
            TestValueRange(column_name="sqft", left=0, right=50000)
        ])

        # Run tests
        tests.run(
            reference_data=reference_data,
            current_data=current_data,
            column_mapping=self.column_mapping
        )

        # Extract results
        results = tests.as_dict()

        # Count failures
        total_tests = len(results.get("tests", []))
        failed_tests = [
            test for test in results.get("tests", [])
            if test.get("status") == "FAIL"
        ]

        summary = {
            "total_tests": total_tests,
            "passed": total_tests - len(failed_tests),
            "failed": len(failed_tests),
            "failures": failed_tests,
            "overall_pass": len(failed_tests) == 0
        }

        if not summary["overall_pass"]:
            logger.warning(f"Drift tests FAILED: {len(failed_tests)}/{total_tests} tests failed")

        return summary

    def _parse_drift_results(self, metrics: Dict) -> Dict:
        """Parse drift results from Evidently metrics"""

        drift_info = {}

        # Extract data drift metrics
        data_drift = metrics.get("metrics", [{}])[0].get("result", {})

        drift_info["number_of_drifted_columns"] = data_drift.get("number_of_drifted_columns", 0)
        drift_info["share_of_drifted_columns"] = data_drift.get("share_of_drifted_columns", 0.0)
        drift_info["dataset_drift"] = data_drift.get("dataset_drift", False)

        # Per-column drift
        drifted_columns = []
        drift_by_columns = data_drift.get("drift_by_columns", {})

        for column, drift_stats in drift_by_columns.items():
            if drift_stats.get("drift_detected", False):
                drifted_columns.append({
                    "column": column,
                    "drift_score": drift_stats.get("drift_score", 0.0),
                    "stattest_name": drift_stats.get("stattest_name")
                })

        drift_info["drifted_columns"] = drifted_columns

        return drift_info

    def _parse_model_drift(self, metrics: Dict) -> Dict:
        """Parse model performance drift from metrics"""

        model_info = {}

        # Extract regression metrics
        if "metrics" in metrics and len(metrics["metrics"]) > 0:
            for metric in metrics["metrics"]:
                metric_type = metric.get("metric")

                # Mean Error
                if "MeanError" in metric_type:
                    result = metric.get("result", {})
                    model_info["mean_error_current"] = result.get("current", {}).get("mean_error")
                    model_info["mean_error_reference"] = result.get("reference", {}).get("mean_error")

                # MAE
                if "MAE" in metric_type:
                    result = metric.get("result", {})
                    model_info["mae_current"] = result.get("current", {}).get("mean_abs_error")
                    model_info["mae_reference"] = result.get("reference", {}).get("mean_abs_error")

                # R²
                if "R2Score" in metric_type:
                    result = metric.get("result", {})
                    model_info["r2_current"] = result.get("current", {}).get("r2_score")
                    model_info["r2_reference"] = result.get("reference", {}).get("r2_score")

        return model_info

    def calculate_alert_severity(self, drift_summary: Dict) -> str:
        """Calculate alert severity based on drift metrics

        Levels:
        - OK: No significant drift
        - WARNING: Moderate drift (10-25%)
        - CRITICAL: Severe drift (>25%)

        Args:
            drift_summary: Drift summary from detect_feature_drift

        Returns:
            Severity level: OK, WARNING, CRITICAL
        """

        share_of_drift = drift_summary.get("share_of_drifted_columns", 0.0)

        if share_of_drift < 0.1:
            return "OK"
        elif share_of_drift < 0.25:
            return "WARNING"
        else:
            return "CRITICAL"

    def should_block_deployment(self, drift_summary: Dict) -> bool:
        """Determine if deployment should be blocked

        Block if:
        - >40% of columns drifted
        - Dataset-level drift detected

        Args:
            drift_summary: Drift summary

        Returns:
            True if deployment should be blocked
        """

        share_of_drift = drift_summary.get("share_of_drifted_columns", 0.0)
        dataset_drift = drift_summary.get("dataset_drift", False)

        return share_of_drift > 0.4 or dataset_drift


# ============================================================================
# Convenience Functions
# ============================================================================

def detect_drift_and_alert(
    reference_data: pd.DataFrame,
    current_data: pd.DataFrame,
    report_path: str
) -> Dict:
    """Detect drift and generate alert

    Args:
        reference_data: Reference dataset
        current_data: Current dataset
        report_path: Path to save report

    Returns:
        Dict with drift summary and alert info
    """

    detector = DriftDetector()

    # Detect drift
    drift_summary = detector.detect_feature_drift(
        reference_data=reference_data,
        current_data=current_data,
        save_path=report_path
    )

    # Calculate severity
    severity = detector.calculate_alert_severity(drift_summary)

    # Check if deployment should be blocked
    block_deployment = detector.should_block_deployment(drift_summary)

    result = {
        "drift_summary": drift_summary,
        "severity": severity,
        "block_deployment": block_deployment,
        "timestamp": datetime.now().isoformat(),
        "report_path": report_path
    }

    logger.info(f"Drift detection complete: {severity}, block={block_deployment}")

    return result
