"""
OpenLineage integration for tracking data lineage

This module provides utilities for emitting OpenLineage events from Airflow tasks
to Marquez for visualization and tracking of data lineage.
"""

import os
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import requests
from dataclasses import dataclass, asdict


logger = logging.getLogger(__name__)

# Marquez API configuration
MARQUEZ_URL = os.getenv("MARQUEZ_URL", "http://localhost:5000")
MARQUEZ_NAMESPACE = os.getenv("MARQUEZ_NAMESPACE", "real-estate-os")


@dataclass
class Dataset:
    """Represents a dataset in OpenLineage"""
    namespace: str
    name: str
    facets: Optional[Dict[str, Any]] = None

    def to_dict(self):
        return {
            "namespace": self.namespace,
            "name": self.name,
            "facets": self.facets or {}
        }


@dataclass
class Job:
    """Represents a job in OpenLineage"""
    namespace: str
    name: str
    facets: Optional[Dict[str, Any]] = None

    def to_dict(self):
        return {
            "namespace": self.namespace,
            "name": self.name,
            "facets": self.facets or {}
        }


@dataclass
class Run:
    """Represents a run in OpenLineage"""
    runId: str
    facets: Optional[Dict[str, Any]] = None

    def to_dict(self):
        return {
            "runId": self.runId,
            "facets": self.facets or {}
        }


