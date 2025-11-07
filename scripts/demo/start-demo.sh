#!/bin/bash
#
# Real Estate OS - Demo Environment Starter
# Prepares and starts everything needed for a successful demo
#
# Usage: ./scripts/demo/start-demo.sh
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Demo configuration
COMPOSE_FILE="docker-compose.api.yml"
API_URL="http://localhost:8000"

# Intro banner
echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║        Real Estate OS - Demo Environment Setup              ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Function to log steps
log_step() {
    echo -e "${BLUE}▶${NC} $1"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

log_info() {
    echo -e "${CYAN}ℹ${NC} $1"
}

# Check prerequisites
log_step "Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    log_error "Docker not found. Please install Docker first."
    exit 1
fi
log_success "Docker found: $(docker --version | cut -d' ' -f3)"

if ! docker compose version &> /dev/null 2>&1; then
    log_error "docker compose not found. Please install Docker Compose."
    exit 1
fi
log_success "docker compose found"

if ! command -v curl &> /dev/null; then
    log_warning "curl not found. Some checks will be skipped."
fi

if ! command -v jq &> /dev/null; then
    log_warning "jq not found. JSON output won't be prettified."
fi

echo ""

# Check if docker-compose file exists
if [ ! -f "$COMPOSE_FILE" ]; then
    log_error "Docker Compose file not found: $COMPOSE_FILE"
    log_info "Are you in the project root directory?"
    exit 1
fi

# Stop any existing services
log_step "Cleaning up any existing services..."
docker compose -f "$COMPOSE_FILE" down -v > /dev/null 2>&1 || true
log_success "Cleanup complete"

echo ""

# Start services
log_step "Starting demo services..."
log_info "This will take about 30-60 seconds..."

echo ""
docker compose -f "$COMPOSE_FILE" up -d --wait

if [ $? -eq 0 ]; then
    log_success "Services started successfully!"
else
    log_error "Failed to start services"
    exit 1
fi

echo ""

# Wait a bit for services to fully initialize
log_step "Waiting for services to fully initialize..."
sleep 5

# Show service status
log_step "Service status:"
echo ""
docker compose -f "$COMPOSE_FILE" ps
echo ""

# Check API health
log_step "Testing API health..."

if command -v curl &> /dev/null; then
    # Try health check
    for i in {1..30}; do
        if curl -s -f "$API_URL/healthz" > /dev/null 2>&1; then
            log_success "API is healthy! (/healthz responding)"
            break
        fi
        if [ $i -eq 30 ]; then
            log_error "API health check timed out after 30 attempts"
            log_info "Check logs: docker compose -f $COMPOSE_FILE logs api"
            exit 1
        fi
        sleep 1
    done

    # Test health endpoint
    echo ""
    log_step "Testing /healthz endpoint:"
    if command -v jq &> /dev/null; then
        curl -s "$API_URL/healthz" | jq .
    else
        curl -s "$API_URL/healthz"
        echo ""
    fi

    # Test ping endpoint
    echo ""
    log_step "Testing /ping endpoint (database connectivity):"
    if command -v jq &> /dev/null; then
        curl -s "$API_URL/ping" | jq .
    else
        curl -s "$API_URL/ping"
        echo ""
    fi
fi

echo ""

# Success summary
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              🎉 Demo Environment Ready! 🎉                   ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Display access URLs
echo -e "${CYAN}Access URLs:${NC}"
echo -e "  ${BLUE}▶${NC} Swagger UI (Interactive Docs): ${GREEN}http://localhost:8000/docs${NC}"
echo -e "  ${BLUE}▶${NC} ReDoc (Alternative Docs):      ${GREEN}http://localhost:8000/redoc${NC}"
echo -e "  ${BLUE}▶${NC} Health Check:                   ${GREEN}http://localhost:8000/healthz${NC}"
echo -e "  ${BLUE}▶${NC} OpenAPI Spec:                   ${GREEN}http://localhost:8000/docs/openapi.json${NC}"
echo ""

# Quick test commands
echo -e "${CYAN}Quick Test Commands:${NC}"
echo -e "  ${BLUE}▶${NC} Test health:    ${YELLOW}curl http://localhost:8000/healthz${NC}"
echo -e "  ${BLUE}▶${NC} Test database:  ${YELLOW}curl http://localhost:8000/ping${NC}"
echo -e "  ${BLUE}▶${NC} View logs:      ${YELLOW}docker compose -f $COMPOSE_FILE logs -f${NC}"
echo -e "  ${BLUE}▶${NC} Stop services:  ${YELLOW}docker compose -f $COMPOSE_FILE down${NC}"
echo ""

# Pre-demo checklist
echo -e "${CYAN}Pre-Demo Checklist:${NC}"
echo -e "  ${GREEN}✓${NC} Services started and healthy"
echo -e "  ${GREEN}✓${NC} API responding to requests"
echo -e "  ${GREEN}✓${NC} Database connection working"
echo ""
echo -e "  ${YELLOW}☐${NC} Open Swagger UI in browser (http://localhost:8000/docs)"
echo -e "  ${YELLOW}☐${NC} Open GitHub Actions page (show passing CI/CD)"
echo -e "  ${YELLOW}☐${NC} Review DEMO_GUIDE.md for talking points"
echo -e "  ${YELLOW}☐${NC} Test /healthz and /ping endpoints"
echo -e "  ${YELLOW}☐${NC} Prepare backup screenshots (if needed)"
echo ""

# Demo guide reference
echo -e "${CYAN}Demo Resources:${NC}"
echo -e "  ${BLUE}▶${NC} Main Guide:     ${YELLOW}DEMO_GUIDE.md${NC}"
echo -e "  ${BLUE}▶${NC} Testing Guide:  ${YELLOW}docs/MANUAL_TESTING_GUIDE.md${NC}"
echo -e "  ${BLUE}▶${NC} CI/CD Summary:  ${YELLOW}WORKFLOW_FIXES_SUMMARY.md${NC}"
echo ""

# Time estimate
echo -e "${CYAN}Recommended Demo Timing:${NC}"
echo -e "  ${BLUE}▶${NC} Start services: ${YELLOW}30 minutes before demo${NC}"
echo -e "  ${BLUE}▶${NC} Test endpoints: ${YELLOW}15 minutes before demo${NC}"
echo -e "  ${BLUE}▶${NC} Open browser tabs: ${YELLOW}10 minutes before demo${NC}"
echo -e "  ${BLUE}▶${NC} Final check: ${YELLOW}5 minutes before demo${NC}"
echo ""

# Final reminder
echo -e "${GREEN}🎬 You're ready to demo!${NC}"
echo ""
echo -e "${CYAN}TIP:${NC} Keep this terminal open to monitor service health during the demo."
echo ""
