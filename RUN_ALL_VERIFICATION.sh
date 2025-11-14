#!/bin/bash
set -euo pipefail

#==============================================================================
# Complete Runtime Verification & PR Evidence Collection
# Run this script on your local machine where Docker is running
#==============================================================================

echo "=============================================="
echo "Runtime Verification & PR Evidence Collection"
echo "=============================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

#------------------------------------------------------------------------------
# A. Auto-locate repo root & branch; prep artifacts dir
#------------------------------------------------------------------------------
echo -e "${YELLOW}Phase A: Locating repository and preparing artifacts...${NC}"

# 1) Find repo root reliably (no hardcoded paths)
if git rev-parse --show-toplevel >/dev/null 2>&1; then
  REPO_ROOT="$(git rev-parse --show-toplevel)"
else
  # Fallback: search up to 3 levels for docker-compose.* and package.json in frontend
  REPO_ROOT="$(pwd)"
  for d in . .. ../.. ../../..; do
    if [ -f "$d/docker-compose.yml" ] || [ -f "$d/docker-compose.yaml" ]; then
      REPO_ROOT="$(cd "$d" && pwd)"
      break
    fi
  done
fi
cd "$REPO_ROOT"

# 2) Ensure correct branch
git fetch --all --prune --quiet 2>/dev/null || true
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)

TARGET_BRANCH="claude/audit-wiring-readiness-014VYQdX46CD1u2s6KGWqbGw"
if [ "$CURRENT_BRANCH" != "$TARGET_BRANCH" ]; then
  echo "Switching to $TARGET_BRANCH..."
  git checkout "$TARGET_BRANCH"
  git pull --rebase 2>/dev/null || true
fi

# 3) Artifacts dir
ART_DIR="artifacts/pr_evidence"
mkdir -p "$ART_DIR"
echo "$REPO_ROOT" > "$ART_DIR/repo_root.txt"
git rev-parse --abbrev-ref HEAD > "$ART_DIR/branch.txt"
git rev-parse HEAD > "$ART_DIR/commit_sha.txt"

echo -e "${GREEN}✓ Phase A complete${NC}"
echo "  - Repo root: $REPO_ROOT"
echo "  - Branch: $(cat "$ART_DIR/branch.txt")"
echo "  - Commit: $(cat "$ART_DIR/commit_sha.txt")"
echo ""

#------------------------------------------------------------------------------
# B. Bring up services (or confirm they're up) & wait until healthy
#------------------------------------------------------------------------------
echo -e "${YELLOW}Phase B: Verifying Docker services are running...${NC}"

# Compose file name normalization
COMPOSE_FILE="docker-compose.yml"
[ -f "docker-compose.yaml" ] && COMPOSE_FILE="docker-compose.yaml"

# Start services (idempotent - won't restart if already running)
echo "Ensuring services are up: docker compose -f $COMPOSE_FILE up -d"
docker compose -f "$COMPOSE_FILE" up -d

# Wait for API health
API_URL="http://localhost:8000"
echo "Waiting for API at $API_URL ..." | tee "$ART_DIR/wait_api.log"
for i in {1..60}; do
  if curl -fsS "$API_URL/api/v1/healthz" >/dev/null 2>&1; then
    echo -e "${GREEN}✓ API is up and healthy!${NC}" | tee -a "$ART_DIR/wait_api.log"
    break
  fi
  if [ $i -eq 60 ]; then
    echo -e "${RED}❌ API did not become healthy after 120 seconds${NC}"
    echo "Please check: docker compose logs api"
    exit 1
  fi
  sleep 2
done
echo ""

#------------------------------------------------------------------------------
# C. OpenAPI & endpoint count + tag verification
#------------------------------------------------------------------------------
echo -e "${YELLOW}Phase C: Collecting OpenAPI spec and verifying coverage...${NC}"

curl -fsS "$API_URL/openapi.json" -o "$ART_DIR/openapi.json"

# Parse OpenAPI using Python
python3 - <<'PY' | tee "$ART_DIR/openapi_summary.json"
import json
with open("artifacts/pr_evidence/openapi.json") as f:
    spec = json.load(f)
paths_count = len(spec.get("paths", {}))
tags = [t.get("name") for t in spec.get("tags", [])]
summary = {
    "paths": paths_count,
    "tags": tags,
    "has_workflow": "workflow" in tags,
    "has_automation": "automation" in tags,
    "has_data": "data" in tags,
    "has_system": "system" in tags
}
print(json.dumps(summary, indent=2))
PY

echo -e "${GREEN}✓ Phase C complete${NC}"
echo ""

