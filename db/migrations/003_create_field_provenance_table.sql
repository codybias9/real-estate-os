-- Migration: Create Field-Level Provenance Table
-- Date: 2024-11-02
-- Description: Creates table for tracking data provenance at field level
--              Enables trust scoring and audit trails for all data changes

-- Create field_provenance table
CREATE TABLE IF NOT EXISTS field_provenance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Subject identification
    entity_type VARCHAR(50) NOT NULL,  -- e.g., 'property', 'prospect', 'lease'
    entity_id UUID NOT NULL,
    field_name VARCHAR(100) NOT NULL,
    tenant_id UUID NOT NULL,

    -- Value tracking
    field_value TEXT,  -- Store as JSON or string
    previous_value TEXT,  -- Previous value for change tracking

    -- Provenance metadata
    source VARCHAR(100) NOT NULL,  -- e.g., 'mls_api', 'user_input', 'ml_model', 'external_enrichment'
    method VARCHAR(100) NOT NULL,  -- e.g., 'api_fetch', 'manual_entry', 'model_inference', 'spatial_join'
    confidence NUMERIC(3,2) DEFAULT 1.0 CHECK (confidence >= 0 AND confidence <= 1),  -- 0-1

    -- Evidence
    evidence_uri TEXT,  -- Link to supporting evidence (S3, API response, etc.)
    evidence_metadata JSONB,  -- Additional context

    -- Trust scoring inputs
    source_reliability NUMERIC(3,2) DEFAULT 0.8,  -- Source reputation score
    freshness_score NUMERIC(3,2) DEFAULT 1.0,  -- Age-based decay
    validation_score NUMERIC(3,2) DEFAULT 1.0,  -- Did it pass validation?
    trust_score NUMERIC(3,2) DEFAULT 0.8,  -- Computed composite trust

    -- Change tracking
    operation VARCHAR(20) NOT NULL,  -- 'CREATE', 'UPDATE', 'DELETE', 'ENRICH'
    changed_by UUID,  -- User or system actor
    changed_by_type VARCHAR(20) DEFAULT 'system',  -- 'user', 'system', 'ml_model'

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP,  -- Optional expiration for stale data

    -- Indexes
    CONSTRAINT fk_field_provenance_tenant
        FOREIGN KEY (tenant_id)
        REFERENCES tenants(id)
        ON DELETE CASCADE
);

-- Note: We don't enforce FK to entity_id because it can reference different tables
-- Instead, we validate via application logic

-- Create indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_field_provenance_tenant_id
    ON field_provenance(tenant_id);

CREATE INDEX IF NOT EXISTS idx_field_provenance_entity
    ON field_provenance(tenant_id, entity_type, entity_id);

CREATE INDEX IF NOT EXISTS idx_field_provenance_entity_field
    ON field_provenance(tenant_id, entity_type, entity_id, field_name);

CREATE INDEX IF NOT EXISTS idx_field_provenance_source
    ON field_provenance(tenant_id, source);

CREATE INDEX IF NOT EXISTS idx_field_provenance_trust_score
    ON field_provenance(tenant_id, trust_score DESC);

CREATE INDEX IF NOT EXISTS idx_field_provenance_created_at
    ON field_provenance(tenant_id, created_at DESC);

-- Composite index for timeline queries
CREATE INDEX IF NOT EXISTS idx_field_provenance_timeline
    ON field_provenance(tenant_id, entity_type, entity_id, field_name, created_at DESC);

-- Enable Row Level Security
ALTER TABLE field_provenance ENABLE ROW LEVEL SECURITY;

-- Drop existing policy if exists (idempotent)
DROP POLICY IF EXISTS field_provenance_tenant_isolation ON field_provenance;

-- Create RLS policy
CREATE POLICY field_provenance_tenant_isolation ON field_provenance
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

-- Grant necessary permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON field_provenance TO postgres;

-- Create helper function to calculate trust score
CREATE OR REPLACE FUNCTION calculate_trust_score(
    p_source_reliability NUMERIC,
    p_freshness_score NUMERIC,
    p_validation_score NUMERIC,
    p_confidence NUMERIC
)
RETURNS NUMERIC AS $$
DECLARE
    trust NUMERIC;
BEGIN
    -- Trust score formula: weighted average of components
    -- Weights: source 30%, freshness 20%, validation 30%, confidence 20%
    trust := (
        p_source_reliability * 0.30 +
        p_freshness_score * 0.20 +
        p_validation_score * 0.30 +
        p_confidence * 0.20
    );

    -- Clamp to [0, 1]
    RETURN LEAST(GREATEST(trust, 0.0), 1.0);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Create trigger function to auto-calculate trust score
