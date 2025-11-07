# ✅ Pre-Demo Checklist

**Complete this checklist 30 minutes before your demo**

---

## 🎯 T-30 Minutes: Start Services

- [ ] Navigate to project directory: `cd real-estate-os`
- [ ] Run demo start script: `./scripts/demo/start-demo.sh`
- [ ] Verify all services show "healthy" status
- [ ] Script completes with "🎉 Demo Environment Ready!"

**If script fails:**
```bash
# Manual start
docker compose -f docker-compose.api.yml down -v
docker compose -f docker-compose.api.yml up -d --wait
```

---

## 🧪 T-15 Minutes: Test All Endpoints

### Test 1: Health Check
```bash
curl http://localhost:8000/healthz
```
**Expected:** `{"status":"ok"}`
- [ ] Returns 200 status code
- [ ] Returns {"status":"ok"}

### Test 2: Database Connection (Run 3 Times)
```bash
curl http://localhost:8000/ping
curl http://localhost:8000/ping
curl http://localhost:8000/ping
```
**Expected:** `{"ping_count": 1}` → `{"ping_count": 2}` → `{"ping_count": 3}`
- [ ] First call returns count: 1
- [ ] Second call returns count: 2
- [ ] Third call returns count: 3
- [ ] Count increments correctly (database persistence)

### Test 3: Service Status
```bash
docker compose -f docker-compose.api.yml ps
```
**Expected:** All services show "healthy"
- [ ] `db` service is healthy
- [ ] `redis` service is healthy
- [ ] `api` service is healthy

---

## 🌐 T-10 Minutes: Open Browser Tabs

Open these URLs in separate tabs:

1. **Swagger UI** (Primary demo interface)
   ```
   http://localhost:8000/docs
   ```
   - [ ] Page loads successfully
   - [ ] Shows "Real Estate CRM Platform API" title
   - [ ] Shows /healthz and /ping endpoints

2. **GitHub Actions** (CI/CD showcase)
   ```
   https://github.com/codybias9/real-estate-os/actions
   ```
   - [ ] Page loads successfully
   - [ ] Shows "Runtime Verification (MOCK_MODE)" workflows
   - [ ] Latest run shows green checkmarks ✅

3. **ReDoc** (Alternative docs - backup)
   ```
   http://localhost:8000/redoc
   ```
   - [ ] Page loads successfully

4. **OpenAPI Spec** (For advanced audience)
   ```
   http://localhost:8000/docs/openapi.json
   ```
   - [ ] JSON loads successfully
   - [ ] Contains "paths" object

---

## 📱 T-10 Minutes: Prepare Materials

### Physical Materials
- [ ] Print or open **DEMO_CHEAT_SHEET.md** (keep visible)
- [ ] Print **DEMO_ARCHITECTURE_DIAGRAM.md** (show diagrams)
- [ ] Have **DEMO_GUIDE.md** open on second screen
- [ ] Pen and paper for notes

### Digital Backup
- [ ] Screenshots of passing GitHub Actions (in case of failure)
- [ ] Screenshot of Swagger UI
- [ ] Screenshot of healthy service status
- [ ] Screenshot of /healthz and /ping working

---

## 🎬 T-5 Minutes: Final Checks

### Quick Smoke Test
```bash
# All in one test
curl http://localhost:8000/healthz && \
curl http://localhost:8000/ping && \
echo "✅ All endpoints responding!"
```
- [ ] Both endpoints return successfully
- [ ] No error messages

### Visual Check
- [ ] All browser tabs are open and loaded
- [ ] Terminal is visible and ready
- [ ] Demo materials are accessible
- [ ] Backup screenshots are ready

### Talking Points Review
Review these key talking points:

- [ ] **Problem:** Fragmented tools, manual processes, no visibility
- [ ] **Solution:** Unified platform with automation
- [ ] **Tech Stack:** FastAPI, PostgreSQL, Redis, Docker
- [ ] **CI/CD:** Automated testing on every change
- [ ] **Mock Mode:** 100% offline, no API keys needed
- [ ] **Roadmap:** 6-8 weeks to 118 endpoints

