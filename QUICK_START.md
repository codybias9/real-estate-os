# Real Estate OS - Quick Start Guide

## Prerequisites

- Docker Desktop (with WSL2 backend for Windows)
- Python 3.11+
- Node.js 18+
- Git

## Setup Steps

### 1. Set Environment Variables

Create a `.env` file in the root directory:

```bash
# Copy the example file
cp .env.example .env
```

Or create it manually with this content:

```
AIRFLOW_UID=50000
AIRFLOW_GID=0
POSTGRES_USER=airflow
POSTGRES_PASSWORD=airflow
POSTGRES_DB=airflow
API_URL=http://localhost:8000
NEXT_PUBLIC_API_URL=http://localhost:8000
```

**Windows users**: You need to export the AIRFLOW_UID variable before starting Docker:

```bash
export AIRFLOW_UID=50000
```

### 2. Start Docker Services

**Option A: Using docker compose (recommended)**
```bash
export AIRFLOW_UID=50000
docker compose up -d
```

**Option B: Using docker-compose**
```bash
export AIRFLOW_UID=50000
docker-compose up -d
```

Wait for all containers to start (about 30 seconds). Check status:
```bash
docker compose ps
```

All containers should show "healthy" or "running" status.

### 3. Run Database Migrations

First, install Python dependencies:

```bash
pip3 install alembic sqlalchemy psycopg2-binary
```

Then run migrations:

```bash
cd db
alembic upgrade head
cd ..
```

### 4. Install Python Dependencies

```bash
pip3 install -r requirements.txt
```

Note: Some packages (like weasyprint) may require system dependencies. If PDF generation fails, the system will save as HTML instead.

### 5. Generate Demo Data

```bash
python3 scripts/generate_demo_data.py
```

This creates:
- 50 properties across 5 cities
- Enrichment data for all properties
- Investment scores (0-100)
- 20 investor memo PDFs
- 3 email campaigns with sample data

**Expected output:**
```
============================================================
REAL ESTATE OS - DEMO DATA GENERATOR
============================================================

Generating 50 properties...
✓ Created 50 properties

Enriching 50 properties...
  Enriched 10/50...
  Enriched 20/50...
  ...
✓ Enriched 50 properties

Scoring 50 properties...
  Scored 10/50...
  ...
✓ Scored 50 properties

Generating investor memos for top properties...
  Generated memo for 123 Main St, Las Vegas (Score: 92)
  ...
✓ Generated 20 investor memos

Creating sample campaigns...
✓ Created 3 campaigns

Executing sample campaign...
  Sent 25 emails
  Engagement: 10 opens, 4 clicks, 1 replies
✓ Campaign executed successfully

============================================================
DEMO DATA GENERATION SUMMARY
============================================================

Database Records:
  Properties: 50
  Enriched: 50
  Scored: 50
  Documents: 20
  Campaigns: 3

Score Distribution:
  High (≥80): 15
  Medium (60-79): 25
  Low (<60): 10

Top 5 Properties:
  95/100 - 456 Lake View Dr, Scottsdale
  92/100 - 789 Desert Rose Ln, Henderson
  ...

============================================================
✓ Demo data generation complete!
============================================================
```

### 6. Start the Frontend

Open a **new terminal** and run:

```bash
cd frontend
npm install
npm run dev
```

The frontend will start on http://localhost:3000

## Access the Platform

Once everything is running, access:

- **Dashboard**: http://localhost:3000
- **API Documentation**: http://localhost:8000/docs
- **Airflow UI**: http://localhost:8080 (username: `airflow`, password: `airflow`)

## Troubleshooting

### Docker Services Not Starting

**Problem**: Redis container unhealthy or dependency failed to start

**Solution 1**: Stop all containers and restart
```bash
docker compose down
export AIRFLOW_UID=50000
docker compose up -d
```

**Solution 2**: Check Docker Desktop is running and has enough resources
- Recommended: 4GB RAM, 2 CPUs minimum

**Solution 3**: View logs to see the error
```bash
docker compose logs redis
docker compose logs postgres
```

