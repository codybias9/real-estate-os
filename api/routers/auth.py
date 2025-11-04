"""
Authentication router - handles registration, login, token refresh, password reset
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import uuid
import time

from api.core.database import get_db
from api.core.security import (
    hash_password,
    verify_password,
    validate_password_strength,
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_token_type,
    calculate_lockout_until,
    get_progressive_backoff_delay,
    is_user_locked_out,
    generate_email_verification_token,
    generate_password_reset_token,
    hash_token,
)
from api.core.config import settings
from api.core.exceptions import (
    AuthenticationError,
    ValidationError,
    DuplicateResourceError,
    AccountLockedError,
)
from api.dependencies.auth import get_current_user, get_current_active_user
from api.schemas.auth import (
    UserRegisterRequest,
    UserLoginRequest,
    TokenRefreshRequest,
    PasswordResetRequest,
    PasswordResetConfirm,
    PasswordChangeRequest,
    EmailVerificationRequest,
    LoginResponse,
    RegisterResponse,
    TokenResponse,
    UserResponse,
    MessageResponse,
)
from db.models import User, Organization, UserStatus


router = APIRouter(prefix="/auth", tags=["Authentication"])


# ============================================================================
# REGISTRATION
# ============================================================================

@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegisterRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Register a new user and organization.
    Creates a new organization and sets the user as the first member.
    """
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise DuplicateResourceError("User", "email")

    # Validate password strength
    is_valid, error_msg = validate_password_strength(user_data.password)
    if not is_valid:
        raise ValidationError(error_msg)

    # Create organization
    org_slug = user_data.organization_name.lower().replace(" ", "-")
    # Ensure unique slug
    base_slug = org_slug
    counter = 1
    while db.query(Organization).filter(Organization.slug == org_slug).first():
        org_slug = f"{base_slug}-{counter}"
        counter += 1

    organization = Organization(
        id=uuid.uuid4(),
        name=user_data.organization_name,
        slug=org_slug,
        is_active=True,
    )
    db.add(organization)
    db.flush()  # Flush to get org ID

    # Create user
    hashed_password = hash_password(user_data.password)
    user = User(
        id=uuid.uuid4(),
        organization_id=organization.id,
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        phone=user_data.phone,
        status=UserStatus.PENDING,  # User needs to verify email
        email_verified=False,
        phone_verified=False,
        failed_login_attempts=0,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Generate tokens
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    # TODO: Send verification email in background
    # background_tasks.add_task(send_verification_email, user.email, verification_token)

    return RegisterResponse(
        user=UserResponse.from_orm(user),
        tokens=TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        ),
        message="Registration successful. Please check your email to verify your account."
    )


# ============================================================================
# LOGIN
# ============================================================================

@router.post("/login", response_model=LoginResponse)
async def login(
    credentials: UserLoginRequest,
    db: Session = Depends(get_db)
):
    """
    Authenticate user and return JWT tokens.
    Implements login lockout and progressive backoff on failed attempts.
    """
    # Find user by email
    user = db.query(User).filter(User.email == credentials.email).first()

    # Use constant-time comparison to prevent timing attacks
    if not user:
        # Still do a dummy password check to prevent timing attacks
        verify_password("dummy", "$2b$12$dummy.hash.that.never.matches")
        raise AuthenticationError("Invalid email or password")

    # Check if account is locked
    if is_user_locked_out(user.locked_until):
        locked_until_str = user.locked_until.isoformat() if user.locked_until else "unknown"
        raise AccountLockedError(locked_until_str)

    # Apply progressive backoff delay
    if settings.PROGRESSIVE_BACKOFF_ENABLED and user.failed_login_attempts > 0:
        delay = get_progressive_backoff_delay(user.failed_login_attempts)
        if delay > 0:
            time.sleep(delay)

    # Verify password
    if not verify_password(credentials.password, user.hashed_password):
        # Increment failed attempts
        user.failed_login_attempts += 1

        # Calculate lockout if max attempts reached
        if user.failed_login_attempts >= settings.MAX_LOGIN_ATTEMPTS:
            user.locked_until = calculate_lockout_until(user.failed_login_attempts)

        db.commit()

        raise AuthenticationError("Invalid email or password")

    # Check if user is soft deleted
    if user.deleted_at is not None:
        raise AuthenticationError("User account has been deleted")

    # Successful login - reset failed attempts
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = datetime.utcnow()

    # Activate user if they were pending
    if user.status == UserStatus.PENDING:
        user.status = UserStatus.ACTIVE

    db.commit()
    db.refresh(user)

    # Generate tokens
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return LoginResponse(
        user=UserResponse.from_orm(user),
        tokens=TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )
    )


