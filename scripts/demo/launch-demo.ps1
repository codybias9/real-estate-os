#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Launch the Real Estate OS Demo
.DESCRIPTION
    Starts Docker Desktop (if needed), launches all demo services, and opens the API documentation.
.EXAMPLE
    .\scripts\demo\launch-demo.ps1
#>

param(
    [switch]$NoBrowser  # Skip opening browser automatically
)

$ErrorActionPreference = "Stop"

Write-Host "🚀 Real Estate OS Demo Launcher" -ForegroundColor Cyan
Write-Host "================================`n" -ForegroundColor Cyan

# Step 1: Check if Docker Desktop is running
Write-Host "Checking Docker Desktop..." -ForegroundColor Yellow

try {
    docker info 2>&1 | Out-Null
    Write-Host "✅ Docker Desktop is running" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Docker Desktop is not running. Starting it now..." -ForegroundColor Yellow

    # Try to start Docker Desktop
    $dockerPath = "${env:ProgramFiles}\Docker\Docker\Docker Desktop.exe"

    if (Test-Path $dockerPath) {
        Start-Process $dockerPath
        Write-Host "   Waiting for Docker Desktop to start (this may take 30-60 seconds)..." -ForegroundColor Yellow

        # Wait for Docker to be ready (max 2 minutes)
        $maxAttempts = 24
        $attempt = 0
        $ready = $false

        while ($attempt -lt $maxAttempts -and -not $ready) {
            Start-Sleep -Seconds 5
            try {
                docker info 2>&1 | Out-Null
                $ready = $true
                Write-Host "✅ Docker Desktop is ready!" -ForegroundColor Green
            } catch {
                $attempt++
                Write-Host "   Still waiting... ($attempt/$maxAttempts)" -ForegroundColor Gray
            }
        }

        if (-not $ready) {
            Write-Host "❌ Docker Desktop failed to start within 2 minutes." -ForegroundColor Red
            Write-Host "   Please start Docker Desktop manually and run this script again." -ForegroundColor Yellow
            exit 1
        }
    } else {
        Write-Host "❌ Docker Desktop not found at: $dockerPath" -ForegroundColor Red
        Write-Host "   Please install Docker Desktop or start it manually." -ForegroundColor Yellow
        exit 1
    }
}

# Step 2: Navigate to project directory
$projectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $projectRoot
Write-Host "`n📁 Working directory: $projectRoot" -ForegroundColor Cyan

# Step 3: Start Docker Compose services
Write-Host "`n🐳 Starting Docker services..." -ForegroundColor Yellow

docker compose -f docker-compose.api.yml up -d

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to start Docker services" -ForegroundColor Red
    exit 1
}

# Step 4: Wait for services to be healthy
Write-Host "`n⏳ Waiting for services to be healthy..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

$maxWait = 30
$waited = 0
$healthy = $false

while ($waited -lt $maxWait -and -not $healthy) {
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:8000/healthz" -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($response.status -eq "ok") {
            $healthy = $true
        }
    } catch {
        Start-Sleep -Seconds 2
        $waited += 2
        Write-Host "   Waiting for API... ($waited seconds)" -ForegroundColor Gray
    }
}

if (-not $healthy) {
    Write-Host "⚠️  Services started but API health check failed" -ForegroundColor Yellow
    Write-Host "   Check logs with: docker compose -f docker-compose.api.yml logs" -ForegroundColor Yellow
} else {
    Write-Host "✅ All services are healthy!" -ForegroundColor Green
}

# Step 5: Test the API
Write-Host "`n🧪 Testing API..." -ForegroundColor Yellow

try {
    $pingResponse = Invoke-RestMethod -Uri "http://localhost:8000/ping"
    Write-Host "✅ Database ping successful! Count: $($pingResponse.count)" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Database ping failed (this might be normal on first run)" -ForegroundColor Yellow
}

# Step 6: Display access information
Write-Host "`n" + ("=" * 60) -ForegroundColor Green
Write-Host "✅ DEMO IS RUNNING!" -ForegroundColor Green
Write-Host ("=" * 60) -ForegroundColor Green

Write-Host "`n📖 Access Points:" -ForegroundColor Cyan
Write-Host "   • API Documentation:  " -NoNewline -ForegroundColor White
Write-Host "http://localhost:8000/docs" -ForegroundColor Yellow
Write-Host "   • Health Check:       " -NoNewline -ForegroundColor White
Write-Host "http://localhost:8000/healthz" -ForegroundColor Yellow
Write-Host "   • Database Ping:      " -NoNewline -ForegroundColor White
Write-Host "http://localhost:8000/ping" -ForegroundColor Yellow

Write-Host "`n📋 Useful Commands:" -ForegroundColor Cyan
Write-Host "   • View logs:          " -NoNewline -ForegroundColor White
Write-Host "docker compose -f docker-compose.api.yml logs -f" -ForegroundColor Gray
Write-Host "   • Stop services:      " -NoNewline -ForegroundColor White
Write-Host "docker compose -f docker-compose.api.yml down" -ForegroundColor Gray
Write-Host "   • Restart services:   " -NoNewline -ForegroundColor White
Write-Host "docker compose -f docker-compose.api.yml restart" -ForegroundColor Gray

# Step 7: Open browser (optional)
if (-not $NoBrowser) {
    Write-Host "`n🌐 Opening API documentation in browser..." -ForegroundColor Yellow
    Start-Sleep -Seconds 2
    Start-Process "http://localhost:8000/docs"
}

Write-Host "`n✨ Enjoy exploring the demo!`n" -ForegroundColor Green
