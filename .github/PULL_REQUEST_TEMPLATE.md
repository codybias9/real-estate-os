# Pull Request: [Feature Name]

## 📋 Summary

<!-- Provide a brief description of the changes in this PR -->

## 🎯 Type of Change

- [ ] New feature
- [ ] Bug fix
- [ ] Breaking change
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Refactoring
- [ ] CI/CD improvements

## 📊 Metrics & Impact

<!-- Fill in applicable metrics -->

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| API Endpoints | | | |
| Database Models | | | |
| Test Coverage | | | |
| Python LOC | | | |

## 🔗 Evidence & Documentation

### Static Analysis
- [ ] Code review completed
- [ ] Evidence pack attached: [link or filename]
- [ ] Documentation updated

### Runtime Verification
- [ ] Runtime evidence pack attached: [link or filename]
- [ ] All health checks passing
- [ ] OpenAPI spec verified
- [ ] Endpoint count confirmed
- [ ] Authentication flow tested
- [ ] Feature flows verified
- [ ] Error handling tested
- [ ] Rate limiting verified
- [ ] Idempotency verified

### Artifacts
<!-- Link to evidence files -->
- Static Evidence: `evidence_pack_YYYYMMDD_HHMMSS.zip`
- Runtime Evidence: `runtime_evidence_YYYYMMDD_HHMMSS.zip`
- GO/NO-GO Document: `audit_artifacts/*/GO_NO_GO.md`
- Reconciliation: `audit_artifacts/*/recon/RECONCILIATION.md`

## ✅ Testing Checklist

### Automated Tests
- [ ] GitHub Actions CI passing
- [ ] Runtime verification script passed
- [ ] Unit tests passing
- [ ] Integration tests passing
- [ ] Linting passing (black, flake8, mypy)
- [ ] Security scan completed

### Manual Testing
- [ ] `docker compose up -d --wait` succeeds
- [ ] `/healthz` returns 200
- [ ] `/health` returns 200
- [ ] `/ready` returns 200
- [ ] OpenAPI spec accessible at `/docs/openapi.json`
- [ ] Swagger UI accessible at `/docs`
- [ ] Auth flow works (register → login → /me)
- [ ] Properties CRUD works
- [ ] Leads CRUD works
- [ ] Deals CRUD works
- [ ] Rate limiting enforced (429 observed)
- [ ] Idempotency working (duplicate handling)
- [ ] Error responses proper (404, 401, 422)

### Infrastructure
- [ ] Database migrations successful
- [ ] All Docker services healthy
- [ ] Redis accessible
- [ ] PostgreSQL accessible
- [ ] MailHog accessible (if configured)
- [ ] MinIO accessible (if configured)

### Mock Providers (MOCK_MODE)
- [ ] Twilio mock verified
- [ ] SendGrid mock verified
- [ ] Storage mock verified
- [ ] PDF mock verified

## 🚀 How to Test

### Prerequisites
```bash
docker --version
docker compose version
jq --version
```

### Quick Test
```bash
# Clone and checkout this branch
git checkout [branch-name]

# Start services
docker compose up -d --wait
sleep 30

# Run verification
./scripts/runtime_verification/verify_platform.sh

# Or manual test
curl http://localhost:8000/healthz
curl http://localhost:8000/docs/openapi.json | jq '.paths | keys | length'
```

### Full Test Sequence
See [MANUAL_TESTING_GUIDE.md](docs/MANUAL_TESTING_GUIDE.md) for detailed testing instructions.

## 💥 Breaking Changes

<!-- List any breaking changes and migration steps -->

- [ ] No breaking changes
- [ ] Breaking changes documented below

**Details:**
<!-- Describe breaking changes and how to migrate -->

## 📝 Implementation Details

### Key Changes
<!-- Describe the main changes in this PR -->

### Technical Decisions
<!-- Explain any important technical decisions made -->

### Database Changes
<!-- List any schema changes, migrations, or data impacts -->

## 🔒 Security Considerations

- [ ] No new security concerns
- [ ] Security review required
- [ ] Credentials properly secured
- [ ] Rate limiting implemented
- [ ] Input validation added
- [ ] SQL injection prevention verified
- [ ] XSS prevention verified
- [ ] CORS properly configured

## 📚 Documentation

- [ ] Code comments added/updated
- [ ] API documentation updated
- [ ] README updated
- [ ] Architecture docs updated
- [ ] Testing guide updated

## 🎬 Demo / Screenshots

<!-- Add screenshots, GIFs, or demo videos if applicable -->

## 🔗 Related Links

- Related Issue: #
- Related PR: #
- Documentation:
- Evidence Pack:

## 📌 Deployment Notes

<!-- Any special deployment instructions or considerations -->

- [ ] No special deployment steps needed
- [ ] Deployment steps documented below

**Steps:**
<!-- List deployment steps if needed -->

## ✍️ Reviewer Checklist

**For reviewers:**

- [ ] Code follows project style guidelines
- [ ] Changes are well-documented
- [ ] Tests are comprehensive
- [ ] Evidence packs reviewed
- [ ] Runtime verification passed
- [ ] No security vulnerabilities introduced
- [ ] Performance impact acceptable
- [ ] Breaking changes acceptable (if any)
- [ ] Documentation is clear and complete

## 🙋 Questions for Reviewers

<!-- List any specific questions or areas where you want reviewer feedback -->

---

## ✅ Pre-Merge Checklist

**Before merging, ensure:**

- [ ] All CI checks passing
- [ ] Code review approved (at least 1 reviewer)
- [ ] All comments addressed
- [ ] Evidence packs attached and reviewed
- [ ] Documentation updated
- [ ] Conflicts resolved
- [ ] CHANGELOG.md updated (if applicable)
- [ ] Version bumped (if applicable)
- [ ] Migration guide provided (if breaking changes)

---

**Confidence Level:** ⬜ LOW (50-69%) | ⬜ MEDIUM (70-84%) | ⬜ HIGH (85-95%)

**Status:** ⬜ ❌ NO GO | ⬜ ⚠️ CONDITIONAL GO | ⬜ ✅ FULL GO

---

<!--
Template version: 1.0
Last updated: 2025-11-05
-->
