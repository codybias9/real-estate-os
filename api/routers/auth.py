"""
Authentication Router
Login, Register, Password Reset, User Profile
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from datetime import timedelta, datetime
from typing import Optional

from api.database import get_db
from api import schemas
from api.auth import (
    authenticate_user,
    create_access_token,
    get_password_hash,
    get_current_user,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from db.models import User, Team, UserRole

router = APIRouter(prefix="/auth", tags=["Authentication"])

# ============================================================================
# REGISTRATION
# ============================================================================

@router.post("/register", response_model=schemas.AuthResponse, status_code=status.HTTP_201_CREATED)
def register(request: schemas.RegisterRequest, db: Session = Depends(get_db)):
    """
    Register a new user and team

    Creates:
    - New team (if team_name provided)
    - New user with hashed password
    - Returns JWT token for immediate login

    Note: First user in a team is automatically assigned ADMIN role
    """
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create or get team
    if request.team_id:
        # Join existing team (requires invite in production)
        team = db.query(Team).filter(Team.id == request.team_id).first()
        if not team:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Team not found"
            )
        user_role = request.role or UserRole.AGENT
    else:
        # Create new team
        team = Team(
            name=request.team_name or f"{request.full_name}'s Team",
            subscription_tier="trial",
            monthly_budget_cap=500.0
        )
        db.add(team)
        db.flush()
        user_role = UserRole.ADMIN  # First user is admin

    # Create user
    user = User(
        team_id=team.id,
        email=request.email,
        full_name=request.full_name,
        password_hash=get_password_hash(request.password),
        role=user_role,
        is_active=True
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    # Create access token
    access_token = create_access_token(
        data={"sub": user.id, "email": user.email, "role": user.role.value}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "team_id": user.team_id,
            "is_active": user.is_active
        }
    }


# ============================================================================
# LOGIN
# ============================================================================

@router.post("/login", response_model=schemas.AuthResponse)
def login(request: schemas.LoginRequest, http_request: Request, db: Session = Depends(get_db)):
    """
    Authenticate user and return JWT token

    Returns:
    - JWT access token (7 day expiration)
    - User profile information

    Token should be included in subsequent requests:
        Authorization: Bearer <token>

    Security:
    - Rate limited: 5 attempts per minute
    - Login lockout: 5 failed attempts = 15 minute lockout
    - Progressive backoff: 15min → 30min → 1hr → 4hr
    - Generic error message (no user enumeration)
    """
    from api.rate_limit import (
        is_locked_out,
        record_failed_login,
        record_successful_login,
        get_remaining_attempts
    )

    # Use email as identifier for lockout tracking
    identifier = request.email.lower()

    # Check if account is locked out
    locked, unlock_in = is_locked_out(identifier)
    if locked:
        remaining_minutes = (unlock_in // 60) + 1
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many failed login attempts. Account locked for {remaining_minutes} minutes.",
            headers={"Retry-After": str(unlock_in)}
        )

    # Attempt authentication
    user = authenticate_user(db, request.email, request.password)

    if not user:
        # Record failed attempt
        record_failed_login(identifier)

        # Get remaining attempts
        remaining = get_remaining_attempts(identifier)

        # Generic error message (prevent user enumeration)
        detail = "Incorrect email or password"
        if remaining > 0 and remaining <= 3:
            # Only show remaining attempts when getting close to lockout
            detail += f". {remaining} attempts remaining before account lockout."

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Successful login - clear failed attempts
    record_successful_login(identifier)

    # Update last login timestamp
    user.last_login = datetime.utcnow()
    db.commit()

    # Create access token
    access_token = create_access_token(
        data={"sub": user.id, "email": user.email, "role": user.role.value}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "team_id": user.team_id,
            "is_active": user.is_active
        }
    }


# ============================================================================
# USER PROFILE
# ============================================================================

@router.get("/me", response_model=schemas.UserResponse)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user's profile

    Requires authentication token in header:
        Authorization: Bearer <token>
    """
    return current_user


@router.patch("/me", response_model=schemas.UserResponse)
def update_current_user_profile(
    request: schemas.UpdateUserRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update current user's profile

    Can update:
    - full_name
    - phone
    - email (must be unique)
    """
    if request.email and request.email != current_user.email:
        # Check if email already exists
        existing = db.query(User).filter(
            User.email == request.email,
            User.id != current_user.id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use"
            )
        current_user.email = request.email

    if request.full_name:
        current_user.full_name = request.full_name

    if request.phone:
        current_user.phone = request.phone

    db.commit()
    db.refresh(current_user)

    return current_user


# ============================================================================
# PASSWORD MANAGEMENT
# ============================================================================

@router.post("/change-password")
def change_password(
    request: schemas.ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Change current user's password

    Requires:
    - current_password: Must match existing password
    - new_password: New password to set
    """
    # Verify current password
    user = authenticate_user(db, current_user.email, request.current_password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )

    # Update password
    current_user.password_hash = get_password_hash(request.new_password)
    db.commit()

    return {"message": "Password changed successfully"}


@router.post("/request-password-reset")
def request_password_reset(request: schemas.RequestPasswordResetRequest, db: Session = Depends(get_db)):
    """
    Request a password reset email

    Production implementation should:
    1. Generate a secure token
    2. Store token with expiration in database
    3. Send email with reset link
    4. Rate limit requests

    For MVP: Returns success regardless of email existence (security best practice)
    """
    user = db.query(User).filter(User.email == request.email).first()

    if user:
        # TODO: Generate reset token and send email
        # reset_token = secrets.token_urlsafe(32)
        # Store token in database with expiration
        # Send email via SendGrid
        pass

    # Always return success (don't reveal if email exists)
    return {
        "message": "If an account exists with this email, a password reset link has been sent"
    }


# ============================================================================
# TOKEN REFRESH
# ============================================================================

@router.post("/refresh", response_model=schemas.TokenResponse)
def refresh_token(current_user: User = Depends(get_current_user)):
    """
    Refresh access token

    Requires valid existing token
    Returns new token with extended expiration
    """
    access_token = create_access_token(
        data={"sub": current_user.id, "email": current_user.email, "role": current_user.role.value}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


# ============================================================================
# LOGOUT (CLIENT-SIDE)
# ============================================================================

@router.post("/logout")
def logout(current_user: User = Depends(get_current_user)):
    """
    Logout endpoint

    Note: JWT tokens are stateless, so logout is handled client-side
    by removing the token from storage.

    For production token blacklisting:
    1. Store token in Redis blacklist with TTL matching token expiration
    2. Check blacklist in get_current_user dependency

    Returns success message
    """
    return {"message": "Logged out successfully"}
