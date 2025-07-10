# src/scraper/scraper/pipelines.py
import json
from airflow.providers.postgres.hooks.postgres import PostgresHook

class PostgresPipeline:
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
        It handles inserting the data into the prospect_queue table.
        """
        insert_sql = """
            INSERT INTO prospect_queue (source, source_id, url, payload)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (source_id) DO NOTHING;
        """
        
        # The source_id is the unique identifier from the source (e.g., Zillow property ID)
        source_id = item.get("property_id")

        # The payload is the entire item, stored as a JSONB object
        payload = json.dumps(dict(item))

        self.cur.execute(insert_sql, (
            spider.name,
            source_id,
            item.get("url"),
            payload
        ))
        self.conn.commit()
        return item
