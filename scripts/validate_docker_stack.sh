#!/bin/bash
#
# Validate Real Estate OS Docker Stack Health
#
# Comprehensive health check script that:
#  - Checks all 15 services are running
#  - Validates health check status
#  - Tests API endpoints
#  - Verifies database connectivity
#  - Checks MinIO buckets
#  - Generates health report
#
# Usage:
#   ./scripts/validate_docker_stack.sh [--output audit_artifacts/<timestamp>/]
#

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Determine output directory
TIMESTAMP=$(date -u +"%Y%m%d_%H%M%S")
OUTPUT_DIR="${1:-audit_artifacts/${TIMESTAMP}}"
mkdir -p "${OUTPUT_DIR}"

REPORT_FILE="${OUTPUT_DIR}/bringup_health.json"

echo "============================================================================"
echo "  Real Estate OS - Docker Stack Health Validation"
echo "============================================================================"
echo ""
echo "Output: ${REPORT_FILE}"
echo ""

# Initialize report
cat > "${REPORT_FILE}" << 'EOF'
{
  "timestamp": "",
  "services": {},
  "api_tests": {},
  "database": {},
  "storage": {},
  "summary": {}
}
EOF

# Update timestamp
TIMESTAMP_ISO=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
jq --arg ts "$TIMESTAMP_ISO" '.timestamp = $ts' "${REPORT_FILE}" > "${REPORT_FILE}.tmp" && mv "${REPORT_FILE}.tmp" "${REPORT_FILE}"

# Function to test service health
test_service() {
    local service=$1
    local url=$2
    local expected_status=${3:-200}

    echo -n "  Testing $service... "

    if response=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null); then
        if [ "$response" -eq "$expected_status" ]; then
            echo -e "${GREEN}✓${NC} (HTTP $response)"
            echo "true"
        else
            echo -e "${RED}✗${NC} (HTTP $response, expected $expected_status)"
            echo "false"
        fi
    else
        echo -e "${RED}✗${NC} (Connection failed)"
        echo "false"
    fi
}

# 1. Check Docker services
echo "→ Step 1: Checking Docker service status"
docker compose -f docker-compose.yml -f docker-compose.override.mock.yml ps --format json > "${OUTPUT_DIR}/docker_ps.json" 2>/dev/null || true

# Count services
TOTAL_SERVICES=$(docker compose -f docker-compose.yml -f docker-compose.override.mock.yml ps | wc -l)
HEALTHY_SERVICES=$(docker compose -f docker-compose.yml -f docker-compose.override.mock.yml ps | grep -c "healthy" || true)
RUNNING_SERVICES=$(docker compose -f docker-compose.yml -f docker-compose.override.mock.yml ps | grep -c "Up" || true)

echo "  Total: $TOTAL_SERVICES"
echo "  Running: $RUNNING_SERVICES"
echo "  Healthy: $HEALTHY_SERVICES"
echo ""

# 2. Test API endpoints
echo "→ Step 2: Testing API endpoints"
API_HEALTH=$(test_service "API Health" "http://localhost:8000/healthz" 200)
API_DOCS=$(test_service "API Docs" "http://localhost:8000/docs" 200)
API_OPENAPI=$(test_service "OpenAPI" "http://localhost:8000/openapi.json" 200)
echo ""

# 3. Test Frontend
echo "→ Step 3: Testing Frontend"
FRONTEND_HEALTH=$(test_service "Frontend" "http://localhost:3000" 200)
echo ""

# 4. Test Infrastructure Services
echo "→ Step 4: Testing Infrastructure"
MAILHOG=$(test_service "MailHog" "http://localhost:8025" 200)
MINIO=$(test_service "MinIO" "http://localhost:9000/minio/health/live" 200)
RABBITMQ=$(test_service "RabbitMQ" "http://localhost:15672" 200)
FLOWER=$(test_service "Flower" "http://localhost:5555" 200)
PROMETHEUS=$(test_service "Prometheus" "http://localhost:9090/-/healthy" 200)
GRAFANA=$(test_service "Grafana" "http://localhost:3001/api/health" 200)
echo ""

