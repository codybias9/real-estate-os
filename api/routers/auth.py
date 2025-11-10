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
from api.schemas import UserRegister, UserResponse, TokenResponse
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
def login(email: str, password: str, db: Session = Depends(get_db)):
    """
    Login endpoint for user authentication.
    """
    user = db.query(User).filter(User.email == email).first()

    if not user or not verify_password(password, user.password_hash):
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
