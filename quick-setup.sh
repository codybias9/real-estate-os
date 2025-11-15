#!/bin/bash
# Simple setup script that works with existing Docker containers
# Run this from: /mnt/c/Users/codyb/real-estate-os

echo "================================================"
echo "Real Estate OS - Quick Setup with Docker"
echo "================================================"
echo ""

# Step 1: Run migrations in the db container
echo "[1/2] Running database migrations..."
docker exec -it real-estate-os-db-1 psql -U postgres -d realestate -c "
CREATE TABLE IF NOT EXISTS properties (
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

CREATE TABLE IF NOT EXISTS property_enrichment (
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

CREATE TABLE IF NOT EXISTS property_scores (
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

CREATE TABLE IF NOT EXISTS generated_documents (
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
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    generated_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS campaigns (
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

CREATE TABLE IF NOT EXISTS outreach_logs (
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
" 2>&1 | grep -v "NOTICE"

echo "✓ Database tables created"
echo ""

# Step 2: Generate sample data using Python
echo "[2/2] Use the frontend to view the platform..."
echo ""
echo "================================================"
echo "Setup Complete!"
echo "================================================"
echo ""
echo "Your database is ready at: localhost:5432"
echo ""
echo "Next steps:"
echo "1. The API is already running at: http://localhost:8000"
echo "2. The frontend is running at: http://localhost:3000"
echo "3. Access Swagger docs at: http://localhost:8000/docs"
echo ""
echo "To add demo data, visit the API docs and use the endpoints to:"
echo "- Create properties via POST /api/properties"
echo "- Or use the Swagger UI to test the API"
echo ""
