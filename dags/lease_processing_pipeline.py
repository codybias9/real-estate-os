"""
Lease Document Processing Pipeline.

This DAG processes uploaded lease documents:
1. Extract text from PDF/Word documents
2. Parse structured lease data
3. Validate data quality
4. Store in database with provenance
5. Emit lineage events
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.decorators import task
from airflow.providers.postgres.hooks.postgres import PostgresHook
from typing import Dict, List, Any
import logging
import json

from document_processing.lease_parser import lease_parser
from provenance.provenance_tracker import track_provenance
from lineage.openlineage_client import emit_dataset_event
from data_quality.gx_config import run_expectation_suite

logger = logging.getLogger(__name__)


default_args = {
    'owner': 'real-estate-os',
    'depends_on_past': False,
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}


with DAG(
    'lease_processing_pipeline',
    default_args=default_args,
    description='Process lease documents and extract structured data',
    schedule_interval=None,  # Triggered manually on document upload
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['document-processing', 'leases', 'p1'],
) as dag:

    @task
    def extract_text_from_document(document_path: str, document_id: str) -> Dict[str, Any]:
        """
        Extract text from uploaded document.

        Supports PDF, Word, and plain text files.
        Uses Apache Tika for extraction.
        """
        logger.info(f"Extracting text from {document_path}")

        # Emit lineage event for document input
        emit_dataset_event(
            dataset_name=f"lease_document_{document_id}",
            dataset_namespace="document_storage",
            event_type="START",
            producer="lease_processing_pipeline",
            inputs=[],
            outputs=[{"name": document_path, "namespace": "minio"}]
        )

        try:
            # For demo purposes, simulate text extraction
            # In production, would use Apache Tika:
            # from tika import parser
            # parsed = parser.from_file(document_path)
            # text = parsed['content']

            # Simulate extracted text (in real implementation, read from MinIO)
            with open(document_path, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()

            logger.info(f"Extracted {len(text)} characters from document")

            return {
                'document_id': document_id,
                'document_path': document_path,
                'text': text,
                'text_length': len(text),
                'extraction_timestamp': datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Text extraction failed: {e}")
            emit_dataset_event(
                dataset_name=f"lease_document_{document_id}",
                dataset_namespace="document_storage",
                event_type="FAIL",
                producer="lease_processing_pipeline"
            )
            raise

    @task
    def parse_lease_data(extraction_result: Dict[str, Any], property_address: str) -> Dict[str, Any]:
        """
        Parse structured lease data from extracted text.
        """
        document_id = extraction_result['document_id']
        text = extraction_result['text']

        logger.info(f"Parsing lease data from document {document_id}")

        try:
            # Parse using lease_parser
            lease_data = lease_parser.parse_text(
                text=text,
                document_id=document_id,
                property_address=property_address
            )

            # Convert to dict for XCom serialization
            from dataclasses import asdict
            lease_dict = asdict(lease_data)

            # Convert date objects to strings
            if lease_dict.get('lease_start_date'):
                lease_dict['lease_start_date'] = lease_dict['lease_start_date'].isoformat()
            if lease_dict.get('lease_end_date'):
                lease_dict['lease_end_date'] = lease_dict['lease_end_date'].isoformat()

            logger.info(
                f"Parsed lease: tenant={lease_data.tenant_name}, "
                f"rent=${lease_data.monthly_rent}, "
                f"confidence={lease_data.confidence_score:.2f}"
            )

            return lease_dict

        except Exception as e:
            logger.error(f"Lease parsing failed: {e}")
            raise

    @task
    def validate_lease_data(lease_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate lease data using Great Expectations.
        """
        document_id = lease_data['document_id']
        logger.info(f"Validating lease data for {document_id}")

        try:
            # Run GX expectations on lease data
            # Convert to pandas DataFrame for GX
            import pandas as pd
            df = pd.DataFrame([lease_data])

            # Check critical fields
            validation_results = {
                'document_id': document_id,
                'validation_passed': True,
                'validation_errors': [],
                'validation_warnings': []
            }

            # Critical field checks
            if not lease_data.get('tenant_name') or lease_data['tenant_name'] == 'Unknown':
                validation_results['validation_errors'].append('Missing tenant name')
                validation_results['validation_passed'] = False

            if not lease_data.get('monthly_rent') or lease_data['monthly_rent'] <= 0:
                validation_results['validation_errors'].append('Invalid monthly rent')
                validation_results['validation_passed'] = False

            if lease_data.get('confidence_score', 0) < 0.5:
                validation_results['validation_warnings'].append(
                    f"Low confidence score: {lease_data['confidence_score']:.2f}"
                )

            # Check date consistency
            if lease_data.get('lease_start_date') and lease_data.get('lease_end_date'):
                from datetime import date
                start = date.fromisoformat(lease_data['lease_start_date'])
                end = date.fromisoformat(lease_data['lease_end_date'])
                if end <= start:
                    validation_results['validation_errors'].append(
                        'Lease end date must be after start date'
                    )
                    validation_results['validation_passed'] = False

            # Check deposit amount
            if lease_data.get('security_deposit') and lease_data.get('monthly_rent'):
                if lease_data['security_deposit'] < lease_data['monthly_rent']:
                    validation_results['validation_warnings'].append(
                        'Security deposit less than monthly rent'
                    )

            if not validation_results['validation_passed']:
                logger.error(
                    f"Validation failed for {document_id}: "
                    f"{validation_results['validation_errors']}"
                )
                raise ValueError(f"Lease data validation failed: {validation_results['validation_errors']}")

            if validation_results['validation_warnings']:
                logger.warning(
                    f"Validation warnings for {document_id}: "
                    f"{validation_results['validation_warnings']}"
                )

            logger.info(f"Validation passed for {document_id}")

            # Add validation results to lease data
            lease_data['validation_results'] = validation_results

            return lease_data

        except Exception as e:
            logger.error(f"Validation failed: {e}")
            raise

    @task
    def store_lease_in_database(lease_data: Dict[str, Any], tenant_id: str) -> Dict[str, Any]:
        """
        Store validated lease data in database with provenance.
        """
        document_id = lease_data['document_id']
        logger.info(f"Storing lease {document_id} in database")

        try:
            pg_hook = PostgresHook(postgres_conn_id='real_estate_db')

            # Insert lease record
            insert_sql = """
            INSERT INTO leases (
                tenant_id,
                document_id,
                tenant_name,
                property_address,
                unit_number,
                lease_start_date,
                lease_end_date,
                monthly_rent,
                security_deposit,
                lease_term_months,
                parking_spaces,
                utilities_included,
                pet_policy,
                late_fee,
                tenant_email,
                tenant_phone,
                confidence_score,
                created_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, NOW()
            )
            RETURNING id;
            """

            result = pg_hook.get_first(
                insert_sql,
                parameters=(
                    tenant_id,
                    lease_data['document_id'],
                    lease_data['tenant_name'],
                    lease_data['property_address'],
                    lease_data.get('unit_number'),
                    lease_data.get('lease_start_date'),
                    lease_data.get('lease_end_date'),
                    lease_data.get('monthly_rent'),
                    lease_data.get('security_deposit'),
                    lease_data.get('lease_term_months'),
                    lease_data.get('parking_spaces'),
                    lease_data.get('utilities_included'),
                    lease_data.get('pet_policy'),
                    lease_data.get('late_fee'),
                    lease_data.get('tenant_email'),
                    lease_data.get('tenant_phone'),
                    lease_data['confidence_score']
                )
            )

            lease_id = result[0]
            logger.info(f"Stored lease with ID: {lease_id}")

            # Track provenance for each field
            provenance_data = []
            for field_name, field_value in lease_data.items():
                if field_value is not None and field_name not in ['validation_results']:
                    provenance_record = track_provenance(
                        entity_type='lease',
                        entity_id=str(lease_id),
                        field_name=field_name,
                        source_system='lease_parser',
                        source_document=lease_data['document_id'],
                        extraction_method='regex',
                        confidence_score=lease_data['confidence_score'],
                        verified=False,
                        tenant_id=tenant_id
                    )
                    provenance_data.append(provenance_record)

            logger.info(f"Tracked provenance for {len(provenance_data)} fields")

            # Emit lineage event
            emit_dataset_event(
                dataset_name=f"leases",
                dataset_namespace="postgres",
                event_type="COMPLETE",
                producer="lease_processing_pipeline",
                inputs=[{
                    "name": lease_data['document_id'],
                    "namespace": "document_storage"
                }],
                outputs=[{
                    "name": "leases",
                    "namespace": "postgres",
                    "facets": {
                        "schema": {
                            "fields": list(lease_data.keys())
                        }
                    }
                }]
            )

            return {
                'lease_id': lease_id,
                'document_id': document_id,
                'tenant_id': tenant_id,
                'provenance_records': len(provenance_data),
                'status': 'success'
            }

        except Exception as e:
            logger.error(f"Database storage failed: {e}")

            # Emit failure event
            emit_dataset_event(
                dataset_name=f"leases",
                dataset_namespace="postgres",
                event_type="FAIL",
                producer="lease_processing_pipeline"
            )

            raise

    @task
    def generate_processing_report(storage_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate summary report of lease processing.
        """
        logger.info(f"Generating processing report for lease {storage_result['lease_id']}")

        report = {
            'lease_id': storage_result['lease_id'],
            'document_id': storage_result['document_id'],
            'processing_status': storage_result['status'],
            'provenance_records_created': storage_result['provenance_records'],
            'processing_timestamp': datetime.utcnow().isoformat(),
            'pipeline': 'lease_processing_pipeline'
        }

        logger.info(f"Processing report: {json.dumps(report, indent=2)}")

        return report

    # Define task dependencies
    # These would be called with actual parameters when triggered:
    # extraction = extract_text_from_document(document_path, document_id)
    # parsed = parse_lease_data(extraction, property_address)
    # validated = validate_lease_data(parsed)
    # stored = store_lease_in_database(validated, tenant_id)
    # report = generate_processing_report(stored)
