# GitHub Actions Monitoring Guide

## How to Monitor Your Runtime Verification

### 1. **View Workflow Status**

After creating the PR, you'll see checks at the bottom:

```
✓ verify-platform — Passed (5m 23s)
✓ lint-and-test — Passed (2m 15s)
✓ security-scan — Passed (1m 45s)
✓ report-status — Passed (0m 10s)
```

Click "Details" next to any check to see logs.

---

### 2. **Access the Actions Tab**

1. Go to your repo: https://github.com/codybias9/real-estate-os
2. Click the "Actions" tab
3. Find the workflow run for your PR
4. Click on it to see detailed logs

---

### 3. **Check Individual Jobs**

Click on each job to see step-by-step logs:

#### **verify-platform Job:**
```
✓ Checkout code
✓ Set up Python
✓ Install dependencies
✓ Start services (docker compose up)
✓ Health checks
✓ Run runtime verification script
  → Running 40+ tests...
  → [✓] /healthz endpoint responding
  → [✓] OpenAPI spec downloaded: 118 endpoints
  → [✓] User registration successful
  → [✓] Login successful (token obtained)
  → [✓] Property created
  → [✓] Lead created
  → [✓] Deal created
  → [✓] Rate limiting working
  → VERIFICATION COMPLETE: ✅ FULL GO
✓ Upload evidence artifacts
✓ Stop services
```

#### **lint-and-test Job:**
```
✓ Code formatting check (black)
✓ Linting (flake8)
✓ Type checking (mypy)
```

#### **security-scan Job:**
```
✓ Dependency security scan
✓ No critical vulnerabilities
```

---

### 4. **Download Evidence Artifacts**

After the workflow completes:

1. Scroll to bottom of the workflow run page
2. Find "Artifacts" section
3. Click on `runtime-evidence-{run_number}.zip`
4. Download to your computer

**Contents:**
```
runtime-evidence-{run_number}.zip
├── audit_artifacts/
│   └── runtime_YYYYMMDD_HHMMSS/
│       ├── RUNTIME_EVIDENCE_SUMMARY.md  ← Main report
│       ├── health/
│       │   ├── healthz.json
│       │   ├── openapi.json
│       │   └── endpoint_count.txt
│       ├── auth/
│       │   ├── register.json
│       │   ├── login.json
│       │   └── token.txt
│       ├── flows/
│       │   ├── property_create.json
│       │   ├── lead_create.json
│       │   └── deal_create.json
│       └── hardening/
│           ├── ratelimit_status_codes.txt
│           └── idempotent_first.json
```

---

### 5. **Expected Results**

#### **If All Tests Pass (FULL GO ✅):**

You'll see:
```
✅ All checks have passed

╔══════════════════════════════════════════════════════════════╗
║            RUNTIME VERIFICATION RESULTS                      ║
╚══════════════════════════════════════════════════════════════╝

  Total Tests:    42
  Passed:         42 ✓
  Failed:         0 ✗
  Success Rate:   100.0%

  STATUS: ✅ FULL GO

  Confidence Level: 85-95% (HIGH)
  Platform is demo-ready!
```

**Actions:**
- ✅ Download evidence artifacts
- ✅ Review RUNTIME_EVIDENCE_SUMMARY.md
- ✅ Merge PR (if ready)
- ✅ Status upgraded to FULL GO!

---

#### **If Some Tests Fail (CONDITIONAL GO ⚠️):**

You'll see:
```
⚠️ Some checks have warnings

  Total Tests:    42
  Passed:         38 ✓
  Failed:         4 ✗
  Success Rate:   90.5%

  STATUS: ⚠️ CONDITIONAL GO
```

**Actions:**
- 📋 Review failed tests in logs
- 🔍 Check which endpoints failed
- 🔧 Fix issues
- 🔄 Push fixes (GitHub Actions will re-run)

---

### 6. **Re-run Failed Checks**

If tests fail:

1. Click "Re-run jobs" button on the Actions page
2. Or push new commits to the PR branch (auto-triggers)

```bash
# Make fixes locally
git add .
git commit -m "fix: Address runtime verification failures"
git push
# GitHub Actions will automatically re-run
```

---

### 7. **View Summary in PR**

GitHub Actions will add a summary to your PR:

```
## 🔍 Runtime Verification Results

| Job | Status |
|-----|--------|
| Platform Verification | ✅ success |
| Lint & Test | ✅ success |
| Security Scan | ✅ success |

**Branch:** claude/runtime-verification-step-2-011CUqLHVczJDiKLgiYTZSpT
**Commit:** a1e213d
**Run:** 123
```

---

### 8. **Troubleshooting**

#### **Workflow doesn't start:**
- Check that `.github/workflows/runtime-verification.yml` exists in your branch
- Verify PR is targeting the correct base branch
- Check GitHub Actions is enabled in repo settings

#### **Docker services fail to start:**
- This is handled automatically by GitHub runners
- Check logs for specific service failures
- May need to adjust timeouts in workflow

#### **Tests timeout:**
- Default timeout is 30 minutes
- Adjust in workflow if needed: `timeout-minutes: 30`

#### **Artifacts not available:**
- Check "Upload evidence artifacts" step completed
- Artifacts are kept for 30 days by default
- Download before they expire

---

### 9. **Success Criteria**

For **FULL GO (85-95% confidence)**, you need:

- ✅ All 4 GitHub Actions jobs passing
- ✅ 40+ tests passed (0 failures)
- ✅ Evidence artifacts generated
- ✅ OpenAPI spec shows 118 endpoints (or 73 for basic CRM)
- ✅ Auth flow working (register → login → /me)
- ✅ Properties/Leads/Deals CRUD working
- ✅ Rate limiting verified (429 responses)
- ✅ Idempotency verified

---

### 10. **Next Steps After Success**

Once GitHub Actions shows ✅ FULL GO:

1. **Download evidence:** `runtime-evidence-{run_number}.zip`
2. **Review summary:** Open `RUNTIME_EVIDENCE_SUMMARY.md` in the zip
3. **Update status:** Confidence = 85-95% (FULL GO)
4. **Merge PR:** (if ready)
5. **Celebrate:** Platform is demo-ready! 🎉

---

## Quick Reference

| Action | Location |
|--------|----------|
| View all workflows | GitHub → Actions tab |
| View PR checks | PR page → bottom "Checks" section |
| Download artifacts | Workflow run page → "Artifacts" section |
| Re-run workflow | Workflow run page → "Re-run jobs" button |
| View logs | Workflow run → Click job → Click step |

---

## Timeline

```
0:00 - PR created
0:30 - GitHub Actions triggered
1:00 - Docker services starting
2:00 - Services healthy, tests beginning
3:00 - Auth tests (register, login, /me)
4:00 - Feature tests (Properties, Leads, Deals)
5:00 - Hardening tests (rate limit, idempotency)
6:00 - Evidence packaging
7:00 - ✅ COMPLETE - Results posted to PR
```

**Total Duration:** ~5-10 minutes

---

**Ready to create your PR!** 🚀

Once created, come back here and paste the PR URL so we can monitor it together.
