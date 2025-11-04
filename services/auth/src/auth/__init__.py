"""
Authentication and Authorization Service

Provides JWT-based authentication, tenant context management,
and role-based access control.
"""

from .jwt_handler import JWTHandler, TokenData
from .password import PasswordHandler
from .middleware import AuthMiddleware, get_current_user, get_current_tenant
from .models import User, UserRole

__all__ = [
    "JWTHandler",
    "TokenData",
    "PasswordHandler",
    "AuthMiddleware",
    "get_current_user",
    "get_current_tenant",
    "User",
    "UserRole",
]
