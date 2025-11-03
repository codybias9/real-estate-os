"""
Authentication endpoints

Provides login, token refresh, and user management endpoints.
"""

from typing import Optional
from datetime import timedelta
from pydantic import BaseModel, EmailStr, Field
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPBearer

# Import auth service (would be from services/auth in production)
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../services/auth/src"))

from auth import JWTHandler, PasswordHandler, User, UserRole, get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Initialize handlers
jwt_handler = JWTHandler()
password_handler = PasswordHandler()


# Request/Response models
class LoginRequest(BaseModel):
    """Login request"""

    email: EmailStr
    password: str = Field(..., min_length=8)


class TokenResponse(BaseModel):
    """Token response"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class RefreshTokenRequest(BaseModel):
    """Refresh token request"""

    refresh_token: str


class UserResponse(BaseModel):
    """User response"""

    id: str
    tenant_id: str
    email: str
    full_name: str
    role: str
    is_active: bool


class CreateUserRequest(BaseModel):
    """Create user request"""

    tenant_id: str
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str
    role: UserRole = UserRole.VIEWER


# Mock user database (in production, this would use UserRepository)
MOCK_USERS = {
    "analyst@example.com": {
        "id": "user-123",
        "tenant_id": "tenant-1",
        "email": "analyst@example.com",
        "full_name": "John Analyst",
        "role": UserRole.ANALYST,
        "hashed_password": password_handler.hash_password("password123"),
        "is_active": True,
    },
    "admin@example.com": {
        "id": "user-admin",
        "tenant_id": "tenant-1",
        "email": "admin@example.com",
        "full_name": "Admin User",
        "role": UserRole.ADMIN,
        "hashed_password": password_handler.hash_password("admin123"),
        "is_active": True,
    },
}


@router.post("/login", response_model=TokenResponse, summary="User login")
def login(request: LoginRequest):
    """
    Authenticate user and return access and refresh tokens.

    The access token should be used in the Authorization header:
    `Authorization: Bearer <access_token>`

    The refresh token can be used to obtain a new access token when it expires.

    **Demo credentials**:
    - Analyst: `analyst@example.com` / `password123`
    - Admin: `admin@example.com` / `admin123`
    """
    # Find user by email
    user_data = MOCK_USERS.get(request.email)
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify password
    if not password_handler.verify_password(request.password, user_data["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if not user_data["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )

    # Create tokens
    access_token = jwt_handler.create_access_token(
        user_id=user_data["id"],
        tenant_id=user_data["tenant_id"],
        email=user_data["email"],
        role=user_data["role"].value,
    )

    refresh_token = jwt_handler.create_refresh_token(
        user_id=user_data["id"],
        tenant_id=user_data["tenant_id"],
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=jwt_handler.access_token_expire_minutes * 60,
    )


@router.post("/refresh", response_model=TokenResponse, summary="Refresh access token")
def refresh(request: RefreshTokenRequest):
    """
    Refresh an expired access token using a valid refresh token.

    Returns a new access token and refresh token pair.
    """
    try:
        # Verify refresh token
        token_data = jwt_handler.verify_refresh_token(request.refresh_token)
        user_id = token_data["user_id"]
        tenant_id = token_data["tenant_id"]

        # Find user
        user_data = None
        for user in MOCK_USERS.values():
            if user["id"] == user_id:
                user_data = user
                break

        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )

        if not user_data["is_active"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is disabled",
            )

        # Create new tokens
        access_token = jwt_handler.create_access_token(
            user_id=user_data["id"],
            tenant_id=user_data["tenant_id"],
            email=user_data["email"],
            role=user_data["role"].value,
        )

        refresh_token = jwt_handler.create_refresh_token(
            user_id=user_data["id"],
            tenant_id=user_data["tenant_id"],
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=jwt_handler.access_token_expire_minutes * 60,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid refresh token: {str(e)}",
        )


@router.get("/me", response_model=UserResponse, summary="Get current user")
def get_me(user: User = Depends(get_current_user)):
    """
    Get current authenticated user information.

    Requires valid JWT token in Authorization header.
    """
    return UserResponse(
        id=user.id,
        tenant_id=user.tenant_id,
        email=user.email,
        full_name=user.full_name or "Demo User",
        role=user.role.value,
        is_active=user.is_active,
    )


@router.post("/logout", summary="User logout")
def logout(user: User = Depends(get_current_user)):
    """
    Logout current user.

    In a production system, this would invalidate the refresh token.
    For JWT-based auth, the client should discard the tokens.
    """
    # In production, add refresh token to blacklist
    return {"message": "Logged out successfully"}


# Protected endpoint example
@router.get("/protected", summary="Protected endpoint example")
def protected_endpoint(user: User = Depends(get_current_user)):
    """
    Example of a protected endpoint that requires authentication.

    Only accessible with a valid JWT token.
    """
    return {
        "message": f"Hello {user.email}!",
        "user_id": user.id,
        "tenant_id": user.tenant_id,
        "role": user.role.value,
    }
