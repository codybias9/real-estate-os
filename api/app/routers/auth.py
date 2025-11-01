"""Authentication router

Endpoints:
- POST /auth/register - Register new user (first user creates tenant)
- POST /auth/login - Login with email/password
- POST /auth/refresh - Refresh access token
- GET /auth/me - Get current user info
- POST /auth/api-keys - Create API key
- GET /auth/api-keys - List API keys
- DELETE /auth/api-keys/{id} - Revoke API key
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from datetime import datetime, timedelta
import secrets
from uuid import UUID

from ..database import get_db
from ..auth.models import (
    LoginRequest, TokenResponse, User, Role,
    APIKeyCreate, APIKeyResponse, APIKeyInfo
)
from ..auth.jwt_handler import create_access_token
from ..auth.dependencies import get_current_user, require_role
from ..auth.config import JWT_EXPIRATION_MINUTES

import sys
sys.path.append('/home/user/real-estate-os')
from db.models_auth import User as DBUser, APIKey as DBAPIKey
from db.models_provenance import Tenant as DBTenant


router = APIRouter(
    prefix="/auth",
    tags=["authentication"]
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(
    email: str,
    password: str,
    tenant_name: str,
    db: Session = Depends(get_db)
):
    """Register new user and tenant

    First user creates the tenant and becomes owner.

    Args:
        email: User email
        password: User password (min 8 chars)
        tenant_name: Tenant organization name
        db: Database session

    Returns:
        JWT access token
    """
    # Validate password
    if len(password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters"
        )

    # Check if user already exists
    existing_user = db.query(DBUser).filter(DBUser.email == email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create tenant
    tenant = DBTenant(name=tenant_name)
    db.add(tenant)
    db.flush()

    # Create user (first user is owner)
    password_hash = pwd_context.hash(password)
    user = DBUser(
        tenant_id=tenant.id,
        email=email,
        password_hash=password_hash,
        roles=[Role.OWNER.value],
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Generate access token
    access_token = create_access_token(
        user_id=user.id,
        tenant_id=user.tenant_id,
        roles=[Role.OWNER]
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=JWT_EXPIRATION_MINUTES * 60
    )


@router.post("/login", response_model=TokenResponse)
def login(
    login_request: LoginRequest,
    db: Session = Depends(get_db)
):
    """Login with email and password

    Args:
        login_request: Email and password
        db: Database session

    Returns:
        JWT access token
    """
    # Find user
    user = db.query(DBUser).filter(DBUser.email == login_request.email).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    # Verify password
    if not pwd_context.verify(login_request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )

    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()

    # Generate access token
    access_token = create_access_token(
        user_id=user.id,
        tenant_id=user.tenant_id,
        roles=[Role(r) for r in user.roles]
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=JWT_EXPIRATION_MINUTES * 60
    )


@router.get("/me", response_model=User)
def get_me(current_user: User = Depends(get_current_user)):
    """Get current user information

    Args:
        current_user: Current authenticated user

    Returns:
        User details
    """
    return current_user


@router.post("/api-keys", response_model=APIKeyResponse)
def create_api_key(
    api_key_request: APIKeyCreate,
    current_user: User = Depends(require_role([Role.OWNER, Role.ADMIN])),
    db: Session = Depends(get_db)
):
    """Create new API key

    Only owners and admins can create API keys.

    Args:
        api_key_request: API key creation request
        current_user: Current authenticated user
        db: Database session

    Returns:
        API key details with full key (only shown once)
    """
    # Generate random API key (32 bytes = 64 hex chars)
    api_key = secrets.token_urlsafe(32)

    # Hash the key for storage
    key_hash = pwd_context.hash(api_key)

    # Store key prefix for identification
    key_prefix = api_key[:8]

    # Create API key record
    db_api_key = DBAPIKey(
        tenant_id=current_user.tenant_id,
        name=api_key_request.name,
        description=api_key_request.description,
        key_hash=key_hash,
        key_prefix=key_prefix,
        roles=[role.value for role in api_key_request.roles],
        expires_at=api_key_request.expires_at
    )
    db.add(db_api_key)
    db.commit()
    db.refresh(db_api_key)

    return APIKeyResponse(
        id=db_api_key.id,
        tenant_id=db_api_key.tenant_id,
        name=db_api_key.name,
        description=db_api_key.description,
        key=api_key,  # Only returned on creation
        key_prefix=db_api_key.key_prefix,
        roles=[Role(r) for r in db_api_key.roles],
        is_active=db_api_key.is_active,
        created_at=db_api_key.created_at,
        expires_at=db_api_key.expires_at,
        last_used=db_api_key.last_used
    )


@router.get("/api-keys", response_model=list[APIKeyInfo])
def list_api_keys(
    current_user: User = Depends(require_role([Role.OWNER, Role.ADMIN])),
    db: Session = Depends(get_db)
):
    """List all API keys for current tenant

    Only owners and admins can list API keys.

    Args:
        current_user: Current authenticated user
        db: Database session

    Returns:
        List of API key info (without full keys)
    """
    api_keys = db.query(DBAPIKey).filter(
        DBAPIKey.tenant_id == current_user.tenant_id
    ).order_by(DBAPIKey.created_at.desc()).all()

    return [
        APIKeyInfo(
            id=key.id,
            tenant_id=key.tenant_id,
            name=key.name,
            description=key.description,
            key_prefix=key.key_prefix,
            roles=[Role(r) for r in key.roles],
            is_active=key.is_active,
            created_at=key.created_at,
            expires_at=key.expires_at,
            last_used=key.last_used
        )
        for key in api_keys
    ]


@router.delete("/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_api_key(
    key_id: UUID,
    current_user: User = Depends(require_role([Role.OWNER, Role.ADMIN])),
    db: Session = Depends(get_db)
):
    """Revoke (deactivate) an API key

    Only owners and admins can revoke API keys.

    Args:
        key_id: API key UUID
        current_user: Current authenticated user
        db: Database session
    """
    api_key = db.query(DBAPIKey).filter(
        DBAPIKey.id == key_id,
        DBAPIKey.tenant_id == current_user.tenant_id
    ).first()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )

    # Deactivate instead of deleting (for audit trail)
    api_key.is_active = False
    db.commit()

    return None
