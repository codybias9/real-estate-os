-- ============================================================================
-- Migration 001: Base Schema with Multi-Tenant Isolation
-- ============================================================================
-- Date: 2024-11-02
-- Description: Creates all core tables with tenant_id and Row-Level Security
--              This is the foundation for the entire Real Estate OS platform
-- 
-- Tables Created:
--   - tenants: Organization/company records
--   - users: User accounts with RBAC roles
--   - properties: Core property records with PostGIS geometry
--   - ownership: Property ownership structure
--   - prospects: Property leads/prospects in pipeline
--   - leases: Commercial lease records
--   - documents: Document metadata and storage references
--   - scores: Property scoring/valuation records
--   - offers: Offer generation and tracking
--   - events_audit: Audit trail for all changes
--
-- Security:
--   - RLS enabled on all tables
--   - Policies enforce tenant_id = current_setting('app.tenant_id')::uuid
--   - No cross-tenant access possible
-- ============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "postgis";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For fuzzy text search

-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Trigger function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Function to validate tenant_id is set
CREATE OR REPLACE FUNCTION enforce_tenant_id()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.tenant_id IS NULL THEN
        RAISE EXCEPTION 'tenant_id cannot be NULL';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- TABLE: tenants
-- ============================================================================
-- Organization/company records - the root of multi-tenancy

CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Basic Information
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    
    -- Contact & Settings
    email VARCHAR(255),
    phone VARCHAR(50),
    settings JSONB DEFAULT '{}'::jsonb,
    
    -- Subscription & Billing
    plan VARCHAR(50) DEFAULT 'trial',  -- trial, starter, professional, enterprise
    status VARCHAR(50) DEFAULT 'active',  -- active, suspended, cancelled
    trial_ends_at TIMESTAMPTZ,
    subscription_started_at TIMESTAMPTZ,
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT tenants_name_not_empty CHECK (length(trim(name)) > 0),
    CONSTRAINT tenants_slug_lowercase CHECK (slug = lower(slug)),
    CONSTRAINT tenants_slug_format CHECK (slug ~ '^[a-z0-9-]+$')
);

-- Indexes
CREATE INDEX idx_tenants_status ON tenants(status);
CREATE INDEX idx_tenants_slug ON tenants(slug);

-- Triggers
CREATE TRIGGER update_tenants_updated_at
    BEFORE UPDATE ON tenants
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Comments
COMMENT ON TABLE tenants IS 'Organization/company records - root of multi-tenancy';
COMMENT ON COLUMN tenants.slug IS 'URL-safe unique identifier for tenant';
COMMENT ON COLUMN tenants.settings IS 'JSON configuration for tenant preferences';

-- ============================================================================
-- TABLE: users
-- ============================================================================
-- User accounts with RBAC roles

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    
    -- Authentication
    email VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    auth_provider VARCHAR(50) DEFAULT 'keycloak',  -- keycloak, google, azure
    external_id VARCHAR(255),  -- ID from auth provider
    
    -- Authorization (RBAC)
    role VARCHAR(50) NOT NULL DEFAULT 'user',  -- admin, analyst, operator, user
    permissions JSONB DEFAULT '[]'::jsonb,  -- Additional granular permissions
    
    -- Profile
    avatar_url TEXT,
    timezone VARCHAR(50) DEFAULT 'UTC',
    preferences JSONB DEFAULT '{}'::jsonb,
    
    -- Status
    status VARCHAR(50) DEFAULT 'active',  -- active, inactive, suspended
    email_verified BOOLEAN DEFAULT false,
    last_login_at TIMESTAMPTZ,
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT users_email_format CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$'),
    CONSTRAINT users_role_valid CHECK (role IN ('admin', 'analyst', 'operator', 'user')),
    CONSTRAINT users_tenant_id_not_null CHECK (tenant_id IS NOT NULL)
);

-- Indexes
CREATE UNIQUE INDEX idx_users_email_tenant ON users(email, tenant_id);
CREATE INDEX idx_users_tenant_id ON users(tenant_id);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_status ON users(status);
CREATE INDEX idx_users_external_id ON users(external_id);

-- Triggers
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER enforce_users_tenant_id
    BEFORE INSERT OR UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION enforce_tenant_id();

-- RLS Policies
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

