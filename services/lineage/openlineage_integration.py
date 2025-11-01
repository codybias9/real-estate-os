"""OpenLineage Integration for Airflow
Emits lineage events to Marquez for all DAG tasks

Usage:
1. Install: pip install openlineage-airflow
2. Configure in airflow.cfg:
   [lineage]
   backend = openlineage.lineage_backend.OpenLineageBackend

3. Set environment variables:
   OPENLINEAGE_URL=http://marquez:5000
   OPENLINEAGE_NAMESPACE=real-estate-os
"""

from openlineage.client import OpenLineageClient
from openlineage.client.run import RunEvent, RunState, Run, Job
from openlineage.client.facet import (
    SqlJobFacet,
    SourceCodeLocationJobFacet,
    DataSourceDatasetFacet,
    SchemaDatasetFacet,
    SchemaField
)
from typing import List, Dict
from datetime import datetime
import os


class LineageEmitter:
    """Emit OpenLineage events for data pipeline tasks"""

    def __init__(self):
        self.client = OpenLineageClient(
            url=os.getenv("OPENLINEAGE_URL", "http://localhost:5000"),
            api_key=os.getenv("OPENLINEAGE_API_KEY")
        )
        self.namespace = os.getenv("OPENLINEAGE_NAMESPACE", "real-estate-os")

    def emit_start(
        self,
        job_name: str,
        run_id: str,
        inputs: List[Dict],
        outputs: List[Dict],
        sql: str = None,
        source_location: str = None
    ):
        """Emit lineage event when task starts"""

        job_facets = {}
        if sql:
            job_facets["sql"] = SqlJobFacet(query=sql)
        if source_location:
            job_facets["sourceCodeLocation"] = SourceCodeLocationJobFacet(
                type="git",
                url=source_location
            )

        event = RunEvent(
            eventType=RunState.START,
            eventTime=datetime.now().isoformat(),
            run=Run(runId=run_id, facets={}),
            job=Job(
                namespace=self.namespace,
                name=job_name,
                facets=job_facets
            ),
            inputs=self._format_datasets(inputs, is_input=True),
            outputs=self._format_datasets(outputs, is_input=False),
            producer="https://github.com/OpenLineage/OpenLineage/tree/0.0.1/client/python"
        )

        self.client.emit(event)

    def emit_complete(
        self,
        job_name: str,
        run_id: str,
        inputs: List[Dict],
        outputs: List[Dict]
    ):
        """Emit lineage event when task completes"""

        event = RunEvent(
            eventType=RunState.COMPLETE,
            eventTime=datetime.now().isoformat(),
            run=Run(runId=run_id, facets={}),
            job=Job(namespace=self.namespace, name=job_name),
            inputs=self._format_datasets(inputs, is_input=True),
            outputs=self._format_datasets(outputs, is_input=False),
            producer="https://github.com/OpenLineage/OpenLineage/tree/0.0.1/client/python"
        )

        self.client.emit(event)

    def emit_fail(
        self,
        job_name: str,
        run_id: str,
        error_message: str
    ):
        """Emit lineage event when task fails"""

        event = RunEvent(
            eventType=RunState.FAIL,
            eventTime=datetime.now().isoformat(),
            run=Run(runId=run_id, facets={"errorMessage": error_message}),
            job=Job(namespace=self.namespace, name=job_name),
            producer="https://github.com/OpenLineage/OpenLineage/tree/0.0.1/client/python"
        )

        self.client.emit(event)

    def _format_datasets(self, datasets: List[Dict], is_input: bool):
        """Format dataset metadata for lineage"""

        formatted = []

        for ds in datasets:
            facets = {
                "dataSource": DataSourceDatasetFacet(
                    name=ds.get("source", "postgres"),
                    uri=ds.get("uri", os.getenv("DB_DSN"))
                )
            }

            # Add schema if available
            if "schema" in ds:
                facets["schema"] = SchemaDatasetFacet(
                    fields=[
                        SchemaField(name=col["name"], type=col["type"])
                        for col in ds["schema"]
                    ]
                )

            formatted.append({
                "namespace": self.namespace,
                "name": ds["name"],
                "facets": facets
            })

        return formatted


# ============================================================================
# Airflow Integration Helpers
# ============================================================================

def lineage_decorator(job_name: str, inputs: List[Dict] = None, outputs: List[Dict] = None):
    """Decorator to automatically emit lineage events for Airflow tasks"""

    def decorator(func):
        def wrapper(*args, **kwargs):
            import uuid

            emitter = LineageEmitter()
            run_id = str(uuid.uuid4())

            # Emit start event
            emitter.emit_start(
                job_name=job_name,
                run_id=run_id,
                inputs=inputs or [],
                outputs=outputs or []
            )

            try:
                # Execute task
                result = func(*args, **kwargs)

                # Emit complete event
                emitter.emit_complete(
                    job_name=job_name,
                    run_id=run_id,
                    inputs=inputs or [],
                    outputs=outputs or []
                )

                return result

            except Exception as e:
                # Emit fail event
                emitter.emit_fail(
                    job_name=job_name,
                    run_id=run_id,
                    error_message=str(e)
                )
                raise

        return wrapper
    return decorator


# ============================================================================
# Example Usage in Airflow DAG
# ============================================================================

"""
from services.lineage.openlineage_integration import lineage_decorator

@lineage_decorator(
    job_name="ingest_properties",
    inputs=[
        {
            "name": "mls_feed",
            "source": "external_api",
            "uri": "https://api.mls.com/listings",
            "schema": [
                {"name": "address", "type": "string"},
                {"name": "price", "type": "integer"}
            ]
        }
    ],
    outputs=[
        {
            "name": "property",
            "source": "postgres",
            "uri": os.getenv("DB_DSN"),
            "schema": [
                {"name": "id", "type": "uuid"},
                {"name": "address", "type": "string"},
                {"name": "list_price", "type": "integer"}
            ]
        }
    ]
)
def ingest_properties(**context):
    # Ingest logic
    pass
"""
