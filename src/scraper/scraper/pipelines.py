# src/scraper/scraper/pipelines.py
import json
from datetime import datetime
from airflow.providers.postgres.hooks.postgres import PostgresHook
from psycopg2.extras import Json


class PostgresPipeline:
    """Save scraped items to PostgreSQL database."""

    def open_spider(self, spider):
        """
        This method is called when the spider is opened.
        We use it to establish a connection to the database.
        """
        # Use the Airflow Hook to get a connection from the 'app_db' connection we created
        hook = PostgresHook(postgres_conn_id="app_db")
        self.conn = hook.get_conn()
        self.cur = self.conn.cursor()
        spider.logger.info("PostgreSQL connection established.")

    def close_spider(self, spider):
        """
        This method is called when the spider is closed.
        We use it to close the database connection.
        """
        self.cur.close()
        self.conn.close()
        spider.logger.info("PostgreSQL connection closed.")

    def process_item(self, item, spider):
        """
        This method is called for every item yielded by the spider.
        It handles inserting the data into the properties table.
        """
        # Check if this is a PropertyItem (new format) or legacy item
        if 'source' in item and 'address' in item:
            return self.process_property_item(item, spider)
        else:
            # Legacy handling for prospect_queue
            return self.process_legacy_item(item, spider)

    def process_property_item(self, item, spider):
        """Process PropertyItem and save to properties table."""
        insert_sql = """
            INSERT INTO properties (
                source, source_id, url,
                address, city, state, zip_code, county, latitude, longitude,
                property_type, price, bedrooms, bathrooms, sqft, lot_size, year_built,
                listing_date, description, features, images,
                status, metadata
            )
            VALUES (
                %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s
            )
            ON CONFLICT (source_id) DO UPDATE SET
                price = EXCLUDED.price,
                status = EXCLUDED.status,
                updated_at = NOW();
        """

        # Parse listing_date
        listing_date = item.get("listing_date")
        if listing_date and isinstance(listing_date, str):
            listing_date = datetime.fromisoformat(listing_date.replace('Z', '+00:00'))

        self.cur.execute(insert_sql, (
            item.get("source"),
            item.get("source_id"),
            item.get("url"),
            item.get("address"),
            item.get("city"),
            item.get("state"),
            item.get("zip_code"),
            item.get("county"),
            item.get("latitude"),
            item.get("longitude"),
            item.get("property_type"),
            item.get("price"),
            item.get("bedrooms"),
            item.get("bathrooms"),
            item.get("sqft"),
            item.get("lot_size"),
            item.get("year_built"),
            listing_date,
            item.get("description"),
            item.get("features", []),
            item.get("images", []),
            item.get("status", "new"),
            Json(item.get("metadata", {}))
        ))
        self.conn.commit()

        spider.logger.info(f"Saved property: {item.get('address')}, {item.get('city')}, {item.get('state')} (ID: {item.get('source_id')})")

        return item

    def process_legacy_item(self, item, spider):
        """Process legacy items and save to prospect_queue table."""
        insert_sql = """
            INSERT INTO prospect_queue (source, source_id, url, payload)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (source_id) DO NOTHING;
        """

        # The source_id is the unique identifier from the source
        source_id = item.get("property_id") or item.get("source_id") or spider.name + "_" + str(hash(str(item)))

        # The payload is the entire item, stored as a JSONB object
        payload = json.dumps(dict(item))

        self.cur.execute(insert_sql, (
            spider.name,
            source_id,
            item.get("url", ""),
            payload
        ))
        self.conn.commit()
        return item
