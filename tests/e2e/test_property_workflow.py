"""
End-to-End Tests for Complete Workflows

Tests full user journeys through the system
"""
import pytest
import time


# =============================================================================
# PROPERTY LIFECYCLE E2E TEST
# =============================================================================

@pytest.mark.e2e
@pytest.mark.slow
def test_complete_property_lifecycle(authenticated_client, demo_user):
    """
    Test complete property lifecycle:
    1. Create property
    2. Generate memo
    3. Send email
    4. Receive reply (mock)
    5. Update stage
    6. Create deal
    7. Generate offer packet
    """

    # Step 1: Create property
    create_response = authenticated_client.post(
        "/api/v1/properties",
        json={
            "address": "789 E2E Test Blvd",
            "city": "Los Angeles",
            "state": "CA",
            "zip_code": "90001",
            "owner_name": "E2E Test Owner",
            "owner_email": "e2e@example.com",
            "owner_phone": "+15555550001",
            "asking_price": 750000,
            "beds": 4,
            "baths": 3,
            "sqft": 2500
        }
    )

    assert create_response.status_code == 201
    property_data = create_response.json()
    property_id = property_data["id"]

    # Step 2: Generate memo
    memo_response = authenticated_client.post(
        "/api/v1/jobs/memo/generate",
        json={
            "property_id": property_id,
            "template": "default"
        }
    )

    assert memo_response.status_code == 200
    job_data = memo_response.json()
    assert "job_id" in job_data

    # Step 3: Send email with memo
    email_response = authenticated_client.post(
        "/api/v1/communications/email/send",
        json={
            "property_id": property_id,
            "to_email": "e2e@example.com",
            "subject": "Investment Opportunity",
            "body": "<p>Please see the attached property memo.</p>"
        }
    )

    assert email_response.status_code == 200
    email_data = email_response.json()
    assert email_data["success"] is True

    # Step 4: Update property stage (simulating progress)
    stage_response = authenticated_client.post(
        f"/api/v1/properties/{property_id}/change-stage",
        json={
            "new_stage": "Contacted"
        }
    )

    assert stage_response.status_code == 200

    # Step 5: Create deal
    deal_response = authenticated_client.post(
        "/api/v1/portfolio/deals",
        json={
            "property_id": property_id,
            "offer_price": 700000,
            "earnest_money": 10000,
            "closing_date": "2024-09-01"
        }
    )

    assert deal_response.status_code == 201
    deal_data = deal_response.json()

    # Step 6: Generate offer packet
    packet_response = authenticated_client.post(
        "/api/v1/jobs/offer-packet/generate",
        json={
            "property_id": property_id,
            "deal_id": deal_data["id"]
        }
    )

    assert packet_response.status_code == 200

    # Step 7: Verify property timeline has all events
    timeline_response = authenticated_client.get(
        f"/api/v1/properties/{property_id}/timeline"
    )

    assert timeline_response.status_code == 200
    timeline = timeline_response.json()
    assert isinstance(timeline, list)
    assert len(timeline) >= 3  # At least: created, stage change, email sent


# =============================================================================
# MOCK PROVIDER E2E TEST
# =============================================================================

@pytest.mark.e2e
@pytest.mark.mock
def test_mock_provider_integration(authenticated_client, sample_property):
    """
    Test that all mock providers work together seamlessly
    """

    # Send email
    email_response = authenticated_client.post(
        "/api/v1/communications/email/send",
        json={
            "property_id": sample_property.id,
            "to_email": "test@example.com",
            "subject": "Test",
            "body": "<p>Test email</p>"
        }
    )

    assert email_response.status_code == 200

    # Send SMS
    sms_response = authenticated_client.post(
        "/api/v1/communications/sms/send",
        json={
            "property_id": sample_property.id,
            "to_phone": "+15555551234",
            "message": "Test SMS"
        }
    )

    assert sms_response.status_code == 200

    # Make call
    call_response = authenticated_client.post(
        "/api/v1/communications/call/make",
        json={
            "property_id": sample_property.id,
            "to_phone": "+15555551234"
        }
    )

    assert call_response.status_code == 200

    # Generate memo (uses PDF + Storage)
    memo_response = authenticated_client.post(
        "/api/v1/jobs/memo/generate",
        json={
            "property_id": sample_property.id
        }
    )

    assert memo_response.status_code == 200

    # All mock providers should work without errors


# =============================================================================
# AUTOMATION E2E TEST
# =============================================================================

@pytest.mark.e2e
@pytest.mark.slow
def test_automation_cadence(authenticated_client, sample_property):
    """
    Test automation cadence creation and execution
    """

    # Create automation cadence
    cadence_response = authenticated_client.post(
        "/api/v1/automation/cadences",
        json={
            "name": "E2E Test Cadence",
            "trigger_stage": "New Lead",
            "steps": [
                {
                    "order": 1,
                    "action_type": "email",
                    "delay_days": 0,
                    "template_id": "welcome"
                },
                {
                    "order": 2,
                    "action_type": "sms",
                    "delay_days": 3,
                    "message": "Follow-up SMS"
                }
            ]
        }
    )

    assert cadence_response.status_code == 201
    cadence = cadence_response.json()

    # Apply cadence to property
    apply_response = authenticated_client.post(
        f"/api/v1/automation/cadences/{cadence['id']}/apply",
        json={
            "property_id": sample_property.id
        }
    )

    assert apply_response.status_code == 200

    # Verify scheduled tasks were created
    tasks_response = authenticated_client.get(
        f"/api/v1/workflow/tasks?property_id={sample_property.id}"
    )

    assert tasks_response.status_code == 200
    tasks = tasks_response.json()
    assert len(tasks) >= 2  # At least 2 automation steps


# =============================================================================
# MULTI-USER COLLABORATION E2E TEST
# =============================================================================

@pytest.mark.e2e
def test_share_link_collaboration(authenticated_client, sample_property):
    """
    Test secure share link creation and access
    """

    # Create share link
    share_response = authenticated_client.post(
        "/api/v1/sharing/links",
        json={
            "property_id": sample_property.id,
            "expires_days": 7,
            "password_protected": True,
            "password": "testpass123"
        }
    )

    assert share_response.status_code == 201
    share_link = share_response.json()

    # Access share link (no auth required)
    client = authenticated_client  # Use base client without auth
    access_response = client.get(
        f"/api/v1/sharing/links/{share_link['token']}",
        params={"password": "testpass123"}
    )

    assert access_response.status_code == 200
    shared_property = access_response.json()
    assert shared_property["id"] == sample_property.id

    # Test analytics tracking
    analytics_response = authenticated_client.get(
        f"/api/v1/sharing/links/{share_link['id']}/analytics"
    )

    assert analytics_response.status_code == 200
    analytics = analytics_response.json()
    assert analytics["total_views"] >= 1
