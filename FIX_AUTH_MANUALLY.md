# Manual Fix for Authentication

Since git is in a messy state, here's how to manually fix the authentication code:

## Step 1: Copy the Fixed auth.py

Replace the contents of `api\routers\auth.py` with this:

```python
"""Authentication router with registration and login endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import sys
import os

# Add parent directory to path to import db models
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from db.models import User, Tenant, Team
from api.database import get_db
from api.schemas import UserRegister, UserLogin, UserResponse, TokenResponse
from api.auth_utils import hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """
    Register a new user.

    This endpoint creates:
    1. A new tenant for the organization
    2. A default team within that tenant
    3. The user account linked to both
    """
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        # Create tenant
        tenant = Tenant(
            name=user_data.team_name,
            subscription_tier='trial'
        )
        db.add(tenant)
        db.flush()  # Flush to get the tenant ID

        # Create default team
        team = Team(
            tenant_id=tenant.id,
            name=user_data.team_name,
            subscription_tier='trial',
            monthly_budget_cap=500.00
        )
        db.add(team)
        db.flush()  # Flush to get the team ID

        # Hash password
        password_hash = hash_password(user_data.password)

        # Create user
        user = User(
            tenant_id=tenant.id,
            team_id=team.id,
            email=user_data.email,
            full_name=user_data.full_name,
            password_hash=password_hash,
            role='admin',  # First user is admin
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        return UserResponse.from_user(user)

    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Database integrity error: {str(e)}"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )


@router.post("/login", response_model=UserResponse)
def login(login_data: UserLogin, db: Session = Depends(get_db)):
    """
    Login endpoint for user authentication.
    """
    user = db.query(User).filter(User.email == login_data.email).first()

    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    return UserResponse.from_user(user)
```

## Step 2: Create auth_utils.py

Create file `api\auth_utils.py`:

```python
"""Authentication utilities for password hashing and verification."""
import bcrypt


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    # Generate salt and hash password
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )
```

## Step 3: Create database.py

Create file `api\database.py`:

```python
"""Database session management."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
import os

# Get database URL from environment
DB_DSN = os.getenv('DB_DSN', 'postgresql://realestate:dev_password@localhost:5432/realestate_db')

# Create engine
engine = create_engine(DB_DSN)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

## Step 4: Rebuild Container

After saving these files, rebuild:

```powershell
docker compose -f docker-compose.api.yml down
docker compose -f docker-compose.api.yml build --no-cache api
docker compose -f docker-compose.api.yml up -d
```

## Step 5: Test Login

The demo user should now work:
- Email: demo@example.com
- Password: demo123456
