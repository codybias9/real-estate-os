# Runtime Verification Tools

This directory contains tools for comprehensive runtime verification of the Real Estate OS Platform in MOCK_MODE.

## 📁 Contents

- `verify_platform.sh` - Automated verification script for all 118 endpoints
- `README.md` - This file

## 🎯 Purpose

These tools provide **runtime proof** that the platform works correctly, upgrading confidence from:
- **CONDITIONAL GO (65%)** - Static analysis only
- **FULL GO (85-95%)** - Static + Runtime verification ✅

## 🚀 Quick Start

### Prerequisites

```bash
# Required
docker --version        # Docker 20.10+
docker compose version  # Docker Compose 2.0+
curl --version         # cURL 7.68+
jq --version           # jq 1.6+

# Optional
python3 --version      # Python 3.11+ (for UUID generation)
zip --version          # For evidence packaging
```

### Run Verification

```bash
# Navigate to project root
cd /path/to/real-estate-os

# Run verification script
./scripts/runtime_verification/verify_platform.sh
```

## 📊 What Gets Tested

### 1. Health Checks
- ✅ `/healthz` endpoint
- ✅ `/health` endpoint (if available)
- ✅ `/ready` endpoint (if available)
- ✅ OpenAPI specification download
- ✅ Endpoint count verification (118 or 73)

### 2. Database
- ✅ Alembic migrations execution
- ✅ Current migration verification

### 3. Authentication
- ✅ User registration
- ✅ User login (JWT token)
- ✅ Token validation (`/auth/me`)

### 4. Properties Feature
- ✅ Create property
- ✅ List properties
- ✅ Get property details

### 5. Leads Feature
- ✅ Create lead
- ✅ List leads

### 6. Deals Feature
- ✅ Create deal
- ✅ Update deal status

### 7. Error Handling
- ✅ 404 Not Found
- ✅ 401 Unauthorized

### 8. Hardening
- ✅ Rate limiting (429 responses)
- ✅ Idempotency (duplicate handling)

### 9. Mock Services
- ✅ MailHog email capture
- ✅ MinIO storage console
- ✅ SSE token endpoint
- ✅ Structured logging

## 📂 Evidence Generated

After running, the script creates:

```
audit_artifacts/
└── runtime_YYYYMMDD_HHMMSS/
    ├── RUNTIME_EVIDENCE_SUMMARY.md   # Summary report
    ├── health/
    │   ├── healthz.json
    │   ├── health.json
    │   ├── ready.json
    │   ├── openapi.json
    │   └── endpoint_count.txt
    ├── auth/
    │   ├── register.json
    │   ├── login.json
    │   ├── token.txt
    │   └── me.json
    ├── flows/
    │   ├── property_create.json
    │   ├── property_list.json
    │   ├── property_detail.json
    │   ├── lead_create.json
    │   ├── lead_list.json
    │   ├── deal_create.json
    │   └── deal_update.json
    ├── hardening/
    │   ├── error_404.json
    │   ├── error_401.json
    │   ├── ratelimit_status_codes.txt
    │   ├── ratelimit_429_count.txt
    │   ├── idempotent_first.json
    │   ├── idempotent_second.json
    │   ├── sse_token.json
    │   ├── mailhog_messages.json
    │   ├── minio_console_head.txt
    │   └── structured_logs_sample.txt
    └── logs/
        ├── startup.log
        ├── compose_ps.txt
        ├── migrations.log
        └── alembic_current.txt

runtime_evidence_YYYYMMDD_HHMMSS.zip  # Complete evidence package
```

## 🎯 Exit Codes

| Code | Status | Meaning |
|------|--------|---------|
| 0 | ✅ **FULL GO** | All tests passed (85-95% confidence) |
| 1 | ⚠️ **CONDITIONAL GO** | Some failures but mostly working (70-84%) |
| 1 | ❌ **NO GO** | Too many failures (50-69%) |

## 🔧 Configuration

### Environment Variables

```bash
# API URL (default: http://localhost:8000)
export API_URL="http://localhost:8000"

# Health check timeout in seconds (default: 30)
export TIMEOUT=60

# Custom runtime directory (default: audit_artifacts/runtime_YYYYMMDD_HHMMSS)
export RUNTIME_DIR="my_custom_dir"
```

### Customization

Edit the script to:
- Skip certain tests (comment out sections)
- Add new feature tests
- Adjust timeout values
- Modify expected responses

## 📋 Sample Output

