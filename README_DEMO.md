# Real Estate OS - Demo & Verification Guide

**Complete guide to running the platform demo and verifying capabilities**

---

## 🚀 Quick Start (Choose Your Path)

### Path 1: Just Run the Demo (Recommended)

**Want to see it working right now?**

```bash
# 1. Start the platform (2 minutes)
./demo_quickstart.sh

# 2. Run interactive demo (10 minutes)
./demo_interactive.sh

# 3. Open API docs in browser
# Visit http://localhost:8000/docs
```

**That's it!** You now have a live platform with 140+ endpoints to explore.

---

### Path 2: Verify Then Demo (Thorough)

**Want proof of all capabilities first?**

```bash
# 1. Run static analysis (30 seconds)
./scripts/audit_static.sh

# 2. Run enhanced verification (90 minutes)
./scripts/runtime_verification_enhanced.sh

# 3. Review results
cat audit_artifacts/runtime_enhanced_*/full-consolidation/SUMMARY.txt

# 4. Run demo
./demo_quickstart.sh
./demo_interactive.sh
```

---

## 📋 What You Get

### Demo Platform Features

**140+ API Endpoints:**
- Authentication & user management
- Property CRUD & enrichment
- Lead & deal management
- Workflow automation
- Communications (email/SMS)
- Real-time events (SSE)
- Background jobs (Celery)
- Portfolio analytics
- Admin & system management