class OpenLineageClient:
    """Client for emitting OpenLineage events to Marquez"""

    def __init__(self, base_url: str = MARQUEZ_URL, namespace: str = MARQUEZ_NAMESPACE):
        self.base_url = base_url.rstrip('/')
        self.namespace = namespace
        self.api_url = f"{self.base_url}/api/v1/lineage"

    def emit_event(self, event: Dict[str, Any]) -> bool:
        """
        Emit an OpenLineage event to Marquez

        Args:
            event: OpenLineage event dictionary

        Returns:
            True if event was successfully emitted, False otherwise
        """
        try:
            response = requests.post(
                self.api_url,
                json=event,
                headers={"Content-Type": "application/json"},
                timeout=5
            )
            response.raise_for_status()
            logger.info(f"Emitted OpenLineage event: {event['eventType']} for job {event['job']['name']}")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to emit OpenLineage event: {e}")
            return False

    def create_start_event(
        self,
        job_name: str,
        run_id: str,
        inputs: List[Dataset],
        outputs: List[Dataset],
        job_facets: Optional[Dict[str, Any]] = None,
        run_facets: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a START event"""
        event = {
            "eventType": "START",
            "eventTime": datetime.utcnow().isoformat() + "Z",
            "producer": "https://github.com/codybias9/real-estate-os",
            "schemaURL": "https://openlineage.io/spec/1-0-5/OpenLineage.json#/$defs/RunEvent",
            "job": Job(
                namespace=self.namespace,
                name=job_name,
                facets=job_facets or {}
            ).to_dict(),
            "run": Run(
                runId=run_id,
                facets=run_facets or {}
            ).to_dict(),
            "inputs": [ds.to_dict() for ds in inputs],
            "outputs": [ds.to_dict() for ds in outputs]
        }
        return event

    def create_complete_event(
        self,
        job_name: str,
        run_id: str,
        inputs: List[Dataset],
        outputs: List[Dataset],
        job_facets: Optional[Dict[str, Any]] = None,
        run_facets: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a COMPLETE event"""
        event = {
            "eventType": "COMPLETE",
            "eventTime": datetime.utcnow().isoformat() + "Z",
            "producer": "https://github.com/codybias9/real-estate-os",
            "schemaURL": "https://openlineage.io/spec/1-0-5/OpenLineage.json#/$defs/RunEvent",
            "job": Job(
                namespace=self.namespace,
                name=job_name,
                facets=job_facets or {}
            ).to_dict(),
            "run": Run(
                runId=run_id,
                facets=run_facets or {}
            ).to_dict(),
            "inputs": [ds.to_dict() for ds in inputs],
            "outputs": [ds.to_dict() for ds in outputs]
        }
        return event

    def create_fail_event(
        self,
        job_name: str,
        run_id: str,
        inputs: List[Dataset],
        outputs: List[Dataset],
        error_message: str,
        job_facets: Optional[Dict[str, Any]] = None,
        run_facets: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a FAIL event"""
        run_facets = run_facets or {}
        run_facets["errorMessage"] = {
            "_producer": "https://github.com/codybias9/real-estate-os",
            "_schemaURL": "https://openlineage.io/spec/facets/1-0-0/ErrorMessageRunFacet.json",
            "message": error_message,
            "programmingLanguage": "python"
        }

        event = {
            "eventType": "FAIL",
            "eventTime": datetime.utcnow().isoformat() + "Z",
            "producer": "https://github.com/codybias9/real-estate-os",
            "schemaURL": "https://openlineage.io/spec/1-0-5/OpenLineage.json#/$defs/RunEvent",
            "job": Job(
                namespace=self.namespace,
                name=job_name,
                facets=job_facets or {}
            ).to_dict(),
            "run": Run(
                runId=run_id,
                facets=run_facets
            ).to_dict(),
            "inputs": [ds.to_dict() for ds in inputs],
            "outputs": [ds.to_dict() for ds in outputs]
        }
        return event


# Helper functions for common dataset patterns

def create_postgres_dataset(table_name: str, schema: str = "public") -> Dataset:
    """Create a PostgreSQL dataset"""
    return Dataset(
        namespace=f"postgres://real-estate-os/{schema}",
        name=table_name,
        facets={
            "schema": {
                "_producer": "https://github.com/codybias9/real-estate-os",
                "_schemaURL": "https://openlineage.io/spec/facets/1-0-0/SchemaDatasetFacet.json",
                "fields": []  # Can be populated with actual schema
            },
            "dataSource": {
                "_producer": "https://github.com/codybias9/real-estate-os",
                "_schemaURL": "https://openlineage.io/spec/facets/1-0-0/DataSourceDatasetFacet.json",
                "name": "real-estate-os-postgres",
                "uri": "postgres://localhost:5432/real_estate"
            }
        }
    )


def create_qdrant_dataset(collection_name: str) -> Dataset:
    """Create a Qdrant vector store dataset"""
    return Dataset(
        namespace="qdrant://real-estate-os",
        name=collection_name,
        facets={
            "dataSource": {
                "_producer": "https://github.com/codybias9/real-estate-os",
                "_schemaURL": "https://openlineage.io/spec/facets/1-0-0/DataSourceDatasetFacet.json",
                "name": "real-estate-os-qdrant",
                "uri": "http://localhost:6333"
            }
        }
    )


def create_minio_dataset(bucket_name: str, object_path: str) -> Dataset:
    """Create a MinIO/S3 dataset"""
    return Dataset(
        namespace=f"s3://real-estate-os/{bucket_name}",
        name=object_path,
        facets={
            "dataSource": {
                "_producer": "https://github.com/codybias9/real-estate-os",
                "_schemaURL": "https://openlineage.io/spec/facets/1-0-0/DataSourceDatasetFacet.json",
                "name": "real-estate-os-minio",
                "uri": "http://localhost:9000"
            }
        }
    )


# Airflow integration decorator
def track_lineage(
    inputs: List[Dataset],
    outputs: List[Dataset],
    job_name: Optional[str] = None
):
    """
    Decorator to automatically track lineage for Airflow tasks

    Usage:
        @track_lineage(
            inputs=[create_postgres_dataset("raw_properties")],
            outputs=[create_postgres_dataset("properties")]
        )
        def process_properties(**context):
            # Task logic here
            pass
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Get job name from function or parameter
            task_name = job_name or func.__name__

            # Get run ID from Airflow context
            context = kwargs.get('context', {})
            dag_run_id = context.get('dag_run', {}).get('run_id', 'unknown')
            task_instance = context.get('task_instance', {})
            run_id = f"{dag_run_id}_{task_instance.get('task_id', task_name)}"

            # Create OpenLineage client
            client = OpenLineageClient()

            # Emit START event
            start_event = client.create_start_event(
                job_name=task_name,
                run_id=run_id,
                inputs=inputs,
                outputs=outputs
            )
            client.emit_event(start_event)

            # Execute task
            try:
                result = func(*args, **kwargs)

                # Emit COMPLETE event
                complete_event = client.create_complete_event(
                    job_name=task_name,
                    run_id=run_id,
                    inputs=inputs,
                    outputs=outputs
                )
                client.emit_event(complete_event)

                return result

            except Exception as e:
                # Emit FAIL event
                fail_event = client.create_fail_event(
                    job_name=task_name,
                    run_id=run_id,
                    inputs=inputs,
                    outputs=outputs,
                    error_message=str(e)
                )
                client.emit_event(fail_event)
                raise

        return wrapper
    return decorator


if __name__ == "__main__":
    # Test lineage emission
    logging.basicConfig(level=logging.INFO)

    client = OpenLineageClient()

    # Example: Properties ingestion job
    inputs = [
        Dataset(namespace="external://mls", name="raw_properties", facets={})
    ]
    outputs = [
        create_postgres_dataset("properties")
    ]

    # Emit START event
    start_event = client.create_start_event(
        job_name="ingest_properties",
        run_id="test_run_001",
        inputs=inputs,
        outputs=outputs
    )
    client.emit_event(start_event)

    # Emit COMPLETE event
    complete_event = client.create_complete_event(
        job_name="ingest_properties",
        run_id="test_run_001",
        inputs=inputs,
        outputs=outputs
    )
    client.emit_event(complete_event)

    print("✅ Test lineage events emitted successfully")
    print(f"View lineage at: {MARQUEZ_URL}:3001")
