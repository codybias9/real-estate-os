# Real Estate OS - Complete Setup Guide
## From Code to Working Demo

**Goal**: Make the platform actually work and be demo-ready

**Current Status**: All code exists, nothing runs
**Target Status**: Full working demo with all features functional

---

## Quick Start (TL;DR)

```bash
# 1. Database
sudo -u postgres createdb realestateos
cd db && alembic upgrade head

# 2. Fix Critical Bug
# Add to db/models.py User class:
password_hash = Column(String(255), nullable=False)

# 3. Backend
cd api
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload

# 4. Frontend
cd frontend
npm install
npm run dev

# 5. Demo!
http://localhost:3000
```

---

## Prerequisites

### System Requirements
- Ubuntu 20.04+ / macOS / WSL2
- 8GB RAM minimum
- 10GB free disk space

### Pre-installed (Already Have)
✅ PostgreSQL 16.10
✅ Redis 7.0.15
✅ Node.js 22.21.0
✅ npm 10.9.4
✅ Python 3.11.14

### Optional (For Full Features)
⚠️ RabbitMQ (for Celery async tasks) - can demo without this
⚠️ MinIO/S3 (for file storage) - can use local filesystem
⚠️ Docker (for easy service management) - not required

---

## Phase 1: Fix Critical Bugs (30 minutes)

### 1.1 Fix User Model - Add Password Storage

**Problem**: User model has NO password_hash column

**File**: `db/models.py`

**Find this** (around line 104):
```python
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255))
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.AGENT)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="SET NULL"))
    is_active = Column(Boolean, default=True)
```

**Add this line** (after `full_name`):
```python
    password_hash = Column(String(255), nullable=False)
```

**Result**:
```python
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255))
    password_hash = Column(String(255), nullable=False)  # ← ADD THIS
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.AGENT)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="SET NULL"))
    is_active = Column(Boolean, default=True)
```

### 1.2 Create Migration

```bash
cd db
alembic revision -m "add_password_hash_to_users"
```

Edit the generated migration file in `db/migrations/versions/XXX_add_password_hash_to_users.py`:

```python
def upgrade():
    op.add_column('users', sa.Column('password_hash', sa.String(length=255), nullable=False))

def downgrade():
    op.drop_column('users', 'password_hash')
```

---

## Phase 2: Database Setup (20 minutes)

### 2.1 Create Databases

```bash
# Production database
sudo -u postgres createdb realestateos

# Test database
sudo -u postgres createdb realestateos_test

# Verify
sudo -u postgres psql -l | grep realestateos
```

### 2.2 Run Migrations

```bash
cd db

# Run all migrations
alembic upgrade head

# Verify tables created
sudo -u postgres psql realestateos -c "\dt"
```

**Expected**: ~30 tables created (users, teams, properties, communications, etc.)

### 2.3 Create First User (Manual)

```bash
# Generate password hash
python3 -c "from passlib.context import CryptContext; print(CryptContext(schemes=['bcrypt']).hash('password123'))"

# Insert user
sudo -u postgres psql realestateos <<EOF
INSERT INTO teams (name, created_at) VALUES ('Demo Team', NOW()) RETURNING id;
-- Note the team_id (probably 1)

INSERT INTO users (email, full_name, password_hash, role, team_id, is_active, created_at)
VALUES (
  'demo@example.com',
  'Demo User',
  '<paste-hash-here>',
  'admin',
  1,
  true,
  NOW()
);
EOF
```

---

## Phase 3: Backend Setup (30 minutes)

### 3.1 Install Python Dependencies

```bash
cd api

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r ../requirements-test.txt

# Verify installation
python -c "import fastapi; print('FastAPI installed:', fastapi.__version__)"
```

### 3.2 Create Environment Configuration

Create `.env` file in project root:

```bash
cat > .env <<'EOF'
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost/realestateos

# JWT Authentication
JWT_SECRET_KEY=$(openssl rand -hex 32)
ACCESS_TOKEN_EXPIRE_MINUTES=10080

# Redis
REDIS_URL=redis://localhost:6379/0

# Optional: External Services (can add later)
# SENDGRID_API_KEY=
# SENDGRID_WEBHOOK_SECRET=
# TWILIO_ACCOUNT_SID=
# TWILIO_AUTH_TOKEN=
# OPENAI_API_KEY=
# S3_ENDPOINT=http://localhost:9000
# S3_ACCESS_KEY=
# S3_SECRET_KEY=
# S3_BUCKET=realestateos-files

# Optional: RabbitMQ (for Celery)
# RABBITMQ_URL=amqp://guest:guest@localhost:5672/
EOF
```

### 3.3 Update API to Load Environment

