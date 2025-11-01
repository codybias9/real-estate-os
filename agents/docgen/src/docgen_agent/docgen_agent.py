"""Document Generation Agent

Orchestrates the creation of investor memo PDFs from property data.

Workflow:
1. Fetch property data from database (prospect + enrichment + scores)
2. Fetch comparable properties from Qdrant
3. Render MJML template with data
4. Convert MJML → HTML → PDF
5. Upload PDF to MinIO
6. Store action packet record in database
"""
import logging
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
import psycopg2
import psycopg2.extras
import json
from pathlib import Path

from .template_renderer import TemplateRenderer
from .pdf_generator import PDFGenerator
from .minio_client import MinIOClient

logger = logging.getLogger(__name__)


class DocGenAgent:
    """
    Document Generation Agent

    Generates professional investor memos for scored properties.
    """

    def __init__(
        self,
        database_url: str,
        minio_endpoint: str,
        minio_access_key: str,
        minio_secret_key: str,
        templates_dir: str = "/app/templates",
        qdrant_url: Optional[str] = None
    ):
        """
        Initialize document generation agent

        Args:
            database_url: PostgreSQL connection string
            minio_endpoint: MinIO endpoint (e.g., "minio:9000")
            minio_access_key: MinIO access key
            minio_secret_key: MinIO secret key
            templates_dir: Path to templates directory
            qdrant_url: Qdrant URL for fetching comparables (optional)
        """
        self.database_url = database_url
        self.qdrant_url = qdrant_url

        # Initialize components
        self.renderer = TemplateRenderer(templates_dir=templates_dir)
        self.pdf_gen = PDFGenerator()
        self.minio = MinIOClient(
            endpoint=minio_endpoint,
            access_key=minio_access_key,
            secret_key=minio_secret_key,
            bucket_name="property-documents",
            secure=False  # For local MinIO
        )

        logger.info("DocGenAgent initialized")

    def generate_batch(self, prospect_ids: List[int]) -> Dict[str, Any]:
        """
        Generate investor memos for a batch of prospects

        Args:
            prospect_ids: List of prospect IDs to process

        Returns:
            Dictionary with generation results and statistics
        """
        logger.info(f"Starting document generation batch: {len(prospect_ids)} prospects")

        results = {
            'total': len(prospect_ids),
            'succeeded': 0,
            'failed': 0,
            'documents': [],
            'errors': []
        }

        conn = None
        try:
            conn = psycopg2.connect(self.database_url)

            for prospect_id in prospect_ids:
                try:
                    doc_info = self.generate_single_document(prospect_id, conn)
                    if doc_info:
                        results['succeeded'] += 1
                        results['documents'].append(doc_info)
                    else:
                        results['failed'] += 1

                except Exception as e:
                    logger.error(f"Failed to generate document for prospect {prospect_id}: {e}")
                    results['failed'] += 1
                    results['errors'].append({
                        'prospect_id': prospect_id,
                        'error': str(e)
                    })

            conn.commit()

        except Exception as e:
            logger.error(f"Batch generation error: {e}")
            if conn:
                conn.rollback()
            raise

        finally:
            if conn:
                conn.close()

        logger.info(f"Document generation batch complete: {results['succeeded']}/{results['total']} succeeded")

        return results

    def generate_single_document(self, prospect_id: int, conn) -> Optional[Dict[str, Any]]:
        """
        Generate investor memo for a single prospect

        Args:
            prospect_id: Prospect ID
            conn: Database connection

        Returns:
            Document info dictionary with PDF URL and metadata
        """
        logger.info(f"Generating document for prospect {prospect_id}")

        # 1. Fetch property data
        property_data = self._fetch_property_data(prospect_id, conn)

        if not property_data:
            logger.error(f"Prospect {prospect_id} not found or incomplete")
            return None

        # 2. Fetch comparable properties (if Qdrant available)
        if self.qdrant_url:
            try:
                comparables = self._fetch_comparable_properties(prospect_id)
                property_data['comparables'] = comparables
            except Exception as e:
                logger.warning(f"Failed to fetch comparables: {e}")
                property_data['comparables'] = []
        else:
            property_data['comparables'] = []

        # 3. Render MJML template to HTML
        html = self.renderer.render_investor_memo(property_data)

        # 4. Convert HTML to PDF
        pdf_bytes = self.pdf_gen.html_to_pdf(html)

        # 5. Validate PDF
        if not self.pdf_gen.validate_pdf(pdf_bytes):
            raise RuntimeError("Generated PDF is invalid")

        # 6. Upload to MinIO
        object_name = f"investor_memos/{prospect_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        metadata = {
            'prospect_id': str(prospect_id),
            'generated_at': datetime.now().isoformat(),
            'score': str(property_data.get('score', {}).get('bird_dog_score', 0))
        }

        self.minio.upload_pdf(pdf_bytes, object_name, metadata)

        # 7. Generate presigned URL
        pdf_url = self.minio.get_presigned_url(object_name)

        # 8. Store action packet record
        action_packet_id = self._store_action_packet(
            prospect_id=prospect_id,
            pdf_url=pdf_url,
            object_name=object_name,
            pdf_size=len(pdf_bytes),
            conn=conn
        )

        logger.info(f"Document generated successfully: {object_name}")

        return {
            'prospect_id': prospect_id,
            'action_packet_id': action_packet_id,
            'pdf_url': pdf_url,
            'object_name': object_name,
            'pdf_size': len(pdf_bytes)
        }

    def _fetch_property_data(self, prospect_id: int, conn) -> Optional[Dict]:
        """
        Fetch all property data for document generation

        Retrieves:
        - Prospect data
        - Enrichment data
        - Score data
        - Census demographics
        """
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        query = """
            SELECT
                -- Prospect
                pq.id as prospect_id,
                pq.source,
                pq.source_id,
                pq.url,
                pq.payload,

                -- Enrichment
                pe.apn,
                pe.square_footage,
                pe.bedrooms,
                pe.bathrooms,
                pe.year_built,
                pe.assessed_value,
                pe.market_value,
                pe.last_sale_date,
                pe.last_sale_price,
                pe.zoning,
                pe.lot_size_sqft,
                pe.property_type,
                pe.owner_name,
                pe.owner_mailing_address,
                pe.tax_amount_annual,
                pe.source_api,
                pe.raw_response as enrichment_raw,

                -- Score
                ps.bird_dog_score,
                ps.confidence_level,
                ps.model_version,
                ps.feature_vector,
                ps.qdrant_point_id

            FROM prospect_queue pq
            INNER JOIN property_enrichment pe ON pe.prospect_id = pq.id
            INNER JOIN property_scores ps ON ps.prospect_id = pq.id
            WHERE pq.id = %s
        """

        cursor.execute(query, (prospect_id,))
        result = cursor.fetchone()
        cursor.close()

        if not result:
            return None

        # Parse into nested structure
        property_data = {
            'prospect': {
                'id': result['prospect_id'],
                'source': result['source'],
                'source_id': result['source_id'],
                'url': result['url'],
                'payload': result['payload']
            },
            'enrichment': {
                'apn': result['apn'],
                'square_footage': result['square_footage'],
                'bedrooms': result['bedrooms'],
                'bathrooms': result['bathrooms'],
                'year_built': result['year_built'],
                'assessed_value': result['assessed_value'],
                'market_value': result['market_value'],
                'last_sale_date': result['last_sale_date'],
                'last_sale_price': result['last_sale_price'],
                'zoning': result['zoning'],
                'lot_size_sqft': result['lot_size_sqft'],
                'property_type': result['property_type'],
                'owner_name': result['owner_name'],
                'owner_mailing_address': result['owner_mailing_address'],
                'tax_amount_annual': result['tax_amount_annual'],
                'source_api': result['source_api']
            },
            'score': {
                'bird_dog_score': float(result['bird_dog_score']) if result['bird_dog_score'] else 0,
                'confidence_level': float(result['confidence_level']) if result['confidence_level'] else 0,
                'model_version': result['model_version'],
                'feature_vector': result['feature_vector'] or [],
                'qdrant_point_id': result['qdrant_point_id']
            },
            'census': {}
        }

        # Extract census data from enrichment raw_response
        enrichment_raw = result.get('enrichment_raw', {})
        if enrichment_raw and 'census' in enrichment_raw:
            property_data['census'] = enrichment_raw['census']

        return property_data

    def _fetch_comparable_properties(self, prospect_id: int) -> List[Dict]:
        """
        Fetch comparable properties from Qdrant

        Args:
            prospect_id: Prospect ID

        Returns:
            List of comparable properties
        """
        # This would use the Qdrant client to find similar properties
        # For now, return empty list as placeholder

        logger.info(f"Fetching comparables for prospect {prospect_id}")

        # TODO: Implement Qdrant search
        # from qdrant_client import QdrantClient
        # client = QdrantClient(url=self.qdrant_url)
        # results = client.search(...)

        return []

    def _store_action_packet(
        self,
        prospect_id: int,
        pdf_url: str,
        object_name: str,
        pdf_size: int,
        conn
    ) -> int:
        """
        Store action packet record in database

        Args:
            prospect_id: Prospect ID
            pdf_url: PDF download URL
            object_name: MinIO object name
            pdf_size: PDF size in bytes
            conn: Database connection

        Returns:
            Action packet ID
        """
        cursor = conn.cursor()

        query = """
            INSERT INTO action_packets (
                prospect_id,
                packet_type,
                pdf_url,
                status,
                metadata,
                created_at,
                updated_at
            )
            VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
            RETURNING id
        """

        metadata = {
            'object_name': object_name,
            'pdf_size': pdf_size,
            'generated_at': datetime.now().isoformat()
        }

        cursor.execute(query, (
            prospect_id,
            'investor_memo',
            pdf_url,
            'generated',
            json.dumps(metadata)
        ))

        action_packet_id = cursor.fetchone()[0]
        cursor.close()

        logger.info(f"Stored action packet {action_packet_id} for prospect {prospect_id}")

        return action_packet_id


