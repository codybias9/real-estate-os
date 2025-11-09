"""
Tests for password hashing and verification
"""

import pytest
from auth.password import PasswordHandler


class TestPasswordHandler:
    """Tests for PasswordHandler class"""

    @pytest.fixture
    def handler(self):
        """Create password handler"""
        return PasswordHandler()

    def test_hash_password(self, handler):
        """Test password hashing"""
        password = "my-secure-password123"
        hashed = handler.hash_password(password)

        assert hashed is not None
        assert isinstance(hashed, str)
        assert hashed != password  # Should not be plain text
        assert hashed.startswith("$2b$")  # bcrypt prefix

    def test_verify_correct_password(self, handler):
        """Test verifying correct password"""
        password = "my-secure-password123"
        hashed = handler.hash_password(password)

        assert handler.verify_password(password, hashed) is True

    def test_verify_incorrect_password(self, handler):
        """Test verifying incorrect password"""
        password = "my-secure-password123"
        wrong_password = "wrong-password"
        hashed = handler.hash_password(password)

        assert handler.verify_password(wrong_password, hashed) is False

    def test_different_hashes_for_same_password(self, handler):
        """Test that same password produces different hashes (salt)"""
        password = "my-secure-password123"
        hash1 = handler.hash_password(password)
        hash2 = handler.hash_password(password)

        # Should be different due to random salt
        assert hash1 != hash2

        # But both should verify correctly
        assert handler.verify_password(password, hash1) is True
        assert handler.verify_password(password, hash2) is True

    def test_hash_empty_string(self, handler):
        """Test hashing empty string"""
        hashed = handler.hash_password("")
        assert hashed is not None
        assert handler.verify_password("", hashed) is True

    def test_hash_unicode_password(self, handler):
        """Test hashing password with unicode characters"""
        password = "пароль-密码-🔐"
        hashed = handler.hash_password(password)

        assert handler.verify_password(password, hashed) is True

    def test_hash_long_password(self, handler):
        """Test hashing very long password"""
        password = "a" * 1000
        hashed = handler.hash_password(password)

        assert handler.verify_password(password, hashed) is True
