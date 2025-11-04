#!/bin/bash
# =============================================================================
# Health Check for Real Estate OS Docker Stack
# =============================================================================
set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Real Estate OS - Health Check${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

HEALTHY=0
UNHEALTHY=0
TOTAL=0

check_service() {
    local service=$1
    local check_command=$2
    local description=$3

    TOTAL=$((TOTAL + 1))
    echo -n "  ${description}: "

    if eval "$check_command" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Healthy${NC}"
        HEALTHY=$((HEALTHY + 1))
        return 0
    else
        echo -e "${RED}✗ Unhealthy${NC}"
        UNHEALTHY=$((UNHEALTHY + 1))
        return 1
    fi
}

echo -e "${YELLOW}🔍 Checking infrastructure services...${NC}"
echo ""

check_service "postgres" \
    "docker-compose exec -T postgres pg_isready -U postgres" \
    "PostgreSQL"

check_service "redis" \
    "docker-compose exec -T redis redis-cli ping" \
    "Redis"

check_service "rabbitmq" \
    "docker-compose exec -T rabbitmq rabbitmq-diagnostics ping" \
    "RabbitMQ"

check_service "minio" \
    "curl -sf http://localhost:9000/minio/health/live" \
    "MinIO"

echo ""
echo -e "${YELLOW}🔍 Checking application services...${NC}"
echo ""

check_service "api" \
    "curl -sf http://localhost:8000/healthz" \
    "API (FastAPI)"

check_service "flower" \
    "curl -sf http://localhost:5555" \
    "Flower (Celery Monitoring)"

echo ""
echo -e "${YELLOW}🔍 Checking optional services...${NC}"
echo ""

check_service "nginx" \
    "curl -sf http://localhost:80" \
    "Nginx (Reverse Proxy)"

check_service "prometheus" \
    "curl -sf http://localhost:9090/-/healthy" \
    "Prometheus"

check_service "grafana" \
    "curl -sf http://localhost:3001/api/health" \
    "Grafana"

echo ""
echo -e "${BLUE}========================================${NC}"

if [ $UNHEALTHY -eq 0 ]; then
    echo -e "${GREEN}✅ All services healthy! (${HEALTHY}/${TOTAL})${NC}"
    echo -e "${BLUE}========================================${NC}"
    exit 0
else
    echo -e "${RED}⚠️  Some services unhealthy (${HEALTHY}/${TOTAL} healthy, ${UNHEALTHY}/${TOTAL} unhealthy)${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    echo -e "${YELLOW}💡 Troubleshooting:${NC}"
    echo ""
    echo -e "  ${YELLOW}View logs:${NC}        docker-compose logs -f [service-name]"
    echo -e "  ${YELLOW}Restart service:${NC}  docker-compose restart [service-name]"
    echo -e "  ${YELLOW}Restart stack:${NC}    ./scripts/docker/stop.sh && ./scripts/docker/start.sh"
    echo ""
    exit 1
fi
