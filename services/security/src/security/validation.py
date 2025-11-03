"""
Input validation and sanitization utilities
"""

import re
from typing import Any
from uuid import UUID


def sanitize_input(value: str, max_length: int = 1000) -> str:
    """
    Sanitize string input to prevent injection attacks.

    - Removes null bytes
    - Trims whitespace
    - Enforces max length
    - Removes control characters

    Args:
        value: Input string to sanitize
        max_length: Maximum allowed length

    Returns:
        Sanitized string

    Example:
        sanitized = sanitize_input(user_input, max_length=100)
    """
    if not isinstance(value, str):
        return str(value)

    # Remove null bytes
    value = value.replace("\x00", "")

    # Remove other control characters (except tab, newline, carriage return)
    value = "".join(
        char for char in value if char in "\t\n\r" or not char.isascii() or ord(char) >= 32
    )

    # Trim whitespace
    value = value.strip()

    # Enforce max length
    if len(value) > max_length:
        value = value[:max_length]

    return value


def validate_uuid(value: str) -> bool:
    """
    Validate UUID string format.

    Args:
        value: UUID string to validate

    Returns:
        True if valid UUID, False otherwise

    Example:
        if not validate_uuid(user_id):
            raise ValueError("Invalid user ID")
    """
    try:
        UUID(value)
        return True
    except (ValueError, AttributeError, TypeError):
        return False


def validate_email(email: str) -> bool:
    """
    Validate email address format.

    Uses regex for basic validation (not RFC-compliant).

    Args:
        email: Email address to validate

    Returns:
        True if valid email format, False otherwise

    Example:
        if not validate_email(user_email):
            raise ValueError("Invalid email address")
    """
    if not email or not isinstance(email, str):
        return False

    # Basic email regex (not RFC-compliant but catches most cases)
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern, email) is not None


def validate_apn(apn: str) -> bool:
    """
    Validate Assessor Parcel Number (APN) format.

    Accepts formats like:
    - 123-456-789
    - 123-45-678
    - 12345678

    Args:
        apn: APN string to validate

    Returns:
        True if valid APN format, False otherwise
    """
    if not apn or not isinstance(apn, str):
        return False

    # Remove hyphens for validation
    apn_clean = apn.replace("-", "")

    # Must be 8-12 digits
    return apn_clean.isdigit() and 8 <= len(apn_clean) <= 12


def validate_phone(phone: str) -> bool:
    """
    Validate phone number format.

    Accepts US phone numbers in various formats:
    - (555) 123-4567
    - 555-123-4567
    - 5551234567
    - +1 555 123 4567

    Args:
        phone: Phone number to validate

    Returns:
        True if valid phone format, False otherwise
    """
    if not phone or not isinstance(phone, str):
        return False

    # Remove common separators
    phone_clean = re.sub(r"[\s\-\(\)\+]", "", phone)

    # Must be 10-11 digits (11 if includes country code)
    if not phone_clean.isdigit():
        return False

    return len(phone_clean) in [10, 11]


def escape_html(value: str) -> str:
    """
    Escape HTML special characters to prevent XSS.

    Args:
        value: String to escape

    Returns:
        HTML-escaped string

    Example:
        safe_value = escape_html(user_input)
    """
    if not isinstance(value, str):
        return str(value)

    replacements = {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#x27;",
        "/": "&#x2F;",
    }

    for char, replacement in replacements.items():
        value = value.replace(char, replacement)

    return value


def validate_json_keys(data: dict[str, Any], allowed_keys: set[str]) -> bool:
    """
    Validate that JSON object only contains allowed keys.

    Args:
        data: Dictionary to validate
        allowed_keys: Set of allowed key names

    Returns:
        True if all keys are allowed, False otherwise

    Example:
        allowed = {"name", "email", "role"}
        if not validate_json_keys(request_data, allowed):
            raise ValueError("Invalid keys in request")
    """
    if not isinstance(data, dict):
        return False

    return set(data.keys()).issubset(allowed_keys)
