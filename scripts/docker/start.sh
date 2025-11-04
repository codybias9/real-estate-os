#!/bin/bash
# =============================================================================
# Start Real Estate OS Docker Stack
# =============================================================================
set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Real Estate OS - Docker Stack Startup${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if .env.mock exists
if [ ! -f .env.mock ]; then
    echo -e "${RED}Error: .env.mock file not found${NC}"
    echo "Please create .env.mock from .env.example"
    exit 1
fi

# Copy .env.mock to .env
echo -e "${YELLOW}📋 Copying .env.mock to .env...${NC}"
cp .env.mock .env
echo -e "${GREEN}✓ Environment configured for MOCK MODE${NC}"
echo ""

# Pull latest images
echo -e "${YELLOW}📥 Pulling Docker images...${NC}"
docker-compose pull --quiet
echo -e "${GREEN}✓ Images up to date${NC}"
echo ""

# Build application images
echo -e "${YELLOW}🔨 Building application images...${NC}"
docker-compose build --quiet
echo -e "${GREEN}✓ Build complete${NC}"
echo ""

# Start infrastructure services first
echo -e "${YELLOW}🚀 Starting infrastructure services...${NC}"
docker-compose up -d postgres redis rabbitmq minio
echo -e "${GREEN}✓ Infrastructure services started${NC}"
echo ""

# Wait for health checks
echo -e "${YELLOW}⏳ Waiting for services to be healthy...${NC}"
sleep 10

# Check PostgreSQL
echo -n "  PostgreSQL: "
until docker-compose exec -T postgres pg_isready -U postgres > /dev/null 2>&1; do
    echo -n "."
    sleep 2
done
echo -e " ${GREEN}✓${NC}"

# Check Redis
echo -n "  Redis: "
until docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; do
    echo -n "."
    sleep 2
done
echo -e " ${GREEN}✓${NC}"

# Check RabbitMQ
echo -n "  RabbitMQ: "
until docker-compose exec -T rabbitmq rabbitmq-diagnostics ping > /dev/null 2>&1; do
    echo -n "."
    sleep 2
done
echo -e " ${GREEN}✓${NC}"

# Check MinIO
echo -n "  MinIO: "
until curl -sf http://localhost:9000/minio/health/live > /dev/null 2>&1; do
    echo -n "."
    sleep 2
done
echo -e " ${GREEN}✓${NC}"

echo ""

# Initialize MinIO buckets
echo -e "${YELLOW}📦 Initializing MinIO buckets...${NC}"
docker-compose up -d minio-init
sleep 5
echo -e "${GREEN}✓ MinIO buckets created${NC}"
echo ""

# Run database migrations
echo -e "${YELLOW}🗃️  Running database migrations...${NC}"
docker-compose run --rm api alembic upgrade head || echo -e "${YELLOW}⚠ Migrations skipped (may not be configured yet)${NC}"
echo ""

# Start application services
echo -e "${YELLOW}🚀 Starting application services...${NC}"
docker-compose up -d api celery-worker celery-beat flower
echo -e "${GREEN}✓ Application services started${NC}"
echo ""

# Start optional services
echo -e "${YELLOW}🚀 Starting optional services...${NC}"
docker-compose up -d nginx prometheus grafana
echo -e "${GREEN}✓ Optional services started${NC}"
echo ""

# Wait for API to be ready
echo -e "${YELLOW}⏳ Waiting for API to be ready...${NC}"
echo -n "  API: "
until curl -sf http://localhost:8000/healthz > /dev/null 2>&1; do
    echo -n "."
    sleep 2
done
echo -e " ${GREEN}✓${NC}"
echo ""

# Show service URLs
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ Stack started successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}📡 Service URLs:${NC}"
echo ""
echo -e "  ${YELLOW}API:${NC}              http://localhost:8000"
echo -e "  ${YELLOW}API Docs:${NC}         http://localhost:8000/docs"
echo -e "  ${YELLOW}RabbitMQ UI:${NC}      http://localhost:15672 (admin/admin)"
echo -e "  ${YELLOW}Flower (Jobs):${NC}    http://localhost:5555"
echo -e "  ${YELLOW}MinIO Console:${NC}    http://localhost:9001 (minioadmin/minioadmin)"
echo -e "  ${YELLOW}Prometheus:${NC}       http://localhost:9090"
echo -e "  ${YELLOW}Grafana:${NC}          http://localhost:3001 (admin/admin)"
echo ""
echo -e "${BLUE}🔐 Demo Credentials:${NC}"
echo ""
echo -e "  ${YELLOW}Admin:${NC}   admin@demo.com / password123"
echo -e "  ${YELLOW}Manager:${NC} manager@demo.com / password123"
echo -e "  ${YELLOW}Agent:${NC}   agent@demo.com / password123"
echo ""
echo -e "${BLUE}💡 Next Steps:${NC}"
echo ""
echo -e "  1. Open API docs: ${YELLOW}http://localhost:8000/docs${NC}"
echo -e "  2. Check health:  ${YELLOW}./scripts/docker/health.sh${NC}"
echo -e "  3. View logs:     ${YELLOW}docker-compose logs -f api${NC}"
echo -e "  4. Stop stack:    ${YELLOW}./scripts/docker/stop.sh${NC}"
echo ""
echo -e "${GREEN}🎉 Ready for demo!${NC}"
echo ""