# ============================================================================
# TOKEN REFRESH
# ============================================================================

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_data: TokenRefreshRequest,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token.
    Validates refresh token and issues new access token.
    """
    # Decode refresh token
    payload = decode_token(refresh_data.refresh_token)
    if payload is None:
        raise AuthenticationError("Invalid refresh token")

    # Verify token type
    if not verify_token_type(payload, "refresh"):
        raise AuthenticationError("Invalid token type")

    # Get user ID
    user_id: str = payload.get("sub")
    if user_id is None:
        raise AuthenticationError("Invalid token payload")

    # Verify user exists and is active
    user = db.query(User).filter(User.id == user_id).first()
    if not user or user.status != UserStatus.ACTIVE or user.deleted_at is not None:
        raise AuthenticationError("User not found or inactive")

    # Generate new access token
    access_token = create_access_token(data={"sub": str(user.id)})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_data.refresh_token,  # Return same refresh token
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


# ============================================================================
# LOGOUT
# ============================================================================

@router.post("/logout", response_model=MessageResponse)
async def logout(
    current_user: User = Depends(get_current_active_user)
):
    """
    Logout current user.
    In a stateless JWT system, this mainly serves as documentation.
    Client should discard tokens.

    For production, consider implementing token blacklisting using Redis.
    """
    return MessageResponse(
        message="Logged out successfully. Please discard your tokens.",
        success=True
    )


# ============================================================================
# PASSWORD MANAGEMENT
# ============================================================================

@router.post("/password/reset-request", response_model=MessageResponse)
async def request_password_reset(
    request_data: PasswordResetRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Request password reset.
    Sends password reset email if user exists.
    Always returns success to prevent email enumeration.
    """
    user = db.query(User).filter(User.email == request_data.email).first()

    if user:
        # Generate reset token
        reset_token = generate_password_reset_token()

        # Store hashed token in user meta
        # In production, store in a separate table with expiration
        user.meta["password_reset_token"] = hash_token(reset_token)
        user.meta["password_reset_expires"] = (
            datetime.utcnow() + timedelta(hours=24)
        ).isoformat()
        db.commit()

        # TODO: Send password reset email in background
        # background_tasks.add_task(send_password_reset_email, user.email, reset_token)

    return MessageResponse(
        message="If an account with that email exists, a password reset link has been sent.",
        success=True
    )


@router.post("/password/reset-confirm", response_model=MessageResponse)
async def confirm_password_reset(
    reset_data: PasswordResetConfirm,
    db: Session = Depends(get_db)
):
    """
    Confirm password reset with token.
    Validates token and updates password.
    """
    # Validate new password strength
    is_valid, error_msg = validate_password_strength(reset_data.new_password)
    if not is_valid:
        raise ValidationError(error_msg)

    # Hash the provided token
    hashed_token = hash_token(reset_data.token)

    # Find user with matching token
    users = db.query(User).filter(User.meta["password_reset_token"].astext == hashed_token).all()

    if not users:
        raise AuthenticationError("Invalid or expired reset token")

    user = users[0]

    # Check token expiration
    reset_expires_str = user.meta.get("password_reset_expires")
    if not reset_expires_str:
        raise AuthenticationError("Invalid or expired reset token")

    reset_expires = datetime.fromisoformat(reset_expires_str)
    if datetime.utcnow() > reset_expires:
        raise AuthenticationError("Reset token has expired")

    # Update password
    user.hashed_password = hash_password(reset_data.new_password)
    user.password_changed_at = datetime.utcnow()

    # Clear reset token
    if "password_reset_token" in user.meta:
        del user.meta["password_reset_token"]
    if "password_reset_expires" in user.meta:
        del user.meta["password_reset_expires"]

    # Reset failed login attempts
    user.failed_login_attempts = 0
    user.locked_until = None

    db.commit()

    return MessageResponse(
        message="Password has been reset successfully. You can now login with your new password.",
        success=True
    )


@router.post("/password/change", response_model=MessageResponse)
async def change_password(
    password_data: PasswordChangeRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Change password for authenticated user.
    Requires old password verification.
    """
    # Verify old password
    if not verify_password(password_data.old_password, current_user.hashed_password):
        raise AuthenticationError("Incorrect current password")

    # Validate new password strength
    is_valid, error_msg = validate_password_strength(password_data.new_password)
    if not is_valid:
        raise ValidationError(error_msg)

    # Ensure new password is different from old
    if verify_password(password_data.new_password, current_user.hashed_password):
        raise ValidationError("New password must be different from current password")

    # Update password
    current_user.hashed_password = hash_password(password_data.new_password)
    current_user.password_changed_at = datetime.utcnow()

    db.commit()

    return MessageResponse(
        message="Password changed successfully",
        success=True
    )


# ============================================================================
# EMAIL VERIFICATION
# ============================================================================

@router.post("/verify-email", response_model=MessageResponse)
async def verify_email(
    verification_data: EmailVerificationRequest,
    db: Session = Depends(get_db)
):
    """
    Verify user email with verification token.
    """
    # Hash the provided token
    hashed_token = hash_token(verification_data.token)

    # Find user with matching token
    users = db.query(User).filter(User.meta["email_verification_token"].astext == hashed_token).all()

    if not users:
        raise AuthenticationError("Invalid verification token")

    user = users[0]

    # Mark email as verified
    user.email_verified = True

    # Activate user if they were pending
    if user.status == UserStatus.PENDING:
        user.status = UserStatus.ACTIVE

    # Clear verification token
    if "email_verification_token" in user.meta:
        del user.meta["email_verification_token"]

    db.commit()

    return MessageResponse(
        message="Email verified successfully",
        success=True
    )


# ============================================================================
# USER INFO
# ============================================================================

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current authenticated user information.
    """
    return UserResponse.from_orm(current_user)