**File**: `api/main.py`

Add at the top:
```python
from dotenv import load_dotenv
load_dotenv()  # Load .env file
```

### 3.4 Start Backend

```bash
cd api
source venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Verify**:
- API running at http://localhost:8000
- Swagger UI at http://localhost:8000/docs
- Metrics at http://localhost:8000/metrics

---

## Phase 4: Frontend Setup (20 minutes)

### 4.1 Install Dependencies

```bash
cd frontend
npm install
```

### 4.2 Configure Environment

Create `frontend/.env.local`:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 4.3 Fix Auth Connection

**File**: `frontend/src/store/authStore.ts`

Replace the mock `login` function:

```typescript
const login = async (email: string, password: string) => {
  try {
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Login failed')
    }

    const data = await response.json()

    set({
      user: data.user,
      token: data.access_token,
      isAuthenticated: true
    })
  } catch (error) {
    console.error('Login error:', error)
    throw error
  }
}
```

Similarly update `register`:

```typescript
const register = async (email: string, password: string, fullName: string, teamName: string) => {
  try {
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email,
        password,
        full_name: fullName,
        team_name: teamName
      })
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Registration failed')
    }

    const data = await response.json()

    set({
      user: data.user,
      token: data.access_token,
      isAuthenticated: true
    })
  } catch (error) {
    console.error('Registration error:', error)
    throw error
  }
}
```

### 4.4 Update API Client

**File**: `frontend/src/lib/api.ts`

Update the baseURL:

```typescript
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
```

### 4.5 Start Frontend

```bash
cd frontend
npm run dev
```

**Verify**:
- Frontend running at http://localhost:3000
- Can access login page
- Can access registration page

---

## Phase 5: Test Basic Flow (10 minutes)

### 5.1 Test Registration

1. Open http://localhost:3000/auth/register
2. Fill in:
   - Email: test@example.com
   - Password: password123
   - Full Name: Test User
   - Team Name: Test Team
3. Click Register
4. Should redirect to /dashboard

### 5.2 Test Login

1. Logout
2. Go to http://localhost:3000/auth/login
3. Login with: test@example.com / password123
4. Should redirect to /dashboard

### 5.3 Test Property Creation

1. Go to http://localhost:3000/dashboard/pipeline
2. Click "Add Property" (if button exists)
3. Or use API directly:

```bash
curl -X POST http://localhost:8000/api/v1/properties \
  -H "Authorization: Bearer <your-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "address": "123 Main St",
    "city": "San Francisco",
    "state": "CA",
    "zip_code": "94102",
    "owner_name": "John Doe",
    "team_id": 1
  }'
```

---

## Phase 6: Optional External Services

### 6.1 OpenAI (for Memo Generation)

1. Sign up: https://platform.openai.com/signup
2. Get API key: https://platform.openai.com/api-keys
3. Add to `.env`:
```
OPENAI_API_KEY=sk-...
```

4. Test memo generation:
```bash
curl -X POST http://localhost:8000/api/v1/quick-wins/generate-and-send \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "property_id": 1,
    "template_id": 1,
    "send_immediately": false
  }'
```

### 6.2 SendGrid (for Email)

1. Sign up: https://signup.sendgrid.com/
2. Verify sender email
3. Get API key
4. Add to `.env`:
```
SENDGRID_API_KEY=SG.xxx
```

### 6.3 MinIO (for File Storage)

```bash
# Run with Docker
docker run -d -p 9000:9000 -p 9001:9001 \
  -e MINIO_ROOT_USER=minioadmin \
  -e MINIO_ROOT_PASSWORD=minioadmin \
  minio/minio server /data --console-address ":9001"

# Add to .env
S3_ENDPOINT=http://localhost:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_BUCKET=realestateos-files
```

---

## Phase 7: Demo Data (Optional)

Create demo data script `scripts/seed_demo_data.py`:

```python
from db.database import SessionLocal
from db.models import Property, PropertyStage, Team, User
from api.auth import get_password_hash

db = SessionLocal()

# Create demo team
team = Team(name="Demo Real Estate Co")
db.add(team)
db.flush()

# Create demo users
users = [
    User(email="admin@demo.com", full_name="Admin User", password_hash=get_password_hash("password123"), role="admin", team_id=team.id, is_active=True),
    User(email="agent@demo.com", full_name="Agent User", password_hash=get_password_hash("password123"), role="agent", team_id=team.id, is_active=True),
]
db.add_all(users)
db.flush()