### AIRFLOW_UID Warning

**Problem**: Warning about AIRFLOW_UID variable not set

**Solution**: Always export the variable before running docker compose
```bash
export AIRFLOW_UID=50000
```

Or add it to your `.bashrc` or `.zshrc`:
```bash
echo 'export AIRFLOW_UID=50000' >> ~/.bashrc
source ~/.bashrc
```

### Alembic Not Found

**Problem**: `Command 'alembic' not found`

**Solution**: Install alembic in your Python environment
```bash
pip3 install alembic sqlalchemy psycopg2-binary
```

Or use a Python virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Python Command Not Found

**Problem**: `Command 'python' not found`

**Solution**: Use `python3` instead
```bash
python3 scripts/generate_demo_data.py
```

Or create an alias:
```bash
alias python=python3
```

### Frontend Directory Not Found

**Problem**: `bash: cd: frontend: No such file or directory`

**Solution**: Make sure you're in the project root directory
```bash
cd /home/user/real-estate-os  # or wherever you cloned the repo
cd frontend
npm install
npm run dev
```

### Database Connection Error

**Problem**: Cannot connect to PostgreSQL

**Solution**:
1. Check PostgreSQL container is running:
```bash
docker compose ps postgres
```

2. Check PostgreSQL logs:
```bash
docker compose logs postgres
```

3. Try restarting the container:
```bash
docker compose restart postgres
sleep 10
```

4. Test connection:
```bash
docker compose exec postgres psql -U airflow -d airflow -c "SELECT 1;"
```

### PDF Generation Fails

**Problem**: Error generating PDFs, or PDFs saved as HTML

**Solution**: Install WeasyPrint dependencies (optional, platform falls back to HTML)

**Ubuntu/Debian**:
```bash
sudo apt-get install python3-dev python3-pip python3-setuptools python3-wheel \
  python3-cffi libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 \
  libffi-dev shared-mime-info
pip3 install weasyprint
```

**macOS**:
```bash
brew install cairo pango gdk-pixbuf libffi
pip3 install weasyprint
```

**Windows**: WeasyPrint can be challenging on Windows. The platform will work fine with HTML fallback.

### Port Already in Use

**Problem**: Port 3000, 8000, or 8080 already in use

**Solution 1**: Stop the conflicting service

**Solution 2**: Change ports in configuration files:
- Frontend: Edit `frontend/package.json`, change dev script to `next dev -p 3001`
- API: Edit `docker-compose.yml`, change API port mapping
- Airflow: Edit `docker-compose.yml`, change Airflow webserver port

## Quick Commands Reference

```bash
# Start all services
export AIRFLOW_UID=50000 && docker compose up -d

# Stop all services
docker compose down

# View logs
docker compose logs -f [service-name]

# Restart a service
docker compose restart [service-name]

# Check service status
docker compose ps

# Access PostgreSQL
docker compose exec postgres psql -U airflow -d airflow

# Run migrations
cd db && alembic upgrade head && cd ..

# Generate demo data
python3 scripts/generate_demo_data.py

# Start frontend
cd frontend && npm install && npm run dev

# View API docs
open http://localhost:8000/docs  # or visit in browser
```

## Complete Reset

If you need to start fresh:

```bash
# Stop and remove all containers
docker compose down -v

# Remove generated PDFs (optional)
rm -rf output/documents/*

# Restart from Step 2
export AIRFLOW_UID=50000
docker compose up -d
# ... continue with remaining steps
```

## Next Steps

Once the platform is running:

1. Follow the **Demo Walkthrough** in `DEMO_GUIDE.md`
2. Explore the API at http://localhost:8000/docs
3. Try the frontend pages:
   - Dashboard: Overview and statistics
   - Properties: Browse and filter properties
   - Pipeline: View processing stages
   - Campaigns: Email campaign management

---

For detailed documentation, see:
- **DEMO_GUIDE.md** - Complete demo walkthrough
- **PLATFORM_COMPLETION_SUMMARY.md** - Technical documentation
- **API Docs** - http://localhost:8000/docs (when running)
