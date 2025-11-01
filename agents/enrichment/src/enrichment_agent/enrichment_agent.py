"""Main enrichment agent

Orchestrates data enrichment from multiple sources.
"""
import logging
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
import psycopg2
import psycopg2.extras
import json

from .models import PropertyEnrichmentData, EnrichmentStatus, AssessorResponse, CensusResponse
from .base_client import BaseAPIClient
from .census_client import CensusAPIClient
from .assessor_client import get_assessor_client, MockAssessorClient

logger = logging.getLogger(__name__)


class EnrichmentAgent:
    """
    Main enrichment agent

    Coordinates data enrichment from multiple sources:
    - County assessor data
    - Census demographics
    - Market data (future)
    """

    def __init__(
        self,
        database_url: str,
        census_api_key: Optional[str] = None,
        county_config: Optional[Dict] = None
    ):
        """
        Initialize enrichment agent

        Args:
            database_url: PostgreSQL connection string
            census_api_key: US Census API key (get free at census.gov)
            county_config: County configuration dict (from YAML)
        """
        self.database_url = database_url
        self.county_config = county_config or {}

        # Initialize API clients
        self.census_client = CensusAPIClient(api_key=census_api_key)

        # Get appropriate assessor client for county
        if county_config:
            self.assessor_client = get_assessor_client(county_config)
        else:
            self.assessor_client = MockAssessorClient()

        logger.info("EnrichmentAgent initialized")
        logger.info(f"Census API: {self.census_client.get_name()}")
        logger.info(f"Assessor: {self.assessor_client.get_name()}")

    def enrich_batch(self, prospect_ids: List[int]) -> Dict[str, Any]:
        """
        Enrich a batch of prospects

        Args:
            prospect_ids: List of prospect IDs to enrich

        Returns:
            Dictionary with enrichment results and statistics
        """
        logger.info(f"Starting enrichment batch: {len(prospect_ids)} prospects")

        results = {
            'total': len(prospect_ids),
            'succeeded': 0,
            'failed': 0,
            'errors': []
        }

        conn = None
        try:
            conn = psycopg2.connect(self.database_url)

            for prospect_id in prospect_ids:
                try:
                    success = self.enrich_single_prospect(prospect_id, conn)
                    if success:
                        results['succeeded'] += 1
                    else:
                        results['failed'] += 1

                except Exception as e:
                    logger.error(f"Failed to enrich prospect {prospect_id}: {e}")
                    results['failed'] += 1
                    results['errors'].append({
                        'prospect_id': prospect_id,
                        'error': str(e)
                    })

            conn.commit()

        except Exception as e:
            logger.error(f"Batch enrichment error: {e}")
            if conn:
                conn.rollback()
            raise

        finally:
            if conn:
                conn.close()

        # Log statistics
        self._log_stats()

        logger.info(f"Enrichment batch complete: {results['succeeded']}/{results['total']} succeeded")

        return results

    def enrich_single_prospect(self, prospect_id: int, conn) -> bool:
        """
        Enrich a single prospect

        Args:
            prospect_id: Prospect ID to enrich
            conn: Database connection

        Returns:
            True if enrichment succeeded, False otherwise
        """
        logger.info(f"Enriching prospect {prospect_id}")

        # Fetch prospect data
        prospect = self._fetch_prospect(prospect_id, conn)

        if not prospect:
            logger.error(f"Prospect {prospect_id} not found")
            return False

        # Extract address and other info from payload
        payload = prospect['payload']
        address = payload.get('address', '')
        zip_code = payload.get('zip_code', '')

        logger.debug(f"Prospect address: {address}, ZIP: {zip_code}")

        # Initialize enrichment data
        enrichment_data = {
            'prospect_id': prospect_id
        }

        # 1. Fetch assessor data
        assessor_data = self._fetch_assessor_data(address, payload.get('apn'))
        if assessor_data:
            enrichment_data.update(self._map_assessor_data(assessor_data))

        # 2. Fetch Census data
        if zip_code:
            census_data = self._fetch_census_data(zip_code)
            if census_data:
                enrichment_data.update(self._map_census_data(census_data))

        # 3. Store enrichment data
        success = self._store_enrichment(enrichment_data, conn)

        return success

    def _fetch_prospect(self, prospect_id: int, conn) -> Optional[Dict]:
        """Fetch prospect from database"""
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute(
            "SELECT id, source, source_id, url, payload, status FROM prospect_queue WHERE id = %s",
            (prospect_id,)
        )
        result = cursor.fetchone()
        cursor.close()
        return dict(result) if result else None

    def _fetch_assessor_data(self, address: str, apn: Optional[str] = None) -> Optional[AssessorResponse]:
        """Fetch data from county assessor"""
        try:
            if apn:
                return self.assessor_client.get_property_by_apn(apn)
            elif address:
                return self.assessor_client.get_property_by_address(address)
            else:
                logger.warning("No address or APN provided for assessor lookup")
                return None

        except Exception as e:
            logger.error(f"Assessor API error: {e}")
            return None

    def _fetch_census_data(self, zip_code: str) -> Optional[CensusResponse]:
        """Fetch demographics from Census Bureau"""
        try:
            return self.census_client.get_zip_demographics(zip_code)

        except Exception as e:
            logger.error(f"Census API error: {e}")
            return None

    def _map_assessor_data(self, assessor: AssessorResponse) -> Dict:
        """Map assessor response to enrichment data"""
        return {
            'apn': assessor.apn,
            'square_footage': assessor.square_footage,
            'bedrooms': assessor.bedrooms,
            'bathrooms': assessor.bathrooms,
            'year_built': assessor.year_built,
            'assessed_value': assessor.assessed_value,
            'market_value': assessor.market_value,
            'last_sale_date': assessor.last_sale_date,
            'last_sale_price': assessor.last_sale_price,
            'zoning': assessor.zoning,
            'lot_size_sqft': assessor.lot_size,
            'property_type': assessor.property_type,
            'owner_name': assessor.owner_name,
            'owner_mailing_address': assessor.owner_address,
            'tax_amount_annual': assessor.annual_tax,
            'source_api': self.assessor_client.get_name(),
            'raw_response': assessor.raw_data
        }

    def _map_census_data(self, census: CensusResponse) -> Dict:
        """Map Census data to enrichment data (stored in raw_response)"""
        # Census data goes into raw_response since we don't have specific columns
        return {
            'raw_response': {
                'census': {
                    'zip_code': census.zip_code,
                    'population': census.population,
                    'median_household_income': float(census.median_household_income) if census.median_household_income else None,
                    'median_age': float(census.median_age) if census.median_age else None,
                    'owner_occupied_rate': float(census.owner_occupied_rate) if census.owner_occupied_rate else None,
                    'median_home_value': float(census.median_home_value) if census.median_home_value else None,
                }
            }
        }

    def _store_enrichment(self, data: Dict, conn) -> bool:
        """Store enrichment data in database"""
        try:
            cursor = conn.cursor()

            # Convert Decimals to float for JSON
            raw_response = data.get('raw_response', {})
            if raw_response:
                raw_response_json = json.dumps(raw_response, default=str)
            else:
                raw_response_json = None

            # Insert or update property_enrichment
            query = """
                INSERT INTO property_enrichment (
                    prospect_id, apn, square_footage, bedrooms, bathrooms, year_built,
                    assessed_value, market_value, last_sale_date, last_sale_price,
                    zoning, lot_size_sqft, property_type, owner_name, owner_mailing_address,
                    tax_amount_annual, source_api, raw_response, created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                ON CONFLICT (prospect_id)
                DO UPDATE SET
                    apn = EXCLUDED.apn,
                    square_footage = EXCLUDED.square_footage,
                    bedrooms = EXCLUDED.bedrooms,
                    bathrooms = EXCLUDED.bathrooms,
                    year_built = EXCLUDED.year_built,
                    assessed_value = EXCLUDED.assessed_value,
                    market_value = EXCLUDED.market_value,
                    last_sale_date = EXCLUDED.last_sale_date,
                    last_sale_price = EXCLUDED.last_sale_price,
                    zoning = EXCLUDED.zoning,
                    lot_size_sqft = EXCLUDED.lot_size_sqft,
                    property_type = EXCLUDED.property_type,
                    owner_name = EXCLUDED.owner_name,
                    owner_mailing_address = EXCLUDED.owner_mailing_address,
                    tax_amount_annual = EXCLUDED.tax_amount_annual,
                    source_api = EXCLUDED.source_api,
                    raw_response = EXCLUDED.raw_response,
                    updated_at = NOW()
            """

            cursor.execute(query, (
                data.get('prospect_id'),
                data.get('apn'),
                data.get('square_footage'),
                data.get('bedrooms'),
                data.get('bathrooms'),
                data.get('year_built'),
                data.get('assessed_value'),
                data.get('market_value'),
                data.get('last_sale_date'),
                data.get('last_sale_price'),
                data.get('zoning'),
                data.get('lot_size_sqft'),
                data.get('property_type'),
                data.get('owner_name'),
                data.get('owner_mailing_address'),
                data.get('tax_amount_annual'),
                data.get('source_api'),
                raw_response_json
            ))

            cursor.close()

            logger.info(f"Stored enrichment for prospect {data.get('prospect_id')}")
            return True

        except Exception as e:
            logger.error(f"Failed to store enrichment: {e}")
            return False

    def _log_stats(self):
        """Log API client statistics"""
        logger.info("=" * 50)
        logger.info("ENRICHMENT API STATISTICS")
        logger.info("=" * 50)

        for client in [self.census_client, self.assessor_client]:
            stats = client.get_stats()
            logger.info(f"{stats['client']}:")
            logger.info(f"  Requests: {stats['requests_made']}")
            logger.info(f"  Cache hits: {stats['cache_hits']}")
            logger.info(f"  Errors: {stats['errors']}")
            logger.info(f"  Total cost: ${stats['total_cost']:.2f}")
            logger.info(f"  Cache hit rate: {stats['cache_hit_rate']:.1%}")

        logger.info("=" * 50)


