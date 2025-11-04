#!/bin/bash
# =============================================================================
# Validate Real Estate OS Docker Stack - Generate JSON Report
# =============================================================================
set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Output file
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_DIR="audit_artifacts/${TIMESTAMP}"
OUTPUT_FILE="${OUTPUT_DIR}/docker_stack_validation.json"

# Create output directory
mkdir -p "$OUTPUT_DIR"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Real Estate OS - Stack Validation${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Start JSON report
cat > "$OUTPUT_FILE" << EOF
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "validation_type": "docker_stack",
  "mode": "mock",
  "services": {
EOF

# Helper function to check service and add to JSON
check_service_json() {
    local service=$1
    local check_command=$2
    local description=$3
    local url=$4

    echo -n "  Checking ${description}... "

    # Run check
    if eval "$check_command" > /dev/null 2>&1; then
        status="healthy"
        echo -e "${GREEN}✓${NC}"
    else
        status="unhealthy"
        echo -e "${RED}✗${NC}"
    fi

    # Get container info if exists
    container_status=$(docker-compose ps $service 2>/dev/null | grep $service | awk '{print $4}' || echo "not_running")

    # Add to JSON (handle comma for all but last)
    cat >> "$OUTPUT_FILE" << EOF
    "${service}": {
      "description": "${description}",
      "status": "${status}",
      "container_status": "${container_status}",
      "url": "${url}",
      "checked_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    },
EOF
}

echo -e "${YELLOW}Infrastructure Services:${NC}"
check_service_json "postgres" \
    "docker-compose exec -T postgres pg_isready -U postgres" \
    "PostgreSQL Database" \
    "postgres://postgres:5432"

check_service_json "redis" \
    "docker-compose exec -T redis redis-cli ping" \
    "Redis Cache" \
    "redis://redis:6379"

check_service_json "rabbitmq" \
    "docker-compose exec -T rabbitmq rabbitmq-diagnostics ping" \
    "RabbitMQ Message Queue" \
    "http://localhost:15672"

check_service_json "minio" \
    "curl -sf http://localhost:9000/minio/health/live" \
    "MinIO Object Storage" \
    "http://localhost:9001"

echo ""
echo -e "${YELLOW}Application Services:${NC}"
check_service_json "api" \
    "curl -sf http://localhost:8000/healthz" \
    "FastAPI Backend" \
    "http://localhost:8000"

check_service_json "celery-worker" \
    "docker-compose ps celery-worker | grep -q Up" \
    "Celery Worker" \
    "N/A"

check_service_json "celery-beat" \
    "docker-compose ps celery-beat | grep -q Up" \
    "Celery Beat Scheduler" \
    "N/A"

check_service_json "flower" \
    "curl -sf http://localhost:5555" \
    "Flower Monitoring" \
    "http://localhost:5555"

echo ""
echo -e "${YELLOW}Optional Services:${NC}"
check_service_json "nginx" \
    "curl -sf http://localhost:80" \
    "Nginx Reverse Proxy" \
    "http://localhost:80"

check_service_json "prometheus" \
    "curl -sf http://localhost:9090/-/healthy" \
    "Prometheus Metrics" \
    "http://localhost:9090"

check_service_json "grafana" \
    "curl -sf http://localhost:3001/api/health" \
    "Grafana Dashboards" \
    "http://localhost:3001"

# Remove trailing comma from last service
sed -i '$ s/,$//' "$OUTPUT_FILE"

# Complete JSON structure
cat >> "$OUTPUT_FILE" << 'EOF'
  },
  "endpoints": {
    "api_docs": "http://localhost:8000/docs",
    "api_redoc": "http://localhost:8000/redoc",
    "api_openapi": "http://localhost:8000/openapi.json",
    "rabbitmq_ui": "http://localhost:15672",
    "minio_console": "http://localhost:9001",
    "flower_ui": "http://localhost:5555",
    "prometheus_ui": "http://localhost:9090",
    "grafana_ui": "http://localhost:3001"
  },
  "credentials": {
    "api_demo_admin": "admin@demo.com / password123",
    "api_demo_manager": "manager@demo.com / password123",
    "api_demo_agent": "agent@demo.com / password123",
    "rabbitmq": "admin / admin",
    "minio": "minioadmin / minioadmin",
    "grafana": "admin / admin"
  }
}
EOF

# Calculate summary
TOTAL_SERVICES=$(grep -o '"status":' "$OUTPUT_FILE" | wc -l)
HEALTHY_SERVICES=$(grep -o '"status": "healthy"' "$OUTPUT_FILE" | wc -l)
UNHEALTHY_SERVICES=$((TOTAL_SERVICES - HEALTHY_SERVICES))

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "  Total Services:     ${TOTAL_SERVICES}"
echo -e "  Healthy:            ${GREEN}${HEALTHY_SERVICES}${NC}"
echo -e "  Unhealthy:          ${RED}${UNHEALTHY_SERVICES}${NC}"
echo ""
echo -e "${GREEN}✓ Validation report generated${NC}"
echo -e "  ${YELLOW}Report:${NC} ${OUTPUT_FILE}"
echo ""

# Pretty print JSON summary
echo -e "${BLUE}Quick View:${NC}"
echo ""
cat "$OUTPUT_FILE" | python3 -m json.tool 2>/dev/null | grep -E '(status|description)' | head -20 || cat "$OUTPUT_FILE" | head -40

echo ""
echo -e "${YELLOW}💡 View full report:${NC}"
echo -e "  cat ${OUTPUT_FILE} | python3 -m json.tool"
echo ""

# Exit with appropriate code
if [ $UNHEALTHY_SERVICES -gt 0 ]; then
    exit 1
else
    exit 0
fi
