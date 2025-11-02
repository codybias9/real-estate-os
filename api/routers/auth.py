"""
Authentication endpoints: login, refresh, logout.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from typing import Dict, Any
import logging

from api.models import (
    LoginRequest, LoginResponse, RefreshTokenRequest, LogoutRequest
)
from api.auth import keycloak_client, TokenData, get_current_user
from api.rate_limit import check_ip_rate_limit

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Login with username and password",
    description="""
    Authenticate with username/email and password to receive JWT tokens.

    Returns:
    - access_token: Short-lived JWT for API authentication
    - refresh_token: Long-lived token to get new access tokens
    - expires_in: Access token lifetime in seconds
    - tenant_id: User's tenant UUID
    - user_id: User's UUID
    - roles: User's roles for RBAC

    Rate limit: 10 requests per minute per IP
    """
)
async def login(
    request: Request,
    credentials: LoginRequest
) -> LoginResponse:
    """
    Login endpoint - exchange username/password for JWT tokens.
    """
    # Apply IP-based rate limiting (stricter for login)
    await check_ip_rate_limit(request, limit=10)

    try:
        # Exchange credentials for token via Keycloak
        token_response = await keycloak_client.exchange_credentials_for_token(
            username=credentials.username,
            password=credentials.password
        )

        # Decode access token to get user info
        from api.auth import verify_token
        token_data = await verify_token(token_response["access_token"])

        # Build response
        response = LoginResponse(
            access_token=token_response["access_token"],
            refresh_token=token_response["refresh_token"],
            token_type="bearer",
            expires_in=token_response.get("expires_in", 300),
            tenant_id=token_data.tenant_id,
            user_id=token_data.sub,
            roles=token_data.roles
        )

        logger.info(
            f"Successful login: user={token_data.sub}, "
            f"tenant={token_data.tenant_id}, ip={request.client.host}"
        )

        return response

    except HTTPException:
        # Re-raise HTTP exceptions (401 for invalid credentials)
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed. Please try again."
        )


@router.post(
    "/refresh",
    response_model=LoginResponse,
    summary="Refresh access token",
    description="""
    Use refresh token to get a new access token without re-authenticating.

    This endpoint should be called when the access token expires.
    The refresh token has a longer lifetime (typically 30 days).

    Returns new access_token and refresh_token (refresh token rotation).
    """
)
async def refresh_token(
    request: Request,
    refresh_request: RefreshTokenRequest
) -> LoginResponse:
    """
    Refresh token endpoint - get new access token using refresh token.
    """
    # Apply IP-based rate limiting
    await check_ip_rate_limit(request, limit=20)

    try:
        # Refresh token via Keycloak
        token_response = await keycloak_client.refresh_token(
            refresh_token=refresh_request.refresh_token
        )

        # Decode new access token
        from api.auth import verify_token
        token_data = await verify_token(token_response["access_token"])

        # Build response
        response = LoginResponse(
            access_token=token_response["access_token"],
            refresh_token=token_response.get("refresh_token", refresh_request.refresh_token),
            token_type="bearer",
            expires_in=token_response.get("expires_in", 300),
            tenant_id=token_data.tenant_id,
            user_id=token_data.sub,
            roles=token_data.roles
        )

        logger.info(
            f"Token refreshed: user={token_data.sub}, "
            f"tenant={token_data.tenant_id}"
        )

        return response

    except HTTPException:
        # Re-raise HTTP exceptions (401 for invalid refresh token)
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed. Please login again."
        )


@router.post(
    "/logout",
    response_model=Dict[str, str],
    summary="Logout and revoke tokens",
    description="""
    Logout by revoking the refresh token in Keycloak.

    After logout, both access and refresh tokens will be invalid.
    Client should discard tokens and redirect to login.
    """
)
async def logout(
    request: Request,
    logout_request: LogoutRequest,
    user: TokenData = Depends(get_current_user)
) -> Dict[str, str]:
    """
    Logout endpoint - revoke refresh token.
    """
    try:
        # Revoke refresh token in Keycloak
        success = await keycloak_client.logout(logout_request.refresh_token)

        if success:
            logger.info(
                f"User logged out: user={user.sub}, tenant={user.tenant_id}, "
                f"ip={request.client.host}"
            )
            return {
                "message": "Logged out successfully",
                "status": "success"
            }
        else:
            # Logout failed but don't leak details
            logger.warning(f"Logout failed for user={user.sub}")
            return {
                "message": "Logout completed (token may already be expired)",
                "status": "success"
            }

    except Exception as e:
        logger.error(f"Logout error: {e}")
        # Don't fail logout - worst case token expires naturally
        return {
            "message": "Logout completed",
            "status": "success"
        }


@router.get(
    "/me",
    response_model=Dict[str, Any],
    summary="Get current user info",
    description="""
    Get information about the currently authenticated user.

    Returns user ID, tenant ID, email, roles, and token expiration.
    """
)
async def get_me(
    user: TokenData = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get current user info endpoint.
    """
    return {
        "user_id": user.sub,
        "email": user.email,
        "tenant_id": user.tenant_id,
        "roles": user.roles,
        "is_admin": user.is_admin,
        "token_expires_at": user.exp
    }


@router.get(
    "/verify",
    response_model=Dict[str, str],
    summary="Verify token validity",
    description="""
    Verify that the provided JWT token is valid.

    Returns 200 if token is valid, 401 if invalid or expired.
    """
)
async def verify_token_endpoint(
    user: TokenData = Depends(get_current_user)
) -> Dict[str, str]:
    """
    Verify token endpoint - checks if token is valid.
    """
    return {
        "status": "valid",
        "user_id": user.sub,
        "tenant_id": user.tenant_id
    }
