"""Pydantic schemas for API requests and responses."""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from uuid import UUID


class UserRegister(BaseModel):
    """Schema for user registration request."""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    full_name: str = Field(..., min_length=1, max_length=255)
    team_name: str = Field(..., min_length=1, max_length=255)


class UserResponse(BaseModel):
    """Schema for user response."""
    id: str  # UUID converted to string for frontend compatibility
    email: str
    full_name: str
    role: str
    team_id: str  # UUID converted to string
    is_active: bool
    created_at: str  # ISO format string
    last_login: Optional[str] = None  # ISO format string

    class Config:
        from_attributes = True

    @classmethod
    def from_user(cls, user):
        """Create response from User model."""
        return cls(
            id=str(user.id),
            email=user.email,
            full_name=user.full_name,  # Now using full_name directly
            role=user.role,
            team_id=str(user.team_id) if user.team_id else "",
            is_active=user.is_active,
            created_at=user.created_at.isoformat(),
            last_login=user.last_login_at.isoformat() if user.last_login_at else None
        )


class TokenResponse(BaseModel):
    """Schema for authentication token response."""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
