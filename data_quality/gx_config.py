"""
Great Expectations configuration and initialization.

This module provides the foundation for data quality validation using
Great Expectations (GX) integrated into the Airflow pipeline.
"""
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
import great_expectations as gx
from great_expectations.core.batch import RuntimeBatchRequest
from great_expectations.data_context import BaseDataContext
from great_expectations.checkpoint import SimpleCheckpoint
import logging

logger = logging.getLogger(__name__)


class GXConfig:
    """Great Expectations configuration manager."""

    def __init__(
        self,
        context_root_dir: Optional[str] = None,
        runtime_environment: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize GX configuration.

        Args:
            context_root_dir: Path to GX context root directory
            runtime_environment: Runtime environment configuration
        """
        if context_root_dir is None:
            context_root_dir = str(Path(__file__).parent.parent / "great_expectations")

        self.context_root_dir = context_root_dir
        self.runtime_environment = runtime_environment or {}

        # Initialize data context
        self.context: Optional[BaseDataContext] = None

    def initialize_context(self) -> BaseDataContext:
        """
        Initialize Great Expectations data context.

        Returns:
            Initialized data context

        Raises:
            RuntimeError: If context initialization fails
        """
        try:
            # Check if context exists, create if not
            if not os.path.exists(self.context_root_dir):
                logger.info(f"Creating new GX context at {self.context_root_dir}")
                self.context = gx.get_context(
                    context_root_dir=self.context_root_dir,
                    mode="file"
                )
            else:
                logger.info(f"Loading existing GX context from {self.context_root_dir}")
                self.context = gx.get_context(context_root_dir=self.context_root_dir)

            logger.info("GX context initialized successfully")
            return self.context

        except Exception as e:
            logger.error(f"Failed to initialize GX context: {e}")
            raise RuntimeError(f"GX context initialization failed: {e}")

    def get_or_create_datasource(
        self,
        datasource_name: str,
        connection_string: str
    ) -> Any:
        """
        Get existing datasource or create new one.

        Args:
            datasource_name: Name of the datasource
            connection_string: Database connection string

        Returns:
            Datasource object
        """
        if self.context is None:
            self.initialize_context()

        try:
            # Try to get existing datasource
            datasource = self.context.get_datasource(datasource_name)
            logger.info(f"Using existing datasource: {datasource_name}")
            return datasource

        except Exception:
            # Create new datasource
            logger.info(f"Creating new datasource: {datasource_name}")

            datasource_config = {
                "name": datasource_name,
                "class_name": "Datasource",
                "module_name": "great_expectations.datasource",
                "execution_engine": {
                    "class_name": "SqlAlchemyExecutionEngine",
                    "module_name": "great_expectations.execution_engine",
                    "connection_string": connection_string
                },
                "data_connectors": {
                    "default_runtime_data_connector": {
                        "class_name": "RuntimeDataConnector",
                        "module_name": "great_expectations.datasource.data_connector",
                        "batch_identifiers": ["default_identifier_name"]
                    },
                    "default_inferred_data_connector": {
                        "class_name": "InferredAssetSqlDataConnector",
                        "module_name": "great_expectations.datasource.data_connector",
                        "include_schema_name": True
                    }
                }
            }

            datasource = self.context.add_datasource(**datasource_config)
            logger.info(f"Datasource created: {datasource_name}")
            return datasource

    def create_expectation_suite(
        self,
        suite_name: str,
        overwrite: bool = False
    ) -> Any:
        """
        Create or get expectation suite.

        Args:
            suite_name: Name of the expectation suite
            overwrite: Whether to overwrite existing suite

        Returns:
            Expectation suite
        """
        if self.context is None:
            self.initialize_context()

        try:
            if overwrite or not self.context.get_expectation_suite(suite_name):
                suite = self.context.add_expectation_suite(
                    expectation_suite_name=suite_name
                )
                logger.info(f"Created expectation suite: {suite_name}")
                return suite
        except Exception:
            suite = self.context.get_expectation_suite(suite_name)
            logger.info(f"Using existing expectation suite: {suite_name}")
            return suite

    def add_checkpoint(
        self,
        checkpoint_name: str,
        expectation_suite_name: str,
        datasource_name: str,
        data_asset_name: Optional[str] = None,
        action_list: Optional[List[Dict]] = None
    ) -> SimpleCheckpoint:
        """
        Add checkpoint for validation.

        Args:
            checkpoint_name: Name of the checkpoint
            expectation_suite_name: Name of expectation suite to use
            datasource_name: Name of datasource
            data_asset_name: Name of data asset (table)
            action_list: List of actions to take on validation

        Returns:
            Created checkpoint
        """
        if self.context is None:
            self.initialize_context()

        # Default actions if not provided
        if action_list is None:
            action_list = [
                {
                    "name": "store_validation_result",
                    "action": {"class_name": "StoreValidationResultAction"}
                },
                {
                    "name": "update_data_docs",
                    "action": {"class_name": "UpdateDataDocsAction"}
                }
            ]

        checkpoint_config = {
            "name": checkpoint_name,
            "config_version": 1.0,
            "class_name": "SimpleCheckpoint",
            "run_name_template": f"%Y%m%d-%H%M%S-{checkpoint_name}",
            "validations": [
                {
                    "batch_request": {
                        "datasource_name": datasource_name,
                        "data_connector_name": "default_runtime_data_connector",
                        "data_asset_name": data_asset_name or "default_asset"
                    },
                    "expectation_suite_name": expectation_suite_name
                }
            ],
            "action_list": action_list
        }

        try:
            checkpoint = self.context.add_checkpoint(**checkpoint_config)
            logger.info(f"Created checkpoint: {checkpoint_name}")
            return checkpoint

        except Exception as e:
            logger.warning(f"Checkpoint {checkpoint_name} may already exist: {e}")
            return self.context.get_checkpoint(checkpoint_name)

    def run_checkpoint(
        self,
        checkpoint_name: str,
        batch_request: Optional[RuntimeBatchRequest] = None
    ) -> Dict[str, Any]:
        """
        Run checkpoint validation.

        Args:
            checkpoint_name: Name of checkpoint to run
            batch_request: Optional batch request for runtime data

        Returns:
            Validation result

        Raises:
            ValueError: If validation fails
        """
        if self.context is None:
            self.initialize_context()

        logger.info(f"Running checkpoint: {checkpoint_name}")

        try:
            if batch_request:
                results = self.context.run_checkpoint(
                    checkpoint_name=checkpoint_name,
                    batch_request=batch_request
                )
            else:
                results = self.context.run_checkpoint(checkpoint_name=checkpoint_name)

            # Check if validation passed
            success = results["success"]

            if not success:
                logger.error(f"Checkpoint {checkpoint_name} FAILED")
                failed_expectations = []

                for run_result in results.run_results.values():
                    for validation_result in run_result["validation_result"]["results"]:
                        if not validation_result["success"]:
                            failed_expectations.append({
                                "expectation_type": validation_result["expectation_config"]["expectation_type"],
                                "kwargs": validation_result["expectation_config"]["kwargs"],
                                "result": validation_result["result"]
                            })

                raise ValueError(
                    f"Data quality validation failed. "
                    f"{len(failed_expectations)} expectations failed: {failed_expectations}"
                )

            logger.info(f"Checkpoint {checkpoint_name} PASSED ✅")
            return results

        except ValueError:
            # Re-raise validation errors
            raise
        except Exception as e:
            logger.error(f"Error running checkpoint {checkpoint_name}: {e}")
            raise RuntimeError(f"Checkpoint execution failed: {e}")

    def get_validation_results(
        self,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get recent validation results.

        Args:
            limit: Maximum number of results to return

        Returns:
            List of validation results
        """
        if self.context is None:
            self.initialize_context()

        try:
            results = self.context.get_validation_results()
            return results[:limit]
        except Exception as e:
            logger.error(f"Failed to get validation results: {e}")
            return []


# Global GX configuration instance
gx_config = GXConfig()