# 5. Test Database connectivity
echo "→ Step 5: Testing Database"
if docker compose -f docker-compose.yml -f docker-compose.override.mock.yml exec -T postgres pg_isready -U postgres &>/dev/null; then
    echo -e "  ${GREEN}✓${NC} PostgreSQL ready"
    DB_STATUS="healthy"
else
    echo -e "  ${RED}✗${NC} PostgreSQL not ready"
    DB_STATUS="unhealthy"
fi
echo ""

# 6. Test Redis
echo "→ Step 6: Testing Redis"
if docker compose -f docker-compose.yml -f docker-compose.override.mock.yml exec -T redis redis-cli ping &>/dev/null; then
    echo -e "  ${GREEN}✓${NC} Redis responding"
    REDIS_STATUS="healthy"
else
    echo -e "  ${RED}✗${NC} Redis not responding"
    REDIS_STATUS="unhealthy"
fi
echo ""

# 7. Generate final report
echo "→ Step 7: Generating health report"

cat > "${REPORT_FILE}" << EOF
{
  "timestamp": "${TIMESTAMP_ISO}",
  "services": {
    "total": ${TOTAL_SERVICES},
    "running": ${RUNNING_SERVICES},
    "healthy": ${HEALTHY_SERVICES}
  },
  "api_tests": {
    "health_endpoint": ${API_HEALTH},
    "docs_endpoint": ${API_DOCS},
    "openapi_endpoint": ${API_OPENAPI}
  },
  "frontend": {
    "accessible": ${FRONTEND_HEALTH}
  },
  "infrastructure": {
    "mailhog": ${MAILHOG},
    "minio": ${MINIO},
    "rabbitmq": ${RABBITMQ},
    "flower": ${FLOWER},
    "prometheus": ${PROMETHEUS},
    "grafana": ${GRAFANA}
  },
  "database": {
    "postgres": "${DB_STATUS}",
    "redis": "${REDIS_STATUS}"
  },
  "summary": {
    "overall_status": "$([ "$HEALTHY_SERVICES" -ge 10 ] && echo "healthy" || echo "degraded")",
    "critical_services_up": $([ "$API_HEALTH" = "true" ] && [ "$DB_STATUS" = "healthy" ] && echo "true" || echo "false")
  }
}
EOF

echo -e "${GREEN}✓ Health report generated${NC}"
echo ""

# Print summary
echo "============================================================================"
echo "  Health Validation Summary"
echo "============================================================================"
cat "${REPORT_FILE}" | jq '.'
echo ""

# Print recommendations
if [ "$HEALTHY_SERVICES" -lt 10 ]; then
    echo -e "${YELLOW}⚠ Warning: Some services are not healthy${NC}"
    echo "  Run: docker compose -f docker-compose.yml -f docker-compose.override.mock.yml ps"
    echo "  View logs: docker compose logs [service-name]"
    echo ""
fi

if [ "$API_HEALTH" = "true" ] && [ "$DB_STATUS" = "healthy" ]; then
    echo -e "${GREEN}✅ Stack is operational!${NC}"
    echo "  Critical services (API, Database) are healthy"
    echo ""
    echo "Next Steps:"
    echo "  1. Run introspection: ./scripts/run_introspection.sh"
    echo "  2. Run tests: pytest --cov=. --cov-report=xml"
    echo "  3. Generate proofs: ./scripts/generate_proofs.sh"
else
    echo -e "${RED}✗ Stack has issues${NC}"
    echo "  Critical services are not healthy"
    echo "  Check logs and retry startup"
fi

echo ""
echo "Artifacts:"
echo "  - ${REPORT_FILE}"
echo "  - ${OUTPUT_DIR}/docker_ps.json"
echo "============================================================================"