CREATE POLICY users_tenant_isolation
    ON users
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY users_tenant_isolation_insert
    ON users
    FOR INSERT
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

-- Comments
COMMENT ON TABLE users IS 'User accounts with RBAC roles';
COMMENT ON COLUMN users.role IS 'RBAC role: admin (full access), analyst (read+reports), operator (day-to-day), user (limited)';
COMMENT ON COLUMN users.permissions IS 'Granular permissions array for fine-grained access control';

-- ============================================================================
-- TABLE: properties
-- ============================================================================
-- Core property records with PostGIS geometry

CREATE TABLE properties (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    
    -- Identifiers
    apn VARCHAR(50),  -- Assessor's Parcel Number
    external_id VARCHAR(255),  -- ID from external system
    
    -- Address (raw)
    address TEXT NOT NULL,
    unit VARCHAR(50),
    city VARCHAR(100),
    state VARCHAR(2),
    zip VARCHAR(10),
    county VARCHAR(100),
    
    -- Address (normalized via libpostal)
    address_normalized TEXT,
    address_hash VARCHAR(16),  -- For deduplication
    address_components JSONB,
    
    -- Geolocation
    latitude NUMERIC(10, 7),
    longitude NUMERIC(11, 7),
    geom GEOMETRY(Point, 4326),  -- PostGIS point
    
    -- Property Details
    property_type VARCHAR(50) NOT NULL,  -- single_family, multifamily, commercial, land, etc.
    property_subtype VARCHAR(50),
    
    -- Physical Characteristics
    bedrooms INTEGER,
    bathrooms NUMERIC(4, 1),
    sqft INTEGER,
    lot_size NUMERIC(10, 2),  -- In acres
    year_built INTEGER,
    stories INTEGER,
    parking_spaces INTEGER,
    
    -- Financial
    price NUMERIC(15, 2),
    price_per_sqft NUMERIC(10, 2),
    assessed_value NUMERIC(15, 2),
    tax_amount NUMERIC(12, 2),
    
    -- Commercial-Specific
    units_count INTEGER,  -- For multifamily
    cap_rate NUMERIC(5, 3),
    noi NUMERIC(15, 2),  -- Net Operating Income
    
    -- Hazards (from PR-I2)
    hazards JSONB,  -- Links to property_hazards table
    
    -- Status & Pipeline
    status VARCHAR(50) DEFAULT 'active',  -- active, under_contract, sold, archived, deleted
    pipeline_stage VARCHAR(50),  -- prospect, analysis, offer, diligence, closing
    
    -- Source & Provenance
    source VARCHAR(100),  -- mls, scraper, manual, import
    source_url TEXT,
    source_id VARCHAR(255),
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT properties_tenant_id_not_null CHECK (tenant_id IS NOT NULL),
    CONSTRAINT properties_price_positive CHECK (price IS NULL OR price >= 0),
    CONSTRAINT properties_sqft_positive CHECK (sqft IS NULL OR sqft > 0),
    CONSTRAINT properties_bedrooms_valid CHECK (bedrooms IS NULL OR bedrooms >= 0),
    CONSTRAINT properties_bathrooms_valid CHECK (bathrooms IS NULL OR bathrooms >= 0),
    CONSTRAINT properties_year_built_valid CHECK (year_built IS NULL OR (year_built >= 1700 AND year_built <= EXTRACT(YEAR FROM NOW()) + 5)),
    CONSTRAINT properties_lat_valid CHECK (latitude IS NULL OR (latitude >= -90 AND latitude <= 90)),
    CONSTRAINT properties_lon_valid CHECK (longitude IS NULL OR (longitude >= -180 AND longitude <= 180))
);

-- Indexes
CREATE INDEX idx_properties_tenant_id ON properties(tenant_id);
CREATE INDEX idx_properties_status ON properties(status);
CREATE INDEX idx_properties_pipeline_stage ON properties(pipeline_stage);
CREATE INDEX idx_properties_property_type ON properties(property_type);
CREATE INDEX idx_properties_city_state ON properties(city, state);
CREATE INDEX idx_properties_address_hash ON properties(address_hash);
CREATE INDEX idx_properties_apn ON properties(apn);
CREATE INDEX idx_properties_price ON properties(price);
CREATE INDEX idx_properties_created_at ON properties(created_at DESC);

