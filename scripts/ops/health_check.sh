#!/bin/bash

# Health Check Script
# Verifies all services are healthy

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "===================================="
echo "Real Estate OS - Health Check"
echo "===================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check service
check_service() {
  local name=$1
  local url=$2
  local expected=${3:-200}

  printf "%-20s " "$name:"

  if response=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>&1); then
    if [ "$response" = "$expected" ]; then
      echo -e "${GREEN}✓ Healthy${NC} ($response)"
      return 0
    else
      echo -e "${YELLOW}⚠ Unhealthy${NC} (HTTP $response, expected $expected)"
      return 1
    fi
  else
    echo -e "${RED}✗ Unreachable${NC}"
    return 1
  fi
}

# Check each service
echo "Checking services..."
echo ""

total=0
healthy=0

# PostgreSQL
((total++))
printf "%-20s " "PostgreSQL:"
if docker compose exec -T postgres pg_isready > /dev/null 2>&1; then
  echo -e "${GREEN}✓ Healthy${NC}"
  ((healthy++))
else
  echo -e "${RED}✗ Unhealthy${NC}"
fi

# Redis
((total++))
printf "%-20s " "Redis:"
if docker compose exec -T redis redis-cli ping > /dev/null 2>&1; then
  echo -e "${GREEN}✓ Healthy${NC}"
  ((healthy++))
else
  echo -e "${RED}✗ Unhealthy${NC}"
fi

# Keycloak
((total++))
if check_service "Keycloak" "http://localhost:8080/health/ready"; then
  ((healthy++))
fi

# MinIO
((total++))
if check_service "MinIO" "http://localhost:9000/minio/health/live"; then
  ((healthy++))
fi

# Qdrant
((total++))
if check_service "Qdrant" "http://localhost:6333/healthz"; then
  ((healthy++))
fi

# Neo4j
((total++))
printf "%-20s " "Neo4j:"
if docker compose exec -T neo4j cypher-shell -u neo4j -p "${NEO4J_PASSWORD:-password}" "RETURN 1" > /dev/null 2>&1; then
  echo -e "${GREEN}✓ Healthy${NC}"
  ((healthy++))
else
  echo -e "${RED}✗ Unhealthy${NC}"
fi

# Prometheus
((total++))
if check_service "Prometheus" "http://localhost:9090/-/healthy"; then
  ((healthy++))
fi

# Grafana
((total++))
if check_service "Grafana" "http://localhost:3000/api/health"; then
  ((healthy++))
fi

# Airflow Webserver
((total++))
if check_service "Airflow Webserver" "http://localhost:8081/health"; then
  ((healthy++))
fi

# API
((total++))
if check_service "API" "http://localhost:8000/health"; then
  ((healthy++))
fi

echo ""
echo "===================================="
echo "Summary: $healthy/$total services healthy"
echo "===================================="
echo ""

if [ $healthy -eq $total ]; then
  echo -e "${GREEN}✓ All services operational${NC}"
  echo ""
  echo "Service URLs:"
  echo "  API:            http://localhost:8000"
  echo "  API Docs:       http://localhost:8000/docs"
  echo "  Keycloak:       http://localhost:8080"
  echo "  MinIO Console:  http://localhost:9001"
  echo "  Neo4j Browser:  http://localhost:7474"
  echo "  Prometheus:     http://localhost:9090"
  echo "  Grafana:        http://localhost:3000"
  echo "  Airflow:        http://localhost:8081"
  exit 0
else
  echo -e "${RED}✗ Some services are unhealthy${NC}"
  echo ""
  echo "To view logs:"
  echo "  docker compose --env-file .env.staging -f docker-compose.staging.yml logs -f [service]"
  exit 1
fi
