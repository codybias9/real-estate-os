"""Scrapy pipelines for data validation, deduplication, and storage"""
import logging
from typing import Set
import psycopg2
import psycopg2.extras
from psycopg2.extensions import connection as PgConnection
from scrapy import Spider
from scrapy.exceptions import DropItem
import json
from datetime import datetime
from .items import PropertyListing, PropertyItem
from pydantic import ValidationError

logger = logging.getLogger(__name__)


class ValidationPipeline:
    """
    Pipeline to validate scraped items using Pydantic models

    Ensures data quality before storage
    """

    def process_item(self, item: PropertyItem, spider: Spider) -> PropertyItem:
        """Validate item using Pydantic model"""
        try:
            # Convert Scrapy Item to dict
            item_dict = dict(item)

            # Validate with Pydantic
            validated = PropertyListing(**item_dict)

            # Update item with validated/cleaned data
            for field, value in validated.dict().items():
                if field in item.fields:
                    item[field] = value

            logger.debug(f"Validated item: {item.get('source_id')}")
            return item

        except ValidationError as e:
            logger.error(f"Validation failed for {item.get('url', 'unknown')}: {e}")
            raise DropItem(f"Validation error: {e}")


class DuplicatesPipeline:
    """
    Pipeline to filter out duplicate items based on source_id

    Keeps track of seen source_ids in memory during spider run
    """

    def __init__(self):
        self.seen_ids: Set[str] = set()

    def open_spider(self, spider: Spider):
        """Reset seen IDs when spider opens"""
        self.seen_ids.clear()
        logger.info("Duplicates filter initialized")

    def process_item(self, item: PropertyItem, spider: Spider) -> PropertyItem:
        """Check for duplicates"""
        source_id = item.get('source_id')

        if not source_id:
            raise DropItem("Missing source_id")

        # Create composite key with source
        composite_id = f"{item.get('source', '')}:{source_id}"

        if composite_id in self.seen_ids:
            logger.debug(f"Duplicate item dropped: {composite_id}")
            raise DropItem(f"Duplicate item: {composite_id}")

        self.seen_ids.add(composite_id)
        return item

    def close_spider(self, spider: Spider):
        """Log statistics when spider closes"""
        logger.info(f"Total unique items processed: {len(self.seen_ids)}")


class DatabasePipeline:
    """
    Pipeline to store validated items in PostgreSQL database

    Inserts items into prospect_queue table with ON CONFLICT handling
    """

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.conn: PgConnection = None
        self.stats = {
            'inserted': 0,
            'updated': 0,
            'errors': 0
        }

    @classmethod
    def from_crawler(cls, crawler):
        """Factory method to get database URL from settings"""
        return cls(
            database_url=crawler.settings.get('DATABASE_URL')
        )

    def open_spider(self, spider: Spider):
        """Open database connection when spider starts"""
        try:
            self.conn = psycopg2.connect(self.database_url)
            self.conn.autocommit = False  # Use transactions
            logger.info("Database connection established")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    def close_spider(self, spider: Spider):
        """Close database connection and log stats"""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")

        logger.info(f"Database stats - Inserted: {self.stats['inserted']}, "
                   f"Updated: {self.stats['updated']}, "
                   f"Errors: {self.stats['errors']}")

    def process_item(self, item: PropertyItem, spider: Spider) -> PropertyItem:
        """Insert or update item in database"""
        try:
            # Convert item to dict
            item_dict = dict(item)

            # Prepare data for prospect_queue table
            source = item_dict.get('source')
            source_id = item_dict.get('source_id')
            url = item_dict.get('url')
            payload = json.dumps(item_dict, default=str)  # Convert to JSON

            # SQL query with ON CONFLICT handling
            query = """
                INSERT INTO prospect_queue (source, source_id, url, payload, status, created_at, updated_at)
                VALUES (%s, %s, %s, %s, 'new', NOW(), NOW())
                ON CONFLICT (source_id)
                DO UPDATE SET
                    url = EXCLUDED.url,
                    payload = EXCLUDED.payload,
                    updated_at = NOW()
                RETURNING id, (xmax = 0) AS inserted
            """

            with self.conn.cursor() as cursor:
                cursor.execute(query, (source, source_id, url, payload))
                result = cursor.fetchone()

                if result:
                    record_id, is_insert = result
                    if is_insert:
                        self.stats['inserted'] += 1
                        logger.debug(f"Inserted new record: {source_id} (id: {record_id})")
                    else:
                        self.stats['updated'] += 1
                        logger.debug(f"Updated existing record: {source_id} (id: {record_id})")

                self.conn.commit()

            return item

        except Exception as e:
            self.stats['errors'] += 1
            self.conn.rollback()
            logger.error(f"Database error for {item.get('source_id')}: {e}")
            raise DropItem(f"Database error: {e}")


class StatsPipeline:
    """
    Pipeline to collect and log statistics about scraped items
    """

    def __init__(self):
        self.stats = {
            'total': 0,
            'by_source': {},
            'by_status': {},
            'price_range': {
                'min': float('inf'),
                'max': 0,
                'sum': 0,
                'count': 0
            }
        }

    def process_item(self, item: PropertyItem, spider: Spider) -> PropertyItem:
        """Collect statistics from item"""
        self.stats['total'] += 1

        # Count by source
        source = item.get('source', 'unknown')
        self.stats['by_source'][source] = self.stats['by_source'].get(source, 0) + 1

        # Count by listing status
        status = item.get('listing_status', 'unknown')
        self.stats['by_status'][status] = self.stats['by_status'].get(status, 0) + 1

        # Price statistics
        listing_price = item.get('listing_price')
        if listing_price and isinstance(listing_price, (int, float)):
            self.stats['price_range']['min'] = min(self.stats['price_range']['min'], listing_price)
            self.stats['price_range']['max'] = max(self.stats['price_range']['max'], listing_price)
            self.stats['price_range']['sum'] += listing_price
            self.stats['price_range']['count'] += 1

        return item

    def close_spider(self, spider: Spider):
        """Log statistics when spider closes"""
        logger.info("=" * 50)
        logger.info("SCRAPING STATISTICS")
        logger.info("=" * 50)
        logger.info(f"Total items: {self.stats['total']}")

        logger.info("\nBy source:")
        for source, count in self.stats['by_source'].items():
            logger.info(f"  {source}: {count}")

        logger.info("\nBy status:")
        for status, count in self.stats['by_status'].items():
            logger.info(f"  {status}: {count}")

        if self.stats['price_range']['count'] > 0:
            avg_price = self.stats['price_range']['sum'] / self.stats['price_range']['count']
            logger.info(f"\nPrice range:")
            logger.info(f"  Min: ${self.stats['price_range']['min']:,.2f}")
            logger.info(f"  Max: ${self.stats['price_range']['max']:,.2f}")
            logger.info(f"  Avg: ${avg_price:,.2f}")

        logger.info("=" * 50)
