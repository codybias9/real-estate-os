#!/bin/bash

# Real Estate OS - Demo Setup Script
# This script sets up and starts the entire platform for demonstration

set -e  # Exit on error

echo "=========================================="
echo "Real Estate OS - Demo Setup"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Step 1: Check prerequisites
echo -e "${YELLOW}[1/7]${NC} Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed${NC}"
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python3 is not installed${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} Prerequisites checked"
echo ""

# Step 2: Set up environment variables
echo -e "${YELLOW}[2/7]${NC} Setting up environment variables..."

if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
        echo -e "${GREEN}✓${NC} Created .env from .env.example"
    else
        cat > .env << EOF
AIRFLOW_UID=50000
AIRFLOW_GID=0
POSTGRES_USER=airflow
POSTGRES_PASSWORD=airflow
POSTGRES_DB=airflow
API_URL=http://localhost:8000
NEXT_PUBLIC_API_URL=http://localhost:8000
EOF
        echo -e "${GREEN}✓${NC} Created .env file"
    fi
else
    echo -e "${GREEN}✓${NC} .env file already exists"
fi

# Export AIRFLOW_UID for docker-compose
export AIRFLOW_UID=50000
echo ""

# Step 3: Start Docker services
echo -e "${YELLOW}[3/7]${NC} Starting Docker services..."

# Use docker compose or docker-compose depending on what's available
if command -v docker &> /dev/null && docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
elif command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
else
    echo -e "${RED}Error: Neither 'docker compose' nor 'docker-compose' is available${NC}"
    exit 1
fi

# Stop any existing containers
$DOCKER_COMPOSE down 2>/dev/null || true

# Start services
echo "Starting containers..."
$DOCKER_COMPOSE up -d

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
sleep 10

MAX_ATTEMPTS=30
ATTEMPT=0
until $DOCKER_COMPOSE exec -T postgres pg_isready -U airflow &>/dev/null || [ $ATTEMPT -eq $MAX_ATTEMPTS ]; do
    echo "  Waiting for PostgreSQL... (attempt $((ATTEMPT+1))/$MAX_ATTEMPTS)"
    sleep 2
    ATTEMPT=$((ATTEMPT+1))
done

if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
    echo -e "${RED}Error: PostgreSQL did not become ready in time${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} Docker services started"
echo ""

# Step 4: Run database migrations
echo -e "${YELLOW}[4/7]${NC} Running database migrations..."

cd db

# Check if alembic is available
if ! command -v alembic &> /dev/null; then
    echo "Installing alembic..."
    pip3 install alembic sqlalchemy psycopg2-binary --quiet
fi

# Run migrations
alembic upgrade head

cd ..

echo -e "${GREEN}✓${NC} Database migrations complete"
echo ""

# Step 5: Install Python dependencies
echo -e "${YELLOW}[5/7]${NC} Installing Python dependencies..."

if [ -f requirements.txt ]; then
    pip3 install -r requirements.txt --quiet || echo "Some packages may have failed to install, continuing..."
fi

echo -e "${GREEN}✓${NC} Python dependencies installed"
echo ""

# Step 6: Generate demo data
echo -e "${YELLOW}[6/7]${NC} Generating demo data..."

python3 scripts/generate_demo_data.py

echo -e "${GREEN}✓${NC} Demo data generated"
echo ""

# Step 7: Instructions for frontend
echo -e "${YELLOW}[7/7]${NC} Frontend setup..."

echo ""
echo "To start the frontend, run the following commands in a NEW terminal:"
echo ""
echo -e "${YELLOW}  cd frontend${NC}"
echo -e "${YELLOW}  npm install${NC}"
echo -e "${YELLOW}  npm run dev${NC}"
echo ""

echo "=========================================="
echo -e "${GREEN}Setup Complete!${NC}"
echo "=========================================="
echo ""
echo "Access the platform at:"
echo ""
echo "  🌐 Dashboard:  http://localhost:3000"
echo "  📡 API Docs:   http://localhost:8000/docs"
echo "  ⚙️  Airflow:    http://localhost:8080"
echo "                 (user: airflow, pass: airflow)"
echo ""
echo "To view running containers:"
echo "  $DOCKER_COMPOSE ps"
echo ""
echo "To view logs:"
echo "  $DOCKER_COMPOSE logs -f [service-name]"
echo ""
echo "To stop all services:"
echo "  $DOCKER_COMPOSE down"
echo ""
