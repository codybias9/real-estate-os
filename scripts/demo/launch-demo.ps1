# ==============================================================================
# Real Estate OS - Demo Launcher (PowerShell)
# ==============================================================================
# Starts the API platform with all endpoints for interactive demo
# Skips optional services (frontend, monitoring) for faster startup
# ==============================================================================

Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host "Real Estate OS - Demo Platform Launcher" -ForegroundColor Cyan
Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host ""

# Navigate to project root
Set-Location $PSScriptRoot\..\..\

Write-Host "📍 Project Directory: $(Get-Location)" -ForegroundColor Yellow
Write-Host "🌿 Git Branch: $(git branch --show-current)" -ForegroundColor Yellow
Write-Host ""

# Stop any existing containers
Write-Host "🛑 Stopping existing containers..." -ForegroundColor Yellow
docker compose -f docker-compose.api.yml down 2>$null

# Build the API container (with all routers)
Write-Host ""
Write-Host "🔨 Building API container (this may take 2-3 minutes)..." -ForegroundColor Yellow
$buildResult = docker compose -f docker-compose.api.yml build --no-cache 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Build failed!" -ForegroundColor Red
    Write-Host $buildResult
    exit 1
}

Write-Host "✅ Build complete!" -ForegroundColor Green

# Start services
Write-Host ""
Write-Host "🚀 Starting services (db, redis, api)..." -ForegroundColor Yellow
docker compose -f docker-compose.api.yml up -d

# Wait for API to be healthy
Write-Host ""
Write-Host "⏳ Waiting for API to be healthy (max 60 seconds)..." -ForegroundColor Yellow

$maxAttempts = 12
$attempt = 0
$healthy = $false

while ($attempt -lt $maxAttempts -and -not $healthy) {
    Start-Sleep -Seconds 5
    $attempt++

    try {
        $health = Invoke-RestMethod -Uri "http://localhost:8000/healthz" -TimeoutSec 2 -ErrorAction Stop
        if ($health.status -eq "healthy") {
            $healthy = $true
            Write-Host "✅ API is healthy!" -ForegroundColor Green
        }
    } catch {
        Write-Host "." -NoNewline -ForegroundColor Yellow
    }
}

if (-not $healthy) {
    Write-Host ""
    Write-Host "❌ API did not become healthy in time" -ForegroundColor Red
    Write-Host ""
    Write-Host "Checking logs..." -ForegroundColor Yellow
    docker logs real-estate-os-api-1 --tail 50
    exit 1
}

# Check endpoint count
Write-Host ""
Write-Host "===============================================================================" -ForegroundColor Cyan
Write-Host "🎯 ENDPOINT VERIFICATION" -ForegroundColor Cyan
Write-Host "===============================================================================" -ForegroundColor Cyan

try {
    $openapi = Invoke-RestMethod -Uri "http://localhost:8000/openapi.json" -ErrorAction Stop
    $endpointCount = $openapi.paths.PSObject.Properties.Count

    Write-Host ""
    Write-Host "📊 Total Endpoints: $endpointCount" -ForegroundColor Green -BackgroundColor Black
    Write-Host ""

    if ($endpointCount -gt 100) {
        Write-Host "✅ SUCCESS! Full Real Estate OS platform is running!" -ForegroundColor Green
        Write-Host "✅ All $endpointCount endpoints loaded successfully!" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Warning: Only $endpointCount endpoints found (expected 140-152)" -ForegroundColor Yellow
    }

    # Show sample endpoints
    Write-Host ""
    Write-Host "📋 Sample Endpoints (first 25):" -ForegroundColor Cyan
    Write-Host "───────────────────────────────────────────────────────────────────" -ForegroundColor Gray
    $openapi.paths.PSObject.Properties.Name | Select-Object -First 25 | ForEach-Object {
        Write-Host "   $_" -ForegroundColor White
    }

    # Group endpoints by category
    Write-Host ""
    Write-Host "📂 Endpoint Categories:" -ForegroundColor Cyan
    Write-Host "───────────────────────────────────────────────────────────────────" -ForegroundColor Gray

    $categories = @{}
    $openapi.paths.PSObject.Properties.Name | ForEach-Object {
        $path = $_
        if ($path -match '^/api/v1/([^/]+)') {
            $category = $matches[1]
            if (-not $categories.ContainsKey($category)) {
                $categories[$category] = 0
            }
            $categories[$category]++
        }
    }

    $categories.GetEnumerator() | Sort-Object Name | ForEach-Object {
        Write-Host "   $($_.Key): $($_.Value) endpoints" -ForegroundColor White
    }

} catch {
    Write-Host "❌ Failed to fetch OpenAPI spec: $_" -ForegroundColor Red
    exit 1
}

# Show running containers
Write-Host ""
Write-Host "===============================================================================" -ForegroundColor Cyan
Write-Host "🐳 RUNNING SERVICES" -ForegroundColor Cyan
Write-Host "===============================================================================" -ForegroundColor Cyan
Write-Host ""
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" --filter "name=real-estate-os"

# Show access URLs
Write-Host ""
Write-Host "===============================================================================" -ForegroundColor Cyan
Write-Host "🌐 ACCESS URLS" -ForegroundColor Cyan
Write-Host "===============================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "   📖 API Documentation (Swagger UI):" -ForegroundColor Green
Write-Host "      http://localhost:8000/docs" -ForegroundColor White
Write-Host ""
Write-Host "   📖 API Documentation (ReDoc):" -ForegroundColor Green
Write-Host "      http://localhost:8000/redoc" -ForegroundColor White
Write-Host ""
Write-Host "   🔍 OpenAPI JSON Spec:" -ForegroundColor Green
Write-Host "      http://localhost:8000/openapi.json" -ForegroundColor White
Write-Host ""
Write-Host "   ❤️  Health Check:" -ForegroundColor Green
Write-Host "      http://localhost:8000/healthz" -ForegroundColor White
Write-Host ""

Write-Host "===============================================================================" -ForegroundColor Cyan
Write-Host "✅ DEMO PLATFORM READY!" -ForegroundColor Green
Write-Host "===============================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Open http://localhost:8000/docs in your browser" -ForegroundColor White
Write-Host "  2. Explore the 16 router categories and $endpointCount endpoints" -ForegroundColor White
Write-Host "  3. Test endpoints interactively using the Swagger UI" -ForegroundColor White
Write-Host ""
Write-Host "To stop the platform:" -ForegroundColor Yellow
Write-Host "  docker compose -f docker-compose.api.yml down" -ForegroundColor White
Write-Host ""
