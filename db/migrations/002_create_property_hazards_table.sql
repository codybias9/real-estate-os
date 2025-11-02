-- Migration: Create Property Hazards Table
-- Date: 2024-11-02
-- Description: Creates table for storing environmental hazard assessments
--              (flood, wildfire, heat) linked to properties

-- Create property_hazards table
CREATE TABLE IF NOT EXISTS property_hazards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    property_id UUID NOT NULL,
    tenant_id UUID NOT NULL,

    -- Flood hazards (FEMA NFHL)
    flood_zone_type VARCHAR(10),  -- A, AE, AO, X, etc.
    flood_risk VARCHAR(20),        -- low, moderate, high
    flood_risk_score NUMERIC(3,2) DEFAULT 0.0 CHECK (flood_risk_score >= 0 AND flood_risk_score <= 1),
    flood_insurance_required BOOLEAN DEFAULT FALSE,

    -- Wildfire hazards (USGS WHP + State data)
    wildfire_risk_level VARCHAR(20),      -- very_low, low, moderate, high, very_high
    wildfire_risk_score NUMERIC(3,2) DEFAULT 0.0 CHECK (wildfire_risk_score >= 0 AND wildfire_risk_score <= 1),
    wildfire_hazard_potential VARCHAR(20), -- Low, Moderate, High, Very High, Extreme
    ca_fire_zone VARCHAR(50),              -- California: Moderate, High, Very High

    -- Heat hazards
    avg_summer_temp NUMERIC(5,2),
    heat_wave_days_per_year INTEGER,
    heat_risk_score NUMERIC(3,2) DEFAULT 0.0 CHECK (heat_risk_score >= 0 AND heat_risk_score <= 1),

    -- Composite scores
    composite_hazard_score NUMERIC(3,2) DEFAULT 0.0 CHECK (composite_hazard_score >= 0 AND composite_hazard_score <= 1),
    total_value_adjustment_pct NUMERIC(6,3) DEFAULT 0.0,  -- e.g., -5.250 means -5.25%
    total_annual_cost_impact NUMERIC(12,2) DEFAULT 0.0,   -- Dollar amount

    -- Metadata
    assessed_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

    -- Foreign key constraint
    CONSTRAINT fk_property_hazards_property
        FOREIGN KEY (property_id)
        REFERENCES properties(id)
        ON DELETE CASCADE,

    -- Ensure one hazard record per property
    CONSTRAINT uq_property_hazards_property_id UNIQUE (property_id)
);

-- Add tenant_id for multi-tenant isolation
CREATE INDEX IF NOT EXISTS idx_property_hazards_tenant_id ON property_hazards(tenant_id);
CREATE INDEX IF NOT EXISTS idx_property_hazards_property_id ON property_hazards(property_id);

-- Create composite index for common queries
CREATE INDEX IF NOT EXISTS idx_property_hazards_composite_score
    ON property_hazards(tenant_id, composite_hazard_score DESC);

-- Create indexes for individual hazard scores
CREATE INDEX IF NOT EXISTS idx_property_hazards_flood_score
    ON property_hazards(tenant_id, flood_risk_score DESC)
    WHERE flood_risk_score > 0;

CREATE INDEX IF NOT EXISTS idx_property_hazards_wildfire_score
    ON property_hazards(tenant_id, wildfire_risk_score DESC)
    WHERE wildfire_risk_score > 0;

-- Enable Row Level Security
ALTER TABLE property_hazards ENABLE ROW LEVEL SECURITY;

-- Drop existing policy if exists (idempotent)
DROP POLICY IF EXISTS property_hazards_tenant_isolation ON property_hazards;

-- Create RLS policy
CREATE POLICY property_hazards_tenant_isolation ON property_hazards
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

-- Create updated_at trigger function if not exists
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Add trigger to auto-update updated_at
DROP TRIGGER IF EXISTS update_property_hazards_updated_at ON property_hazards;

CREATE TRIGGER update_property_hazards_updated_at
    BEFORE UPDATE ON property_hazards
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Grant necessary permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON property_hazards TO postgres;

-- Create materialized view for high-risk properties
CREATE MATERIALIZED VIEW IF NOT EXISTS high_risk_properties AS
SELECT
    ph.property_id,
    ph.tenant_id,
    p.address,
    p.city,
    p.state,
    p.zip,
    ph.composite_hazard_score,
    ph.flood_risk,
    ph.flood_risk_score,
    ph.wildfire_risk_level,
    ph.wildfire_risk_score,
    ph.heat_risk_score,
    ph.total_value_adjustment_pct,
    ph.total_annual_cost_impact,
    ph.assessed_at
FROM property_hazards ph
JOIN properties p ON ph.property_id = p.id
WHERE ph.composite_hazard_score >= 0.6  -- High risk threshold
ORDER BY ph.composite_hazard_score DESC;

-- Create index on materialized view
CREATE UNIQUE INDEX IF NOT EXISTS idx_high_risk_properties_property_id
    ON high_risk_properties(property_id);

CREATE INDEX IF NOT EXISTS idx_high_risk_properties_tenant_composite
    ON high_risk_properties(tenant_id, composite_hazard_score DESC);

-- Refresh materialized view (run this after initial data load)
-- REFRESH MATERIALIZED VIEW CONCURRENTLY high_risk_properties;

-- Verification queries to run after migration:
--
-- 1. Check table structure:
-- \d property_hazards
--
-- 2. Verify RLS policy:
-- SELECT tablename, policyname, permissive, roles, cmd, qual
-- FROM pg_policies
-- WHERE schemaname = 'public' AND tablename = 'property_hazards';
--
-- 3. Test tenant isolation:
-- SELECT set_tenant_context('00000000-0000-0000-0000-000000000001'::uuid);
-- SELECT COUNT(*) FROM property_hazards;
--
-- 4. Check materialized view:
-- SELECT * FROM high_risk_properties LIMIT 10;