def main():
    """CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Property Enrichment Agent")
    parser.add_argument('--prospect-ids', type=str, required=True,
                       help='Comma-separated prospect IDs to enrich')
    parser.add_argument('--db-dsn', type=str, default=os.getenv('DB_DSN'),
                       help='Database connection string')
    parser.add_argument('--census-api-key', type=str, default=os.getenv('CENSUS_API_KEY'),
                       help='Census API key')
    parser.add_argument('--county-config', type=str,
                       help='Path to county configuration YAML')

    args = parser.parse_args()

    # Parse prospect IDs
    prospect_ids = [int(pid.strip()) for pid in args.prospect_ids.split(',')]

    # Load county config if provided
    county_config = None
    if args.county_config:
        import yaml
        with open(args.county_config, 'r') as f:
            county_config = yaml.safe_load(f)

    # Initialize agent
    agent = EnrichmentAgent(
        database_url=args.db_dsn,
        census_api_key=args.census_api_key,
        county_config=county_config
    )

    # Run enrichment
    results = agent.enrich_batch(prospect_ids)

    print(f"\nEnrichment Results:")
    print(f"  Total: {results['total']}")
    print(f"  Succeeded: {results['succeeded']}")
    print(f"  Failed: {results['failed']}")

    if results['errors']:
        print(f"\nErrors:")
        for error in results['errors']:
            print(f"  Prospect {error['prospect_id']}: {error['error']}")


if __name__ == "__main__":
    main()
