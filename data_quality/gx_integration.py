"""
Great Expectations integration for data quality gates

This module provides utilities for running GX checkpoints in Airflow DAGs
and handling validation results.
"""

import os
import logging
from typing import Dict, Any, Optional
from pathlib import Path

import great_expectations as gx
from great_expectations.core.batch import BatchRequest
from great_expectations.checkpoint import Checkpoint


logger = logging.getLogger(__name__)

# Get GX context directory
GX_ROOT_DIR = Path(__file__).parent.parent / "great_expectations"


class GXCheckpointRunner:
    """Runner for Great Expectations checkpoints in Airflow"""

    def __init__(self, context_root_dir: Optional[str] = None):
        """
        Initialize GX checkpoint runner

        Args:
            context_root_dir: Path to GX context directory.
                             Defaults to ../great_expectations
        """
        self.context_root_dir = context_root_dir or str(GX_ROOT_DIR)
        self.context = None

    def get_context(self) -> gx.DataContext:
        """Get or create GX DataContext"""
        if self.context is None:
            self.context = gx.get_context(context_root_dir=self.context_root_dir)
        return self.context

    def run_checkpoint(
        self,
        checkpoint_name: str,
        batch_request: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Run a GX checkpoint

        Args:
            checkpoint_name: Name of the checkpoint to run
            batch_request: Optional batch request to override checkpoint config
            **kwargs: Additional runtime configuration

        Returns:
            Checkpoint result dictionary

        Raises:
            Exception: If checkpoint fails validation
        """
        logger.info(f"Running GX checkpoint: {checkpoint_name}")

        context = self.get_context()

        # Get checkpoint
        checkpoint = context.get_checkpoint(checkpoint_name)

        # Build checkpoint run config
        run_config = {}
        if batch_request:
            run_config["batch_request"] = batch_request
        if kwargs:
            run_config.update(kwargs)

        # Run checkpoint
        result = checkpoint.run(**run_config)

        # Check if validation passed
        success = result["success"]

        logger.info(f"Checkpoint {checkpoint_name} completed. Success: {success}")

        # Log validation results
        for validation_result in result.run_results.values():
            results = validation_result["validation_result"]
            stats = results.statistics
            logger.info(
                f"Validation statistics: "
                f"evaluated={stats['evaluated_expectations']}, "
                f"successful={stats['successful_expectations']}, "
                f"unsuccessful={stats['unsuccessful_expectations']}, "
                f"success_percent={stats['success_percent']:.2f}%"
            )

            # Log failed expectations
            if not success:
                failed_expectations = [
                    exp for exp in results.results
                    if not exp["success"]
                ]
                logger.error(f"Failed {len(failed_expectations)} expectations:")
                for exp in failed_expectations[:10]:  # Log first 10
                    logger.error(
                        f"  - {exp['expectation_config']['expectation_type']}: "
                        f"{exp.get('exception_info', {}).get('exception_message', 'Unknown error')}"
                    )

        # Raise exception if validation failed
        if not success:
            raise GXValidationError(
                f"Checkpoint {checkpoint_name} failed validation. "
                f"Check logs for details."
            )

        return result.to_json_dict()

    def run_properties_ingestion_checkpoint(self) -> Dict[str, Any]:
        """Run properties ingestion checkpoint"""
        return self.run_checkpoint("properties_ingestion_checkpoint")

    def run_prospects_pre_ml_checkpoint(self) -> Dict[str, Any]:
        """Run prospects pre-ML checkpoint"""
        return self.run_checkpoint("prospects_pre_ml_checkpoint")


class GXValidationError(Exception):
    """Exception raised when GX validation fails"""
    pass


# Airflow callable functions
def validate_properties_ingestion(**context):
    """
    Airflow task to validate properties at ingestion

    Usage:
        PythonOperator(
            task_id='validate_properties',
            python_callable=validate_properties_ingestion
        )
    """
    runner = GXCheckpointRunner()
    result = runner.run_properties_ingestion_checkpoint()

    # Push result to XCom
    return result


def validate_prospects_pre_ml(**context):
    """
    Airflow task to validate prospects before ML pipeline

    Usage:
        PythonOperator(
            task_id='validate_prospects',
            python_callable=validate_prospects_pre_ml
        )
    """
    runner = GXCheckpointRunner()
    result = runner.run_prospects_pre_ml_checkpoint()

    # Push result to XCom
    return result


def get_validation_stats(checkpoint_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract validation statistics from checkpoint result

    Args:
        checkpoint_result: Result from run_checkpoint()

    Returns:
        Dictionary with aggregated statistics
    """
    stats = {
        "success": checkpoint_result["success"],
        "total_evaluated": 0,
        "total_successful": 0,
        "total_unsuccessful": 0,
        "success_percent": 0.0
    }

    for validation_result in checkpoint_result["run_results"].values():
        result_stats = validation_result["validation_result"]["statistics"]
        stats["total_evaluated"] += result_stats["evaluated_expectations"]
        stats["total_successful"] += result_stats["successful_expectations"]
        stats["total_unsuccessful"] += result_stats["unsuccessful_expectations"]

    if stats["total_evaluated"] > 0:
        stats["success_percent"] = (
            stats["total_successful"] / stats["total_evaluated"] * 100
        )

    return stats


if __name__ == "__main__":
    # Test runner
    logging.basicConfig(level=logging.INFO)

    runner = GXCheckpointRunner()

    print("Testing properties ingestion checkpoint...")
    try:
        result = runner.run_properties_ingestion_checkpoint()
        print("✅ Properties checkpoint passed")
        print(f"Statistics: {get_validation_stats(result)}")
    except GXValidationError as e:
        print(f"❌ Properties checkpoint failed: {e}")
    except Exception as e:
        print(f"❌ Error running checkpoint: {e}")
