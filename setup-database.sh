#!/bin/bash
# Setup database tables in the running container
# Run from: /mnt/c/Users/codyb/real-estate-os

echo "================================================"
echo "Real Estate OS - Database Setup"
echo "================================================"
echo ""

echo "Creating database tables..."

# The db-1 container uses airflow as the default user
docker exec -i real-estate-os-db-1 psql -U airflow -d realestate << 'EOF'
-- Drop tables if they exist (for clean setup)
DROP TABLE IF EXISTS outreach_logs CASCADE;
DROP TABLE IF EXISTS campaigns CASCADE;
DROP TABLE IF EXISTS generated_documents CASCADE;
DROP TABLE IF EXISTS property_scores CASCADE;
DROP TABLE IF EXISTS property_enrichment CASCADE;
DROP TABLE IF EXISTS properties CASCADE;

-- Create properties table
CREATE TABLE properties (
    id SERIAL PRIMARY KEY,
    source VARCHAR(255),
    address VARCHAR(500) NOT NULL,
    city VARCHAR(100),
    state VARCHAR(50),
    zip_code VARCHAR(20),
    price DECIMAL(15, 2),
    bedrooms INTEGER,
    bathrooms DECIMAL(3, 1),
    sqft INTEGER,
    lot_size DECIMAL(10, 2),
    year_built INTEGER,
    property_type VARCHAR(50),
    description TEXT,
    url TEXT,
    features TEXT[],
    images TEXT[],
    status VARCHAR(50) DEFAULT 'new',
    extra_data JSON DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create property_enrichment table
CREATE TABLE property_enrichment (
    id SERIAL PRIMARY KEY,
    property_id INTEGER REFERENCES properties(id) ON DELETE CASCADE,
    tax_assessment_value DECIMAL(15, 2),
    annual_tax_amount DECIMAL(15, 2),
    last_sale_date DATE,
    last_sale_price DECIMAL(15, 2),
    owner_name VARCHAR(500),
    owner_type VARCHAR(100),
    ownership_length_years INTEGER,
    zoning VARCHAR(100),
    school_district VARCHAR(200),
    school_rating INTEGER,
    walkability_score INTEGER,
    crime_rate VARCHAR(50),
    median_income DECIMAL(15, 2),
    population_growth DECIMAL(5, 2),
    unemployment_rate DECIMAL(5, 2),
    median_home_price DECIMAL(15, 2),
    median_rent DECIMAL(15, 2),
    vacancy_rate DECIMAL(5, 2),
    days_on_market_avg INTEGER,
    enrichment_metadata JSON DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create property_scores table
CREATE TABLE property_scores (
    id SERIAL PRIMARY KEY,
    property_id INTEGER REFERENCES properties(id) ON DELETE CASCADE,
    total_score INTEGER NOT NULL,
    score_breakdown JSON DEFAULT '{}',
    features JSON DEFAULT '{}',
    recommendation VARCHAR(50),
    recommendation_reason TEXT,
    risk_level VARCHAR(50),
    risk_factors TEXT[],
    comparable_properties JSON DEFAULT '{}',
    scoring_metadata JSON DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create generated_documents table
CREATE TABLE generated_documents (
    id SERIAL PRIMARY KEY,
    property_id INTEGER REFERENCES properties(id) ON DELETE CASCADE,
    document_type VARCHAR(100),
    file_path TEXT,
    file_size INTEGER,
    status VARCHAR(50) DEFAULT 'pending',
    error_message TEXT,
    template_version VARCHAR(50),
    generated_by VARCHAR(255),
    generation_time_ms INTEGER,
    extra_data JSON DEFAULT '{}',
    generated_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create campaigns table
CREATE TABLE campaigns (
    id SERIAL PRIMARY KEY,
    name VARCHAR(500) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'draft',
    template_type VARCHAR(100),
    target_criteria JSON DEFAULT '{}',
    scheduled_send_date TIMESTAMP,
    sent_count INTEGER DEFAULT 0,
    opened_count INTEGER DEFAULT 0,
    clicked_count INTEGER DEFAULT 0,
    replied_count INTEGER DEFAULT 0,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    extra_data JSON DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create outreach_logs table
CREATE TABLE outreach_logs (
    id SERIAL PRIMARY KEY,
    campaign_id INTEGER REFERENCES campaigns(id) ON DELETE CASCADE,
    property_id INTEGER REFERENCES properties(id) ON DELETE SET NULL,
    recipient_email VARCHAR(500),
    subject VARCHAR(1000),
    status VARCHAR(50) DEFAULT 'pending',
    sent_at TIMESTAMP,
    opened_at TIMESTAMP,
    clicked_at TIMESTAMP,
    replied_at TIMESTAMP,
    bounced_at TIMESTAMP,
    bounce_reason TEXT,
    template_used VARCHAR(100),
    extra_data JSON DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX idx_properties_city ON properties(city);
CREATE INDEX idx_properties_status ON properties(status);
CREATE INDEX idx_properties_price ON properties(price);
CREATE INDEX idx_property_enrichment_property_id ON property_enrichment(property_id);
CREATE INDEX idx_property_scores_property_id ON property_scores(property_id);
CREATE INDEX idx_property_scores_total_score ON property_scores(total_score);
CREATE INDEX idx_campaigns_status ON campaigns(status);
CREATE INDEX idx_outreach_logs_campaign_id ON outreach_logs(campaign_id);

\dt
EOF

echo ""
echo "================================================"
echo "✓ Database Setup Complete!"
echo "================================================"
echo ""
echo "Your database is ready at: localhost:5432"
echo "Database name: realestate"
echo "User: airflow"
echo ""
echo "Next steps:"
echo ""
echo "1. View the API at: http://localhost:8000/docs"
echo "2. View the Frontend at: http://localhost:3000"
echo ""
echo "The platform is ready to use!"
echo "You can create properties via the API or access the frontend."
echo ""
