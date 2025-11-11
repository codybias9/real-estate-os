# PowerShell script to copy updated authentication files from git to working directory
# This bypasses the merge conflict issues

Write-Host "Fetching updated authentication files from git repository..." -ForegroundColor Yellow

# Extract files from the correct git commit
git show origin/claude/review-continue-conversation-011CUxutGDfzr2gDmqgZ22uz:api/routers/auth.py > api\routers\auth.py.new
git show origin/claude/review-continue-conversation-011CUxutGDfzr2gDmqgZ22uz:api/auth_utils.py > api\auth_utils.py.new
git show origin/claude/review-continue-conversation-011CUxutGDfzr2gDmqgZ22uz:api/database.py > api\database.py.new
git show origin/claude/review-continue-conversation-011CUxutGDfzr2gDmqgZ22uz:api/schemas.py > api\schemas.py.new

# Backup old files
Write-Host "Backing up old files..." -ForegroundColor Yellow
Copy-Item api\routers\auth.py api\routers\auth.py.backup -Force
if (Test-Path api\auth_utils.py) { Copy-Item api\auth_utils.py api\auth_utils.py.backup -Force }
if (Test-Path api\database.py) { Copy-Item api\database.py api\database.py.backup -Force }
Copy-Item api\schemas.py api\schemas.py.backup -Force

# Replace with new files
Write-Host "Installing updated files..." -ForegroundColor Yellow
Move-Item api\routers\auth.py.new api\routers\auth.py -Force
Move-Item api\auth_utils.py.new api\auth_utils.py -Force
Move-Item api\database.py.new api\database.py -Force
Move-Item api\schemas.py.new api\schemas.py -Force

Write-Host "Files updated successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Verifying new auth.py..." -ForegroundColor Cyan
Get-Content api\routers\auth.py | Select-Object -First 15

Write-Host "`nNow rebuild the container:" -ForegroundColor Yellow
Write-Host "docker compose -f docker-compose.api.yml build --no-cache api" -ForegroundColor White
Write-Host "docker compose -f docker-compose.api.yml up -d" -ForegroundColor White
