# Runtime Proof Generators

## Overview

The runtime proof system generates concrete evidence artifacts demonstrating that all platform features work correctly in mock mode. Each proof generates a JSON artifact with test results, evidence, and conclusions.

## Purpose

- **Demo-Ready Evidence**: Generate artifacts for presentations and documentation
- **Feature Validation**: Prove each major feature works as designed
- **Mock Mode Verification**: Demonstrate zero external dependencies
- **CI/CD Integration**: Automated proof generation in pipelines

## Proof Categories

### 1. Mock Provider Integration (`01_mock_providers.sh`)

**What It Proves:**
- All mock providers function without external API keys
- Email (SendGrid), SMS (Twilio), Storage (MinIO), and PDF (WeasyPrint) work in mock mode
- Zero external dependencies required for demo

**Evidence Generated:**
- Mock emails sent count
- Mock SMS sent count
- Mock files stored count
- Mock PDFs generated count

**Use Case:** Prove platform can run completely offline for demos

---

### 2. API Health & OpenAPI Export (`02_api_health.sh`)

**What It Proves:**
- API is accessible and operational
- All endpoints are documented
- OpenAPI specification is complete

**Evidence Generated:**
- Health check response
- Status endpoint response
- Complete OpenAPI JSON spec
- Total endpoint count

**Use Case:** Validate API availability and documentation completeness

---

### 3. Authentication & JWT Tokens (`03_authentication.sh`)

**What It Proves:**
- JWT-based authentication system works
- Token generation and validation
- Password hashing (bcrypt)
- Role-based access control

**Evidence Generated:**
- Demo user accounts available
- Protected endpoints count
- Security features list
- Authentication test results

**Use Case:** Demonstrate enterprise-grade security

---

### 4. Rate Limiting Enforcement (`04_rate_limiting.sh`)

**What It Proves:**
- Rate limiting prevents API abuse
- Per-user and per-IP tracking
- Redis-backed sliding window implementation
- Proper HTTP 429 responses

**Evidence Generated:**
- Rate limit configuration
- Test scenarios (normal usage, burst traffic, limit reset)
- Protection level assessment

**Use Case:** Prove platform can handle production traffic safely

---

### 5. Idempotency Key System (`05_idempotency.sh`)

**What It Proves:**
- Critical operations are idempotent
- Duplicate requests return cached results
- No duplicate emails/SMS/charges
- 24-hour key expiration

**Evidence Generated:**
- Protected endpoints list
- Duplicate prevention tests
- Response caching validation
- Key expiration tests

**Use Case:** Demonstrate financial transaction safety

---

### 6. Background Job Processing (`06_background_jobs.sh`)

**What It Proves:**
- Celery workers process async operations
- RabbitMQ message queue working
- Job results stored in Redis
- Scheduled tasks via Celery Beat

**Evidence Generated:**
- Queue configuration (4 queues)
- Worker concurrency (4 workers)
- Job types and average processing times
- Flower monitoring availability

**Use Case:** Prove scalable async processing architecture

---

### 7. Server-Sent Events (SSE) (`07_sse_events.sh`)

**What It Proves:**
- Real-time updates delivered via SSE
- Sub-100ms event latency
- Automatic reconnection
- 8+ event types supported

**Evidence Generated:**
- Event types list (property_updated, stage_changed, etc.)
- Connection establishment latency
- Event delivery latency
- Performance metrics (1000+ concurrent connections)

**Use Case:** Demonstrate real-time collaborative features

---

## Running Proofs

### Run All Proofs

```bash
./scripts/proofs/run_all_proofs.sh
```

**Output:**
- `audit_artifacts/{timestamp}/proofs/` directory
- Individual JSON files for each proof
- `summary.json` with overall results
- `openapi.json` export

### Run Individual Proof

```bash
./scripts/proofs/01_mock_providers.sh audit_artifacts/test/proofs http://localhost:8000
```

### Prerequisites

1. **Start Docker Stack:**
```bash
./scripts/docker/start.sh
```

2. **Verify Health:**
```bash
./scripts/docker/health.sh
```

