"""
Tests for Prometheus metrics
"""

import pytest
from observability.metrics import (
    request_count,
    request_duration,
    error_count,
    record_request,
    record_error,
    record_property_operation,
    record_score_operation,
    get_metrics,
)


class TestMetrics:
    """Tests for Prometheus metrics"""

    def test_request_count_metric(self):
        """Test request count metric"""
        initial = request_count.labels(
            method="GET",
            endpoint="/api/properties",
            status_code=200,
        )._value.get()

        request_count.labels(
            method="GET",
            endpoint="/api/properties",
            status_code=200,
        ).inc()

        final = request_count.labels(
            method="GET",
            endpoint="/api/properties",
            status_code=200,
        )._value.get()

        assert final == initial + 1

    def test_request_duration_metric(self):
        """Test request duration metric"""
        request_duration.labels(
            method="GET",
            endpoint="/api/properties",
        ).observe(0.5)

        # Metric should be recorded
        assert request_duration._metrics

    def test_error_count_metric(self):
        """Test error count metric"""
        error_count.labels(
            method="POST",
            endpoint="/api/properties",
            error_type="ValidationError",
        ).inc()

        # Metric should be recorded
        assert error_count._metrics

    def test_record_request(self):
        """Test recording request metrics"""
        record_request(
            method="POST",
            endpoint="/api/properties",
            status_code=201,
            duration=0.3,
        )
        # Should not raise exception

    def test_record_error(self):
        """Test recording error metrics"""
        record_error(
            method="GET",
            endpoint="/api/properties/123",
            error_type="NotFoundError",
        )
        # Should not raise exception

    def test_record_property_operation(self):
        """Test recording property operation"""
        record_property_operation(
            operation="create",
            status="success",
        )
        # Should not raise exception

    def test_record_score_operation(self):
        """Test recording score operation"""
        record_score_operation(status="success")
        # Should not raise exception

    def test_get_metrics(self):
        """Test getting Prometheus metrics"""
        metrics_output = get_metrics()
        assert metrics_output is not None
        assert isinstance(metrics_output, bytes)
        # Should contain metric names
        assert b"http_requests_total" in metrics_output