**Mock Services (No External APIs):**
- Email (MailHog - view at http://localhost:8025)
- SMS (Twilio mock)
- Storage (MinIO - view at http://localhost:9001)
- PDF generation
- LLM interactions

**Web Interfaces:**
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Flower (jobs): http://localhost:5555
- MailHog: http://localhost:8025
- MinIO: http://localhost:9001

---

## 📁 File Guide

### Demo Scripts (Start Here)

**`demo_quickstart.sh`** ⭐ **RUN THIS FIRST**
- Automated platform setup
- Selects branch, configures environment
- Starts Docker stack
- Validates health
- **Duration:** 2-3 minutes

**`demo_interactive.sh`**
- Guided walkthrough of 9 key features
- Automated API calls with formatted output
- **Duration:** 10-15 minutes

**`DEMO_RUNBOOK.md`**
- Complete manual reference
- Step-by-step API examples
- Troubleshooting guide
- Advanced usage

---

### Verification Scripts (Thorough Testing)

**`scripts/runtime_verification_enhanced.sh`** ⭐ **MOST THOROUGH**
- Hardened verification (addresses all false-positives)
- Proves MOUNTED endpoint count
- Validates migrations, mocks, tests
- **Duration:** 90-120 minutes
- **Output:** `audit_artifacts/runtime_enhanced_*/`

**`scripts/runtime_verification_dual.sh`**
- Standard verification
- Dual-branch comparison
- **Duration:** 60-90 minutes

**`scripts/audit_static.sh`**
- Fast code analysis (no Docker)
- Counts declared endpoints, models, tests
- **Duration:** 30 seconds

**`scripts/audit_all_branches.sh`**
- Multi-branch comparison
- **Duration:** 2-3 minutes

**`scripts/reconcile_models.sh`**
- Resolves model count confusion
- SQLAlchemy vs Pydantic vs migrations
- **Duration:** 10 seconds

---

### Documentation

**`VERIFICATION_READY.md`**
- Handoff summary
- What's ready, what's next
- Expected outcomes

**`scripts/README.md`**
- Complete script documentation
- Workflow guide
- Output interpretation

**`scripts/RUNTIME_VERIFICATION_PLAN.md`**
- Detailed verification checklist
- Timeline and expectations

**`scripts/DECISION_MATRIX.md`**
- Objective decision criteria
- Pass/fail scenarios
- Action plans

**`scripts/HARDENING_CHECKLIST.md`**
- False-positive failure modes addressed
- Hardening improvements
- Acceptance bars

---

## 🎯 Common Use Cases

### Use Case 1: "I just want to see it working"

```bash
./demo_quickstart.sh
# Open http://localhost:8000/docs in browser
# Click around, try endpoints
```

**Time:** 2 minutes + exploration

---

### Use Case 2: "Show me the key features"

```bash
./demo_quickstart.sh
./demo_interactive.sh
```

**Time:** 15 minutes total

---

### Use Case 3: "I need proof of 118+ endpoints"

```bash
# Static proof
./scripts/audit_all_branches.sh
cat audit_artifacts/branch_comparison_*/BRANCH_COMPARISON_SUMMARY.md
# Shows: full-consolidation has 152 declared endpoints

# Runtime proof
./scripts/runtime_verification_enhanced.sh
cat audit_artifacts/runtime_enhanced_*/full-consolidation/SUMMARY.txt
# Shows: 140-152 MOUNTED endpoints ✅
```

**Time:** 2 hours (mostly waiting for Docker)

---

### Use Case 4: "Manual API exploration"

```bash
./demo_quickstart.sh
# Then follow DEMO_RUNBOOK.md for curl examples

# Example: Create property
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@demo.com","password":"password123"}' | jq -r '.access_token')

curl -X POST http://localhost:8000/api/v1/properties \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"address":"123 Main St","city":"Austin","state":"TX","zip":"78701"}' | jq .
```

**Time:** Varies (explore at your own pace)

---

### Use Case 5: "I need to present this to stakeholders"

```bash
# 1. Start demo
./demo_quickstart.sh

# 2. Open multiple browser tabs:
#    - http://localhost:8000/docs (API docs)
#    - http://localhost:8025 (MailHog - email viewer)
#    - http://localhost:5555 (Flower - job queue)

# 3. Run through demo_interactive.sh in terminal
./demo_interactive.sh

# 4. Show real-time events:
# Terminal 1: SSE stream
curl -N -H "Accept: text/event-stream" http://localhost:8000/api/v1/events/stream

# Terminal 2: Trigger events
curl -X POST http://localhost:8000/api/v1/properties \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"address":"456 Oak Ave","city":"Austin","state":"TX","zip":"78701"}'

# Watch event appear in Terminal 1
```

**Time:** 30 minutes for full presentation

---

## 🔍 Troubleshooting

### Quick Fixes

**API won't start:**
```bash
docker compose down -v
./demo_quickstart.sh
```

**Only 2 endpoints showing:**
```bash
# Check you're on the right branch
git branch --show-current
# Should be: full-consolidation or mock-providers-twilio

# If not:
git checkout full-consolidation
docker compose restart api
```

**401 Unauthorized:**
```bash
# Get fresh token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@demo.com","password":"password123"}' | jq -r '.access_token')
export TOKEN
```

**Full troubleshooting:** See `DEMO_RUNBOOK.md` for 8 common issues + fixes

---

## 📊 What to Expect

### Static Analysis Results

**Current branch (audit-endpoint-discrepancy):**
- 2 endpoints (skeleton only)
- 0 routers
- 1 model

**full-consolidation branch:**
- 152 declared endpoints ✅
- 21 routers
- 20 models
- 47 tests
- Complete mock providers

**mock-providers-twilio branch:**
- 132 declared endpoints ✅
- 16 routers
- 20 models
- 3 tests

---

### Runtime Verification Results (Expected)

**full-consolidation:**
```
Mounted endpoints:    140-152 ✅
Alembic heads:        1 ✅
Tests:                60-95% pass ✅
Coverage:             30-70%
Mock providers:       All wired ✅
Demo flow:            Works ✅
```

**Verdict:** ✅ **RELEASE CANDIDATE**

---

## 🧹 Cleanup

**Stop demo (keep data):**
```bash
docker compose stop
```

**Stop and remove containers:**
```bash
docker compose down
```

**Complete cleanup (removes all data):**
```bash
docker compose down -v --remove-orphans
docker system prune -f
```

---

## 📦 Prerequisites

- Docker Engine 20.10+
- Docker Compose V2
- 4GB RAM free (8GB recommended)
- 10GB disk space free
- Ports 8000, 5432, 6379, 8025, 5555, 9001 available

**Check:**
```bash
docker --version
docker compose version
df -h .
netstat -tuln | grep -E ':(8000|5432|6379)'
```

---

## 🎓 Learning Path

### Beginner: "I've never used this platform"

1. Run `./demo_quickstart.sh`
2. Open http://localhost:8000/docs
3. Try the "Try it out" buttons in Swagger UI
4. Run `./demo_interactive.sh` for guided tour

**Time:** 30 minutes

---

### Intermediate: "I want to integrate this"

1. Run demo
2. Review `DEMO_RUNBOOK.md` for API examples
3. Try manual curl commands
4. Explore code in `api/routers/`

**Time:** 2-3 hours

---

### Advanced: "I need to verify everything"

1. Run static analysis: `./scripts/audit_static.sh`
2. Run branch comparison: `./scripts/audit_all_branches.sh`
3. Run enhanced verification: `./scripts/runtime_verification_enhanced.sh`
4. Review all artifacts in `audit_artifacts/`
5. Read `scripts/HARDENING_CHECKLIST.md`

**Time:** 4-6 hours

---

## 🏆 Deliverables

After running the demo, you'll have:

✅ **Working platform** with 140+ endpoints
✅ **Interactive exploration** capability
✅ **Evidence artifacts** (if you ran verification)
✅ **Understanding** of key features
✅ **Confidence** in platform capabilities

---

## 🚦 Quick Status Check

```bash
# Is the platform running?
curl -s http://localhost:8000/healthz | jq .

# How many endpoints?
curl -s http://localhost:8000/docs/openapi.json | jq '.paths | keys | length'

# Any errors?
docker compose logs api --tail=50 | grep -i error

# What's my token?
echo $TOKEN
```

---

## 📞 Support

**Need help?**

- **Demo issues:** See `DEMO_RUNBOOK.md` troubleshooting
- **Verification questions:** See `scripts/HARDENING_CHECKLIST.md`
- **API usage:** Check http://localhost:8000/docs
- **Logs:** Run `docker compose logs -f api`

---

## 🎉 Success Criteria

**You're successful when:**

✅ Can run `./demo_quickstart.sh` without errors
✅ See 100+ endpoints in http://localhost:8000/docs
✅ Can create properties via API
✅ Receive mock emails in MailHog
✅ See real-time events via SSE
✅ Background jobs appear in Flower

---

## 🔗 Quick Links

- **Start demo:** `./demo_quickstart.sh`
- **Interactive tour:** `./demo_interactive.sh`
- **Manual guide:** `DEMO_RUNBOOK.md`
- **Verification:** `scripts/runtime_verification_enhanced.sh`
- **API docs:** http://localhost:8000/docs (after starting)

---

## 📝 Summary

**This repository provides:**

1. **Complete demo infrastructure** (quickstart + interactive scripts)
2. **Comprehensive verification** (static + runtime)
3. **Detailed documentation** (runbooks, checklists, guides)
4. **Evidence artifacts** (audit results, comparisons, summaries)

**You can:**

- ✅ Run a live demo in 2 minutes
- ✅ Explore 140+ API endpoints interactively
- ✅ Verify all capabilities with objective proof
- ✅ Present to stakeholders with confidence

**No external APIs needed** - all services are mocked!

---

**Ready to start?**

```bash
./demo_quickstart.sh
```

🚀 **Let's go!**
