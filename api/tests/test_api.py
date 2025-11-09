"""
Tests for API endpoints: health, ping, and metrics
"""

import os
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from api.main import app

client = TestClient(app)


class TestHealthEndpoints:
    """Test health check endpoints"""

    def test_root_redirects_to_docs(self):
        """Root endpoint should redirect to /docs"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/docs"

    def test_healthz_returns_ok(self):
        """GET /v1/healthz should return 200 with status ok"""
        response = client.get("/v1/healthz")
        assert response.status_code == 200
        data = response.json()
        assert data == {"status": "ok"}

    def test_healthz_response_schema(self):
        """GET /v1/healthz should match response schema"""
        response = client.get("/v1/healthz")
        data = response.json()
        assert "status" in data
        assert isinstance(data["status"], str)

    def test_ping_without_db_dsn(self):
        """GET /v1/ping should return 500 if DB_DSN not set"""
        with patch.dict(os.environ, {}, clear=True):
            response = client.get("/v1/ping")
            assert response.status_code == 500
            data = response.json()
            assert "DB_DSN" in data["detail"]

    @pytest.mark.requires_db
    def test_ping_with_mocked_db(self):
        """GET /v1/ping should return 200 with ping_count when DB works"""
        # Mock the database engine and connection
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = 42

        mock_conn.execute.return_value = mock_result
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_engine.begin.return_value = mock_conn

        test_dsn = "postgresql://test:test@localhost/test"

        with patch.dict(os.environ, {"DB_DSN": test_dsn}):
            with patch("api.v1.health.create_engine", return_value=mock_engine):
                response = client.get("/v1/ping")
                assert response.status_code == 200
                data = response.json()
                assert "ping_count" in data
                assert isinstance(data["ping_count"], int)
                assert data["ping_count"] == 42

    @pytest.mark.requires_db
    def test_ping_creates_table_and_inserts(self):
        """GET /v1/ping should create table if needed and insert a record"""
        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = 1

        execute_calls = []

        def track_execute(stmt):
            execute_calls.append(str(stmt))
            return mock_result

        mock_conn.execute.side_effect = track_execute
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_engine.begin.return_value = mock_conn

        test_dsn = "postgresql://test:test@localhost/test"

        with patch.dict(os.environ, {"DB_DSN": test_dsn}):
            with patch("api.v1.health.create_engine", return_value=mock_engine):
                response = client.get("/v1/ping")
                assert response.status_code == 200

                # Verify CREATE TABLE, INSERT, and SELECT were called
                assert len(execute_calls) == 3
                assert "CREATE TABLE" in execute_calls[0]
                assert "INSERT" in execute_calls[1]
                assert "SELECT" in execute_calls[2]

    def test_ping_with_invalid_db_dsn(self):
        """GET /v1/ping should return 500 if DB connection fails"""
        invalid_dsn = "postgresql://invalid:invalid@invalid:9999/invalid"

        with patch.dict(os.environ, {"DB_DSN": invalid_dsn}):
            response = client.get("/v1/ping")
            assert response.status_code == 500
            data = response.json()
            assert "connection failed" in data["detail"].lower()


class TestMetricsEndpoint:
    """Test Prometheus metrics endpoint"""

    def test_metrics_endpoint_exists(self):
        """GET /metrics should return 200"""
        response = client.get("/metrics")
        assert response.status_code == 200

    def test_metrics_content_type(self):
        """GET /metrics should return Prometheus content type"""
        response = client.get("/metrics")
        # Prometheus uses text/plain with version parameter
        assert "text/plain" in response.headers["content-type"]

    def test_metrics_contains_python_info(self):
        """GET /metrics should include Python runtime metrics"""
        response = client.get("/metrics")
        content = response.text
        # Prometheus client exports Python runtime metrics by default
        assert "python_info" in content or "process_" in content

    def test_metrics_format(self):
        """GET /metrics should return valid Prometheus format"""
        response = client.get("/metrics")
        content = response.text
        # Basic Prometheus format validation
        # Should contain metric names and values
        assert len(content) > 0
        # Should not be JSON
        assert not content.startswith("{")


class TestOpenAPIDocumentation:
    """Test OpenAPI documentation and metadata"""

    def test_openapi_schema_accessible(self):
        """GET /openapi.json should return OpenAPI schema"""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert "openapi" in schema
        assert "info" in schema
        assert "paths" in schema

    def test_api_metadata(self):
        """OpenAPI schema should include correct metadata"""
        response = client.get("/openapi.json")
        schema = response.json()
        assert schema["info"]["title"] == "Real Estate OS API"
        assert schema["info"]["version"] == "0.1.0"
        assert "description" in schema["info"]

    def test_health_tag_in_openapi(self):
        """OpenAPI schema should include Health tag"""
        response = client.get("/openapi.json")
        schema = response.json()
        tags = [tag["name"] for tag in schema.get("tags", [])]
        assert "Health" in tags

    def test_v1_endpoints_in_openapi(self):
        """OpenAPI schema should include v1 endpoints"""
        response = client.get("/openapi.json")
        schema = response.json()
        paths = schema["paths"]
        assert "/v1/healthz" in paths
        assert "/v1/ping" in paths

    def test_healthz_endpoint_documentation(self):
        """GET /v1/healthz should have proper OpenAPI documentation"""
        response = client.get("/openapi.json")
        schema = response.json()
        healthz_endpoint = schema["paths"]["/v1/healthz"]["get"]
        assert "summary" in healthz_endpoint
        assert "description" in healthz_endpoint
        assert healthz_endpoint["tags"] == ["Health"]

    def test_ping_endpoint_documentation(self):
        """GET /v1/ping should have proper OpenAPI documentation"""
        response = client.get("/openapi.json")
        schema = response.json()
        ping_endpoint = schema["paths"]["/v1/ping"]["get"]
        assert "summary" in ping_endpoint
        assert "description" in ping_endpoint
        assert ping_endpoint["tags"] == ["Health"]


class TestAPIIntegration:
    """Integration tests for API behavior"""

    def test_docs_page_accessible(self):
        """GET /docs should return 200 (Swagger UI)"""
        response = client.get("/docs")
        assert response.status_code == 200
        assert "swagger" in response.text.lower() or "openapi" in response.text.lower()

    def test_redoc_page_accessible(self):
        """GET /redoc should return 200 (ReDoc UI)"""
        response = client.get("/redoc")
        assert response.status_code == 200

    def test_cors_headers_not_present_by_default(self):
        """CORS should not be enabled by default"""
        response = client.get("/v1/healthz")
        assert "access-control-allow-origin" not in response.headers
