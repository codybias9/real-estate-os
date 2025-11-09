#!/usr/bin/env bash
set -euo pipefail

TS=$(date +"%Y%m%d_%H%M%S")
OUT="audit_artifacts/${TS}"
mkdir -p "${OUT}/static" "${OUT}/recon" "${OUT}/lists"

echo "branch: $(git rev-parse --abbrev-ref HEAD)" | tee "${OUT}/branch.txt"
git rev-parse HEAD | tee "${OUT}/commit_sha.txt"
git status --porcelain | tee "${OUT}/git_status.txt"

# LOC
echo "=== LOC (by language) ===" | tee "${OUT}/static/loc.txt"
if command -v cloc >/dev/null 2>&1; then
  cloc . --exclude-dir=node_modules,.next,.git,__pycache__,.venv --quiet | tee -a "${OUT}/static/loc.txt"
else
  echo "(cloc not installed) falling back to wc -l" | tee -a "${OUT}/static/loc.txt"
  { find . -name "*.py" -not -path "*/node_modules/*" -not -path "*/.git/*" -not -path "*/__pycache__/*" -print0 | xargs -0 wc -l | tail -n1 ; } | tee -a "${OUT}/static/loc.txt"
fi

# Endpoint extraction (FastAPI-style decorators)
echo "=== Endpoint decorators ===" | tee "${OUT}/static/endpoints_decorators.txt"
find api -type f -name "*.py" 2>/dev/null | xargs grep -nE "@router\.(get|post|put|patch|delete)\(" \
  | tee "${OUT}/lists/endpoints_grep.txt" || true
TOTAL=$(wc -l < "${OUT}/lists/endpoints_grep.txt" 2>/dev/null || echo 0)
echo "DECLARED_ENDPOINTS=${TOTAL}" | tee -a "${OUT}/static/endpoints_decorators.txt"

# Router files
find api -type f -name "*.py" | xargs grep -l "APIRouter" 2>/dev/null | sort | tee "${OUT}/lists/router_files.txt" || true
wc -l < "${OUT}/lists/router_files.txt" | xargs echo "ROUTER_FILES=" | tee -a "${OUT}/static/endpoints_decorators.txt"

# Models (SQLAlchemy Base subclasses)
echo "=== SQLAlchemy models ===" | tee "${OUT}/static/models.txt"
find db -type f -name "*.py" 2>/dev/null | xargs grep -nE "^class\s+[A-Z][A-Za-z0-9_]*\(.+Base" \
  | tee "${OUT}/lists/models_raw.txt" || true
cut -d':' -f3 "${OUT}/lists/models_raw.txt" | sed 's/class\s\+\([A-Za-z0-9_]\+\).*/\1/' | sort -u \
  | tee "${OUT}/lists/models_names.txt" || true
wc -l < "${OUT}/lists/models_names.txt" | xargs echo "MODEL_COUNT=" | tee -a "${OUT}/static/models.txt"

# Alembic migrations
echo "=== Alembic migrations ===" | tee "${OUT}/static/migrations.txt"
find db -type d -name "versions" -print0 2>/dev/null | xargs -0 -I{} bash -c 'echo "versions dir: {}"; ls -1 {}' \
  | tee -a "${OUT}/static/migrations.txt" || true

# Tests
echo "=== Tests ===" | tee "${OUT}/static/tests.txt"
find tests -type f -name "test_*.py" 2>/dev/null | sort | tee "${OUT}/lists/test_files.txt" || true
wc -l < "${OUT}/lists/test_files.txt" | xargs echo "TEST_FILE_COUNT=" | tee -a "${OUT}/static/tests.txt"
if command -v pytest >/dev/null 2>&1; then
  echo "(pytest present) suggested: pytest -q --collect-only" | tee -a "${OUT}/static/tests.txt"
else
  echo "(pytest not installed in this environment)" | tee -a "${OUT}/static/tests.txt"
fi

# Airflow DAGs
echo "=== Airflow DAGs ===" | tee "${OUT}/static/airflow.txt"
find . -type f -path "*/dags/*.py" 2>/dev/null | tee "${OUT}/lists/dags.txt" || true
wc -l < "${OUT}/lists/dags.txt" | xargs echo "DAG_FILES=" | tee -a "${OUT}/static/airflow.txt"
# Count Operators heuristically
if [ -s "${OUT}/lists/dags.txt" ]; then
  xargs -a "${OUT}/lists/dags.txt" grep -hE "PythonOperator|BashOperator|KubernetesPodOperator|@dag|TaskGroup" \
    | wc -l | xargs echo "DAG_OPERATOR_LINES=" | tee -a "${OUT}/static/airflow.txt"
fi

# Compose services
echo "=== docker-compose services ===" | tee "${OUT}/static/compose.txt"
if [ -f docker-compose.yml ]; then
  grep -E "^[[:space:]]{2}[a-zA-Z0-9_-]+:" docker-compose.yml | sed 's/://;s/^[ ]\+//' \
    | sort | uniq | tee "${OUT}/lists/compose_services.txt"
  echo "SERVICE_COUNT=$(wc -l < ${OUT}/lists/compose_services.txt)" | tee -a "${OUT}/static/compose.txt"
else
  echo "docker-compose.yml not found" | tee -a "${OUT}/static/compose.txt"
fi

# Mock providers / feature flags
echo "=== mock providers / flags ===" | tee "${OUT}/static/mocks.txt"
grep -Rni "MOCK_MODE" -n . | tee -a "${OUT}/static/mocks.txt" || true
find api -type f -name "*provider*.py" -o -name "providers/*.py" 2>/dev/null | tee -a "${OUT}/static/mocks.txt" || true

# Frontend presence
echo "=== frontend presence ===" | tee "${OUT}/static/frontend.txt"
[ -f package.json ] && jq -r '.name,.scripts' package.json 2>/dev/null | tee -a "${OUT}/static/frontend.txt" || echo "no package.json" | tee -a "${OUT}/static/frontend.txt"

# Summarize truth table skeleton
cat > "${OUT}/recon/TRUTH_TABLE.csv" <<'CSV'
Area,Claimed,Observed,Status,Notes
API endpoints,118,<fill>,<derive>,grep @router.* count vs runtime
Models,35,<fill>,<derive>,class .*Base() count
Routers,17,<fill>,<derive>,APIRouter files
Airflow DAGs,<n/a>,<fill>,<derive>,present & operator count
Compose services,11-15,<fill>,<derive>,service name list
Tests,~47-68 files,<fill>,<derive>,discover test files
Frontend,Next.js 14,<fill>,<derive>,package.json/scripts
Mock providers,SendGrid/Twilio/MinIO/PDF,<fill>,<derive>,files + MOCK_MODE
CSV

echo "Static audit complete → ${OUT}"