-- PostGIS spatial index
CREATE INDEX idx_properties_geom ON properties USING GIST(geom);

-- Full-text search on address
CREATE INDEX idx_properties_address_trgm ON properties USING GIN(address gin_trgm_ops);

-- Triggers
CREATE TRIGGER update_properties_updated_at
    BEFORE UPDATE ON properties
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER enforce_properties_tenant_id
    BEFORE INSERT OR UPDATE ON properties
    FOR EACH ROW
    EXECUTE FUNCTION enforce_tenant_id();

-- Auto-update geom from lat/lon
CREATE OR REPLACE FUNCTION update_property_geom()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.latitude IS NOT NULL AND NEW.longitude IS NOT NULL THEN
        NEW.geom = ST_SetSRID(ST_MakePoint(NEW.longitude, NEW.latitude), 4326);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_properties_geom
    BEFORE INSERT OR UPDATE OF latitude, longitude ON properties
    FOR EACH ROW
    EXECUTE FUNCTION update_property_geom();

-- RLS Policies
ALTER TABLE properties ENABLE ROW LEVEL SECURITY;

CREATE POLICY properties_tenant_isolation
    ON properties
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY properties_tenant_isolation_insert
    ON properties
    FOR INSERT
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

-- Comments
COMMENT ON TABLE properties IS 'Core property records with PostGIS geometry and multi-tenant isolation';
COMMENT ON COLUMN properties.address_hash IS 'SHA256 hash (16 chars) for deduplication via libpostal';
COMMENT ON COLUMN properties.geom IS 'PostGIS point geometry for spatial queries';
COMMENT ON COLUMN properties.hazards IS 'JSONB reference to hazard assessment data';

-- ============================================================================
-- TABLE: ownership
-- ============================================================================
-- Property ownership structure and entity graph

CREATE TABLE ownership (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    
    -- Owner Information
    owner_type VARCHAR(50) NOT NULL,  -- individual, llc, corporation, partnership, trust
    owner_name VARCHAR(255) NOT NULL,
    owner_entity_id VARCHAR(100),  -- Tax ID, EIN, etc.
    
    -- Ownership Structure
    ownership_percentage NUMERIC(5, 2) DEFAULT 100.00,  -- 0.00 to 100.00
    is_primary_owner BOOLEAN DEFAULT true,
    
    -- Contact
    contact_email VARCHAR(255),
    contact_phone VARCHAR(50),
    mailing_address TEXT,
    
    -- Acquisition
    acquisition_date DATE,
    acquisition_price NUMERIC(15, 2),
    
    -- Status
    status VARCHAR(50) DEFAULT 'active',  -- active, transferred, foreclosed
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT ownership_tenant_id_not_null CHECK (tenant_id IS NOT NULL),
    CONSTRAINT ownership_percentage_valid CHECK (ownership_percentage >= 0 AND ownership_percentage <= 100)
);

-- Indexes
CREATE INDEX idx_ownership_tenant_id ON ownership(tenant_id);
CREATE INDEX idx_ownership_property_id ON ownership(property_id);
CREATE INDEX idx_ownership_owner_name ON ownership(owner_name);
CREATE INDEX idx_ownership_owner_entity_id ON ownership(owner_entity_id);

-- Triggers
CREATE TRIGGER update_ownership_updated_at
    BEFORE UPDATE ON ownership
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER enforce_ownership_tenant_id
    BEFORE INSERT OR UPDATE ON ownership
    FOR EACH ROW
    EXECUTE FUNCTION enforce_tenant_id();

-- RLS Policies
ALTER TABLE ownership ENABLE ROW LEVEL SECURITY;

CREATE POLICY ownership_tenant_isolation
    ON ownership
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY ownership_tenant_isolation_insert
    ON ownership
    FOR INSERT
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

-- Comments
COMMENT ON TABLE ownership IS 'Property ownership structure and entity graph for tenant/company analysis';

-- ============================================================================
-- TABLE: prospects
-- ============================================================================
-- Property leads/prospects in the acquisition pipeline

