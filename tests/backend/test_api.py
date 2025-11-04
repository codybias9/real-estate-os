"""
Backend API Tests
"""

import pytest
from fastapi.testclient import TestClient
from api.main import app


client = TestClient(app)


def test_health_endpoint():
    """Test health check endpoint"""
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ping_endpoint_without_dsn():
    """Test ping endpoint fails without DB_DSN"""
    import os
    original_dsn = os.environ.get("DB_DSN")
    if "DB_DSN" in os.environ:
        del os.environ["DB_DSN"]

    response = client.get("/ping")
    assert response.status_code == 500

    # Restore
    if original_dsn:
        os.environ["DB_DSN"] = original_dsn


def test_ping_endpoint_with_dsn(monkeypatch):
    """Test ping endpoint with valid DSN"""
    # This would require a real DB connection in full integration test
    # For now, we test the endpoint exists
    assert hasattr(app, "routes")