#------------------------------------------------------------------------------
# D. Auth flip & write-guard checks (401→200)
#------------------------------------------------------------------------------
echo -e "${YELLOW}Phase D: Testing auth flip and write guard...${NC}"

# 1) Call protected PATCH without token → expect 401/403
echo "Testing PATCH without token (expect 401/403)..."
NO_TOKEN_CODE=$(curl -s -o "$ART_DIR/patch_no_token.json" -w "%{http_code}" \
  -X PATCH "$API_URL/api/v1/properties/demo-1" \
  -H "Content-Type: application/json" \
  --data '{"nickname":"demo"}' 2>/dev/null || echo "000")

echo "  Result: $NO_TOKEN_CODE" | tee "$ART_DIR/auth_flip_summary.txt"

# 2) Login to get token
echo "Logging in to get auth token..."
LOGIN_CODE=$(curl -s -o "$ART_DIR/login.json" -w "%{http_code}" \
  -X POST "$API_URL/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  --data '{"email":"demo@example.com","password":"demo123"}' 2>/dev/null || echo "000")

if [ -f "$ART_DIR/login.json" ]; then
  # Extract token using grep/sed if jq not available
  if command -v jq &> /dev/null; then
    jq -r '.access_token // empty' "$ART_DIR/login.json" > "$ART_DIR/token.txt"
  else
    grep -o '"access_token":"[^"]*"' "$ART_DIR/login.json" | sed 's/"access_token":"\([^"]*\)"/\1/' > "$ART_DIR/token.txt"
  fi
fi

if [ ! -s "$ART_DIR/token.txt" ]; then
  echo -e "${RED}❌ Failed to get auth token. Login response code: $LOGIN_CODE${NC}"
  cat "$ART_DIR/login.json" 2>/dev/null || echo "No login response"
  exit 1
fi

# 3) Repeat PATCH with token
echo "Testing PATCH with token (expect 200/204)..."
TOKEN="$(cat "$ART_DIR/token.txt")"
WITH_TOKEN_CODE=$(curl -s -o "$ART_DIR/patch_with_token.json" -w "%{http_code}" \
  -X PATCH "$API_URL/api/v1/properties/demo-1" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  --data '{"nickname":"demo"}' 2>/dev/null || echo "000")

echo "  Result: $WITH_TOKEN_CODE" | tee -a "$ART_DIR/auth_flip_summary.txt"

{
  echo "SUMMARY:"
  echo "  - PATCH without token: $NO_TOKEN_CODE (expect 401/403)"
  echo "  - PATCH with token: $WITH_TOKEN_CODE (expect 200/204)"
} | tee -a "$ART_DIR/auth_flip_summary.txt"

echo -e "${GREEN}✓ Phase D complete${NC}"
echo ""

#------------------------------------------------------------------------------
# E. CORS sanity (preflight + simple GET)
#------------------------------------------------------------------------------
echo -e "${YELLOW}Phase E: Verifying CORS headers...${NC}"

# Preflight example
echo "Testing CORS preflight (OPTIONS)..."
curl -s -D "$ART_DIR/cors_preflight_headers.txt" -o /dev/null \
  -X OPTIONS "$API_URL/api/v1/properties" \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: content-type,authorization" 2>/dev/null || true

# Simple GET with Origin
echo "Testing CORS on GET request..."
curl -s -D "$ART_DIR/cors_get_headers.txt" -o "$ART_DIR/cors_get_body.json" \
  -H "Origin: http://localhost:3000" \
  "$API_URL/api/v1/healthz" 2>/dev/null || true

# Check for CORS header
if grep -qi '^access-control-allow-origin:' "$ART_DIR/cors_get_headers.txt"; then
  echo -e "${GREEN}✓ CORS headers present${NC}"
else
  echo -e "${YELLOW}⚠ CORS headers not found in response${NC}"
fi

echo -e "${GREEN}✓ Phase E complete${NC}"
echo ""

#------------------------------------------------------------------------------
# F. SSE proof (headless): open stream, emit, capture one event
#------------------------------------------------------------------------------
echo -e "${YELLOW}Phase F: Testing SSE stream end-to-end...${NC}"

SSE_STREAM="$ART_DIR/sse_stream.jsonl"
rm -f "$SSE_STREAM"

# Start stream in background
echo "Opening SSE stream..."
( timeout 10s curl -N -H "Accept: text/event-stream" "$API_URL/api/v1/sse/stream" 2>/dev/null | tee "$SSE_STREAM" ) &
SSE_PID=$!
sleep 2

# Emit a test event
echo "Emitting test event..."
EMIT_CODE=$(curl -s -o "$ART_DIR/sse_emit_resp.json" -w "%{http_code}" \
  -X POST "$API_URL/api/v1/sse/test/emit" \
  -H "Content-Type: application/json" \
  --data '{"event_type":"property_updated","data":{"id":"pr-verify-123","source":"pr-evidence"}}' \
  2>/dev/null || echo "000")

echo "  Emit response code: $EMIT_CODE" | tee "$ART_DIR/sse_emit_code.txt"

# Wait a bit for event to be received
sleep 3

# Kill the background stream
kill $SSE_PID 2>/dev/null || true
wait $SSE_PID 2>/dev/null || true

# Summarize the first event lines
echo "Captured SSE stream (first 10 lines):"
( head -n 10 "$SSE_STREAM" 2>/dev/null || echo "(no stream lines captured)" ) | tee "$ART_DIR/sse_stream_head.txt"

if grep -q 'data:' "$ART_DIR/sse_stream.jsonl" 2>/dev/null; then
  echo -e "${GREEN}✓ SSE event received!${NC}"
else
  echo -e "${YELLOW}⚠ No SSE events captured${NC}"
fi

echo -e "${GREEN}✓ Phase F complete${NC}"
echo ""

#------------------------------------------------------------------------------
# G. Minimal page-walk proxy (API only)
#------------------------------------------------------------------------------
echo -e "${YELLOW}Phase G: Testing API endpoints for all 6 pages...${NC}"

# Adjust these to the actual API calls each page uses in your app
declare -a CHECKS=(
  "$API_URL/api/v1/workflow/smart-lists"
  "$API_URL/api/v1/automation/cadence-rules"
  "$API_URL/api/v1/leads"
  "$API_URL/api/v1/deals"
  "$API_URL/api/v1/data/summary"
  "$API_URL/api/v1/system/health"
)

: > "$ART_DIR/page_walk.txt"
for url in "${CHECKS[@]}"; do
  CODE=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || echo "000")
  echo "  $url → $CODE" | tee -a "$ART_DIR/page_walk.txt"
