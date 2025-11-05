"""Authentication router."""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from jose import JWTError, jwt
import time

from ..database import get_db
from ..models import User, Organization
from ..schemas.auth import (
    RegisterRequest,
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    ChangePasswordRequest,
    PasswordResetRequest,
    PasswordResetConfirm,
    VerifyEmailRequest,
    UserResponse,
)
from ..services.auth import AuthService
from ..dependencies import get_current_user
from ..config import settings

router = APIRouter(prefix="/auth", tags=["authentication"])


def send_verification_email(email: str, token: str):
    """Mock function to send verification email."""
    # In production, this would send an actual email
    print(f"Verification email would be sent to {email} with token: {token}")


def send_password_reset_email(email: str, token: str):
    """Mock function to send password reset email."""
    # In production, this would send an actual email
    print(f"Password reset email would be sent to {email} with token: {token}")


@router.post("/register", response_model=LoginResponse, status_code=status.HTTP_201_CREATED)
def register(
    request: RegisterRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Register a new user."""
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Validate password
    is_valid, error_message = AuthService.validate_password(request.password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message,
        )

    # Create or get organization
    if request.organization_name:
        # Create new organization
        org_slug = request.organization_name.lower().replace(" ", "-")
        org = Organization(name=request.organization_name, slug=org_slug)
        db.add(org)
        db.flush()
    else:
        # For demo purposes, create a default org or use existing
        org = db.query(Organization).first()
        if not org:
            org = Organization(name="Default Organization", slug="default")
            db.add(org)
            db.flush()

    # Create user
    hashed_password = AuthService.hash_password(request.password)
    user = User(
        organization_id=org.id,
        email=request.email,
        hashed_password=hashed_password,
        first_name=request.first_name,
        last_name=request.last_name,
        phone=request.phone,
        is_active=True,
        is_verified=False,  # Require email verification
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    # Send verification email
    verification_token = AuthService.create_verification_token(user.id)
    background_tasks.add_task(send_verification_email, user.email, verification_token)

    # Generate tokens
    access_token = AuthService.create_access_token(data={"sub": user.id})
    refresh_token = AuthService.create_refresh_token(data={"sub": user.id})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": user,
    }


@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Login user."""
    # Find user
    user = db.query(User).filter(User.email == request.email).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    # Check if account is locked
    if user.locked_until and user.locked_until > datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account is locked until {user.locked_until}. Too many failed login attempts.",
        )

    # Verify password
    if not AuthService.verify_password(request.password, user.hashed_password):
        # Increment failed login attempts
        user.failed_login_attempts += 1
        user.last_failed_login = datetime.utcnow()

        # Progressive delays: 0, 1, 2, 5, 10 seconds
        delay_map = {1: 0, 2: 1, 3: 2, 4: 5, 5: 10}
        delay = delay_map.get(user.failed_login_attempts, 10)

        # Lock account after max attempts
        if user.failed_login_attempts >= settings.MAX_LOGIN_ATTEMPTS:
            user.locked_until = datetime.utcnow() + timedelta(
                minutes=settings.ACCOUNT_LOCKOUT_DURATION_MINUTES
            )

        db.commit()

        # Apply progressive delay
        if delay > 0:
            time.sleep(delay)

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    # Reset failed login attempts
    user.failed_login_attempts = 0
    user.last_failed_login = None
    user.locked_until = None
    user.last_login = datetime.utcnow()
    db.commit()

    # Generate tokens
    access_token = AuthService.create_access_token(data={"sub": user.id})
    refresh_token = AuthService.create_refresh_token(data={"sub": user.id})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": user,
    }


@router.post("/refresh", response_model=RefreshTokenResponse)
def refresh_token(request: RefreshTokenRequest, db: Session = Depends(get_db)):
    """Refresh access token."""
    try:
        payload = jwt.decode(
            request.refresh_token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )

        token_type = payload.get("type")
        if token_type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )

        user_id: int = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )

        # Verify user exists and is active
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )

        # Generate new access token
        access_token = AuthService.create_access_token(data={"sub": user.id})

        return {
            "access_token": access_token,
            "token_type": "bearer",
        }

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )


@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information."""
    return current_user


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Change user password."""
    # Verify current password
    if not AuthService.verify_password(request.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password",
        )

    # Validate new password
    is_valid, error_message = AuthService.validate_password(request.new_password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message,
        )

    # Update password
    current_user.hashed_password = AuthService.hash_password(request.new_password)
    current_user.updated_at = datetime.utcnow()
    db.commit()


@router.post("/password-reset-request", status_code=status.HTTP_204_NO_CONTENT)
def request_password_reset(
    request: PasswordResetRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Request password reset."""
    user = db.query(User).filter(User.email == request.email).first()

    # Always return success to prevent user enumeration
    if user:
        reset_token = AuthService.create_password_reset_token(user.id)
        background_tasks.add_task(send_password_reset_email, user.email, reset_token)


@router.post("/password-reset-confirm", status_code=status.HTTP_204_NO_CONTENT)
def confirm_password_reset(
    request: PasswordResetConfirm,
    db: Session = Depends(get_db),
):
    """Confirm password reset with token."""
    try:
        payload = jwt.decode(
            request.token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )

        token_type = payload.get("type")
        if token_type != "password_reset":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token type",
            )

        user_id: int = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token",
            )

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        # Validate new password
        is_valid, error_message = AuthService.validate_password(request.new_password)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_message,
            )

        # Update password
        user.hashed_password = AuthService.hash_password(request.new_password)
        user.updated_at = datetime.utcnow()
        db.commit()

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired token",
        )


@router.post("/verify-email", status_code=status.HTTP_204_NO_CONTENT)
def verify_email(request: VerifyEmailRequest, db: Session = Depends(get_db)):
    """Verify email address with token."""
    try:
        payload = jwt.decode(
            request.token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )

        token_type = payload.get("type")
        if token_type != "verification":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token type",
            )

        user_id: int = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token",
            )

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        # Mark email as verified
        user.is_verified = True
        user.updated_at = datetime.utcnow()
        db.commit()

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired token",
        )
