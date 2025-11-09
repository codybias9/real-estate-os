# PowerShell script to run Alembic migrations
# Run this from the real-estate-os directory in PowerShell

Write-Host "================================" -ForegroundColor Cyan
Write-Host "Running Alembic Migrations" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# Execute migrations inside the API container
Write-Host "Executing migrations in API container..." -ForegroundColor Yellow
docker exec -it real-estate-os-api-1 bash -c "cd /app && alembic -c db/alembic.ini upgrade head"

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "================================" -ForegroundColor Green
    Write-Host "Migrations completed successfully!" -ForegroundColor Green
    Write-Host "================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "You can now register a user account at http://localhost:3000" -ForegroundColor Cyan
} else {
    Write-Host ""
    Write-Host "================================" -ForegroundColor Red
    Write-Host "Migration failed!" -ForegroundColor Red
    Write-Host "================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Check the output above for errors." -ForegroundColor Yellow
}
