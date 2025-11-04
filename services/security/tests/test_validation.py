"""
Tests for input validation utilities
"""

import pytest
from security.validation import (
    sanitize_input,
    validate_uuid,
    validate_email,
    validate_apn,
    validate_phone,
    escape_html,
    validate_json_keys,
)


class TestSanitizeInput:
    """Tests for sanitize_input function"""

    def test_sanitize_normal_string(self):
        """Test sanitizing normal string"""
        result = sanitize_input("Hello World")
        assert result == "Hello World"

    def test_sanitize_null_bytes(self):
        """Test removing null bytes"""
        result = sanitize_input("Hello\x00World")
        assert result == "HelloWorld"

    def test_sanitize_whitespace(self):
        """Test trimming whitespace"""
        result = sanitize_input("  Hello World  ")
        assert result == "Hello World"

    def test_sanitize_max_length(self):
        """Test enforcing max length"""
        long_string = "a" * 1500
        result = sanitize_input(long_string, max_length=100)
        assert len(result) == 100

    def test_sanitize_control_characters(self):
        """Test removing control characters"""
        result = sanitize_input("Hello\x01\x02World")
        assert result == "HelloWorld"

    def test_sanitize_preserves_allowed_chars(self):
        """Test that tabs, newlines, carriage returns are preserved"""
        result = sanitize_input("Hello\tWorld\nTest\r")
        assert "\t" in result
        assert "\n" in result
        assert "\r" in result

    def test_sanitize_non_string_input(self):
        """Test sanitizing non-string input"""
        result = sanitize_input(123)
        assert result == "123"


class TestValidateUUID:
    """Tests for validate_uuid function"""

    def test_valid_uuid(self):
        """Test validating valid UUID"""
        assert validate_uuid("550e8400-e29b-41d4-a716-446655440000") is True

    def test_valid_uuid_uppercase(self):
        """Test validating uppercase UUID"""
        assert validate_uuid("550E8400-E29B-41D4-A716-446655440000") is True

    def test_invalid_uuid_format(self):
        """Test invalidating malformed UUID"""
        assert validate_uuid("not-a-uuid") is False

    def test_invalid_uuid_empty(self):
        """Test invalidating empty string"""
        assert validate_uuid("") is False

    def test_invalid_uuid_none(self):
        """Test invalidating None"""
        assert validate_uuid(None) is False


class TestValidateEmail:
    """Tests for validate_email function"""

    def test_valid_email(self):
        """Test validating valid email"""
        assert validate_email("test@example.com") is True

    def test_valid_email_subdomain(self):
        """Test validating email with subdomain"""
        assert validate_email("test@mail.example.com") is True

    def test_valid_email_plus(self):
        """Test validating email with plus sign"""
        assert validate_email("test+tag@example.com") is True

    def test_invalid_email_no_at(self):
        """Test invalidating email without @"""
        assert validate_email("testexample.com") is False

    def test_invalid_email_no_domain(self):
        """Test invalidating email without domain"""
        assert validate_email("test@") is False

    def test_invalid_email_no_tld(self):
        """Test invalidating email without TLD"""
        assert validate_email("test@example") is False

    def test_invalid_email_empty(self):
        """Test invalidating empty string"""
        assert validate_email("") is False

    def test_invalid_email_none(self):
        """Test invalidating None"""
        assert validate_email(None) is False


class TestValidateAPN:
    """Tests for validate_apn function"""

    def test_valid_apn_with_hyphens(self):
        """Test validating APN with hyphens"""
        assert validate_apn("123-456-789") is True

    def test_valid_apn_without_hyphens(self):
        """Test validating APN without hyphens"""
        assert validate_apn("12345678") is True

    def test_valid_apn_long(self):
        """Test validating longer APN"""
        assert validate_apn("123456789012") is True

    def test_invalid_apn_too_short(self):
        """Test invalidating too short APN"""
        assert validate_apn("1234567") is False

    def test_invalid_apn_too_long(self):
        """Test invalidating too long APN"""
        assert validate_apn("1234567890123") is False

    def test_invalid_apn_non_numeric(self):
        """Test invalidating non-numeric APN"""
        assert validate_apn("ABC-DEF-GHI") is False

    def test_invalid_apn_empty(self):
        """Test invalidating empty string"""
        assert validate_apn("") is False


class TestValidatePhone:
    """Tests for validate_phone function"""

    def test_valid_phone_with_parens(self):
        """Test validating phone with parentheses"""
        assert validate_phone("(555) 123-4567") is True

    def test_valid_phone_with_hyphens(self):
        """Test validating phone with hyphens"""
        assert validate_phone("555-123-4567") is True

    def test_valid_phone_no_separators(self):
        """Test validating phone without separators"""
        assert validate_phone("5551234567") is True

    def test_valid_phone_with_country_code(self):
        """Test validating phone with country code"""
        assert validate_phone("+1 555 123 4567") is True

    def test_invalid_phone_too_short(self):
        """Test invalidating too short phone"""
        assert validate_phone("123456") is False

    def test_invalid_phone_too_long(self):
        """Test invalidating too long phone"""
        assert validate_phone("123456789012") is False

    def test_invalid_phone_non_numeric(self):
        """Test invalidating non-numeric phone"""
        assert validate_phone("ABC-DEF-GHIJ") is False


class TestEscapeHTML:
    """Tests for escape_html function"""

    def test_escape_html_basic(self):
        """Test escaping basic HTML"""
        result = escape_html("<script>alert('xss')</script>")
        assert result == "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;&#x2F;script&gt;"

    def test_escape_html_ampersand(self):
        """Test escaping ampersand"""
        result = escape_html("Tom & Jerry")
        assert result == "Tom &amp; Jerry"

    def test_escape_html_quotes(self):
        """Test escaping quotes"""
        result = escape_html('Say "Hello"')
        assert result == "Say &quot;Hello&quot;"

    def test_escape_html_no_special_chars(self):
        """Test string without special characters"""
        result = escape_html("Hello World")
        assert result == "Hello World"


class TestValidateJSONKeys:
    """Tests for validate_json_keys function"""

    def test_validate_json_keys_valid(self):
        """Test validating JSON with allowed keys"""
        data = {"name": "John", "email": "john@example.com"}
        allowed = {"name", "email", "role"}
        assert validate_json_keys(data, allowed) is True

    def test_validate_json_keys_invalid(self):
        """Test invalidating JSON with extra keys"""
        data = {"name": "John", "evil": "payload"}
        allowed = {"name", "email"}
        assert validate_json_keys(data, allowed) is False

    def test_validate_json_keys_empty(self):
        """Test validating empty JSON"""
        data = {}
        allowed = {"name", "email"}
        assert validate_json_keys(data, allowed) is True

    def test_validate_json_keys_non_dict(self):
        """Test invalidating non-dictionary input"""
        data = "not a dict"
        allowed = {"name"}
        assert validate_json_keys(data, allowed) is False
