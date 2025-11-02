"""
OpenLineage integration for Airflow pipeline lineage tracking.

This module provides OpenLineage event emission for tracking data lineage
across pipeline executions. Events are sent to Marquez for visualization.
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid
import logging
import requests
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


@dataclass
class OpenLineageDataset:
    """Represents a dataset in OpenLineage."""
    namespace: str
    name: str
    facets: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OpenLineageJob:
    """Represents a job in OpenLineage."""
    namespace: str
    name: str
    facets: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OpenLineageRun:
    """Represents a run in OpenLineage."""
    runId: str
    facets: Dict[str, Any] = field(default_factory=dict)


class OpenLineageClient:
    """Client for emitting OpenLineage events."""

    def __init__(
        self,
        marquez_url: str = "http://localhost:5000",
        namespace: str = "real_estate_os",
        producer: str = "https://github.com/real-estate-os/pipeline"
    ):
        """
        Initialize OpenLineage client.

        Args:
            marquez_url: URL of Marquez API
            namespace: Default namespace for jobs and datasets
            producer: URI identifying the producer of events
        """
        self.marquez_url = marquez_url.rstrip("/")
        self.api_url = f"{self.marquez_url}/api/v1/lineage"
        self.namespace = namespace
        self.producer = producer

    def emit_event(self, event: Dict[str, Any]) -> bool:
        """
        Emit OpenLineage event to Marquez.

        Args:
            event: OpenLineage event dictionary

        Returns:
            True if successful, False otherwise
        """
        try:
            response = requests.post(
                self.api_url,
                json=event,
                headers={"Content-Type": "application/json"},
                timeout=5
            )

            if response.status_code in [200, 201]:
                logger.info(f"OpenLineage event emitted: {event['eventType']}")
                return True
            else:
                logger.error(
                    f"Failed to emit event: {response.status_code} - {response.text}"
                )
                return False

        except requests.exceptions.RequestException as e:
            logger.error(f"Error emitting OpenLineage event: {e}")
            return False

    def create_start_event(
        self,
        job_name: str,
        run_id: str,
        inputs: List[OpenLineageDataset],
        outputs: List[OpenLineageDataset],
        job_facets: Optional[Dict[str, Any]] = None,
        run_facets: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create START event for job run.

        Args:
            job_name: Name of the job
            run_id: Unique run identifier
            inputs: List of input datasets
            outputs: List of output datasets
            job_facets: Additional job metadata
            run_facets: Additional run metadata

        Returns:
            OpenLineage event dictionary
        """
        event = {
            "eventType": "START",
            "eventTime": datetime.utcnow().isoformat() + "Z",
            "run": {
                "runId": run_id,
                "facets": run_facets or {}
            },
            "job": {
                "namespace": self.namespace,
                "name": job_name,
                "facets": job_facets or {}
            },
            "inputs": [
                {
                    "namespace": ds.namespace,
                    "name": ds.name,
                    "facets": ds.facets
                }
                for ds in inputs
            ],
            "outputs": [
                {
                    "namespace": ds.namespace,
                    "name": ds.name,
                    "facets": ds.facets
                }
                for ds in outputs
            ],
            "producer": self.producer
        }

        return event

    def create_complete_event(
        self,
        job_name: str,
        run_id: str,
        inputs: List[OpenLineageDataset],
        outputs: List[OpenLineageDataset],
        job_facets: Optional[Dict[str, Any]] = None,
        run_facets: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create COMPLETE event for successful job run.

        Args:
            job_name: Name of the job
            run_id: Unique run identifier
            inputs: List of input datasets
            outputs: List of output datasets
            job_facets: Additional job metadata
            run_facets: Additional run metadata

        Returns:
            OpenLineage event dictionary
        """
        event = self.create_start_event(
            job_name, run_id, inputs, outputs, job_facets, run_facets
        )
        event["eventType"] = "COMPLETE"
        event["eventTime"] = datetime.utcnow().isoformat() + "Z"

        return event

    def create_fail_event(
        self,
        job_name: str,
        run_id: str,
        inputs: List[OpenLineageDataset],
        outputs: List[OpenLineageDataset],
        error_message: Optional[str] = None,
        job_facets: Optional[Dict[str, Any]] = None,
        run_facets: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create FAIL event for failed job run.

        Args:
            job_name: Name of the job
            run_id: Unique run identifier
            inputs: List of input datasets
            outputs: List of output datasets
            error_message: Error message if available
            job_facets: Additional job metadata
            run_facets: Additional run metadata

        Returns:
            OpenLineage event dictionary
        """
        run_facets = run_facets or {}

        if error_message:
            run_facets["errorMessage"] = {
                "_producer": self.producer,
                "_schemaURL": "https://openlineage.io/spec/facets/1-0-0/ErrorMessageRunFacet.json",
                "message": error_message,
                "programmingLanguage": "python"
            }

        event = self.create_start_event(
            job_name, run_id, inputs, outputs, job_facets, run_facets
        )
        event["eventType"] = "FAIL"
        event["eventTime"] = datetime.utcnow().isoformat() + "Z"

        return event

    def emit_start(
        self,
        job_name: str,
        run_id: str,
        inputs: List[OpenLineageDataset],
        outputs: List[OpenLineageDataset],
        **kwargs
    ) -> bool:
        """Emit START event."""
        event = self.create_start_event(job_name, run_id, inputs, outputs, **kwargs)
        return self.emit_event(event)

    def emit_complete(
        self,
        job_name: str,
        run_id: str,
        inputs: List[OpenLineageDataset],
        outputs: List[OpenLineageDataset],
        **kwargs
    ) -> bool:
        """Emit COMPLETE event."""
        event = self.create_complete_event(job_name, run_id, inputs, outputs, **kwargs)
        return self.emit_event(event)

    def emit_fail(
        self,
        job_name: str,
        run_id: str,
        inputs: List[OpenLineageDataset],
        outputs: List[OpenLineageDataset],
        error_message: Optional[str] = None,
        **kwargs
    ) -> bool:
        """Emit FAIL event."""
        event = self.create_fail_event(
            job_name, run_id, inputs, outputs, error_message, **kwargs
        )
        return self.emit_event(event)


class AirflowOpenLineageIntegration:
    """Helper for integrating OpenLineage with Airflow tasks."""

    def __init__(self, client: OpenLineageClient):
        """
        Initialize Airflow integration.

        Args:
            client: OpenLineage client instance
        """
        self.client = client

    def get_run_id_from_context(self, context: Dict[str, Any]) -> str:
        """
        Generate run ID from Airflow context.

        Args:
            context: Airflow task context

        Returns:
            Unique run ID
        """
        dag_run = context.get('dag_run')
        task_instance = context.get('task_instance')

        if dag_run and task_instance:
            # Use Airflow's dag_run_id + task_id for uniqueness
            return f"{dag_run.run_id}_{task_instance.task_id}"
        else:
            # Fallback to UUID
            return str(uuid.uuid4())

    def get_job_name_from_context(self, context: Dict[str, Any]) -> str:
        """
        Get job name from Airflow context.

        Args:
            context: Airflow task context

        Returns:
            Job name (DAG.task format)
        """
        dag = context.get('dag')
        task = context.get('task')

        if dag and task:
            return f"{dag.dag_id}.{task.task_id}"
        else:
            return "unknown_job"

    def create_dataset_facets(
        self,
        schema: Optional[List[Dict[str, str]]] = None,
        source_code: Optional[str] = None,
        documentation: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create dataset facets with schema and metadata.

        Args:
            schema: List of field definitions [{"name": str, "type": str}]
            source_code: SQL or code that produces the dataset
            documentation: Dataset documentation

        Returns:
            Dataset facets dictionary
        """
        facets = {}

        if schema:
            facets["schema"] = {
                "_producer": self.client.producer,
                "_schemaURL": "https://openlineage.io/spec/facets/1-0-0/SchemaDatasetFacet.json",
                "fields": [
                    {"name": field["name"], "type": field["type"]}
                    for field in schema
                ]
            }

        if source_code:
            facets["sourceCode"] = {
                "_producer": self.client.producer,
                "_schemaURL": "https://openlineage.io/spec/facets/1-0-0/SourceCodeJobFacet.json",
                "language": "python",
                "sourceCode": source_code
            }

        if documentation:
            facets["documentation"] = {
                "_producer": self.client.producer,
                "_schemaURL": "https://openlineage.io/spec/facets/1-0-0/DocumentationDatasetFacet.json",
                "description": documentation
            }

        return facets

    def emit_task_lineage(
        self,
        context: Dict[str, Any],
        inputs: List[OpenLineageDataset],
        outputs: List[OpenLineageDataset],
        event_type: str = "COMPLETE",
        error_message: Optional[str] = None
    ) -> bool:
        """
        Emit lineage event for Airflow task.

        Args:
            context: Airflow task context
            inputs: Input datasets
            outputs: Output datasets
            event_type: START, COMPLETE, or FAIL
            error_message: Error message if FAIL

        Returns:
            True if successful
        """
        run_id = self.get_run_id_from_context(context)
        job_name = self.get_job_name_from_context(context)

        if event_type == "START":
            return self.client.emit_start(job_name, run_id, inputs, outputs)
        elif event_type == "COMPLETE":
            return self.client.emit_complete(job_name, run_id, inputs, outputs)
        elif event_type == "FAIL":
            return self.client.emit_fail(
                job_name, run_id, inputs, outputs, error_message
            )
        else:
            logger.error(f"Invalid event type: {event_type}")
            return False


# Global client instance
openlineage_client = OpenLineageClient()
airflow_integration = AirflowOpenLineageIntegration(openlineage_client)