```
========================================
Real Estate OS - Runtime Verification
========================================
[INFO] Timestamp: 2025-11-05 20:00:00 UTC
[INFO] API URL: http://localhost:8000
[INFO] Evidence Directory: audit_artifacts/runtime_20251105_200000

========================================
1. SETUP & PREREQUISITES
========================================
[✓] Docker found: Docker version 24.0.5
[✓] docker-compose found
[✓] jq found: jq-1.6
[✓] curl found: curl 8.1.2

========================================
2. START SERVICES
========================================
[INFO] Starting Docker Compose stack...
[✓] Services started

========================================
3. HEALTH CHECKS
========================================
[✓] /healthz endpoint responding
[✓] /health endpoint responding
[INFO] Downloading OpenAPI specification...
[✓] OpenAPI spec downloaded: 118 endpoints found
[✓] Endpoint count matches expected: 118 ✓

========================================
5. AUTHENTICATION FLOW
========================================
[INFO] Registering test user...
[✓] User registration successful
[INFO] Logging in...
[✓] Login successful (token obtained)
[INFO] Testing /auth/me endpoint...
[✓] /auth/me endpoint working

...

========================================
VERIFICATION COMPLETE
========================================

╔══════════════════════════════════════════════════════════════╗
║            RUNTIME VERIFICATION RESULTS                      ║
╚══════════════════════════════════════════════════════════════╝

  Total Tests:    42
  Passed:         42 ✓
  Failed:         0 ✗
  Success Rate:   100.0%

  Endpoint Count: 118
  Evidence Dir:   audit_artifacts/runtime_20251105_200000
  Evidence Pkg:   runtime_evidence_20251105_200000.zip

  STATUS: ✅ FULL GO

  All tests passed! Platform is demo-ready.

  Next steps:
  1. Review evidence in audit_artifacts/runtime_20251105_200000/
  2. Commit evidence: git add audit_artifacts/runtime_20251105_200000 runtime_evidence_20251105_200000.zip
  3. Push to remote branch
  4. Create PR with evidence attached
```

## 🐛 Troubleshooting

### Services don't start

```bash
# Check Docker daemon
systemctl status docker

# Check ports in use
lsof -i :8000
lsof -i :5432

# Check logs
docker compose logs
```

### Health checks fail

```bash
# Wait longer for services
export TIMEOUT=60
./scripts/runtime_verification/verify_platform.sh

# Manual check
curl http://localhost:8000/healthz
docker compose ps
```

### Token errors

```bash
# Check token is obtained
cat audit_artifacts/runtime_*/auth/token.txt

# Check token format
TOKEN=$(cat audit_artifacts/runtime_*/auth/token.txt)
echo $TOKEN | base64 -d
```

### Missing jq

```bash
# Ubuntu/Debian
sudo apt-get install jq

# macOS
brew install jq

# Alpine
apk add jq
```

### Permission denied

```bash
chmod +x scripts/runtime_verification/verify_platform.sh
```

## 🔄 Integration with CI/CD

This script is automatically run by GitHub Actions on every PR.

See: `.github/workflows/runtime-verification.yml`

### GitHub Actions

```yaml
- name: Run runtime verification
  run: ./scripts/runtime_verification/verify_platform.sh

- name: Upload evidence
  uses: actions/upload-artifact@v4
  with:
    name: runtime-evidence
    path: runtime_evidence_*.zip
```

## 📖 Related Documentation

- **Manual Testing Guide:** `docs/MANUAL_TESTING_GUIDE.md`
- **Path to Full GO:** `PATH_TO_FULL_GO.md`
- **GO/NO-GO Decision:** `audit_artifacts/*/GO_NO_GO.md`
- **PR Template:** `.github/PULL_REQUEST_TEMPLATE.md`

## 🎬 Demo Usage

### Pre-Demo Run

```bash
# 1 hour before demo
./scripts/runtime_verification/verify_platform.sh

# Verify FULL GO status
cat audit_artifacts/runtime_*/RUNTIME_EVIDENCE_SUMMARY.md
```

### Post-Demo Cleanup

```bash
# Stop services
docker compose down

# Or stop and remove volumes
docker compose down -v
```

## 🔐 Security Notes

- Script runs in **MOCK_MODE** only
- No real external API calls
- No production data
- Test credentials only
- Safe for CI/CD environments

## 📊 Metrics & Performance

| Metric | Value |
|--------|-------|
| Total Tests | 40-50 |
| Execution Time | 2-5 minutes |
| Evidence Size | 50-200 KB |
| Zip Size | 10-50 KB |

## 🤝 Contributing

To add new tests:

1. Add test section to `verify_platform.sh`
2. Follow existing pattern:
   ```bash
   log_section "NEW TEST SECTION"

   log_info "Testing new feature..."
   RESULT=$(curl ...)

   if [ condition ]; then
       log_success "Test passed"
   else
       log_error "Test failed"
   fi
   ```
3. Save evidence to `${RUNTIME_DIR}/category/`
4. Update this README
5. Test locally before committing

## 📝 Changelog

### v1.0.0 (2025-11-05)
- Initial release
- 40+ automated tests
- Complete evidence generation
- CI/CD integration
- FULL GO certification

---

**Questions?** Review PATH_TO_FULL_GO.md or docs/MANUAL_TESTING_GUIDE.md
