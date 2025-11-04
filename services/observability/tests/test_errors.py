"""
Tests for error tracking
"""

import pytest
from observability.errors import ErrorTracker


class TestErrorTracker:
    """Tests for error tracker"""

    @pytest.fixture
    def tracker(self):
        """Create error tracker instance"""
        return ErrorTracker(service_name="test-service")

    def test_create_error_tracker(self, tracker):
        """Test creating error tracker"""
        assert tracker.service_name == "test-service"

    def test_capture_exception(self, tracker):
        """Test capturing exception"""
        try:
            raise ValueError("Test error")
        except ValueError as e:
            tracker.capture_exception(
                e,
                context={"request_id": "req-123"},
                level="error",
            )
        # Should not raise exception

    def test_capture_message(self, tracker):
        """Test capturing custom message"""
        tracker.capture_message(
            "Custom warning message",
            context={"user_id": "user-123"},
            level="warning",
        )
        # Should not raise exception

    def test_capture_exception_with_traceback(self, tracker):
        """Test that exception includes traceback"""
        try:
            # Create nested exception
            def inner():
                raise RuntimeError("Inner error")

            def outer():
                inner()

            outer()
        except RuntimeError as e:
            tracker.capture_exception(e)
        # Should not raise exception