done

echo -e "${GREEN}✓ Phase G complete${NC}"
echo ""

#------------------------------------------------------------------------------
# H. Gate evaluation & PR body
#------------------------------------------------------------------------------
echo -e "${YELLOW}Phase H: Evaluating gates and generating PR body...${NC}"

# Parse results
if command -v jq &> /dev/null; then
  PATHS=$(jq -r '.paths' "$ART_DIR/openapi_summary.json" 2>/dev/null || echo "0")
  HAS_WORKFLOW=$(jq -r '.has_workflow' "$ART_DIR/openapi_summary.json" 2>/dev/null || echo "false")
  HAS_AUTOMATION=$(jq -r '.has_automation' "$ART_DIR/openapi_summary.json" 2>/dev/null || echo "false")
  HAS_DATA=$(jq -r '.has_data' "$ART_DIR/openapi_summary.json" 2>/dev/null || echo "false")
  HAS_SYSTEM=$(jq -r '.has_system' "$ART_DIR/openapi_summary.json" 2>/dev/null || echo "false")
else
  PATHS=$(grep -o '"paths":[0-9]*' "$ART_DIR/openapi_summary.json" | grep -o '[0-9]*' || echo "0")
  HAS_WORKFLOW=$(grep -o '"has_workflow":[a-z]*' "$ART_DIR/openapi_summary.json" | grep -o '[a-z]*' || echo "false")
  HAS_AUTOMATION=$(grep -o '"has_automation":[a-z]*' "$ART_DIR/openapi_summary.json" | grep -o '[a-z]*' || echo "false")
  HAS_DATA=$(grep -o '"has_data":[a-z]*' "$ART_DIR/openapi_summary.json" | grep -o '[a-z]*' || echo "false")
  HAS_SYSTEM=$(grep -o '"has_system":[a-z]*' "$ART_DIR/openapi_summary.json" | grep -o '[a-z]*' || echo "false")
fi

# Gate 1: OpenAPI coverage
if [ "$PATHS" -ge 140 ] && [ "$HAS_WORKFLOW" = "true" ] && [ "$HAS_AUTOMATION" = "true" ] && [ "$HAS_DATA" = "true" ] && [ "$HAS_SYSTEM" = "true" ]; then
  G1="PASS"
else
  G1="FAIL"
fi

# Gate 2: Auth flip
if ([ "$NO_TOKEN_CODE" = "401" ] || [ "$NO_TOKEN_CODE" = "403" ]) && ([ "$WITH_TOKEN_CODE" = "200" ] || [ "$WITH_TOKEN_CODE" = "204" ]); then
  G2="PASS"
else
  G2="FAIL"
fi

