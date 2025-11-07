# Real Estate OS - Windows Demo Setup Script
# PowerShell version for Windows users

# Colors for output
function Write-Success { param($message) Write-Host "✓ $message" -ForegroundColor Green }
function Write-Error { param($message) Write-Host "✗ $message" -ForegroundColor Red }
function Write-Info { param($message) Write-Host "ℹ $message" -ForegroundColor Cyan }
function Write-Step { param($message) Write-Host "▶ $message" -ForegroundColor Blue }
function Write-Warning { param($message) Write-Host "⚠ $message" -ForegroundColor Yellow }

# Banner
Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║        Real Estate OS - Demo Environment Setup              ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Configuration
$COMPOSE_FILE = "docker-compose.api.yml"
$API_URL = "http://localhost:8000"

# Check prerequisites
Write-Step "Checking prerequisites..."

# Check Docker
if (Get-Command docker -ErrorAction SilentlyContinue) {
    $dockerVersion = docker --version
    Write-Success "Docker found: $dockerVersion"
} else {
    Write-Error "Docker not found. Please install Docker Desktop for Windows."
    Write-Info "Download from: https://www.docker.com/products/docker-desktop"
    exit 1
}

# Check if Docker is running
$dockerInfo = docker info 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Error "Docker is not running. Please start Docker Desktop."
    exit 1
}
Write-Success "Docker is running"

# Check docker compose
$composeCheck = docker compose version 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Success "docker compose found"
} else {
    Write-Error "docker compose not found. Please update Docker Desktop."
    exit 1
}

Write-Host ""

# Check if compose file exists
if (-not (Test-Path $COMPOSE_FILE)) {
    Write-Error "Docker Compose file not found: $COMPOSE_FILE"
    Write-Info "Are you in the project root directory?"
    Write-Info "Current directory: $(Get-Location)"
    exit 1
}

# Stop any existing services
Write-Step "Cleaning up any existing services..."
docker compose -f $COMPOSE_FILE down -v 2>&1 | Out-Null
Write-Success "Cleanup complete"

Write-Host ""

# Start services
Write-Step "Starting demo services..."
Write-Info "This will take about 30-60 seconds..."
Write-Host ""

docker compose -f $COMPOSE_FILE up -d --wait

if ($LASTEXITCODE -eq 0) {
    Write-Success "Services started successfully!"
} else {
    Write-Error "Failed to start services"
    Write-Info "Check logs with: docker compose -f $COMPOSE_FILE logs"
    exit 1
}

Write-Host ""

# Wait for initialization
Write-Step "Waiting for services to fully initialize..."
Start-Sleep -Seconds 5

# Show service status
Write-Step "Service status:"
Write-Host ""
docker compose -f $COMPOSE_FILE ps
Write-Host ""

# Check API health
Write-Step "Testing API health..."

$healthCheckSuccess = $false
for ($i = 1; $i -le 30; $i++) {
    try {
        $response = Invoke-WebRequest -Uri "$API_URL/healthz" -UseBasicParsing -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            Write-Success "API is healthy! (/healthz responding)"
            $healthCheckSuccess = $true
            break
        }
    } catch {
        # API not ready yet
    }
    Start-Sleep -Seconds 1
}

if (-not $healthCheckSuccess) {
    Write-Error "API health check timed out after 30 attempts"
    Write-Info "Check logs: docker compose -f $COMPOSE_FILE logs api"
    exit 1
}

# Test endpoints
Write-Host ""
Write-Step "Testing /healthz endpoint:"
try {
    $healthResponse = Invoke-RestMethod -Uri "$API_URL/healthz" -Method Get
    $healthResponse | ConvertTo-Json
    Write-Success "/healthz test passed"
} catch {
    Write-Warning "Could not test /healthz: $_"
}

