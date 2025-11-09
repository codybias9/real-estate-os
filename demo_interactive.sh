#!/usr/bin/env bash
#
# Real Estate OS - Interactive Demo
# Walk through key platform capabilities
#
set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

API_URL="http://localhost:8000"
TOKEN=""

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; }
log_demo() { echo -e "${MAGENTA}[DEMO]${NC} $1"; }
log_step() { echo -e "${CYAN}➜ $1${NC}"; }

pause() {
  echo ""
  read -p "$(echo -e ${YELLOW}Press ENTER to continue...${NC})"
  echo ""
}

run_api_call() {
  local METHOD=$1
  local ENDPOINT=$2
  local DATA=${3:-}

  echo -e "${CYAN}API Call:${NC} $METHOD $ENDPOINT"

  if [ -n "$DATA" ]; then
    echo -e "${CYAN}Payload:${NC}"
    echo "$DATA" | jq . 2>/dev/null || echo "$DATA"
  fi

  echo ""
  echo -e "${CYAN}Response:${NC}"

  local RESPONSE
  if [ -n "$DATA" ]; then
    RESPONSE=$(curl -s -X "$METHOD" "${API_URL}${ENDPOINT}" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d "$DATA")
  else
    RESPONSE=$(curl -s -X "$METHOD" "${API_URL}${ENDPOINT}" \
      -H "Authorization: Bearer $TOKEN")
  fi

  echo "$RESPONSE" | jq . 2>/dev/null || echo "$RESPONSE"
  echo ""

  echo "$RESPONSE"
}

# ============================================================================
# Banner
# ============================================================================

clear
echo -e "${CYAN}"
cat << "EOF"
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║            Real Estate OS - Interactive Demo                    ║
║                                                                  ║
║            Walk through key platform capabilities               ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

# ============================================================================
# Pre-flight Check
# ============================================================================

log_step "Pre-flight check..."

if ! curl -fsS "${API_URL}/healthz" >/dev/null 2>&1; then
  log_error "API is not running"
  echo ""
  log_info "Start the platform first:"
  echo "  ./demo_quickstart.sh"
  exit 1
fi

log_success "API is running"
echo ""

# ============================================================================
# DEMO 1: Authentication
# ============================================================================

log_demo "DEMO 1: Authentication & User Management"
echo ""
pause

log_step "1.1 - Register a new user"
REGISTER_RESPONSE=$(run_api_call POST "/api/v1/auth/register" '{
  "email": "investor@example.com",
  "password": "SecurePass123!",
  "name": "Demo Investor",
  "role": "investor"
}')

pause

log_step "1.2 - Login and get access token"
LOGIN_RESPONSE=$(run_api_call POST "/api/v1/auth/login" '{
  "email": "investor@example.com",
  "password": "SecurePass123!"
}')

TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.access_token // .token // empty' 2>/dev/null || echo "")

if [ -z "$TOKEN" ]; then
  log_warning "No token received, trying without auth"
else
  log_success "Token received: ${TOKEN:0:50}..."
fi

pause

# ============================================================================
# DEMO 2: Property Management
# ============================================================================

log_demo "DEMO 2: Property Management & Enrichment"
echo ""
pause

log_step "2.1 - Create a property"
PROPERTY_RESPONSE=$(run_api_call POST "/api/v1/properties" '{
  "address": "123 Market Street",
  "city": "San Francisco",
  "state": "CA",
  "zip": "94103",
  "property_type": "single_family",
  "bedrooms": 3,
  "bathrooms": 2,
  "sqft": 1850,
  "status": "active"
}')

PROPERTY_ID=$(echo "$PROPERTY_RESPONSE" | jq -r '.id // .property_id // empty' 2>/dev/null || echo "")

pause

log_step "2.2 - List all properties"
run_api_call GET "/api/v1/properties" >/dev/null

pause

if [ -n "$PROPERTY_ID" ]; then
  log_step "2.3 - Get property details (with enrichment)"
  run_api_call GET "/api/v1/properties/${PROPERTY_ID}" >/dev/null

  log_info "Look for enriched fields like:"
  echo "  • assessed_value"
  echo "  • market_value"
  echo "  • tax_amount"
  echo "  • owner_name"
  echo "  • last_sale_date"

  pause
fi

# ============================================================================
# DEMO 3: Quick Wins (if available)
# ============================================================================

log_demo "DEMO 3: Quick Wins - Template Generation"
echo ""
pause

log_step "3.1 - Check available templates"
run_api_call GET "/api/v1/quick-wins/templates" >/dev/null || {
  log_warning "Quick wins endpoint not available on this branch"
}

pause

# ============================================================================
# DEMO 4: Workflow Automation
# ============================================================================

log_demo "DEMO 4: Workflow Automation"
echo ""
pause

log_step "4.1 - Get next best actions"
run_api_call GET "/api/v1/workflow/next-best-action" >/dev/null || {
  log_warning "Workflow endpoint not available"
}

pause

