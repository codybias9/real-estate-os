"""
Tests for structured logging
"""

import pytest
import logging
from observability.logging import configure_logging, get_logger, set_request_context


class TestLogging:
    """Tests for logging configuration"""

    def test_configure_logging_json(self):
        """Test configuring JSON logging"""
        configure_logging(level="INFO", json_logs=True)
        logger = get_logger("test")
        assert logger is not None

    def test_configure_logging_console(self):
        """Test configuring console logging"""
        configure_logging(level="DEBUG", json_logs=False)
        logger = get_logger("test")
        assert logger is not None

    def test_get_logger(self):
        """Test getting a logger instance"""
        logger = get_logger("test_module")
        assert logger is not None

    def test_logger_with_context(self):
        """Test logger with request context"""
        set_request_context(
            request_id="req-123",
            user_id="user-456",
            tenant_id="tenant-789",
        )
        logger = get_logger("test")
        # Logger should include context variables
        assert logger is not None

    def test_logger_methods(self):
        """Test logger has all standard methods"""
        logger = get_logger("test")
        assert hasattr(logger, "debug")
        assert hasattr(logger, "info")
        assert hasattr(logger, "warning")
        assert hasattr(logger, "error")
        assert hasattr(logger, "critical")

    def test_logger_with_extra_fields(self):
        """Test logging with extra fields"""
        logger = get_logger("test")
        # Should not raise exception
        logger.info("test_event", property_id="123", action="created")
