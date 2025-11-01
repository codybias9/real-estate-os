-- Migration: Add PostGIS extensions and enhanced spatial features
-- Version: 0010
-- Date: 2025-11-01

-- ============================================================================
-- Enable PostGIS Extension
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- Verify PostGIS version
SELECT PostGIS_full_version();

-- ============================================================================
-- Add Geography Column to Property Table
-- ============================================================================

-- Add geography column (better for distance calculations)
ALTER TABLE property
ADD COLUMN IF NOT EXISTS geom geography(Point, 4326);

-- Add geocoding confidence
ALTER TABLE property
ADD COLUMN IF NOT EXISTS geocode_confidence DECIMAL(3, 2) DEFAULT 0.0;

-- Add geocoding method
ALTER TABLE property
ADD COLUMN IF NOT EXISTS geocode_method VARCHAR(50);

-- Add canonical address
ALTER TABLE property
ADD COLUMN IF NOT EXISTS canonical_address TEXT;

-- Add address components (JSONB)
ALTER TABLE property
ADD COLUMN IF NOT EXISTS address_components JSONB;

-- ============================================================================
-- Populate Geography from Latitude/Longitude
-- ============================================================================

-- Convert existing lat/lon to geography
UPDATE property
SET geom = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)::geography
WHERE longitude IS NOT NULL
  AND latitude IS NOT NULL
  AND geom IS NULL;

-- ============================================================================
-- Create Spatial Indexes
-- ============================================================================

-- GiST index for geography (fast spatial queries)
CREATE INDEX IF NOT EXISTS idx_property_geom
ON property USING GIST(geom);

-- GIN index for address components (fast JSON queries)
CREATE INDEX IF NOT EXISTS idx_property_address_components
ON property USING GIN(address_components);

-- Composite index for tenant + spatial queries
CREATE INDEX IF NOT EXISTS idx_property_tenant_geom
ON property (tenant_id) INCLUDE (geom)
WHERE geom IS NOT NULL;

-- ============================================================================
-- Add Spatial Functions
-- ============================================================================

-- Function: Calculate distance between two properties
CREATE OR REPLACE FUNCTION property_distance(
    property_id_1 UUID,
    property_id_2 UUID
) RETURNS DECIMAL AS $$
DECLARE
    dist DECIMAL;
BEGIN
    SELECT ST_Distance(p1.geom, p2.geom)
    INTO dist
    FROM property p1, property p2
    WHERE p1.id = property_id_1
      AND p2.id = property_id_2;

    RETURN dist;
END;
$$ LANGUAGE plpgsql;

-- Function: Find properties within radius
CREATE OR REPLACE FUNCTION properties_within_radius(
    center_lat DECIMAL,
    center_lon DECIMAL,
    radius_meters INTEGER,
    filter_tenant_id UUID DEFAULT NULL
) RETURNS TABLE (
    id UUID,
    address TEXT,
    distance_meters DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.id,
        p.address,
        ST_Distance(
            p.geom,
            ST_SetSRID(ST_MakePoint(center_lon, center_lat), 4326)::geography
        ) AS distance_meters
    FROM property p
    WHERE ST_DWithin(
        p.geom,
        ST_SetSRID(ST_MakePoint(center_lon, center_lat), 4326)::geography,
        radius_meters
    )
    AND (filter_tenant_id IS NULL OR p.tenant_id = filter_tenant_id)
    ORDER BY distance_meters;
END;
$$ LANGUAGE plpgsql;

-- Function: Find properties within polygon
CREATE OR REPLACE FUNCTION properties_within_polygon(
    polygon_coords JSONB,
    filter_tenant_id UUID DEFAULT NULL
) RETURNS TABLE (
    id UUID,
    address TEXT
) AS $$
DECLARE
    polygon_geom GEOGRAPHY;
BEGIN
    -- Convert JSONB coords to geography polygon
    -- Expects: [[lon1, lat1], [lon2, lat2], ...]
    polygon_geom := ST_GeogFromText(
        'SRID=4326;POLYGON((' ||
        (SELECT string_agg(coord->1 || ' ' || coord->0, ', ')
         FROM jsonb_array_elements(polygon_coords) AS coord) ||
        '))'
    );

    RETURN QUERY
    SELECT
        p.id,
        p.address
    FROM property p
    WHERE ST_Covers(polygon_geom, p.geom)
    AND (filter_tenant_id IS NULL OR p.tenant_id = filter_tenant_id);
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Add Constraints
-- ============================================================================

-- Ensure geocode_confidence is between 0 and 1
ALTER TABLE property
ADD CONSTRAINT check_geocode_confidence
CHECK (geocode_confidence >= 0.0 AND geocode_confidence <= 1.0);

-- Ensure geom is set when lat/lon exist
CREATE OR REPLACE FUNCTION ensure_geom_consistency()
RETURNS TRIGGER AS $$
BEGIN
    -- If lat/lon are set, populate geom
    IF NEW.latitude IS NOT NULL AND NEW.longitude IS NOT NULL THEN
        NEW.geom := ST_SetSRID(ST_MakePoint(NEW.longitude, NEW.latitude), 4326)::geography;
    END IF;

    -- If geom is set, populate lat/lon
    IF NEW.geom IS NOT NULL AND (NEW.latitude IS NULL OR NEW.longitude IS NULL) THEN
        NEW.latitude := ST_Y(NEW.geom::geometry);
        NEW.longitude := ST_X(NEW.geom::geometry);
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER ensure_geom_consistency_trigger
BEFORE INSERT OR UPDATE ON property
FOR EACH ROW
EXECUTE FUNCTION ensure_geom_consistency();

-- ============================================================================
-- Add Comments
-- ============================================================================

COMMENT ON COLUMN property.geom IS 'Geographic point (SRID 4326) for spatial queries';
COMMENT ON COLUMN property.geocode_confidence IS 'Confidence score (0.0-1.0) for geocoding accuracy';
COMMENT ON COLUMN property.geocode_method IS 'Method used for geocoding (nominatim, google, manual, etc.)';
COMMENT ON COLUMN property.canonical_address IS 'Normalized address from libpostal';
COMMENT ON COLUMN property.address_components IS 'Parsed address components (house_number, road, city, state, postcode)';

COMMENT ON INDEX idx_property_geom IS 'GiST index for fast spatial queries';
COMMENT ON INDEX idx_property_address_components IS 'GIN index for fast JSON queries on address components';

COMMENT ON FUNCTION property_distance IS 'Calculate distance in meters between two properties';
COMMENT ON FUNCTION properties_within_radius IS 'Find properties within radius of a point';
COMMENT ON FUNCTION properties_within_polygon IS 'Find properties within a polygon boundary';

-- ============================================================================
-- Grant Permissions
-- ============================================================================

-- Grant execute on functions to application role
GRANT EXECUTE ON FUNCTION property_distance TO postgres;
GRANT EXECUTE ON FUNCTION properties_within_radius TO postgres;
GRANT EXECUTE ON FUNCTION properties_within_polygon TO postgres;

-- ============================================================================
-- Verification
-- ============================================================================

-- Verify PostGIS is enabled
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_extension WHERE extname = 'postgis'
    ) THEN
        RAISE EXCEPTION 'PostGIS extension not enabled';
    END IF;
END $$;

-- Verify indexes exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes WHERE indexname = 'idx_property_geom'
    ) THEN
        RAISE EXCEPTION 'Spatial index not created';
    END IF;
END $$;

-- Log completion
DO $$
BEGIN
    RAISE NOTICE 'PostGIS migration completed successfully';
END $$;
