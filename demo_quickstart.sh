#!/usr/bin/env bash
#
# Real Estate OS - Demo Quickstart
# Get the platform running in 2 minutes
#
# Usage: ./demo_quickstart.sh [branch]
#   branch: full-consolidation (default) | mock-providers-twilio
#
set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration
BRANCH=${1:-full-consolidation}
API_URL="http://localhost:8000"
TIMEOUT=120

echo -e "${CYAN}"
cat << "EOF"
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║               Real Estate OS - Interactive Demo                 ║
║                                                                  ║
║  Decision speed, not just data                                  ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[!]${NC} $1"; }
log_step() { echo -e "${CYAN}➜ $1${NC}"; }

# ============================================================================
# STEP 1: Select Branch
# ============================================================================

log_step "STEP 1: Selecting branch..."

if [ "$BRANCH" = "full-consolidation" ]; then
  BRANCH_REF="origin/claude/full-consolidation-011CUo8XMMdfTgWrwjpAVcE1"
  log_info "Using full-consolidation (152 endpoints, 47 tests, production features)"
elif [ "$BRANCH" = "mock-providers-twilio" ]; then
  BRANCH_REF="origin/claude/mock-providers-twilio-011CUoNy9C1cvzAMeQmPjREU"
  log_info "Using mock-providers-twilio (132 endpoints, demo-focused)"
else
  log_error "Unknown branch: $BRANCH"
  echo "Usage: $0 [full-consolidation|mock-providers-twilio]"
  exit 1
fi

git fetch --all --prune --quiet
git checkout -B "$BRANCH" "$BRANCH_REF" --quiet || {
  log_error "Failed to checkout $BRANCH_REF"
  exit 1
}

log_success "Checked out $BRANCH"

# ============================================================================
# STEP 2: Environment Setup
# ============================================================================

log_step "STEP 2: Setting up environment..."

if [ ! -f .env.mock ]; then
  log_error ".env.mock not found"
  exit 1
fi

cp .env.mock .env
cat >> .env <<EOF

# Demo mode
MOCK_MODE=true
VERIFY_MODE=false
LOG_LEVEL=INFO

# Demo admin credentials
DEMO_ADMIN_EMAIL=admin@demo.com
DEMO_ADMIN_PASSWORD=password123
EOF

log_success "Environment configured (MOCK_MODE=true)"

# ============================================================================
# STEP 3: Start Docker Stack
# ============================================================================

log_step "STEP 3: Starting Docker stack..."

# Clean previous state
log_info "Cleaning previous containers..."
docker compose down -v --remove-orphans 2>/dev/null || true

# Start stack
log_info "Starting services (this may take 2-3 minutes)..."
docker compose up -d --wait || {
  log_error "Docker Compose failed to start"
  docker compose logs --tail=50
  exit 1
}

log_success "Docker stack started"

# Show running services
echo ""
log_info "Running services:"
docker compose ps --format "table {{.Service}}\t{{.Status}}\t{{.Ports}}"

# ============================================================================
# STEP 4: Wait for API Health
# ============================================================================

log_step "STEP 4: Waiting for API to be healthy..."

ATTEMPTS=$((TIMEOUT / 2))
until curl -fsS "${API_URL}/healthz" >/dev/null 2>&1 || [ $ATTEMPTS -eq 0 ]; do
  echo -n "."
  sleep 2
  ATTEMPTS=$((ATTEMPTS - 1))
done
echo ""

if [ $ATTEMPTS -eq 0 ]; then
  log_error "API never became healthy"
  echo ""
  log_info "API logs (last 50 lines):"
  docker compose logs api --tail=50
  exit 1
fi

log_success "API is healthy"

# ============================================================================
# STEP 5: Quick Verification
# ============================================================================

log_step "STEP 5: Quick verification..."

# Check OpenAPI
ENDPOINT_COUNT=$(curl -s "${API_URL}/docs/openapi.json" | jq '.paths | keys | length' 2>/dev/null || echo "0")
log_info "OpenAPI endpoint count: ${ENDPOINT_COUNT}"

if [ "$ENDPOINT_COUNT" -lt 10 ]; then
  log_warning "Only $ENDPOINT_COUNT endpoints found (expected 100+)"
  log_warning "This may indicate a routing issue"
else
  log_success "Endpoint count looks good: ${ENDPOINT_COUNT}"
fi

# Check for errors in logs
ERROR_COUNT=$(docker compose logs api --tail=200 | grep -ciE "error|exception|traceback" || echo 0)
if [ "$ERROR_COUNT" -gt 5 ]; then
  log_warning "Found $ERROR_COUNT error/exception lines in logs"
  log_info "Review with: docker compose logs api | grep -i error"
else
  log_success "Logs look clean (< 5 errors)"
fi

# ============================================================================
# STEP 6: Run Migrations
# ============================================================================

log_step "STEP 6: Running database migrations..."

docker compose exec -T api alembic upgrade head >/dev/null 2>&1 || {
  log_warning "Migrations failed or not configured"
  log_info "This may be expected if the branch doesn't use Alembic"
}

log_success "Migrations complete (or skipped)"

# ============================================================================
# STEP 7: Demo Information
# ============================================================================

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                                  ║${NC}"
echo -e "${GREEN}║                  DEMO IS READY! 🚀                              ║${NC}"
echo -e "${GREEN}║                                                                  ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${CYAN}Available Services:${NC}"
echo "  • API (FastAPI):        ${API_URL}/docs"
echo "  • API Health:           ${API_URL}/healthz"
echo "  • OpenAPI Spec:         ${API_URL}/docs/openapi.json"
echo "  • Flower (Celery):      http://localhost:5555  (if configured)"
echo "  • MailHog (Email):      http://localhost:8025  (mock emails)"
echo "  • MinIO Console:        http://localhost:9001  (mock storage)"
echo ""

echo -e "${CYAN}Quick Stats:${NC}"
echo "  • Branch:               $BRANCH"
echo "  • Endpoints:            ${ENDPOINT_COUNT}"
echo "  • Mode:                 MOCK (no external APIs)"
echo ""

echo -e "${CYAN}Next Steps:${NC}"
echo "  1. Open API docs:       ${API_URL}/docs"
echo "  2. Run interactive demo: ./demo_interactive.sh"
echo "  3. Or manually explore with curl (see DEMO_RUNBOOK.md)"
echo ""

echo -e "${CYAN}Useful Commands:${NC}"
echo "  • View logs:            docker compose logs -f api"
echo "  • Stop demo:            docker compose down -v"
echo "  • Restart:              docker compose restart api"
echo "  • Shell access:         docker compose exec api bash"
echo ""

echo -e "${YELLOW}Demo Admin Credentials:${NC}"
echo "  Email:    admin@demo.com"
echo "  Password: password123"
echo ""

# ============================================================================
# STEP 8: Optional - Auto-open browser
# ============================================================================

if command -v xdg-open >/dev/null 2>&1; then
  read -p "Open API docs in browser? (y/n) " -n 1 -r
  echo
  if [[ $REPLY =~ ^[Yy]$ ]]; then
    xdg-open "${API_URL}/docs" 2>/dev/null || true
  fi
elif command -v open >/dev/null 2>&1; then
  read -p "Open API docs in browser? (y/n) " -n 1 -r
  echo
  if [[ $REPLY =~ ^[Yy]$ ]]; then
    open "${API_URL}/docs" 2>/dev/null || true
  fi
fi

echo -e "${GREEN}Demo quickstart complete! ✨${NC}"
echo ""
