"""
Custom exceptions for the application
"""
from fastapi import HTTPException, status


class AuthenticationError(HTTPException):
    """Raised when authentication fails"""
    def __init__(self, detail: str = "Could not validate credentials"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class PermissionDeniedError(HTTPException):
    """Raised when user doesn't have required permissions"""
    def __init__(self, detail: str = "Permission denied"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )


class ResourceNotFoundError(HTTPException):
    """Raised when a requested resource is not found"""
    def __init__(self, resource: str, resource_id: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{resource} with id '{resource_id}' not found",
        )


class ValidationError(HTTPException):
    """Raised when validation fails"""
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
        )


class DuplicateResourceError(HTTPException):
    """Raised when attempting to create a duplicate resource"""
    def __init__(self, resource: str, field: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{resource} with this {field} already exists",
        )


class AccountLockedError(HTTPException):
    """Raised when account is locked due to too many failed login attempts"""
    def __init__(self, locked_until: str):
        super().__init__(
            status_code=status.HTTP_423_LOCKED,
            detail=f"Account is locked due to too many failed login attempts. Try again after {locked_until}",
        )


class RateLimitExceededError(HTTPException):
    """Raised when rate limit is exceeded"""
    def __init__(self, retry_after: int):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(retry_after)},
        )
