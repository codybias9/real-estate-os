#!/bin/bash
#
# Start Real Estate OS Docker Stack (Mock Mode)
#
# Brings up the complete 15-service Docker stack in mock mode:
#  - 7 infrastructure services (postgres, redis, rabbitmq, minio, etc.)
#  - 8 application services (api, celery, frontend, nginx, monitoring)
#
# Prerequisites:
#  - Docker Engine 20.10+ installed
#  - Docker Compose v2.x installed
#  - Ports available: 80, 3000, 3001, 5432, 5555, 6379, 8000, 8025, 9000, 9090, 15672
#
# Usage:
#   ./scripts/start_docker_stack.sh [--build] [--logs]
#
# Options:
#   --build  : Force rebuild of images
#   --logs   : Tail logs after startup
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "============================================================================"
echo "  Real Estate OS - Docker Stack Startup (Mock Mode)"
echo "============================================================================"
echo ""

# Parse arguments
BUILD_FLAG=""
LOGS_FLAG=false

for arg in "$@"; do
    case $arg in
        --build)
            BUILD_FLAG="--build"
            echo "→ Build flag set: Will rebuild images"
            ;;
        --logs)
            LOGS_FLAG=true
            echo "→ Logs flag set: Will tail logs after startup"
            ;;
        *)
            echo "Unknown option: $arg"
            echo "Usage: $0 [--build] [--logs]"
            exit 1
            ;;
    esac
done

echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker not found${NC}"
    echo "  Please install Docker Engine 20.10+ from https://docs.docker.com/engine/install/"
    exit 1
fi

echo -e "${GREEN}✓ Docker found:${NC} $(docker --version)"

# Check if Docker Compose is available
if ! docker compose version &> /dev/null; then
    echo -e "${RED}✗ Docker Compose not found${NC}"
    echo "  Please install Docker Compose v2+ from https://docs.docker.com/compose/install/"
    exit 1
fi

echo -e "${GREEN}✓ Docker Compose found:${NC} $(docker compose version)"
echo ""

# Step 1: Copy .env.mock to .env
echo "→ Step 1: Setting up environment"
if [ ! -f .env ]; then
    cp .env.mock .env
    echo -e "${GREEN}  ✓ Copied .env.mock to .env${NC}"
else
    echo -e "${YELLOW}  ⚠ .env already exists, skipping copy${NC}"
    echo "    (If you want fresh config, run: cp .env.mock .env)"
fi

# Step 2: Create Docker network if needed
echo ""
echo "→ Step 2: Checking Docker network"
if ! docker network inspect realtor-network &> /dev/null; then
    docker network create realtor-network
    echo -e "${GREEN}  ✓ Created realtor-network${NC}"
else
    echo -e "${GREEN}  ✓ Network realtor-network exists${NC}"
fi

# Step 3: Pull/build images
echo ""
echo "→ Step 3: Pulling/building images (this may take a few minutes)"
docker compose -f docker-compose.yml -f docker-compose.override.mock.yml pull --ignore-pull-failures || true
docker compose -f docker-compose.yml -f docker-compose.override.mock.yml build $BUILD_FLAG

# Step 4: Start services
echo ""
echo "→ Step 4: Starting services"
echo "  Starting infrastructure services first..."
docker compose -f docker-compose.yml up -d postgres redis rabbitmq minio mailhog mock-twilio gotenberg

echo "  Waiting for services to be healthy (30s)..."
sleep 30

echo "  Starting application services..."
docker compose -f docker-compose.yml -f docker-compose.override.mock.yml up -d

# Step 5: Wait for all services to be healthy
echo ""
echo "→ Step 5: Waiting for all services to be healthy (60s)..."
sleep 60

# Step 6: Check service health
echo ""
echo "→ Step 6: Checking service health"
echo "============================================================================"
docker compose -f docker-compose.yml -f docker-compose.override.mock.yml ps
echo "============================================================================"

# Count healthy services
HEALTHY=$(docker compose -f docker-compose.yml -f docker-compose.override.mock.yml ps | grep -c "healthy" || true)
TOTAL=$(docker compose -f docker-compose.yml -f docker-compose.override.mock.yml ps | wc -l)

echo ""
echo "Health Summary: $HEALTHY/$TOTAL services healthy"
echo ""

# Step 7: Run database migrations
echo "→ Step 7: Running database migrations"
docker compose -f docker-compose.yml -f docker-compose.override.mock.yml exec -T api alembic upgrade head || {
    echo -e "${YELLOW}  ⚠ Migrations may have failed or already applied${NC}"
}

# Step 8: Display access URLs
echo ""
echo "============================================================================"
echo "  ✅ Docker Stack Started Successfully!"
echo "============================================================================"
echo ""
echo "Service URLs:"
echo "  → API (FastAPI):        http://localhost:8000"
echo "  → API Docs (Swagger):   http://localhost:8000/docs"
echo "  → API Health:           http://localhost:8000/healthz"
echo "  → Frontend (Next.js):   http://localhost:3000"
echo "  → MailHog (Email):      http://localhost:8025"
echo "  → RabbitMQ Mgmt:        http://localhost:15672 (guest/guest)"
echo "  → MinIO Console:        http://localhost:9001 (minioadmin/minioadmin)"
echo "  → Flower (Celery):      http://localhost:5555"
echo "  → Prometheus:           http://localhost:9090"
echo "  → Grafana:              http://localhost:3001 (admin/admin)"
echo ""
echo "Quick Tests:"
echo "  curl http://localhost:8000/healthz"
echo "  curl http://localhost:8000/docs"
echo ""
echo "View Logs:"
echo "  docker compose -f docker-compose.yml -f docker-compose.override.mock.yml logs -f [service]"
echo ""
echo "Stop Stack:"
echo "  docker compose -f docker-compose.yml -f docker-compose.override.mock.yml down"
echo ""
echo "============================================================================"

# Tail logs if requested
if [ "$LOGS_FLAG" = true ]; then
    echo ""
    echo "→ Tailing logs (Ctrl+C to exit)..."
    docker compose -f docker-compose.yml -f docker-compose.override.mock.yml logs -f
fi
