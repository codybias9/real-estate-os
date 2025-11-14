# PowerShell script to rebuild API container with updated authentication code

Write-Host "Stopping containers..." -ForegroundColor Yellow
docker compose -f docker-compose.api.yml down

Write-Host "`nRebuilding API container (this may take a few minutes)..." -ForegroundColor Yellow
docker compose -f docker-compose.api.yml build --no-cache api

Write-Host "`nStarting containers..." -ForegroundColor Yellow
docker compose -f docker-compose.api.yml up -d

Write-Host "`nWaiting for services to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 15

Write-Host "`nChecking API health..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/healthz" -UseBasicParsing
    Write-Host "API is healthy! Status: $($response.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "API not responding yet, give it a few more seconds..." -ForegroundColor Red
}

Write-Host "`nRecreating demo user with correct password hash..." -ForegroundColor Yellow
$createUserScript = @"
import sys
import os
sys.path.insert(0, '/app')

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from db.models import User, Tenant, Team
from api.auth_utils import hash_password
import uuid

# Connect to database
engine = create_engine('postgresql://realestate:dev_password@db:5432/realestate_db')

with Session(engine) as session:
    # Check if demo user exists
    demo_user = session.query(User).filter(User.email == 'demo@example.com').first()

    if demo_user:
        # Update password hash
        demo_user.password_hash = hash_password('demo123456')
        session.commit()
        print('Demo user password updated successfully!')
    else:
        # Create demo user with tenant and team
        tenant = Tenant(name='Demo Company')
        session.add(tenant)
        session.flush()

        team = Team(tenant_id=tenant.id, name='Demo Company')
        session.add(team)
        session.flush()

        user = User(
            tenant_id=tenant.id,
            team_id=team.id,
            email='demo@example.com',
            full_name='Demo User',
            password_hash=hash_password('demo123456'),
            role='admin',
            is_active=True
        )
        session.add(user)
        session.commit()
        print('Demo user created successfully!')
"@

$createUserScript | docker exec -i real-estate-os-api-1 python -

Write-Host "`nDone! The API is now running with updated authentication." -ForegroundColor Green
Write-Host "You can test login with:" -ForegroundColor Cyan
Write-Host "  Email: demo@example.com" -ForegroundColor White
Write-Host "  Password: demo123456" -ForegroundColor White
Write-Host "`nTry logging in at http://localhost:3000" -ForegroundColor Cyan