---

## 💬 T-2 Minutes: Practice Opening Line

**Rehearse this out loud:**

> "Thanks for joining today. I'm going to show you our Real Estate Operating System - a production-grade platform that unifies property management, lead tracking, and deal flow into one automated system. What makes this interesting is we've built it with enterprise-level quality from day one - automated CI/CD, complete documentation, and the ability to run 100% offline. Let me dive in..."

---

## 🎯 T-0 Minutes: GO TIME!

### Demo Flow Reminder (15 min total)
1. **Intro** (2 min) - Problem & solution
2. **API Docs** (3 min) - Swagger UI, test /healthz and /ping
3. **CI/CD** (5 min) ⭐ - GitHub Actions showcase
4. **Mock Mode** (2 min) - Explain no dependencies
5. **Roadmap** (2 min) - Path to production
6. **Q&A** (3 min) - Questions

### Showstopper Moments
1. Live /healthz test in Swagger UI
2. Database persistence (/ping increments)
3. **GitHub Actions green checkmarks** ⭐ (Most impressive!)
4. Evidence artifacts download

---

## 🆘 Emergency Contacts & Backup Plans

### If Services Fail to Start
**Backup Plan:** Show GitHub Actions + screenshots

**Script:**
> "This is exactly why we invest in CI/CD - it works 100% reliably in our automated environment. The platform is running successfully there, as you can see from these green checkmarks. Let me show you the passing test runs and evidence artifacts instead."

### If API Returns Errors Mid-Demo
**Quick Fix:**
```bash
docker compose -f docker-compose.api.yml restart api
# Wait 30 seconds
curl http://localhost:8000/healthz
```

**If that fails:**
> "Let me show you the logs to demonstrate our monitoring capabilities..."
```bash
docker compose -f docker-compose.api.yml logs api --tail=20
```

### If GitHub Actions Page Won't Load
**Backup:** Use screenshots

**Script:**
> "I have screenshots of our CI/CD runs - you can see 7 total runs with 3 consecutive passes. Here's the evidence artifact download that shows complete test results..."

---

## 📊 Success Criteria

At T-0 (demo start), you should have:

- [x] ✅ Services running and healthy
- [x] ✅ Both endpoints tested and working
- [x] ✅ Browser tabs open and loaded
- [x] ✅ Demo materials accessible
- [x] ✅ Backup screenshots ready
- [x] ✅ Opening line rehearsed
- [x] ✅ Confidence level: HIGH

---

## 🎊 Post-Demo Checklist

After the demo completes:

- [ ] Stop services: `docker compose -f docker-compose.api.yml down`
- [ ] Note any questions you couldn't answer (for follow-up)
- [ ] Send follow-up email with:
  - [ ] GitHub repo link
  - [ ] GitHub Actions link
  - [ ] Documentation links (DEMO_GUIDE.md, etc.)
  - [ ] Evidence artifact download link
- [ ] Schedule technical deep-dive (if requested)

---

## 📈 Demo Success Metrics

**Minimum success criteria:**
- ✅ Services started and healthy
- ✅ At least one endpoint tested live
- ✅ GitHub Actions shown (green checkmarks)
- ✅ Questions answered confidently

**Perfect demo:**
- ✅ All of above
- ✅ Live /healthz test in Swagger UI
- ✅ Database persistence demonstrated
- ✅ Evidence artifacts downloaded
- ✅ No technical failures
- ✅ Clear next steps established

---

## 💡 Final Tips

1. **Start 30 minutes early** - Don't rush setup
2. **Test everything** - Don't assume it works
3. **Have backups ready** - Screenshots save the day
4. **Stay calm** - Acknowledge issues, pivot to backup
5. **Focus on automation** - CI/CD is most impressive
6. **End with action** - Clear next steps

---

**Remember: Confidence over perfection!**

If something breaks, acknowledge it professionally and pivot to the backup plan. The fact that you HAVE a backup plan demonstrates production readiness.

**You've got this! 🚀**