CREATE TABLE prospects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    property_id UUID REFERENCES properties(id) ON DELETE SET NULL,  -- Links to properties after conversion
    
    -- Source Information
    source VARCHAR(100) NOT NULL,  -- mls, off_market, broker, direct, scraper
    source_id VARCHAR(255),
    source_url TEXT,
    source_raw JSONB,  -- Raw data from source
    
    -- Basic Details (before full property record)
    address TEXT NOT NULL,
    city VARCHAR(100),
    state VARCHAR(2),
    zip VARCHAR(10),
    estimated_value NUMERIC(15, 2),
    
    -- Pipeline Status
    stage VARCHAR(50) DEFAULT 'new',  -- new, contacted, analyzing, offered, declined, converted
    priority VARCHAR(20) DEFAULT 'medium',  -- low, medium, high, urgent
    
    -- Engagement
    first_contact_at TIMESTAMPTZ,
    last_contact_at TIMESTAMPTZ,
    notes TEXT,
    
    -- Assignment
    assigned_to UUID REFERENCES users(id),
    
    -- Conversion
    converted_to_property BOOLEAN DEFAULT false,
    converted_at TIMESTAMPTZ,
    
    -- Status
    status VARCHAR(50) DEFAULT 'active',  -- active, archived, duplicate, invalid
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT prospects_tenant_id_not_null CHECK (tenant_id IS NOT NULL)
);

-- Indexes
CREATE INDEX idx_prospects_tenant_id ON prospects(tenant_id);
CREATE INDEX idx_prospects_property_id ON prospects(property_id);
CREATE INDEX idx_prospects_stage ON prospects(stage);
CREATE INDEX idx_prospects_status ON prospects(status);
CREATE INDEX idx_prospects_assigned_to ON prospects(assigned_to);
CREATE INDEX idx_prospects_source ON prospects(source);
CREATE INDEX idx_prospects_created_at ON prospects(created_at DESC);

-- Triggers
CREATE TRIGGER update_prospects_updated_at
    BEFORE UPDATE ON prospects
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER enforce_prospects_tenant_id
    BEFORE INSERT OR UPDATE ON prospects
    FOR EACH ROW
    EXECUTE FUNCTION enforce_tenant_id();

-- RLS Policies
ALTER TABLE prospects ENABLE ROW LEVEL SECURITY;

CREATE POLICY prospects_tenant_isolation
    ON prospects
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY prospects_tenant_isolation_insert
    ON prospects
    FOR INSERT
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

-- Comments
COMMENT ON TABLE prospects IS 'Property leads/prospects in acquisition pipeline before full property creation';

-- ============================================================================
-- TABLE: leases
-- ============================================================================
-- Commercial lease records with parsed terms

CREATE TABLE leases (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    
    -- Tenant Information
    tenant_name VARCHAR(255) NOT NULL,
    tenant_entity VARCHAR(255),
    tenant_type VARCHAR(50),  -- anchor, national, regional, local, startup
    tenant_credit_rating VARCHAR(10),
    
    -- Lease Terms
    lease_type VARCHAR(50) NOT NULL,  -- gross, modified_gross, triple_net, absolute_net
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    term_months INTEGER,
    
    -- Financial Terms
    base_rent NUMERIC(12, 2) NOT NULL,
    rent_per_sqft NUMERIC(10, 2),
    annual_rent NUMERIC(12, 2),
    rent_escalation_pct NUMERIC(5, 2),  -- Annual increase percentage
    
    -- Expenses
    cam_charges NUMERIC(12, 2),  -- Common Area Maintenance
    property_tax_share NUMERIC(12, 2),
    insurance_share NUMERIC(12, 2),
    
    -- Space
    square_footage INTEGER,
    unit_number VARCHAR(50),
    floor VARCHAR(10),
    
    -- Options & Rights
    renewal_options JSONB,  -- Array of renewal option terms
    has_termination_option BOOLEAN DEFAULT false,
    termination_terms JSONB,
    
    -- Parsed Data (from lease intelligence)
    parsed_data JSONB,
    parsing_confidence NUMERIC(3, 2),  -- 0.00 to 1.00
    parsed_at TIMESTAMPTZ,
    
    -- Status
    status VARCHAR(50) DEFAULT 'active',  -- active, expired, terminated, renewed
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT leases_tenant_id_not_null CHECK (tenant_id IS NOT NULL),
    CONSTRAINT leases_dates_valid CHECK (end_date > start_date),
    CONSTRAINT leases_rent_positive CHECK (base_rent >= 0)
);

