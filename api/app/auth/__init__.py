"""Authentication and authorization module

Provides:
- JWT token generation and validation
- OAuth2/OIDC integration (Keycloak or generic OAuth2)
- API key management for service-to-service auth
- Role-based access control (RBAC)
"""

from .jwt_handler import create_access_token, verify_token
from .dependencies import (
    get_current_user,
    get_current_tenant,
    require_role,
    get_api_key_user
)
from .models import User, Role

__all__ = [
    'create_access_token',
    'verify_token',
    'get_current_user',
    'get_current_tenant',
    'require_role',
    'get_api_key_user',
    'User',
    'Role',
]
