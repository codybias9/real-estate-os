"""Authentication data models

Pydantic models for authentication requests/responses
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum
from uuid import UUID


class Role(str, Enum):
    """User roles for RBAC"""
    OWNER = "owner"  # Tenant owner, full access
    ADMIN = "admin"  # Administrator, manage users
    ANALYST = "analyst"  # Read-only analyst
    SERVICE = "service"  # Service account for API keys


class User(BaseModel):
    """User model"""
    id: UUID
    email: EmailStr
    tenant_id: UUID
    roles: List[Role]
    is_active: bool = True
    created_at: datetime
    last_login: Optional[datetime] = None


class Tenant(BaseModel):
    """Tenant model"""
    id: UUID
    name: str
    is_active: bool = True
    created_at: datetime


class TokenPayload(BaseModel):
    """JWT token payload"""
    sub: str  # User ID
    tenant_id: str
    roles: List[str]
    exp: int  # Expiration timestamp


class TokenResponse(BaseModel):
    """Token response"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class LoginRequest(BaseModel):
    """Login request"""
    email: EmailStr
    password: str


class APIKeyCreate(BaseModel):
    """API key creation request"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    roles: List[Role] = [Role.SERVICE]
    expires_at: Optional[datetime] = None


class APIKeyResponse(BaseModel):
    """API key response"""
    id: UUID
    tenant_id: UUID
    name: str
    description: Optional[str]
    key: str  # Only returned on creation
    key_prefix: str  # First 8 chars for identification
    roles: List[Role]
    is_active: bool
    created_at: datetime
    expires_at: Optional[datetime]
    last_used: Optional[datetime]


class APIKeyInfo(BaseModel):
    """API key info (without full key)"""
    id: UUID
    tenant_id: UUID
    name: str
    description: Optional[str]
    key_prefix: str
    roles: List[Role]
    is_active: bool
    created_at: datetime
    expires_at: Optional[datetime]
    last_used: Optional[datetime]