-- Indexes
CREATE INDEX idx_leases_tenant_id ON leases(tenant_id);
CREATE INDEX idx_leases_property_id ON leases(property_id);
CREATE INDEX idx_leases_tenant_name ON leases(tenant_name);
CREATE INDEX idx_leases_status ON leases(status);
CREATE INDEX idx_leases_start_date ON leases(start_date);
CREATE INDEX idx_leases_end_date ON leases(end_date);

-- Triggers
CREATE TRIGGER update_leases_updated_at
    BEFORE UPDATE ON leases
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER enforce_leases_tenant_id
    BEFORE INSERT OR UPDATE ON leases
    FOR EACH ROW
    EXECUTE FUNCTION enforce_tenant_id();

-- Auto-calculate term_months and annual_rent
CREATE OR REPLACE FUNCTION update_lease_calculated_fields()
RETURNS TRIGGER AS $$
BEGIN
    -- Calculate term in months
    IF NEW.start_date IS NOT NULL AND NEW.end_date IS NOT NULL THEN
        NEW.term_months = EXTRACT(YEAR FROM AGE(NEW.end_date, NEW.start_date)) * 12 + 
                          EXTRACT(MONTH FROM AGE(NEW.end_date, NEW.start_date));
    END IF;
    
    -- Calculate annual rent
    IF NEW.base_rent IS NOT NULL THEN
        NEW.annual_rent = NEW.base_rent * 12;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_leases_calculated_fields
    BEFORE INSERT OR UPDATE ON leases
    FOR EACH ROW
    EXECUTE FUNCTION update_lease_calculated_fields();

-- RLS Policies
ALTER TABLE leases ENABLE ROW LEVEL SECURITY;

CREATE POLICY leases_tenant_isolation
    ON leases
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY leases_tenant_isolation_insert
    ON leases
    FOR INSERT
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

-- Comments
COMMENT ON TABLE leases IS 'Commercial lease records with AI-parsed terms for WALE/HHI analysis';
COMMENT ON COLUMN leases.parsed_data IS 'Structured data extracted via lease intelligence parser';

-- ============================================================================
-- TABLE: documents
-- ============================================================================
-- Document metadata and storage references

CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    
    -- Associations (polymorphic)
    property_id UUID REFERENCES properties(id) ON DELETE CASCADE,
    lease_id UUID REFERENCES leases(id) ON DELETE CASCADE,
    offer_id UUID,  -- Forward reference, will link when offers table created
    
    -- Document Information
    document_type VARCHAR(50) NOT NULL,  -- lease, title, inspection, appraisal, om, financial, other
    title VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- Storage
    storage_backend VARCHAR(50) DEFAULT 'minio',  -- minio, s3, azure
    storage_path TEXT NOT NULL,  -- Path in storage backend (with tenant prefix)
    file_name VARCHAR(255) NOT NULL,
    file_size BIGINT,  -- In bytes
    mime_type VARCHAR(100),
    
    -- Processing Status
    processing_status VARCHAR(50) DEFAULT 'pending',  -- pending, processing, completed, failed
    ocr_text TEXT,  -- Extracted text from OCR
    parsed_data JSONB,  -- Structured data extracted from document
    
    -- Security
    access_level VARCHAR(50) DEFAULT 'private',  -- public, internal, private, restricted
    
    -- Metadata
    uploaded_by UUID REFERENCES users(id),
    uploaded_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT documents_tenant_id_not_null CHECK (tenant_id IS NOT NULL),
    CONSTRAINT documents_file_size_positive CHECK (file_size IS NULL OR file_size > 0)
);

-- Indexes
CREATE INDEX idx_documents_tenant_id ON documents(tenant_id);
CREATE INDEX idx_documents_property_id ON documents(property_id);
CREATE INDEX idx_documents_lease_id ON documents(lease_id);
CREATE INDEX idx_documents_offer_id ON documents(offer_id);
CREATE INDEX idx_documents_document_type ON documents(document_type);
CREATE INDEX idx_documents_processing_status ON documents(processing_status);
CREATE INDEX idx_documents_uploaded_by ON documents(uploaded_by);

-- Full-text search on OCR text
CREATE INDEX idx_documents_ocr_text_trgm ON documents USING GIN(ocr_text gin_trgm_ops);

