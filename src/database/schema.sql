-- src/database/schema.sql

-- Drop the table if it exists to ensure a clean slate for development
DROP TABLE IF EXISTS prospect_queue;

-- Create the prospect_queue table
-- This table acts as the initial ingestion point for all scraped data.
CREATE TABLE prospect_queue (
    id SERIAL PRIMARY KEY,
    source VARCHAR(255) NOT NULL,
    source_id VARCHAR(255) UNIQUE NOT NULL,
    url TEXT NOT NULL,
    payload JSONB NOT NULL,
    status VARCHAR(50) DEFAULT 'new' NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add an index on the status column for faster querying of unprocessed items
CREATE INDEX idx_prospect_queue_status ON prospect_queue(status);

-- Optional: Add a trigger to automatically update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
   NEW.updated_at = NOW();
   RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_prospect_queue_updated_at
BEFORE UPDATE ON prospect_queue
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();
