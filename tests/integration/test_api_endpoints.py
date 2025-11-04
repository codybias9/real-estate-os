"""
Integration Tests for API Endpoints

Tests API endpoints with database and mock providers
"""
import pytest


# =============================================================================
# HEALTH & STATUS TESTS
# =============================================================================

@pytest.mark.integration
def test_health_endpoint(client):
    """Test health check endpoint"""
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.integration
def test_status_endpoint(client):
    """Test API status endpoint"""
    response = client.get("/api/v1/status")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "operational"
    assert "features" in data


# =============================================================================
# AUTH TESTS
# =============================================================================

@pytest.mark.integration
def test_login_success(client, demo_user):
    """Test successful login"""
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "test@example.com",
            "password": "password123"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "user" in data
    assert data["user"]["email"] == "test@example.com"


@pytest.mark.integration
def test_login_invalid_credentials(client):
    """Test login with invalid credentials"""
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "nonexistent@example.com",
            "password": "wrongpassword"
        }
    )

    assert response.status_code == 401


# =============================================================================
# PROPERTY TESTS
# =============================================================================

@pytest.mark.integration
def test_list_properties(authenticated_client, sample_property):
    """Test listing properties"""
    response = authenticated_client.get("/api/v1/properties")
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert data[0]["id"] == sample_property.id


@pytest.mark.integration
def test_get_property(authenticated_client, sample_property):
    """Test getting single property"""
    response = authenticated_client.get(f"/api/v1/properties/{sample_property.id}")
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == sample_property.id
    assert data["address"] == sample_property.address


@pytest.mark.integration
def test_create_property(authenticated_client):
    """Test creating a new property"""
    response = authenticated_client.post(
        "/api/v1/properties",
        json={
            "address": "456 New St",
            "city": "Test City",
            "state": "CA",
            "zip_code": "90210",
            "owner_name": "Jane Doe",
            "asking_price": 600000
        }
    )

    assert response.status_code == 201
    data = response.json()
    assert data["address"] == "456 New St"
    assert data["asking_price"] == 600000


# =============================================================================
# COMMUNICATION TESTS
# =============================================================================

@pytest.mark.integration
@pytest.mark.mock
def test_send_email_mock(authenticated_client, sample_property):
    """Test sending email using mock provider"""
    response = authenticated_client.post(
        "/api/v1/communications/email/send",
        json={
            "property_id": sample_property.id,
            "to_email": sample_property.owner_email,
            "subject": "Test Email",
            "body": "<p>Test content</p>"
        }
    )

    # Should succeed with mock provider
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "message_id" in data


@pytest.mark.integration
@pytest.mark.mock
def test_send_sms_mock(authenticated_client, sample_property):
    """Test sending SMS using mock provider"""
    response = authenticated_client.post(
        "/api/v1/communications/sms/send",
        json={
            "property_id": sample_property.id,
            "to_phone": sample_property.owner_phone,
            "message": "Test SMS message"
        }
    )

    # Should succeed with mock provider
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "message_sid" in data


# =============================================================================
# BACKGROUND JOBS TESTS
# =============================================================================

@pytest.mark.integration
@pytest.mark.slow
def test_queue_memo_generation(authenticated_client, sample_property):
    """Test queueing memo generation job"""
    response = authenticated_client.post(
        "/api/v1/jobs/memo/generate",
        json={
            "property_id": sample_property.id,
            "template": "default"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert data["status"] in ("pending", "queued", "processing")


# =============================================================================
# WORKFLOW TESTS
# =============================================================================

@pytest.mark.integration
def test_next_best_actions(authenticated_client, sample_property):
    """Test next best actions generation"""
    response = authenticated_client.post(
        "/api/v1/workflow/next-best-actions/generate",
        json={
            "property_id": sample_property.id
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # Should have at least one recommendation
    if len(data) > 0:
        assert "action_type" in data[0]
        assert "priority" in data[0]


# =============================================================================
# QUICK WINS TESTS
# =============================================================================

@pytest.mark.integration
@pytest.mark.mock
def test_generate_and_send(authenticated_client, sample_property):
    """Test generate & send combo feature"""
    response = authenticated_client.post(
        "/api/v1/quick-wins/generate-and-send",
        json={
            "property_id": sample_property.id,
            "recipient_email": sample_property.owner_email
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "memo_generated" in data
    assert "email_sent" in data