# Gate 3: Write guard (reuse NO_TOKEN_CODE)
if [ "$NO_TOKEN_CODE" = "401" ] || [ "$NO_TOKEN_CODE" = "403" ]; then
  G3="PASS"
else
  G3="FAIL"
fi

# Gate 4: CORS
if grep -qi '^access-control-allow-origin:' "$ART_DIR/cors_get_headers.txt" 2>/dev/null; then
  G4="PASS"
else
  G4="FAIL"
fi

# Gate 5: SSE
if grep -q 'data:' "$ART_DIR/sse_stream.jsonl" 2>/dev/null; then
  G5="PASS"
else
  G5="FAIL"
fi

# Write gates summary
{
  echo "G1 OpenAPI/tag coverage: $G1 (paths=$PATHS, workflow=$HAS_WORKFLOW, automation=$HAS_AUTOMATION, data=$HAS_DATA, system=$HAS_SYSTEM)"
  echo "G2 Auth flip 401→200: $G2 (no_token=$NO_TOKEN_CODE, with_token=$WITH_TOKEN_CODE)"
  echo "G3 Write guard unauth write blocked: $G3 (no_token=$NO_TOKEN_CODE)"
  echo "G4 CORS headers present: $G4"
  echo "G5 SSE emit→receive: $G5"
} | tee "$ART_DIR/gates_summary.txt"

# Generate PR body
PR_MD="$ART_DIR/PR_BODY.md"
cat > "$PR_MD" <<EOF
# Demo Readiness — Runtime Evidence

**Commit:** \`$(cat "$ART_DIR/commit_sha.txt")\`
**Branch:** \`$(cat "$ART_DIR/branch.txt")\`
**Verification Date:** $(date -u +"%Y-%m-%d %H:%M:%S UTC")

## Gate Results

| Gate | Status | Details |
|------|--------|---------|
| **G1** OpenAPI/tag coverage | **$G1** | paths=$PATHS, workflow=$HAS_WORKFLOW, automation=$HAS_AUTOMATION, data=$HAS_DATA, system=$HAS_SYSTEM |
| **G2** Auth flip 401→200 | **$G2** | no_token=$NO_TOKEN_CODE, with_token=$WITH_TOKEN_CODE |
| **G3** Write guard (unauth blocked) | **$G3** | unauth_code=$NO_TOKEN_CODE |
| **G4** CORS headers present | **$G4** | - |
| **G5** SSE emit→receive | **$G5** | - |

## OpenAPI Summary

\`\`\`json
$(cat "$ART_DIR/openapi_summary.json")
\`\`\`

## Auth Flip Details

\`\`\`
$(cat "$ART_DIR/auth_flip_summary.txt")
\`\`\`

## SSE Stream Capture (first 10 lines)

\`\`\`
$(cat "$ART_DIR/sse_stream_head.txt" 2>/dev/null || echo "(no stream lines captured)")
\`\`\`

## Page Walk (API endpoints)

\`\`\`
$(cat "$ART_DIR/page_walk.txt")
\`\`\`

---

## Browser-Only Proofs (To Be Verified Manually)

The following checks require browser-based verification:

1. **Auth Banner**: Login → Console shows "🔐 AUTH: Demo token attached"
2. **SSE Badge**: Dashboard header shows **🟢 Connected**
3. **SSE Event Test**: Admin → "Emit Test Event" → Toast appears + Badge flashes
4. **Page Walk**: All 6 pages load with no console errors

### Browser Testing Checklist

- [ ] Login shows auth token in console
- [ ] Dashboard shows SSE badge as "Connected"
- [ ] Admin test event triggers toast notification
- [ ] All pages load: workflow, automation, leads, deals, data, admin
- [ ] No red console errors on any page
- [ ] Network tab shows 200 responses

---

**All artifacts saved to:** \`$ART_DIR/\`
EOF

echo ""
echo "=============================================="
echo -e "${GREEN}✓ Evidence Collection Complete!${NC}"
echo "=============================================="
echo ""
echo "Gate Summary:"
echo "  G1 (OpenAPI): $G1"
echo "  G2 (Auth flip): $G2"
echo "  G3 (Write guard): $G3"
echo "  G4 (CORS): $G4"
echo "  G5 (SSE): $G5"
echo ""
echo "Next Steps:"
echo "  1. Review: $PR_MD"
echo "  2. Complete browser-based checks (see PR_BODY.md)"
echo "  3. Take 4 screenshots:"
echo "     - Auth token console log"
echo "     - SSE badge showing Connected"
echo "     - Toast notification appearing"
echo "     - All pages with no errors"
echo "  4. Paste PR_BODY.md into your pull request"
echo ""
echo "All artifacts saved to: $ART_DIR/"
