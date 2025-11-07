# 🪟 Windows Quick Start - Get Demo Running NOW

**For Windows users using PowerShell**

---

## 🚀 Option 1: PowerShell Script (Easiest)

### Step 1: Allow PowerShell Scripts

**First time only - run this in PowerShell as Administrator:**

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Press **Y** when prompted.

### Step 2: Run the Demo Script

```powershell
cd real-estate-os
.\scripts\demo\start-demo.ps1
```

**That's it!** The script will:
- Check Docker is running
- Start all services
- Test endpoints
- Open your browser

---

## 🔧 Option 2: Manual Commands (If Script Fails)

Run these commands one by one in PowerShell:

### Step 1: Navigate to Project

```powershell
cd C:\Users\mason\real-estate-os
```

### Step 2: Check Docker is Running

```powershell
docker --version
# Should show: Docker version...

docker info
# Should show Docker system info (not an error)
```

**If Docker isn't running:**
- Open **Docker Desktop** from Start Menu
- Wait for it to say "Docker Desktop is running"
- Try again

### Step 3: Stop Any Existing Services

```powershell
docker compose -f docker-compose.api.yml down -v
```

### Step 4: Start Services

```powershell
docker compose -f docker-compose.api.yml up -d --wait
```

**This will take 30-60 seconds. You should see:**
```
✔ Container real-estate-os-db-1     Healthy
✔ Container real-estate-os-redis-1  Healthy
✔ Container real-estate-os-api-1    Healthy
```

### Step 5: Wait for API to be Ready

```powershell
Start-Sleep -Seconds 10
```

### Step 6: Test Health Endpoint

```powershell
Invoke-RestMethod http://localhost:8000/healthz
```

**Expected output:**
```
status
------
ok
```

### Step 7: Test Database (Run This 3 Times)

```powershell
# First time
Invoke-RestMethod http://localhost:8000/ping

# Second time
Invoke-RestMethod http://localhost:8000/ping

# Third time
Invoke-RestMethod http://localhost:8000/ping
```

**Expected output:**
```
ping_count
----------
1          # First time
2          # Second time
3          # Third time
```

The count should increment! This proves the database is working.

### Step 8: Open Swagger UI

```powershell
Start-Process http://localhost:8000/docs
```

Or just open this in your browser:
```
http://localhost:8000/docs
```

**You should see:**
- "Real Estate CRM Platform API" title
- /healthz endpoint
- /ping endpoint

---

## 🆘 Troubleshooting

### Error: "Docker is not running"

**Fix:**
1. Open **Docker Desktop** from Windows Start Menu
2. Wait for it to show "Docker Desktop is running" in system tray
3. Try the commands again

### Error: "Cannot find docker-compose.api.yml"

**Fix:**
```powershell
# Check you're in the right directory
Get-Location
# Should show: C:\Users\mason\real-estate-os

# List files to verify
Get-ChildItem -Name docker-compose*
# Should show: docker-compose.api.yml
```

If you don't see `docker-compose.api.yml`, you might need to pull the latest code:

```powershell
git pull origin claude/runtime-verification-step-2-011CUqLHVczJDiKLgiYTZSpT
```

### Error: "Port 8000 already in use"

**Fix:**
```powershell
# See what's using port 8000
netstat -ano | findstr :8000

# Stop the process (if needed)
# Find the PID from above command, then:
Stop-Process -Id <PID> -Force

# Or restart Docker
docker compose -f docker-compose.api.yml down -v
docker compose -f docker-compose.api.yml up -d --wait
```

### Services Start but API Returns Errors

**Check logs:**
```powershell
docker compose -f docker-compose.api.yml logs api
```

**Restart services:**
```powershell
docker compose -f docker-compose.api.yml restart api
Start-Sleep -Seconds 10
Invoke-RestMethod http://localhost:8000/healthz
```

---

## ✅ Verification Checklist

After starting services, verify everything works:

- [ ] Docker Desktop is running
- [ ] Services are healthy:
  ```powershell
  docker compose -f docker-compose.api.yml ps
  # All should show "healthy"
  ```