log_step "4.2 - Create a workflow task"
run_api_call POST "/api/v1/workflow/tasks" '{
  "title": "Follow up with investor",
  "description": "Send property details and schedule viewing",
  "priority": "high",
  "due_date": "2025-11-15"
}' >/dev/null || {
  log_warning "Task creation not available"
}

pause

# ============================================================================
# DEMO 5: Communications (Mock)
# ============================================================================

log_demo "DEMO 5: Communications (Email & SMS Mock)"
echo ""
pause

log_step "5.1 - Send email (mock)"
run_api_call POST "/api/v1/communications/email" '{
  "to": "investor@example.com",
  "subject": "Property Match: 123 Market Street",
  "template": "property_match",
  "data": {
    "property_address": "123 Market Street, SF",
    "estimated_value": "$1.2M"
  }
}' >/dev/null || {
  log_warning "Email endpoint not available"
}

log_info "Mock emails are captured in MailHog: http://localhost:8025"

pause

log_step "5.2 - Send SMS (mock)"
run_api_call POST "/api/v1/communications/sms" '{
  "to": "+14155551234",
  "message": "New property match! 123 Market St - $1.2M. View details: https://demo.com/prop/123"
}' >/dev/null || {
  log_warning "SMS endpoint not available"
}

pause

# ============================================================================
# DEMO 6: Real-time Events (SSE)
# ============================================================================

log_demo "DEMO 6: Real-time Events (Server-Sent Events)"
echo ""
pause

log_step "6.1 - Open SSE stream (will run for 10 seconds)"
echo ""
log_info "Watching for real-time events..."

timeout 10 curl -N -H "Accept: text/event-stream" \
  -H "Authorization: Bearer $TOKEN" \
  "${API_URL}/api/v1/events/stream" 2>/dev/null | sed -n '1,20p' || {
  log_warning "SSE endpoint not available or no events in 10s"
}

echo ""
pause

# ============================================================================
# DEMO 7: Background Jobs
# ============================================================================

log_demo "DEMO 7: Background Jobs & Task Queue"
echo ""
pause

log_step "7.1 - List background jobs"
run_api_call GET "/api/v1/jobs" >/dev/null || {
  log_warning "Jobs endpoint not available"
}

pause

log_step "7.2 - Trigger enrichment job"
if [ -n "$PROPERTY_ID" ]; then
  run_api_call POST "/api/v1/jobs/enrich" "{
    \"property_id\": \"${PROPERTY_ID}\",
    \"sources\": [\"assessor\", \"market_data\", \"demographics\"]
  }" >/dev/null || {
    log_warning "Enrichment job endpoint not available"
  }
fi

pause

# ============================================================================
# DEMO 8: Analytics & Insights
# ============================================================================

log_demo "DEMO 8: Analytics & Portfolio Insights"
echo ""
pause

log_step "8.1 - Portfolio overview"
run_api_call GET "/api/v1/portfolio/overview" >/dev/null || {
  log_warning "Portfolio endpoint not available"
}

pause

log_step "8.2 - Deal economics"
run_api_call GET "/api/v1/portfolio/deals/economics" >/dev/null || {
  log_warning "Deal economics not available"
}

pause

# ============================================================================
# DEMO 9: Admin & System
# ============================================================================

log_demo "DEMO 9: Admin & System Management"
echo ""
pause

log_step "9.1 - System health (detailed)"
run_api_call GET "/api/v1/admin/health" >/dev/null || {
  log_warning "Admin health endpoint not available"
}

pause

log_step "9.2 - Dead Letter Queue (DLQ) status"
run_api_call GET "/api/v1/admin/dlq" >/dev/null || {
  log_warning "DLQ endpoint not available"
}

pause

# ============================================================================
# Summary
# ============================================================================

clear
echo -e "${GREEN}"
cat << "EOF"
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║                  DEMO COMPLETE! ✨                              ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

echo -e "${CYAN}You've explored:${NC}"
echo "  ✓ Authentication & user management"
echo "  ✓ Property CRUD & enrichment"
echo "  ✓ Quick wins & templates"
echo "  ✓ Workflow automation"
echo "  ✓ Communications (email/SMS)"
echo "  ✓ Real-time events (SSE)"
echo "  ✓ Background jobs"
echo "  ✓ Analytics & insights"
echo "  ✓ Admin & system management"
echo ""

echo -e "${CYAN}Next Steps:${NC}"
echo "  1. Explore API docs:       ${API_URL}/docs"
echo "  2. View mock emails:       http://localhost:8025"
echo "  3. Check Flower (jobs):    http://localhost:5555"
echo "  4. Review logs:            docker compose logs -f api"
echo ""

echo -e "${CYAN}Customize the Demo:${NC}"
echo "  • Edit this script:        vim demo_interactive.sh"
echo "  • Create properties:       curl -X POST ${API_URL}/api/v1/properties ..."
echo "  • Test workflows:          See DEMO_RUNBOOK.md for more examples"
echo ""

echo -e "${YELLOW}Stop the demo:${NC}"
echo "  docker compose down -v"
echo ""

log_success "Demo session complete!"