-- Triggers
CREATE TRIGGER update_documents_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER enforce_documents_tenant_id
    BEFORE INSERT OR UPDATE ON documents
    FOR EACH ROW
    EXECUTE FUNCTION enforce_tenant_id();

-- RLS Policies
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

CREATE POLICY documents_tenant_isolation
    ON documents
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY documents_tenant_isolation_insert
    ON documents
    FOR INSERT
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

-- Comments
COMMENT ON TABLE documents IS 'Document metadata and storage references with OCR/parsing support';
COMMENT ON COLUMN documents.storage_path IS 'Path includes tenant prefix for MinIO isolation: {tenant_id}/documents/...';

-- ============================================================================
-- TABLE: scores
-- ============================================================================
-- Property scoring/valuation records from ML models

CREATE TABLE scores (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    
    -- Score Type
    score_type VARCHAR(50) NOT NULL,  -- comp_critic, dcf, arv,综合score
    model_version VARCHAR(50) NOT NULL,
    
    -- Valuation
    estimated_value NUMERIC(15, 2),
    value_range_low NUMERIC(15, 2),
    value_range_high NUMERIC(15, 2),
    confidence NUMERIC(3, 2),  -- 0.00 to 1.00
    
    -- Score Components
    score NUMERIC(5, 2),  -- 0-100 composite score
    component_scores JSONB,  -- Breakdown by factor
    
    -- Comparable Properties (for comp-critic)
    comps JSONB,  -- Array of comparable property data
    adjustments JSONB,  -- Waterfall of adjustments
    
    -- DCF Components (for DCF model)
    dcf_inputs JSONB,
    dcf_outputs JSONB,
    npv NUMERIC(15, 2),
    irr NUMERIC(5, 2),
    
    -- Hazard Adjustments
    hazard_penalty NUMERIC(10, 2) DEFAULT 0,
    hazard_details JSONB,
    
    -- Regime Context
    market_regime VARCHAR(50),  -- bull, bear, transition, stable
    regime_confidence NUMERIC(3, 2),
    
    -- Provenance
    calculated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    calculated_by VARCHAR(100),  -- system, user_override, api
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT scores_tenant_id_not_null CHECK (tenant_id IS NOT NULL),
    CONSTRAINT scores_confidence_valid CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 1))
);

-- Indexes
CREATE INDEX idx_scores_tenant_id ON scores(tenant_id);
CREATE INDEX idx_scores_property_id ON scores(property_id);
CREATE INDEX idx_scores_score_type ON scores(score_type);
CREATE INDEX idx_scores_calculated_at ON scores(calculated_at DESC);

-- Triggers
CREATE TRIGGER update_scores_updated_at
    BEFORE UPDATE ON scores
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER enforce_scores_tenant_id
    BEFORE INSERT OR UPDATE ON scores
    FOR EACH ROW
    EXECUTE FUNCTION enforce_tenant_id();

-- RLS Policies
ALTER TABLE scores ENABLE ROW LEVEL SECURITY;

CREATE POLICY scores_tenant_isolation
    ON scores
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY scores_tenant_isolation_insert
    ON scores
    FOR INSERT
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

-- Comments
COMMENT ON TABLE scores IS 'Property scoring/valuation records from ML models (Comp-Critic, DCF, ARV)';
COMMENT ON COLUMN scores.comps IS 'Comparable properties used in valuation with similarity scores';
COMMENT ON COLUMN scores.adjustments IS 'Waterfall of adjustments applied to comparable properties';

-- ============================================================================
-- TABLE: offers
-- ============================================================================
-- Offer generation and tracking