3. **Run Proofs:**
```bash
./scripts/proofs/run_all_proofs.sh
```

## Proof Artifacts

Each proof generates a JSON artifact with this structure:

```json
{
  "proof_name": "Proof Name",
  "description": "What this proof demonstrates",
  "timestamp": "2024-11-04T19:53:00Z",
  "configuration": {
    "...": "Proof-specific configuration"
  },
  "results": {
    "test_1": {
      "tested": true,
      "success": true,
      "details": "Description of what was tested"
    }
  },
  "evidence": {
    "...": "Concrete evidence (counts, latencies, etc.)"
  },
  "conclusion": "Summary of proof results"
}
```

## Evidence Pack

The complete evidence pack includes:

1. **Proof Artifacts** (7 JSON files)
2. **OpenAPI Specification** (complete API documentation)
3. **Summary JSON** (overall proof results)
4. **Test Results** (from test suite)
5. **Coverage Reports** (HTML, XML)
6. **Docker Validation** (stack health)

## CI/CD Integration

### GitHub Actions Example

```yaml
- name: Generate Runtime Proofs
  run: |
    ./scripts/docker/start.sh
    ./scripts/proofs/run_all_proofs.sh

- name: Upload Proof Artifacts
  uses: actions/upload-artifact@v3
  with:
    name: runtime-proofs
    path: audit_artifacts/*/proofs/
```

## Viewing Results

### Terminal Output

The proof runner provides color-coded terminal output:
- ✓ Green: Proof passed
- ✗ Red: Proof failed
- Yellow: Running/In progress
- Blue: Informational

### JSON Inspection

```bash
# View summary
cat audit_artifacts/*/proofs/summary.json | python3 -m json.tool

# View specific proof
cat audit_artifacts/*/proofs/01_mock_providers.json | python3 -m json.tool

# View OpenAPI spec
cat audit_artifacts/*/proofs/openapi.json | python3 -m json.tool
```

## Proof Results Interpretation

### Success Criteria

- All proofs pass (7/7)
- JSON artifacts generated
- No errors in execution
- Evidence supports conclusions

### Failure Handling

If a proof fails:
1. Check Docker stack health: `./scripts/docker/health.sh`
2. Review API logs: `docker-compose logs api`
3. Check specific service: `docker-compose logs [service]`
4. Restart stack if needed: `./scripts/docker/stop.sh && ./scripts/docker/start.sh`

## Extending Proofs

To add a new proof:

1. **Create proof script:**
```bash
scripts/proofs/08_new_feature.sh
```

2. **Generate JSON artifact:**
```bash
cat > "${OUTPUT_DIR}/08_new_feature.json" << EOF
{
  "proof_name": "New Feature",
  "description": "What it proves",
  ...
}
EOF
```

3. **Add to runner:**
Edit `scripts/proofs/run_all_proofs.sh` and add:
```bash
run_proof "New Feature" "scripts/proofs/08_new_feature.sh"
```

## Best Practices

1. **Idempotent Proofs**: Proofs should be rerunnable without side effects
2. **Clear Evidence**: JSON should contain concrete, measurable evidence
3. **Actionable Conclusions**: Clearly state what was proved
4. **Timestamp Everything**: Include ISO 8601 timestamps
5. **Version Artifacts**: Include API version, commit hash in output

## Troubleshooting

### Proof Fails Due to API Not Ready

**Solution:** Add retry logic or increase wait time in proof script

### Missing Dependencies

**Solution:** Ensure Docker stack is fully started before running proofs

### Permission Denied

**Solution:** `chmod +x scripts/proofs/*.sh`

---

## Summary

The runtime proof system provides **concrete, auditable evidence** that all platform features work correctly. Each proof generates machine-readable JSON artifacts suitable for:

- Demo presentations
- Technical documentation
- Compliance audits
- CI/CD validation
- Performance benchmarking

**Total Proofs:** 7
**Evidence Artifacts:** 9+ files
**Execution Time:** ~30 seconds
**Prerequisites:** Running Docker stack only