CREATE OR REPLACE FUNCTION update_trust_score()
RETURNS TRIGGER AS $$
BEGIN
    NEW.trust_score := calculate_trust_score(
        NEW.source_reliability,
        NEW.freshness_score,
        NEW.validation_score,
        NEW.confidence
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Add trigger to auto-update trust score on insert/update
DROP TRIGGER IF EXISTS trigger_update_trust_score ON field_provenance;

CREATE TRIGGER trigger_update_trust_score
    BEFORE INSERT OR UPDATE ON field_provenance
    FOR EACH ROW
    EXECUTE FUNCTION update_trust_score();

-- Create function to calculate freshness score based on age
CREATE OR REPLACE FUNCTION calculate_freshness_score(created_at TIMESTAMP)
RETURNS NUMERIC AS $$
DECLARE
    age_days INTEGER;
    freshness NUMERIC;
BEGIN
    -- Calculate age in days
    age_days := EXTRACT(EPOCH FROM (NOW() - created_at)) / 86400;

    -- Decay function: exponential decay with half-life of 90 days
    -- freshness = 0.5^(age_days / 90)
    IF age_days <= 0 THEN
        freshness := 1.0;
    ELSIF age_days >= 365 THEN
        freshness := 0.1;  -- Floor at 0.1 for data older than 1 year
    ELSE
        freshness := POWER(0.5, age_days::NUMERIC / 90.0);
    END IF;

    RETURN LEAST(GREATEST(freshness, 0.0), 1.0);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Create materialized view for latest provenance per field
CREATE MATERIALIZED VIEW IF NOT EXISTS latest_field_provenance AS
SELECT DISTINCT ON (tenant_id, entity_type, entity_id, field_name)
    id,
    entity_type,
    entity_id,
    field_name,
    tenant_id,
    field_value,
    source,
    method,
    confidence,
    evidence_uri,
    trust_score,
    created_at,
    changed_by,
    changed_by_type
FROM field_provenance
ORDER BY tenant_id, entity_type, entity_id, field_name, created_at DESC;

-- Create unique index on materialized view
CREATE UNIQUE INDEX IF NOT EXISTS idx_latest_field_provenance_unique
    ON latest_field_provenance(tenant_id, entity_type, entity_id, field_name);

-- Create index for queries by entity
CREATE INDEX IF NOT EXISTS idx_latest_field_provenance_entity
    ON latest_field_provenance(tenant_id, entity_type, entity_id);

-- Refresh materialized view (run this periodically via cron/Airflow)
-- REFRESH MATERIALIZED VIEW CONCURRENTLY latest_field_provenance;

-- Create view for trust score aggregation by entity
CREATE VIEW entity_trust_scores AS
SELECT
    tenant_id,
    entity_type,
    entity_id,
    COUNT(*) as field_count,
    AVG(trust_score) as avg_trust_score,
    MIN(trust_score) as min_trust_score,
    MAX(trust_score) as max_trust_score,
    STDDEV(trust_score) as stddev_trust_score,
    -- Identify fields with low trust (<0.5)
    COUNT(CASE WHEN trust_score < 0.5 THEN 1 END) as low_trust_fields,
    -- Identify stale fields (>90 days old)
    COUNT(CASE WHEN created_at < NOW() - INTERVAL '90 days' THEN 1 END) as stale_fields
FROM latest_field_provenance
GROUP BY tenant_id, entity_type, entity_id;

-- Create view for provenance timeline (full history)
CREATE VIEW field_provenance_timeline AS
SELECT
    fp.id,
    fp.entity_type,
    fp.entity_id,
    fp.field_name,
    fp.tenant_id,
    fp.field_value,
    fp.previous_value,
    fp.source,
    fp.method,
    fp.confidence,
    fp.trust_score,
    fp.operation,
    fp.changed_by,
    fp.changed_by_type,
    fp.created_at,
    fp.evidence_uri,
    -- Calculate change significance
    CASE
        WHEN fp.previous_value IS NULL THEN 'INITIAL'
        WHEN fp.field_value = fp.previous_value THEN 'NO_CHANGE'
        WHEN fp.operation = 'DELETE' THEN 'DELETION'
        ELSE 'MODIFICATION'
    END as change_type
FROM field_provenance fp
ORDER BY fp.entity_type, fp.entity_id, fp.field_name, fp.created_at DESC;

-- Verification queries to run after migration:
--
-- 1. Check table structure:
-- \d field_provenance
--
-- 2. Verify RLS policy:
-- SELECT tablename, policyname, permissive, roles, cmd, qual
-- FROM pg_policies
-- WHERE schemaname = 'public' AND tablename = 'field_provenance';
--
-- 3. Test trust score calculation:
-- SELECT calculate_trust_score(0.9, 0.8, 1.0, 0.95);
--
-- 4. Test freshness score:
-- SELECT calculate_freshness_score(NOW() - INTERVAL '30 days');
-- SELECT calculate_freshness_score(NOW() - INTERVAL '90 days');
-- SELECT calculate_freshness_score(NOW() - INTERVAL '180 days');
--
-- 5. Insert test provenance:
-- INSERT INTO field_provenance (
--     entity_type, entity_id, field_name, tenant_id,
--     field_value, source, method, confidence,
--     source_reliability, validation_score, operation
-- ) VALUES (
--     'property', '123e4567-e89b-12d3-a456-426614174000', 'price',
--     '00000000-0000-0000-0000-000000000001',
--     '500000', 'mls_api', 'api_fetch', 0.95,
--     0.9, 1.0, 'CREATE'
-- );
--
-- 6. Check materialized view:
-- SELECT * FROM latest_field_provenance LIMIT 10;
--
-- 7. Check entity trust scores:
-- SELECT * FROM entity_trust_scores LIMIT 10;