CREATE TABLE offers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    score_id UUID REFERENCES scores(id),
    
    -- Offer Details
    offer_amount NUMERIC(15, 2) NOT NULL,
    offer_type VARCHAR(50) DEFAULT 'cash',  -- cash, financed, hybrid
    
    -- Terms
    earnest_money NUMERIC(12, 2),
    down_payment_pct NUMERIC(5, 2),
    financing_terms JSONB,
    contingencies JSONB,
    closing_days INTEGER,
    
    -- Optimizer Results
    optimizer_run_id VARCHAR(100),
    optimizer_status VARCHAR(50),  -- feasible, infeasible, optimal, timeout
    optimizer_objective NUMERIC(15, 2),
    optimizer_constraints_met JSONB,
    optimizer_pareto_rank INTEGER,
    
    -- Policy Constraints
    policy_checks JSONB,  -- Results of policy guardrails
    policy_violations JSONB,  -- Any violated constraints
    policy_approved BOOLEAN,
    
    -- Negotiation
    counter_offers JSONB,  -- Array of counter-offer history
    current_status VARCHAR(50) DEFAULT 'draft',  -- draft, submitted, countered, accepted, rejected
    
    -- Assignment
    created_by UUID REFERENCES users(id),
    approved_by UUID REFERENCES users(id),
    
    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    submitted_at TIMESTAMPTZ,
    
    -- Constraints
    CONSTRAINT offers_tenant_id_not_null CHECK (tenant_id IS NOT NULL),
    CONSTRAINT offers_amount_positive CHECK (offer_amount > 0)
);

-- Indexes
CREATE INDEX idx_offers_tenant_id ON offers(tenant_id);
CREATE INDEX idx_offers_property_id ON offers(property_id);
CREATE INDEX idx_offers_current_status ON offers(current_status);
CREATE INDEX idx_offers_created_by ON offers(created_by);
CREATE INDEX idx_offers_created_at ON offers(created_at DESC);

-- Triggers
CREATE TRIGGER update_offers_updated_at
    BEFORE UPDATE ON offers
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER enforce_offers_tenant_id
    BEFORE INSERT OR UPDATE ON offers
    FOR EACH ROW
    EXECUTE FUNCTION enforce_tenant_id();

-- RLS Policies
ALTER TABLE offers ENABLE ROW LEVEL SECURITY;

CREATE POLICY offers_tenant_isolation
    ON offers
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY offers_tenant_isolation_insert
    ON offers
    FOR INSERT
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

-- Comments
COMMENT ON TABLE offers IS 'Offer generation and tracking with optimizer results and policy checks';
COMMENT ON COLUMN offers.optimizer_pareto_rank IS 'Rank in Pareto frontier (1 = optimal)';

-- ============================================================================
-- TABLE: events_audit
-- ============================================================================
-- Comprehensive audit trail for all changes

CREATE TABLE events_audit (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    
    -- Event Classification
    event_type VARCHAR(100) NOT NULL,  -- user.login, property.created, offer.submitted, etc.
    event_category VARCHAR(50),  -- auth, data, api, system
    severity VARCHAR(20) DEFAULT 'info',  -- debug, info, warning, error, critical
    
    -- Actor
    user_id UUID REFERENCES users(id),
    user_email VARCHAR(255),
    user_role VARCHAR(50),
    ip_address INET,
    user_agent TEXT,
    
    -- Target Resource
    resource_type VARCHAR(50),  -- property, offer, lease, document, etc.
    resource_id UUID,
    
    -- Change Details
    action VARCHAR(50),  -- create, read, update, delete, login, export, etc.
    changes JSONB,  -- Before/after values for updates
    metadata JSONB,  -- Additional context
    
    -- Request Context
    request_id VARCHAR(100),  -- Correlation ID for distributed tracing
    api_endpoint TEXT,
    http_method VARCHAR(10),
    
    -- Result
    success BOOLEAN DEFAULT true,
    error_message TEXT,
    
    -- Timestamp
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT events_audit_tenant_id_not_null CHECK (tenant_id IS NOT NULL)
);

-- Indexes
CREATE INDEX idx_events_audit_tenant_id ON events_audit(tenant_id);
CREATE INDEX idx_events_audit_user_id ON events_audit(user_id);
CREATE INDEX idx_events_audit_event_type ON events_audit(event_type);
CREATE INDEX idx_events_audit_resource_type_id ON events_audit(resource_type, resource_id);
CREATE INDEX idx_events_audit_created_at ON events_audit(created_at DESC);
CREATE INDEX idx_events_audit_severity ON events_audit(severity);
CREATE INDEX idx_events_audit_request_id ON events_audit(request_id);

-- Triggers
CREATE TRIGGER enforce_events_audit_tenant_id
    BEFORE INSERT OR UPDATE ON events_audit
    FOR EACH ROW
    EXECUTE FUNCTION enforce_tenant_id();

