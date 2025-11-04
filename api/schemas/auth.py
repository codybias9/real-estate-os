"""
Pydantic schemas for authentication endpoints
"""
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime
import uuid


# ============================================================================
# AUTH REQUEST SCHEMAS
# ============================================================================

class UserRegisterRequest(BaseModel):
    """Schema for user registration"""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    full_name: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    organization_name: str = Field(..., min_length=2, max_length=255)

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "SecurePass123!",
                "full_name": "John Doe",
                "phone": "+1234567890",
                "organization_name": "Acme Real Estate"
            }
        }


class UserLoginRequest(BaseModel):
    """Schema for user login"""
    email: EmailStr
    password: str

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "SecurePass123!"
            }
        }


class TokenRefreshRequest(BaseModel):
    """Schema for token refresh"""
    refresh_token: str


class PasswordResetRequest(BaseModel):
    """Schema for password reset request"""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Schema for password reset confirmation"""
    token: str
    new_password: str = Field(..., min_length=8, max_length=100)


class PasswordChangeRequest(BaseModel):
    """Schema for password change (when logged in)"""
    old_password: str
    new_password: str = Field(..., min_length=8, max_length=100)


class EmailVerificationRequest(BaseModel):
    """Schema for email verification"""
    token: str


# ============================================================================
# AUTH RESPONSE SCHEMAS
# ============================================================================

class TokenResponse(BaseModel):
    """Schema for token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 1800
            }
        }


class UserResponse(BaseModel):
    """Schema for user response"""
    id: uuid.UUID
    email: str
    username: Optional[str]
    full_name: Optional[str]
    phone: Optional[str]
    avatar_url: Optional[str]
    status: str
    email_verified: bool
    phone_verified: bool
    organization_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "email": "user@example.com",
                "username": "johndoe",
                "full_name": "John Doe",
                "phone": "+1234567890",
                "avatar_url": "https://example.com/avatar.jpg",
                "status": "active",
                "email_verified": True,
                "phone_verified": False,
                "organization_id": "123e4567-e89b-12d3-a456-426614174001",
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-01T00:00:00Z"
            }
        }


class LoginResponse(BaseModel):
    """Schema for login response"""
    user: UserResponse
    tokens: TokenResponse

    class Config:
        json_schema_extra = {
            "example": {
                "user": UserResponse.Config.json_schema_extra["example"],
                "tokens": TokenResponse.Config.json_schema_extra["example"]
            }
        }


class RegisterResponse(BaseModel):
    """Schema for registration response"""
    user: UserResponse
    tokens: TokenResponse
    message: str = "Registration successful"

    class Config:
        json_schema_extra = {
            "example": {
                "user": UserResponse.Config.json_schema_extra["example"],
                "tokens": TokenResponse.Config.json_schema_extra["example"],
                "message": "Registration successful. Please verify your email."
            }
        }


class MessageResponse(BaseModel):
    """Generic message response"""
    message: str
    success: bool = True

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Operation completed successfully",
                "success": True
            }
        }


class ErrorResponse(BaseModel):
    """Error response schema"""
    detail: str
    error_code: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "detail": "Invalid credentials",
                "error_code": "AUTH_001"
            }
        }


# ============================================================================
# USER UPDATE SCHEMAS
# ============================================================================

class UserUpdateRequest(BaseModel):
    """Schema for updating user profile"""
    full_name: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    avatar_url: Optional[str] = Field(None, max_length=500)

    class Config:
        json_schema_extra = {
            "example": {
                "full_name": "John Updated Doe",
                "phone": "+1234567890",
                "avatar_url": "https://example.com/new-avatar.jpg"
            }
        }
