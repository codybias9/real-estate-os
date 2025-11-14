# Simplified Runtime Verification for Windows
# This version uses the Bash script via Git Bash

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "Runtime Verification - Windows Helper" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "This script will run the verification using Git Bash." -ForegroundColor Yellow
Write-Host ""

# Check if Git Bash is available
$gitBash = "C:\Program Files\Git\bin\bash.exe"
if (-not (Test-Path $gitBash)) {
    $gitBash = "C:\Program Files (x86)\Git\bin\bash.exe"
}

if (-not (Test-Path $gitBash)) {
    Write-Host "ERROR: Git Bash not found!" -ForegroundColor Red
    Write-Host "Please install Git for Windows from: https://git-scm.com/download/win" -ForegroundColor Red
    Write-Host ""
    Write-Host "Or run the verification script directly in Git Bash:" -ForegroundColor Yellow
    Write-Host "  ./RUN_ALL_VERIFICATION.sh" -ForegroundColor Yellow
    exit 1
}

Write-Host "Found Git Bash at: $gitBash" -ForegroundColor Green
Write-Host "Running verification script..." -ForegroundColor Yellow
Write-Host ""

# Run the bash script
& $gitBash -c "./RUN_ALL_VERIFICATION.sh"

Write-Host ""
Write-Host "Verification complete!" -ForegroundColor Green
Write-Host "Check artifacts/pr_evidence/ for results" -ForegroundColor Yellow
