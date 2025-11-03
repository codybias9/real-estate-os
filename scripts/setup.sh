#!/bin/bash

# Real Estate OS - Initial Setup Script
# This script initializes the development environment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Real Estate OS - Initial Setup${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Function to print status
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
echo -e "${BLUE}Checking prerequisites...${NC}"

if ! command_exists docker; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi
print_status "Docker is installed"

if ! command_exists docker-compose; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi
print_status "Docker Compose is installed"

if ! command_exists poetry; then
    print_warning "Poetry is not installed. Install it from https://python-poetry.org/"
    echo "  curl -sSL https://install.python-poetry.org | python3 -"
    read -p "Press enter to continue or Ctrl+C to exit..."
fi

echo ""

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo -e "${BLUE}Creating .env file from template...${NC}"
    cp .env.example .env
    print_status ".env file created"
    print_warning "Please edit .env file with your actual credentials before proceeding"
    echo ""
    read -p "Press enter after editing .env file..."
else
    print_status ".env file already exists"
fi

echo ""

# Create necessary directories
echo -e "${BLUE}Creating necessary directories...${NC}"
mkdir -p logs tmp data/postgres data/redis data/rabbitmq data/minio
print_status "Directories created"

echo ""

# Start infrastructure services
echo -e "${BLUE}Starting infrastructure services...${NC}"
echo "This may take a few minutes on first run..."

docker-compose up -d postgres redis rabbitmq minio

echo ""
echo "Waiting for services to be healthy..."

# Wait for PostgreSQL
echo -n "Waiting for PostgreSQL..."
until docker-compose exec -T postgres pg_isready -U postgres > /dev/null 2>&1; do
    echo -n "."
    sleep 2
done
echo ""
print_status "PostgreSQL is ready"

# Wait for Redis
echo -n "Waiting for Redis..."
until docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; do
    echo -n "."
    sleep 2
done
echo ""
print_status "Redis is ready"

# Wait for RabbitMQ
echo -n "Waiting for RabbitMQ..."
until docker-compose exec -T rabbitmq rabbitmq-diagnostics ping > /dev/null 2>&1; do
    echo -n "."
    sleep 2
done
echo ""
print_status "RabbitMQ is ready"

# Wait for MinIO
echo -n "Waiting for MinIO..."
until curl -sf http://localhost:9000/minio/health/live > /dev/null 2>&1; do
    echo -n "."
    sleep 2
done
echo ""
print_status "MinIO is ready"

echo ""

# Run database migrations
echo -e "${BLUE}Running database migrations...${NC}"

# Check if poetry is available
if command_exists poetry; then
    cd db
    poetry install
    poetry run alembic upgrade head
    cd ..
    print_status "Database migrations completed"
else
    print_warning "Poetry not found. Skipping migrations."
    print_warning "Please run manually: cd db && poetry install && poetry run alembic upgrade head"
fi

echo ""

# Create MinIO buckets
echo -e "${BLUE}Creating S3 buckets in MinIO...${NC}"
docker-compose up -d minio-init
sleep 5
print_status "MinIO buckets created"

echo ""

# Display service URLs
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}Service URLs:${NC}"
echo "  PostgreSQL:        localhost:5432"
echo "  Redis:             localhost:6379"
echo "  RabbitMQ:          localhost:5672"
echo "  RabbitMQ UI:       http://localhost:15672 (admin/admin)"
echo "  MinIO:             http://localhost:9000"
echo "  MinIO Console:     http://localhost:9001 (minioadmin/minioadmin)"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "  1. Start the API: docker-compose up api"
echo "  2. Or start everything: docker-compose up"
echo "  3. Access API docs: http://localhost:8000/docs"
echo "  4. Access Grafana: http://localhost:3001 (admin/admin)"
echo ""
echo -e "${YELLOW}Optional - Load seed data:${NC}"
echo "  poetry run python scripts/seed_data.py"
echo ""