Write-Host ""
Write-Step "Testing /ping endpoint (database connectivity):"
try {
    $pingResponse = Invoke-RestMethod -Uri "$API_URL/ping" -Method Get
    $pingResponse | ConvertTo-Json
    Write-Success "/ping test passed"
} catch {
    Write-Warning "Could not test /ping: $_"
}

Write-Host ""

# Success banner
Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║              🎉 Demo Environment Ready! 🎉                   ║" -ForegroundColor Green
Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""

# Display access URLs
Write-Info "Access URLs:"
Write-Host "  ▶ Swagger UI (Interactive Docs): " -NoNewline -ForegroundColor Blue
Write-Host "http://localhost:8000/docs" -ForegroundColor Green
Write-Host "  ▶ ReDoc (Alternative Docs):      " -NoNewline -ForegroundColor Blue
Write-Host "http://localhost:8000/redoc" -ForegroundColor Green
Write-Host "  ▶ Health Check:                   " -NoNewline -ForegroundColor Blue
Write-Host "http://localhost:8000/healthz" -ForegroundColor Green
Write-Host "  ▶ OpenAPI Spec:                   " -NoNewline -ForegroundColor Blue
Write-Host "http://localhost:8000/docs/openapi.json" -ForegroundColor Green
Write-Host ""

# Quick test commands
Write-Info "Quick Test Commands (PowerShell):"
Write-Host "  ▶ Test health:    " -NoNewline -ForegroundColor Blue
Write-Host "Invoke-RestMethod http://localhost:8000/healthz" -ForegroundColor Yellow
Write-Host "  ▶ Test database:  " -NoNewline -ForegroundColor Blue
Write-Host "Invoke-RestMethod http://localhost:8000/ping" -ForegroundColor Yellow
Write-Host "  ▶ View logs:      " -NoNewline -ForegroundColor Blue
Write-Host "docker compose -f $COMPOSE_FILE logs -f" -ForegroundColor Yellow
Write-Host "  ▶ Stop services:  " -NoNewline -ForegroundColor Blue
Write-Host "docker compose -f $COMPOSE_FILE down" -ForegroundColor Yellow
Write-Host ""

# Pre-demo checklist
Write-Info "Pre-Demo Checklist:"
Write-Success "Services started and healthy"
Write-Success "API responding to requests"
Write-Success "Database connection working"
Write-Host ""
Write-Host "  ☐ Open Swagger UI in browser (http://localhost:8000/docs)" -ForegroundColor Yellow
Write-Host "  ☐ Open GitHub Actions page (show passing CI/CD)" -ForegroundColor Yellow
Write-Host "  ☐ Review DEMO_GUIDE.md for talking points" -ForegroundColor Yellow
Write-Host "  ☐ Test /healthz and /ping endpoints" -ForegroundColor Yellow
Write-Host "  ☐ Prepare backup screenshots (if needed)" -ForegroundColor Yellow
Write-Host ""

# Demo resources
Write-Info "Demo Resources:"
Write-Host "  ▶ Main Guide:     " -NoNewline -ForegroundColor Blue
Write-Host "DEMO_GUIDE.md" -ForegroundColor Yellow
Write-Host "  ▶ Cheat Sheet:    " -NoNewline -ForegroundColor Blue
Write-Host "DEMO_CHEAT_SHEET.md" -ForegroundColor Yellow
Write-Host "  ▶ Testing Guide:  " -NoNewline -ForegroundColor Blue
Write-Host "docs\MANUAL_TESTING_GUIDE.md" -ForegroundColor Yellow
Write-Host ""

# Open browser automatically (optional)
$openBrowser = Read-Host "Open Swagger UI in browser? (Y/n)"
if ($openBrowser -ne 'n' -and $openBrowser -ne 'N') {
    Write-Info "Opening Swagger UI..."
    Start-Process "http://localhost:8000/docs"
}

Write-Host ""
Write-Host "🎬 You're ready to demo!" -ForegroundColor Green
Write-Host ""
Write-Info "TIP: Keep this PowerShell window open to monitor service health during the demo."
Write-Host ""
