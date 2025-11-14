# Authentication Fix - Quick Start Guide

## Problem Summary

The login is failing because the Docker container is running with old authentication code that uses `passlib`, while your local codebase has been updated to use simple `bcrypt` hashing. The password hashes created by the new code aren't compatible with the old verification code in the container.

## The Solution

Rebuild the API container to pick up the updated authentication code. I've created scripts to make this easy.

## Quick Fix (Recommended)

### On Windows (PowerShell):
```powershell
.\rebuild-api.ps1
```

### On Linux/Mac (Bash):
```bash
./rebuild-api.sh
```

## What These Scripts Do

1. **Stop** the current containers
2. **Rebuild** the API container with `--no-cache` to ensure fresh build
3. **Start** all containers (db, redis, api)
4. **Wait** for services to become healthy
5. **Create/Update** a demo user with credentials:
   - Email: `demo@example.com`
   - Password: `demo123456`

## After Running the Script

1. Wait about 15-20 seconds for all services to start
2. Open your browser to http://localhost:3000
3. Login with the demo credentials above
4. You should now see the dashboard!

## Manual Steps (If Scripts Don't Work)

If the automated scripts fail, you can run these commands manually:

```bash
# Stop containers
docker compose -f docker-compose.api.yml down

# Rebuild API (no cache)
docker compose -f docker-compose.api.yml build --no-cache api

# Start containers
docker compose -f docker-compose.api.yml up -d

# Wait 15 seconds, then create demo user
docker exec real-estate-os-api-1 python -c "
import sys; sys.path.insert(0, '/app')
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from db.models import User, Tenant, Team
from api.auth_utils import hash_password

engine = create_engine('postgresql://realestate:dev_password@db:5432/realestate_db')
with Session(engine) as session:
    # Delete old demo user if exists
    session.query(User).filter(User.email == 'demo@example.com').delete()
    session.commit()

    # Create new demo user
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
    print('Demo user created!')
"
```

## Verification

Check that the API is running:
```bash
curl http://localhost:8000/healthz
# Should return: {"status":"ok"}
```

Check the API logs:
```bash
docker logs real-estate-os-api-1
# Should show uvicorn started without errors
```

## What Changed

The updated authentication code:
- **Location**: `api/routers/auth.py`, `api/auth_utils.py`
- **Uses**: Simple bcrypt password hashing (no passlib)
- **API Endpoint**: `POST /api/v1/auth/login` (accepts JSON body)
- **Response Format**: Returns user data with string UUIDs and ISO timestamps

## Troubleshooting

### "Docker command not found"
- Make sure Docker Desktop is running
- Try opening a new terminal window

### "Container name not found"
- Run `docker ps` to see running containers
- The container name might be different (use the actual name you see)

### Login still fails after rebuild
1. Check API logs: `docker logs real-estate-os-api-1`
2. Verify the demo user was created: Run the demo user creation script again
3. Check the frontend is pointing to the right API endpoint

### Frontend not loading
- The frontend (port 3000) must be running separately
- This repository only contains the API backend
- Make sure the frontend is configured to use `http://localhost:8000/api/v1`

## Next Steps After Login Works

Once you can log in and see the dashboard:
1. Test the property listing features
2. Test team/tenant isolation
3. Verify all API endpoints work correctly
4. Consider setting up proper JWT token authentication for production
