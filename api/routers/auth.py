"""Authentication router."""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from ..database import get_db
from ..dependencies import get_current_user, get_current_active_user
from ..models import User
from ..schemas.auth import (
    LoginRequest,
    RegisterRequest,
    Token,
    RefreshTokenRequest,
    PasswordResetRequest,
    PasswordResetConfirm,
    ChangePasswordRequest,
    EmailVerificationRequest,
    UserResponse,
    OrganizationResponse,
)
from ..services.auth import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    validate_password_strength,
    record_failed_login,
    is_account_locked,
    reset_failed_attempts,
    generate_verification_token,
    generate_password_reset_token,
    create_organization_with_user,
)
import time

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new organization and user."""
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Validate password strength
    is_valid, error_message = validate_password_strength(request.password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message,
        )

    # Create organization and user
    organization, user = create_organization_with_user(
        db=db,
        org_name=request.organization_name,
        org_email=request.organization_email,
        user_email=request.email,
        user_password=request.password,
        user_first_name=request.first_name,
        user_last_name=request.last_name,
    )

    # Generate email verification token
    user.email_verification_token = generate_verification_token()
    user.email_verification_sent_at = datetime.utcnow()
    db.commit()

    # TODO: Send verification email via background task

    # Create tokens
    access_token = create_access_token(
        data={"sub": user.id, "email": user.email, "org_id": organization.id}
    )
    refresh_token = create_refresh_token(
        data={"sub": user.id, "email": user.email, "org_id": organization.id}
    )

    return Token(access_token=access_token, refresh_token=refresh_token)


@router.post("/login", response_model=Token)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Login with email and password."""
    # Find user
    user = db.query(User).filter(User.email == request.email, User.deleted_at.is_(None)).first()

    # Check if account is locked
    if user and is_account_locked(user):
        lockout_remaining = (user.locked_until - datetime.utcnow()).total_seconds()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Account locked. Try again in {int(lockout_remaining)} seconds.",
        )

    # Progressive delay based on failed attempts
    if user and user.failed_login_attempts > 0:
        delays = [0, 1, 2, 5, 10]  # seconds
        delay_index = min(user.failed_login_attempts, len(delays) - 1)
        time.sleep(delays[delay_index])

    # Authenticate
    authenticated_user = authenticate_user(db, request.email, request.password)

    if not authenticated_user:
        if user:
            record_failed_login(db, user)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Reset failed attempts on successful login
    reset_failed_attempts(db, authenticated_user)

    # Create tokens
    access_token = create_access_token(
        data={
            "sub": authenticated_user.id,
            "email": authenticated_user.email,
            "org_id": authenticated_user.organization_id,
        }
    )
    refresh_token = create_refresh_token(
        data={
            "sub": authenticated_user.id,
            "email": authenticated_user.email,
            "org_id": authenticated_user.organization_id,
        }
    )

    return Token(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=Token)
def refresh_token(request: RefreshTokenRequest, db: Session = Depends(get_db)):
    """Refresh access token using refresh token."""
    payload = decode_token(request.refresh_token)

    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    user_id: int = payload.get("sub")
    user = db.query(User).filter(User.id == user_id, User.deleted_at.is_(None)).first()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    # Create new tokens
    access_token = create_access_token(
        data={"sub": user.id, "email": user.email, "org_id": user.organization_id}
    )
    refresh_token = create_refresh_token(
        data={"sub": user.id, "email": user.email, "org_id": user.organization_id}
    )

    return Token(access_token=access_token, refresh_token=refresh_token)


@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """Get current user information."""
    return current_user


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Change password for current user."""
    from ..services.auth import verify_password

    # Verify current password
    if not verify_password(request.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    # Validate new password
    is_valid, error_message = validate_password_strength(request.new_password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message,
        )

    # Update password
    current_user.password_hash = get_password_hash(request.new_password)
    db.commit()


@router.post("/password-reset-request", status_code=status.HTTP_204_NO_CONTENT)
def request_password_reset(
    request: PasswordResetRequest,
    db: Session = Depends(get_db),
):
    """Request password reset email."""
    user = db.query(User).filter(User.email == request.email, User.deleted_at.is_(None)).first()

    # Always return success to prevent email enumeration
    if not user:
        return

    # Generate reset token
    user.password_reset_token = generate_password_reset_token()
    user.password_reset_sent_at = datetime.utcnow()
    db.commit()

    # TODO: Send password reset email via background task


@router.post("/password-reset-confirm", status_code=status.HTTP_204_NO_CONTENT)
def confirm_password_reset(
    request: PasswordResetConfirm,
    db: Session = Depends(get_db),
):
    """Confirm password reset with token."""
    user = (
        db.query(User)
        .filter(
            User.password_reset_token == request.token,
            User.deleted_at.is_(None),
        )
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    # Check if token is expired (24 hours)
    if user.password_reset_sent_at:
        expiry = user.password_reset_sent_at + timedelta(hours=24)
        if datetime.utcnow() > expiry:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reset token has expired",
            )

    # Validate new password
    is_valid, error_message = validate_password_strength(request.new_password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message,
        )

    # Update password and clear reset token
    user.password_hash = get_password_hash(request.new_password)
    user.password_reset_token = None
    user.password_reset_at = datetime.utcnow()
    db.commit()


@router.post("/verify-email", status_code=status.HTTP_204_NO_CONTENT)
def verify_email(
    request: EmailVerificationRequest,
    db: Session = Depends(get_db),
):
    """Verify email with token."""
    user = (
        db.query(User)
        .filter(
            User.email_verification_token == request.token,
            User.deleted_at.is_(None),
        )
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification token",
        )

    # Mark email as verified
    user.is_verified = True
    user.email_verified_at = datetime.utcnow()
    user.email_verification_token = None
    db.commit()