def main():
    """CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Document Generation Agent")
    parser.add_argument('--prospect-ids', type=str, required=True,
                       help='Comma-separated prospect IDs to process')
    parser.add_argument('--db-dsn', type=str, default=os.getenv('DB_DSN'),
                       help='Database connection string')
    parser.add_argument('--minio-endpoint', type=str, default=os.getenv('MINIO_ENDPOINT', 'minio:9000'),
                       help='MinIO endpoint')
    parser.add_argument('--minio-access-key', type=str, default=os.getenv('MINIO_ACCESS_KEY', 'minioadmin'),
                       help='MinIO access key')
    parser.add_argument('--minio-secret-key', type=str, default=os.getenv('MINIO_SECRET_KEY', 'minioadmin'),
                       help='MinIO secret key')
    parser.add_argument('--templates-dir', type=str, default='/app/templates',
                       help='Templates directory path')
    parser.add_argument('--qdrant-url', type=str, default=os.getenv('QDRANT_URL'),
                       help='Qdrant URL for comparables')

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Parse prospect IDs
    prospect_ids = [int(pid.strip()) for pid in args.prospect_ids.split(',')]

    # Initialize agent
    agent = DocGenAgent(
        database_url=args.db_dsn,
        minio_endpoint=args.minio_endpoint,
        minio_access_key=args.minio_access_key,
        minio_secret_key=args.minio_secret_key,
        templates_dir=args.templates_dir,
        qdrant_url=args.qdrant_url
    )

    # Run document generation
    results = agent.generate_batch(prospect_ids)

    print(f"\nDocument Generation Results:")
    print(f"  Total: {results['total']}")
    print(f"  Succeeded: {results['succeeded']}")
    print(f"  Failed: {results['failed']}")

    if results['documents']:
        print(f"\nGenerated Documents:")
        for doc in results['documents']:
            print(f"  Prospect {doc['prospect_id']}: {doc['pdf_url']}")

    if results['errors']:
        print(f"\nErrors:")
        for error in results['errors']:
            print(f"  Prospect {error['prospect_id']}: {error['error']}")


if __name__ == "__main__":
    main()