# Create demo properties
properties = [
    Property(address="123 Main St", city="San Francisco", state="CA", zip_code="94102", owner_name="John Doe", team_id=team.id, current_stage=PropertyStage.NEW, bird_dog_score=0.85),
    Property(address="456 Oak Ave", city="Oakland", state="CA", zip_code="94601", owner_name="Jane Smith", team_id=team.id, current_stage=PropertyStage.OUTREACH, bird_dog_score=0.72),
    # Add 48 more...
]
db.add_all(properties)

db.commit()
print("Demo data created!")
```

Run:
```bash
cd api
source venv/bin/activate
python ../scripts/seed_demo_data.py
```

---

## Phase 8: Monitoring (Optional)

### 8.1 Prometheus

```bash
# Download and run
wget https://github.com/prometheus/prometheus/releases/download/v2.45.0/prometheus-2.45.0.linux-amd64.tar.gz
tar xvfz prometheus-*.tar.gz
cd prometheus-*

# Create config
cat > prometheus.yml <<EOF
scrape_configs:
  - job_name: 'realestateos'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
EOF

# Start
./prometheus --config.file=prometheus.yml
```

Access: http://localhost:9090

### 8.2 Grafana

```bash
# Download and run
wget https://dl.grafana.com/oss/release/grafana-10.0.0.linux-amd64.tar.gz
tar -zxvf grafana-*.tar.gz
cd grafana-*

# Start
./bin/grafana-server
```

Access: http://localhost:3000 (admin/admin)

Import dashboards from `docs/grafana/*.json`

---

## Troubleshooting

### Backend won't start

```bash
# Check Python version
python3 --version  # Should be 3.9+

# Check dependencies
pip list | grep fastapi

# Check database connection
psql postgresql://postgres:postgres@localhost/realestateos -c "SELECT 1"

# Check port not in use
lsof -i :8000
```

### Frontend won't build

```bash
# Clear cache
rm -rf .next node_modules
npm install
npm run build

# Check Node version
node --version  # Should be 18+
```

### Database connection fails

```bash
# Check PostgreSQL running
pg_isready

# Check connection string
echo $DATABASE_URL

# Test connection
psql $DATABASE_URL -c "SELECT 1"
```

### Login fails

```bash
# Check user exists
psql $DATABASE_URL -c "SELECT email, password_hash FROM users"

# Check JWT secret
echo $JWT_SECRET_KEY

# Check backend logs
# (Look for authentication errors)
```

---

## Success Criteria

✅ Backend starts at http://localhost:8000
✅ Swagger UI accessible at http://localhost:8000/docs
✅ Frontend starts at http://localhost:3000
✅ Can register new user
✅ Can login with credentials
✅ Can create property
✅ Can view pipeline
✅ Can drag property between stages
✅ Can view property details in drawer
✅ Real-time updates work (two tabs)

**DEMO READY!**

---

## What Works Without External Services

| Feature | Without External Services | Notes |
|---------|---------------------------|-------|
| Authentication | ✅ Works | JWT + database |
| Property CRUD | ✅ Works | All database operations |
| Pipeline Kanban | ✅ Works | Drag & drop functional |
| Real-time (SSE) | ✅ Works | Doesn't need external services |
| Memo Generation | ❌ Needs OpenAI | Shows error without API key |
| Email Sending | ❌ Needs SendGrid | Can skip for demo |
| File Uploads | ⚠️ Limited | Works with local filesystem |
| PDF Generation | ⚠️ Partial | Needs ReportLab integration |
| Background Jobs | ⚠️ Optional | Needs RabbitMQ/Celery |
| Monitoring | ⚠️ Optional | Needs Prometheus/Grafana |

**Minimum for Demo**: Just database + backend + frontend = Working pipeline management!

---

## Next Steps After Demo Works

1. **Add OpenAI** - For memo generation ($0.002/memo)
2. **Add SendGrid** - For email sending (40k emails free)
3. **Add MinIO** - For file storage (local or S3)
4. **Load Testing** - Test with 1000+ properties
5. **Mobile Polish** - Responsive layouts
6. **Security Audit** - Penetration testing
7. **Deployment** - Docker + Kubernetes

---

## Estimated Timeline

| Phase | Time | Done? |
|-------|------|-------|
| Fix bugs | 30 min | ⬜ |
| Database setup | 20 min | ⬜ |
| Backend setup | 30 min | ⬜ |
| Frontend setup | 20 min | ⬜ |
| Connect auth | 15 min | ⬜ |
| Test basic flow | 10 min | ⬜ |
| **WORKING DEMO** | **2 hours** | ⬜ |
| Add external services | 4 hours | ⬜ |
| Add demo data | 1 hour | ⬜ |
| Add monitoring | 2 hours | ⬜ |
| **COMPLETE DEMO** | **9 hours** | ⬜ |

---

**Let's make it work!** 🚀