- [ ] Health endpoint works:
  ```powershell
  Invoke-RestMethod http://localhost:8000/healthz
  # Returns: status = ok
  ```
- [ ] Database works:
  ```powershell
  Invoke-RestMethod http://localhost:8000/ping
  # Returns: ping_count = (increments)
  ```
- [ ] Swagger UI loads:
  ```
  http://localhost:8000/docs
  ```

**If all checkboxes are checked ✅ - YOU'RE READY TO DEMO!**

---

## 📊 Quick Demo Test

Run this complete test in PowerShell:

```powershell
# Test 1: Health
Write-Host "Test 1: Health Check" -ForegroundColor Cyan
Invoke-RestMethod http://localhost:8000/healthz
Write-Host ""

# Test 2: Database (3 times)
Write-Host "Test 2: Database Persistence" -ForegroundColor Cyan
Write-Host "Call 1:"
Invoke-RestMethod http://localhost:8000/ping
Start-Sleep -Seconds 1
Write-Host "Call 2:"
Invoke-RestMethod http://localhost:8000/ping
Start-Sleep -Seconds 1
Write-Host "Call 3:"
Invoke-RestMethod http://localhost:8000/ping
Write-Host ""

Write-Host "✅ All tests passed! Demo is ready!" -ForegroundColor Green
```

---

## 🎬 You're Ready to Demo!

Once everything above works:

1. **Keep PowerShell open** (to see logs if needed)
2. **Open browser tabs:**
   - Swagger UI: http://localhost:8000/docs
   - GitHub Actions: https://github.com/codybias9/real-estate-os/actions
3. **Print this:** DEMO_CHEAT_SHEET.md
4. **Follow:** DEMO_GUIDE.md

---

## 🛑 Stopping the Demo

When done:

```powershell
docker compose -f docker-compose.api.yml down
```

Or to completely clean up (removes data):

```powershell
docker compose -f docker-compose.api.yml down -v
```

---

## 💡 Pro Tips for Windows

### Use Windows Terminal (Better than PowerShell)

Download from Microsoft Store: **Windows Terminal**

It has:
- Better colors
- Multiple tabs
- Better copy/paste

### Or Use Git Bash

If you have Git for Windows installed:

1. Open **Git Bash** (not PowerShell)
2. Navigate to project: `cd /c/Users/mason/real-estate-os`
3. Run the bash script: `./scripts/demo/start-demo.sh`

This works exactly like Linux!

### Enable Copy/Paste in PowerShell

Right-click PowerShell title bar → Properties → Options → Enable Ctrl+Shift+C/V

---

## 🎯 Next Steps

Once your demo environment is running:

1. **Practice once** - Run through DEMO_GUIDE.md
2. **Test /healthz** in Swagger UI (click "Try it out")
3. **Test /ping** 3 times (watch count increment)
4. **Show GitHub Actions** (green checkmarks)
5. **You're ready!** 🚀

---

## 🆘 Still Having Issues?

### Common Windows-Specific Issues:

**1. Docker Desktop won't start**
- Restart Windows
- Check Windows updates
- Reinstall Docker Desktop

**2. WSL 2 error**
- Docker Desktop needs WSL 2
- Run: `wsl --update` in PowerShell (as Admin)
- Restart Docker Desktop

**3. Virtualization not enabled**
- Restart computer
- Enter BIOS (usually F2 or Del during startup)
- Enable "Intel VT-x" or "AMD-V"
- Save and exit BIOS

**4. Firewall blocking ports**
- Temporarily disable Windows Firewall
- Or add exception for Docker Desktop

---

## 📞 Getting Help

If still stuck:
1. Check Docker Desktop logs (click whale icon → Troubleshoot)
2. Run: `docker compose -f docker-compose.api.yml logs`
3. Check: GitHub Issues in the repo

---

**Remember: Once it's running, it's EASY. The first setup is always the hardest part!**

**You've got this!** 💪
