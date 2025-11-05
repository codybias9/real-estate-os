"""Custom exceptions for Real Estate OS API."""

from typing import Any, Dict, Optional
from fastapi import status


class RealEstateOSException(Exception):
    """Base exception for Real Estate OS API."""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


# Authentication & Authorization Exceptions
class AuthenticationError(RealEstateOSException):
    """Authentication failed."""

    def __init__(self, message: str = "Authentication failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status.HTTP_401_UNAUTHORIZED, details)


class InvalidCredentialsError(AuthenticationError):
    """Invalid email or password."""

    def __init__(self, message: str = "Invalid email or password"):
        super().__init__(message)


class TokenExpiredError(AuthenticationError):
    """Token has expired."""

    def __init__(self, message: str = "Token has expired"):
        super().__init__(message)


class InvalidTokenError(AuthenticationError):
    """Invalid or malformed token."""

    def __init__(self, message: str = "Invalid token"):
        super().__init__(message)


class AccountLockedError(AuthenticationError):
    """Account is locked due to too many failed login attempts."""

    def __init__(self, locked_until: str, message: str = "Account is locked"):
        super().__init__(message, details={"locked_until": locked_until})


class AuthorizationError(RealEstateOSException):
    """User lacks permission for this action."""

    def __init__(self, message: str = "Permission denied", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status.HTTP_403_FORBIDDEN, details)


class InsufficientPermissionsError(AuthorizationError):
    """User does not have required permissions."""

    def __init__(self, required_permission: str):
        super().__init__(
            f"Missing required permission: {required_permission}",
            details={"required_permission": required_permission}
        )


# Resource Exceptions
class ResourceNotFoundError(RealEstateOSException):
    """Requested resource not found."""

    def __init__(self, resource_type: str, resource_id: Any):
        super().__init__(
            f"{resource_type} with id {resource_id} not found",
            status.HTTP_404_NOT_FOUND,
            details={"resource_type": resource_type, "resource_id": str(resource_id)}
        )


class ResourceAlreadyExistsError(RealEstateOSException):
    """Resource already exists."""

    def __init__(self, resource_type: str, identifier: str):
        super().__init__(
            f"{resource_type} with {identifier} already exists",
            status.HTTP_409_CONFLICT,
            details={"resource_type": resource_type, "identifier": identifier}
        )


class ResourceDeletionError(RealEstateOSException):
    """Resource cannot be deleted."""

    def __init__(self, resource_type: str, reason: str):
        super().__init__(
            f"Cannot delete {resource_type}: {reason}",
            status.HTTP_400_BAD_REQUEST,
            details={"resource_type": resource_type, "reason": reason}
        )


# Validation Exceptions
class ValidationError(RealEstateOSException):
    """Request validation failed."""

    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        details = details or {}
        if field:
            details["field"] = field
        super().__init__(message, status.HTTP_422_UNPROCESSABLE_ENTITY, details)


class InvalidInputError(ValidationError):
    """Invalid input provided."""

    def __init__(self, field: str, message: str):
        super().__init__(f"Invalid {field}: {message}", field=field)


class MissingRequiredFieldError(ValidationError):
    """Required field is missing."""

    def __init__(self, field: str):
        super().__init__(f"Missing required field: {field}", field=field)


# Business Logic Exceptions
class BusinessLogicError(RealEstateOSException):
    """Business logic constraint violated."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status.HTTP_400_BAD_REQUEST, details)


class PropertyNotAvailableError(BusinessLogicError):
    """Property is not available for the requested action."""

    def __init__(self, property_id: int, current_status: str):
        super().__init__(
            f"Property {property_id} is not available (current status: {current_status})",
            details={"property_id": property_id, "current_status": current_status}
        )


class LeadAlreadyConvertedError(BusinessLogicError):
    """Lead has already been converted to a deal."""

    def __init__(self, lead_id: int):
        super().__init__(
            f"Lead {lead_id} has already been converted",
            details={"lead_id": lead_id}
        )


class CampaignAlreadySentError(BusinessLogicError):
    """Campaign has already been sent."""

    def __init__(self, campaign_id: int):
        super().__init__(
            f"Campaign {campaign_id} has already been sent",
            details={"campaign_id": campaign_id}
        )


class DealClosedError(BusinessLogicError):
    """Deal is closed and cannot be modified."""

    def __init__(self, deal_id: int):
        super().__init__(
            f"Deal {deal_id} is closed and cannot be modified",
            details={"deal_id": deal_id}
        )


# Multi-tenancy Exceptions
class OrganizationMismatchError(AuthorizationError):
    """Resource belongs to a different organization."""

    def __init__(self, resource_type: str):
        super().__init__(
            f"Access denied: {resource_type} belongs to a different organization",
            details={"resource_type": resource_type}
        )


class OrganizationNotActiveError(RealEstateOSException):
    """Organization is not active."""

    def __init__(self, organization_id: int):
        super().__init__(
            f"Organization {organization_id} is not active",
            status.HTTP_403_FORBIDDEN,
            details={"organization_id": organization_id}
        )


# Rate Limiting Exceptions
class RateLimitExceededError(RealEstateOSException):
    """Rate limit exceeded."""

    def __init__(self, limit: int, window: str, retry_after: int):
        super().__init__(
            f"Rate limit exceeded: {limit} requests per {window}",
            status.HTTP_429_TOO_MANY_REQUESTS,
            details={"limit": limit, "window": window, "retry_after": retry_after}
        )


# External Service Exceptions
class ExternalServiceError(RealEstateOSException):
    """External service error."""

    def __init__(self, service_name: str, message: str):
        super().__init__(
            f"{service_name} error: {message}",
            status.HTTP_503_SERVICE_UNAVAILABLE,
            details={"service": service_name}
        )


class EmailServiceError(ExternalServiceError):
    """Email service error."""

    def __init__(self, message: str):
        super().__init__("Email Service", message)


class SMSServiceError(ExternalServiceError):
    """SMS service error."""

    def __init__(self, message: str):
        super().__init__("SMS Service", message)


class StorageServiceError(ExternalServiceError):
    """Storage service error."""

    def __init__(self, message: str):
        super().__init__("Storage Service", message)


# Database Exceptions
class DatabaseError(RealEstateOSException):
    """Database operation failed."""

    def __init__(self, message: str, operation: Optional[str] = None):
        details = {"operation": operation} if operation else {}
        super().__init__(message, status.HTTP_500_INTERNAL_SERVER_ERROR, details)


class DatabaseConnectionError(DatabaseError):
    """Cannot connect to database."""

    def __init__(self):
        super().__init__("Database connection failed", "connect")


class DatabaseTransactionError(DatabaseError):
    """Database transaction failed."""

    def __init__(self, message: str):
        super().__init__(message, "transaction")


# File Upload Exceptions
class FileUploadError(RealEstateOSException):
    """File upload failed."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status.HTTP_400_BAD_REQUEST, details)


class FileTooLargeError(FileUploadError):
    """Uploaded file exceeds size limit."""

    def __init__(self, max_size_mb: int):
        super().__init__(
            f"File size exceeds maximum allowed size of {max_size_mb}MB",
            details={"max_size_mb": max_size_mb}
        )


class InvalidFileTypeError(FileUploadError):
    """Invalid file type."""

    def __init__(self, allowed_types: list):
        super().__init__(
            f"Invalid file type. Allowed types: {', '.join(allowed_types)}",
            details={"allowed_types": allowed_types}
        )


# Configuration Exceptions
class ConfigurationError(RealEstateOSException):
    """Configuration error."""

    def __init__(self, message: str, config_key: Optional[str] = None):
        details = {"config_key": config_key} if config_key else {}
        super().__init__(message, status.HTTP_500_INTERNAL_SERVER_ERROR, details)


class MissingConfigurationError(ConfigurationError):
    """Required configuration is missing."""

    def __init__(self, config_key: str):
        super().__init__(f"Missing required configuration: {config_key}", config_key)
