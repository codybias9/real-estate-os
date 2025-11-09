#!/usr/bin/env bash
set -euo pipefail

TS=$(date +"%Y%m%d_%H%M%S")
OUT="audit_artifacts/${TS}/runtime"
mkdir -p "${OUT}"

# 1) Env
if [ -f .env.mock ]; then
  cp .env.mock .env
  echo "Using .env.mock → .env"
else
  echo "ERROR: .env.mock missing" | tee "${OUT}/errors.txt"
  exit 1
fi

# 2) Bring up stack
docker compose up -d --wait || {
  docker compose logs > "${OUT}/compose_logs.txt" || true
  echo "Compose failed" | tee -a "${OUT}/errors.txt"; exit 1;
}

docker compose ps | tee "${OUT}/compose_ps.txt"

# 3) Health probe (retry)
ATTEMPTS=60
until curl -fsS http://localhost:8000/healthz > "${OUT}/healthz.json" 2>/dev/null || [ $ATTEMPTS -eq 0 ]; do
  sleep 2; ATTEMPTS=$((ATTEMPTS-1))
done
if [ $ATTEMPTS -eq 0 ]; then
  docker compose logs api | tee "${OUT}/api_logs.txt" || true
  echo "API never became healthy" | tee -a "${OUT}/errors.txt"; exit 1;
fi

# 4) OpenAPI + endpoint count
curl -fsS http://localhost:8000/docs/openapi.json -o "${OUT}/openapi.json" || {
  echo "Failed to fetch openapi.json" | tee -a "${OUT}/errors.txt"; exit 1;
}
jq '.paths | length' "${OUT}/openapi.json" | tee "${OUT}/endpoint_count_openapi.txt"

# 5) Minimal ping + health
curl -fsS http://localhost:8000/ping | tee "${OUT}/ping.json" || true

# 6) Optional: enrichment flow (only if routes exist)
if jq -e '.paths | has("/properties")' "${OUT}/openapi.json" >/dev/null 2>&1; then
  echo '{"address":"123 Main St","city":"Anytown","state":"TX","zip":"73301"}' > "${OUT}/sample_property.json"
  curl -fsS -X POST http://localhost:8000/properties \
    -H "Content-Type: application/json" \
    -d @"${OUT}/sample_property.json" | tee "${OUT}/post_properties.json" || true
  curl -fsS http://localhost:8000/properties | tee "${OUT}/get_properties.json" || true
fi

# 7) Save API logs for diagnosis
docker compose logs api | tail -n 500 | tee "${OUT}/api_tail.log" || true

echo "Runtime audit complete → ${OUT}"
