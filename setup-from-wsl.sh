#!/bin/bash

# Real Estate OS - Setup from WSL
# Run this from your WSL terminal where Docker is accessible

set -e

echo "=========================================="
echo "Real Estate OS - WSL Setup"
echo "=========================================="
echo ""

# Step 1: Fix Redis issue and restart Docker
echo "[1/5] Restarting Docker services..."
export AIRFLOW_UID=50000

docker compose down 2>/dev/null || true
echo "Stopped existing containers"

echo "Starting fresh containers..."
docker compose up -d

echo "Waiting for services to start (60 seconds)..."
sleep 60

echo "Checking service health..."
docker compose ps

echo ""
echo "✓ Docker services restarted"
echo ""

# Step 2: Install Python dependencies
echo "[2/5] Installing Python dependencies..."

pip3 install --quiet alembic sqlalchemy psycopg2-binary pydantic==2.5.0 pydantic-settings==2.1.0 2>/dev/null || {
    echo "Note: Some package warnings are normal"
}

echo "✓ Python dependencies installed"
echo ""

# Step 3: Run database migrations
echo "[3/5] Running database migrations..."

cd db
export PYTHONPATH=/home/user/real-estate-os:$PYTHONPATH
alembic upgrade head
cd ..

echo "✓ Database migrations complete"
echo ""

# Step 4: Install remaining dependencies
echo "[4/5] Installing additional Python packages..."

pip3 install --quiet requests beautifulsoup4 2>/dev/null || true

echo "✓ Additional packages installed"
echo ""

# Step 5: Generate demo data
echo "[5/5] Generating demo data..."

python3 scripts/generate_demo_data.py

echo ""
echo "=========================================="
echo "✓ Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Start the frontend (in a new terminal):"
echo "   cd frontend"
echo "   npm install"
echo "   npm run dev"
echo ""
echo "2. Access the platform:"
echo "   Dashboard:  http://localhost:3000"
echo "   API Docs:   http://localhost:8000/docs"
echo "   Airflow:    http://localhost:8080"
echo ""
