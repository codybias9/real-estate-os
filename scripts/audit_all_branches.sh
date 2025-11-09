#!/usr/bin/env bash
set -euo pipefail

TS=$(date +"%Y%m%d_%H%M%S")
OUT="audit_artifacts/branch_comparison_${TS}"
mkdir -p "${OUT}"

# Branches to audit
BRANCHES=(
  "origin/claude/mock-providers-twilio-011CUoNy9C1cvzAMeQmPjREU"
  "origin/claude/review-real-estate-api-011CUoxkF8YQMZHkH78uaABC"
  "origin/claude/crm-platform-full-implementation-011CUob6oo4RPnAbQsWxSPrW"
  "origin/claude/continue-api-implementation-011CUorMFDQTXZTAgKxzs2uQ"
  "origin/claude/full-consolidation-011CUo8XMMdfTgWrwjpAVcE1"
)

# Current branch for restoration
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)

echo "Auditing ${#BRANCHES[@]} branches..."
echo "Results will be saved to: ${OUT}"
echo ""

# CSV header
echo "Branch,Endpoints,Routers,Models,DAGs,Tests,Frontend,Docker Compose,Commit SHA,Last Commit" > "${OUT}/comparison.csv"

for BRANCH in "${BRANCHES[@]}"; do
  # Extract short name
  SHORT_NAME=$(echo "${BRANCH}" | sed 's|origin/||; s|claude/||; s|-[0-9A-Za-z]\{24\}$||')

  echo "========================================="
  echo "Checking out: ${BRANCH}"
  echo "========================================="

  # Create branch-specific output dir
  BRANCH_DIR="${OUT}/${SHORT_NAME}"
  mkdir -p "${BRANCH_DIR}"

  # Checkout branch (detached HEAD to avoid conflicts)
  git checkout "${BRANCH}" --detach 2>&1 | tee "${BRANCH_DIR}/checkout.log" || {
    echo "FAILED to checkout ${BRANCH}" | tee "${BRANCH_DIR}/error.txt"
    echo "${SHORT_NAME},ERROR,ERROR,ERROR,ERROR,ERROR,ERROR,ERROR,ERROR,checkout failed" >> "${OUT}/comparison.csv"
    continue
  }

  # Get commit info
  COMMIT_SHA=$(git rev-parse --short HEAD)
  LAST_COMMIT=$(git log -1 --format="%s" | head -c 80)

  # Count endpoints (FastAPI decorators)
  ENDPOINTS=$(find api -type f -name "*.py" 2>/dev/null | xargs grep -cE "@router\.(get|post|put|patch|delete)\(" 2>/dev/null || echo 0)

  # Count router files
  ROUTERS=$(find api -type f -name "*.py" 2>/dev/null | xargs grep -l "APIRouter" 2>/dev/null | wc -l || echo 0)

  # Count models (SQLAlchemy Base subclasses)
  MODELS=$(find . -type f -name "*.py" 2>/dev/null | xargs grep -hE "^class\s+[A-Z][A-Za-z0-9_]*\(.+Base" 2>/dev/null | wc -l || echo 0)

  # Count DAG files
  DAGS=$(find . -type f -path "*/dags/*.py" 2>/dev/null | wc -l || echo 0)

  # Count test files
  TESTS=$(find . -type f -name "test_*.py" 2>/dev/null | wc -l || echo 0)

  # Check for frontend
  FRONTEND="No"
  [ -f package.json ] && FRONTEND="Yes"

  # Check for docker-compose
  COMPOSE="No"
  [ -f docker-compose.yml ] && COMPOSE="Yes"

  # Save detailed counts
  cat > "${BRANCH_DIR}/counts.txt" <<EOF
Branch: ${BRANCH}
Commit: ${COMMIT_SHA}
Last Commit: ${LAST_COMMIT}

Endpoints: ${ENDPOINTS}
Routers: ${ROUTERS}
Models: ${MODELS}
DAGs: ${DAGS}
Tests: ${TESTS}
Frontend: ${FRONTEND}
Docker Compose: ${COMPOSE}
EOF

  # List router files
  find api -type f -name "*.py" 2>/dev/null | xargs grep -l "APIRouter" 2>/dev/null | sort > "${BRANCH_DIR}/router_files.txt" || true

  # List endpoint decorators
  find api -type f -name "*.py" 2>/dev/null | xargs grep -nE "@router\.(get|post|put|patch|delete)\(" 2>/dev/null > "${BRANCH_DIR}/endpoints.txt" || true

  # Add to CSV
  echo "${SHORT_NAME},${ENDPOINTS},${ROUTERS},${MODELS},${DAGS},${TESTS},${FRONTEND},${COMPOSE},${COMMIT_SHA},\"${LAST_COMMIT}\"" >> "${OUT}/comparison.csv"

  echo "✓ ${SHORT_NAME}: ${ENDPOINTS} endpoints, ${ROUTERS} routers, ${MODELS} models"
  echo ""
done

# Return to original branch
echo "Returning to original branch: ${CURRENT_BRANCH}"
git checkout "${CURRENT_BRANCH}"

echo ""
echo "========================================="
echo "Audit Complete!"
echo "========================================="
echo "Results saved to: ${OUT}/comparison.csv"
echo ""
cat "${OUT}/comparison.csv" | column -t -s','

echo ""
echo "Detailed results for each branch available in:"
echo "  ${OUT}/<branch-name>/counts.txt"
echo "  ${OUT}/<branch-name>/endpoints.txt"
echo "  ${OUT}/<branch-name>/router_files.txt"
