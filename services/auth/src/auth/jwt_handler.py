"""
JWT token generation and validation
"""

import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from dataclasses import dataclass

import jwt
from jwt.exceptions import InvalidTokenError


@dataclass
class TokenData:
    """Data extracted from JWT token"""

    user_id: str
    tenant_id: str
    email: str
    role: str
    exp: int
    iat: int


class JWTHandler:
    """Handles JWT token creation and validation"""

    def __init__(
        self,
        secret_key: Optional[str] = None,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 30,
        refresh_token_expire_days: int = 7,
    ):
        """
        Initialize JWT handler.

        Args:
            secret_key: Secret key for signing tokens (from env if not provided)
            algorithm: JWT algorithm (default: HS256)
            access_token_expire_minutes: Access token expiration in minutes
            refresh_token_expire_days: Refresh token expiration in days
        """
        self.secret_key = secret_key or os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-in-production")
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days

    def create_access_token(
        self,
        user_id: str,
        tenant_id: str,
        email: str,
        role: str,
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """
        Create a new access token.

        Args:
            user_id: User ID
            tenant_id: Tenant ID
            email: User email
            role: User role
            expires_delta: Custom expiration time delta

        Returns:
            Encoded JWT token string
        """
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)

        payload = {
            "sub": user_id,  # Subject (user ID)
            "tenant_id": tenant_id,
            "email": email,
            "role": role,
            "type": "access",
            "exp": expire,
            "iat": datetime.utcnow(),
        }

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(
        self,
        user_id: str,
        tenant_id: str,
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """
        Create a new refresh token.

        Args:
            user_id: User ID
            tenant_id: Tenant ID
            expires_delta: Custom expiration time delta

        Returns:
            Encoded JWT refresh token string
        """
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)

        payload = {
            "sub": user_id,
            "tenant_id": tenant_id,
            "type": "refresh",
            "exp": expire,
            "iat": datetime.utcnow(),
        }

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def verify_token(self, token: str) -> TokenData:
        """
        Verify and decode a JWT token.

        Args:
            token: JWT token string

        Returns:
            TokenData with extracted claims

        Raises:
            InvalidTokenError: If token is invalid or expired
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])

            # Verify this is an access token
            if payload.get("type") != "access":
                raise InvalidTokenError("Invalid token type")

            return TokenData(
                user_id=payload["sub"],
                tenant_id=payload["tenant_id"],
                email=payload["email"],
                role=payload["role"],
                exp=payload["exp"],
                iat=payload["iat"],
            )
        except jwt.ExpiredSignatureError:
            raise InvalidTokenError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise InvalidTokenError(f"Invalid token: {str(e)}")
        except KeyError as e:
            raise InvalidTokenError(f"Missing required claim: {str(e)}")

    def verify_refresh_token(self, token: str) -> Dict[str, Any]:
        """
        Verify a refresh token.

        Args:
            token: JWT refresh token string

        Returns:
            Dictionary with user_id and tenant_id

        Raises:
            InvalidTokenError: If token is invalid or expired
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])

            # Verify this is a refresh token
            if payload.get("type") != "refresh":
                raise InvalidTokenError("Invalid token type")

            return {
                "user_id": payload["sub"],
                "tenant_id": payload["tenant_id"],
            }
        except jwt.ExpiredSignatureError:
            raise InvalidTokenError("Refresh token has expired")
        except jwt.InvalidTokenError as e:
            raise InvalidTokenError(f"Invalid refresh token: {str(e)}")
        except KeyError as e:
            raise InvalidTokenError(f"Missing required claim: {str(e)}")

    def decode_token_unsafe(self, token: str) -> Dict[str, Any]:
        """
        Decode token without verification (for debugging/inspection only).

        Args:
            token: JWT token string

        Returns:
            Decoded payload dictionary
        """
        return jwt.decode(token, options={"verify_signature": False})