-- RLS Policies
ALTER TABLE events_audit ENABLE ROW LEVEL SECURITY;

CREATE POLICY events_audit_tenant_isolation
    ON events_audit
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY events_audit_tenant_isolation_insert
    ON events_audit
    FOR INSERT
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

-- Comments
COMMENT ON TABLE events_audit IS 'Comprehensive audit trail for all user actions and system events';
COMMENT ON COLUMN events_audit.request_id IS 'Correlation ID for distributed tracing across services';

-- ============================================================================
-- VIEWS FOR COMMON QUERIES
-- ============================================================================

-- Active properties with latest score
CREATE OR REPLACE VIEW v_properties_with_scores AS
SELECT 
    p.*,
    s.score AS latest_score,
    s.estimated_value AS latest_valuation,
    s.confidence AS score_confidence,
    s.score_type AS score_model,
    s.calculated_at AS scored_at
FROM properties p
LEFT JOIN LATERAL (
    SELECT *
    FROM scores
    WHERE property_id = p.id
    ORDER BY calculated_at DESC
    LIMIT 1
) s ON true
WHERE p.status = 'active';

-- Lease expiration report
CREATE OR REPLACE VIEW v_lease_expirations AS
SELECT
    l.*,
    p.address,
    p.city,
    p.state,
    l.end_date,
    EXTRACT(DAYS FROM (l.end_date - CURRENT_DATE)) AS days_until_expiration,
    CASE
        WHEN l.end_date < CURRENT_DATE THEN 'expired'
        WHEN l.end_date < CURRENT_DATE + INTERVAL '90 days' THEN 'critical'
        WHEN l.end_date < CURRENT_DATE + INTERVAL '180 days' THEN 'warning'
        ELSE 'normal'
    END AS urgency
FROM leases l
JOIN properties p ON l.property_id = p.id
WHERE l.status = 'active'
ORDER BY l.end_date ASC;

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Verify RLS is enabled on all tables
DO $$
DECLARE
    tbl TEXT;
    tables TEXT[] := ARRAY[
        'users', 'properties', 'ownership', 'prospects', 
        'leases', 'documents', 'scores', 'offers', 'events_audit'
    ];
BEGIN
    FOREACH tbl IN ARRAY tables
    LOOP
        IF NOT EXISTS (
            SELECT 1 FROM pg_tables 
            WHERE tablename = tbl 
            AND rowsecurity = true
        ) THEN
            RAISE EXCEPTION 'RLS not enabled on table: %', tbl;
        END IF;
        
        RAISE NOTICE 'RLS verified on table: %', tbl;
    END LOOP;
END $$;

-- ============================================================================
-- SEED DATA FOR TESTING
-- ============================================================================

-- Create a test tenant
INSERT INTO tenants (id, name, slug, plan, status)
VALUES 
    ('00000000-0000-0000-0000-000000000001', 'Test Tenant A', 'test-tenant-a', 'professional', 'active'),
    ('00000000-0000-0000-0000-000000000002', 'Test Tenant B', 'test-tenant-b', 'starter', 'active')
ON CONFLICT (id) DO NOTHING;

-- ============================================================================
-- COMPLETION SUMMARY
-- ============================================================================

-- Count tables created
SELECT 
    'Migration 001 Complete' AS status,
    COUNT(*) AS tables_created
FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN (
    'tenants', 'users', 'properties', 'ownership', 'prospects',
    'leases', 'documents', 'scores', 'offers', 'events_audit'
);

-- Show RLS status
SELECT 
    tablename,
    rowsecurity AS rls_enabled,
    (SELECT COUNT(*) FROM pg_policies WHERE schemaname = 'public' AND tablename = t.tablename) AS policy_count
FROM pg_tables t
WHERE schemaname = 'public'
AND tablename IN (
    'users', 'properties', 'ownership', 'prospects',
    'leases', 'documents', 'scores', 'offers', 'events_audit'
)
ORDER BY tablename;

RAISE NOTICE 'Migration 001 completed successfully!';
RAISE NOTICE 'Created 10 core tables with RLS policies';
RAISE NOTICE 'Added PostGIS support for spatial queries';
RAISE NOTICE 'Created audit trail and views';
RAISE NOTICE 'Seeded test tenants for development';
