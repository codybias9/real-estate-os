-- Migration: Enable Row Level Security for Multi-Tenant Isolation
-- Date: 2024-11-02
-- Description: Adds tenant_id columns and RLS policies to all core tables

-- Add tenant_id column to core tables if not exists
ALTER TABLE IF EXISTS properties
  ADD COLUMN IF NOT EXISTS tenant_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000';

ALTER TABLE IF EXISTS ownership
  ADD COLUMN IF NOT EXISTS tenant_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000';

ALTER TABLE IF EXISTS prospects
  ADD COLUMN IF NOT EXISTS tenant_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000';

ALTER TABLE IF EXISTS leases
  ADD COLUMN IF NOT EXISTS tenant_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000';

ALTER TABLE IF EXISTS offers
  ADD COLUMN IF NOT EXISTS tenant_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000';

ALTER TABLE IF EXISTS documents
  ADD COLUMN IF NOT EXISTS tenant_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000';

ALTER TABLE IF EXISTS outreach_log
  ADD COLUMN IF NOT EXISTS tenant_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000';

-- Create indexes on tenant_id for performance
CREATE INDEX IF NOT EXISTS idx_properties_tenant_id ON properties(tenant_id);
CREATE INDEX IF NOT EXISTS idx_ownership_tenant_id ON ownership(tenant_id);
CREATE INDEX IF NOT EXISTS idx_prospects_tenant_id ON prospects(tenant_id);
CREATE INDEX IF NOT EXISTS idx_leases_tenant_id ON leases(tenant_id);
CREATE INDEX IF NOT EXISTS idx_offers_tenant_id ON offers(tenant_id);
CREATE INDEX IF NOT EXISTS idx_documents_tenant_id ON documents(tenant_id);
CREATE INDEX IF NOT EXISTS idx_outreach_log_tenant_id ON outreach_log(tenant_id);

-- Enable Row Level Security
ALTER TABLE properties ENABLE ROW LEVEL SECURITY;
ALTER TABLE ownership ENABLE ROW LEVEL SECURITY;
ALTER TABLE prospects ENABLE ROW LEVEL SECURITY;
ALTER TABLE leases ENABLE ROW LEVEL SECURITY;
ALTER TABLE offers ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE outreach_log ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist (idempotent)
DROP POLICY IF EXISTS properties_tenant_isolation ON properties;
DROP POLICY IF EXISTS ownership_tenant_isolation ON ownership;
DROP POLICY IF EXISTS prospects_tenant_isolation ON prospects;
DROP POLICY IF EXISTS leases_tenant_isolation ON leases;
DROP POLICY IF EXISTS offers_tenant_isolation ON offers;
DROP POLICY IF EXISTS documents_tenant_isolation ON documents;
DROP POLICY IF EXISTS outreach_log_tenant_isolation ON outreach_log;

-- Create RLS policies
-- These policies filter rows based on app.tenant_id session variable
CREATE POLICY properties_tenant_isolation ON properties
  USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY ownership_tenant_isolation ON ownership
  USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY prospects_tenant_isolation ON prospects
  USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY leases_tenant_isolation ON leases
  USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY offers_tenant_isolation ON offers
  USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY documents_tenant_isolation ON documents
  USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY outreach_log_tenant_isolation ON outreach_log
  USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

-- Grant necessary permissions
-- Ensure application role can set session variables
GRANT USAGE ON SCHEMA public TO postgres;

-- Add helper function to set tenant context
CREATE OR REPLACE FUNCTION set_tenant_context(p_tenant_id UUID)
RETURNS void AS $$
BEGIN
  PERFORM set_config('app.tenant_id', p_tenant_id::text, false);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Add helper function to get current tenant context
CREATE OR REPLACE FUNCTION get_tenant_context()
RETURNS UUID AS $$
BEGIN
  RETURN current_setting('app.tenant_id', true)::uuid;
EXCEPTION
  WHEN OTHERS THEN
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Verification: Show all RLS policies
-- Run this after migration to verify:
-- SELECT tablename, policyname, permissive, roles, cmd, qual
-- FROM pg_policies
-- WHERE schemaname = 'public';
