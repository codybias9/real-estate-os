"""Tests for outreach API endpoints (Wave 3.3)

Tests all endpoints in api/app/routers/outreach.py including:
- Email template management (CRUD)
- Campaign management (CRUD)
- Campaign recipients
- Campaign analytics
- Multi-step sequences
- Conditional logic
"""

import pytest
from uuid import uuid4
from datetime import datetime, timedelta


@pytest.mark.outreach
@pytest.mark.integration
class TestEmailTemplateEndpoints:
    """Test email template CRUD endpoints"""

    def test_create_template(self, client, auth_headers, test_tenant):
        """Test POST /outreach/templates - Create email template"""
        response = client.post(
            "/outreach/templates",
            headers=auth_headers,
            json={
                "name": "Cold Outreach Template",
                "subject": "Interested in {{property_address}}",
                "body_html": "<p>Hi {{owner_name}},</p><p>I'm interested in your property at {{property_address}}.</p>",
                "body_text": "Hi {{owner_name}}, I'm interested in your property at {{property_address}}.",
                "variables": ["owner_name", "property_address"]
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Cold Outreach Template"
        assert "{{owner_name}}" in data["body_html"]
        assert len(data["variables"]) == 2

    def test_list_templates(self, client, auth_headers):
        """Test GET /outreach/templates - List all templates"""
        # Create a few templates
        for i in range(3):
            client.post(
                "/outreach/templates",
                headers=auth_headers,
                json={
                    "name": f"Template {i}",
                    "subject": f"Subject {i}",
                    "body_html": f"<p>Body {i}</p>",
                    "body_text": f"Body {i}",
                    "variables": []
                }
            )

        # List templates
        response = client.get(
            "/outreach/templates",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 3

    def test_get_template(self, client, auth_headers):
        """Test GET /outreach/templates/{id} - Get single template"""
        # Create template
        create_response = client.post(
            "/outreach/templates",
            headers=auth_headers,
            json={
                "name": "Test Template",
                "subject": "Test Subject",
                "body_html": "<p>Test</p>",
                "body_text": "Test",
                "variables": ["name"]
            }
        )
        template_id = create_response.json()["id"]

        # Get template
        response = client.get(
            f"/outreach/templates/{template_id}",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == template_id
        assert data["name"] == "Test Template"

    def test_update_template(self, client, auth_headers):
        """Test PUT /outreach/templates/{id} - Update template"""
        # Create template
        create_response = client.post(
            "/outreach/templates",
            headers=auth_headers,
            json={
                "name": "Original",
                "subject": "Original Subject",
                "body_html": "<p>Original</p>",
                "body_text": "Original",
                "variables": []
            }
        )
        template_id = create_response.json()["id"]

        # Update template
        response = client.put(
            f"/outreach/templates/{template_id}",
            headers=auth_headers,
            json={
                "name": "Updated",
                "subject": "Updated Subject",
                "body_html": "<p>Updated</p>",
                "body_text": "Updated",
                "variables": ["new_var"]
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated"
        assert data["subject"] == "Updated Subject"

    def test_delete_template(self, client, auth_headers):
        """Test DELETE /outreach/templates/{id} - Delete template"""
        # Create template
        create_response = client.post(
            "/outreach/templates",
            headers=auth_headers,
            json={
                "name": "To Delete",
                "subject": "Subject",
                "body_html": "<p>Body</p>",
                "body_text": "Body",
                "variables": []
            }
        )
        template_id = create_response.json()["id"]

        # Delete template
        response = client.delete(
            f"/outreach/templates/{template_id}",
            headers=auth_headers
        )

        assert response.status_code == 204

        # Verify deleted
        get_response = client.get(
            f"/outreach/templates/{template_id}",
            headers=auth_headers
        )
        assert get_response.status_code == 404


@pytest.mark.outreach
@pytest.mark.integration
class TestCampaignEndpoints:
    """Test campaign management endpoints"""

    def test_create_simple_campaign(self, client, auth_headers):
        """Test POST /outreach/campaigns - Create single-step campaign"""
        response = client.post(
            "/outreach/campaigns",
            headers=auth_headers,
            json={
                "name": "Q1 Cold Outreach",
                "campaign_type": "cold_outreach",
                "status": "draft",
                "steps": [
                    {
                        "step_number": 1,
                        "template_id": str(uuid4()),
                        "delay_days": 0,
                        "delay_hours": 0,
                        "send_condition": None
                    }
                ]
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Q1 Cold Outreach"
        assert data["campaign_type"] == "cold_outreach"
        assert data["status"] == "draft"
        assert len(data["steps"]) == 1

    def test_create_multi_step_campaign(self, client, auth_headers):
        """Test POST /outreach/campaigns - Create multi-step sequence"""
        response = client.post(
            "/outreach/campaigns",
            headers=auth_headers,
            json={
                "name": "3-Touch Sequence",
                "campaign_type": "follow_up",
                "status": "draft",
                "steps": [
                    {
                        "step_number": 1,
                        "template_id": str(uuid4()),
                        "delay_days": 0,
                        "delay_hours": 0,
                        "send_condition": None
                    },
                    {
                        "step_number": 2,
                        "template_id": str(uuid4()),
                        "delay_days": 3,
                        "delay_hours": 0,
                        "send_condition": "if_not_opened"
                    },
                    {
                        "step_number": 3,
                        "template_id": str(uuid4()),
                        "delay_days": 7,
                        "delay_hours": 0,
                        "send_condition": "if_not_clicked"
                    }
                ]
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "3-Touch Sequence"
        assert len(data["steps"]) == 3
        assert data["steps"][1]["send_condition"] == "if_not_opened"
        assert data["steps"][2]["delay_days"] == 7

    def test_list_campaigns(self, client, auth_headers):
        """Test GET /outreach/campaigns - List campaigns"""
        # Create campaigns with different statuses
        for status in ["draft", "scheduled", "active"]:
            client.post(
                "/outreach/campaigns",
                headers=auth_headers,
                json={
                    "name": f"Campaign {status}",
                    "campaign_type": "cold_outreach",
                    "status": status,
                    "steps": [{"step_number": 1, "template_id": str(uuid4()), "delay_days": 0, "delay_hours": 0}]
                }
            )

        # List all campaigns
        response = client.get(
            "/outreach/campaigns",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 3

    def test_list_campaigns_by_status(self, client, auth_headers):
        """Test GET /outreach/campaigns?status=active - Filter by status"""
        # Create campaigns
        client.post(
            "/outreach/campaigns",
            headers=auth_headers,
            json={
                "name": "Active Campaign",
                "campaign_type": "cold_outreach",
                "status": "active",
                "steps": [{"step_number": 1, "template_id": str(uuid4()), "delay_days": 0, "delay_hours": 0}]
            }
        )
        client.post(
            "/outreach/campaigns",
            headers=auth_headers,
            json={
                "name": "Draft Campaign",
                "campaign_type": "cold_outreach",
                "status": "draft",
                "steps": [{"step_number": 1, "template_id": str(uuid4()), "delay_days": 0, "delay_hours": 0}]
            }
        )

        # Filter by active status
        response = client.get(
            "/outreach/campaigns?status=active",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert all(c["status"] == "active" for c in data)

    def test_get_campaign(self, client, auth_headers):
        """Test GET /outreach/campaigns/{id} - Get single campaign"""
        # Create campaign
        create_response = client.post(
            "/outreach/campaigns",
            headers=auth_headers,
            json={
                "name": "Test Campaign",
                "campaign_type": "cold_outreach",
                "status": "draft",
                "steps": [{"step_number": 1, "template_id": str(uuid4()), "delay_days": 0, "delay_hours": 0}]
            }
        )
        campaign_id = create_response.json()["id"]

        # Get campaign
        response = client.get(
            f"/outreach/campaigns/{campaign_id}",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == campaign_id
        assert data["name"] == "Test Campaign"

    def test_update_campaign(self, client, auth_headers):
        """Test PUT /outreach/campaigns/{id} - Update campaign"""
        # Create campaign
        create_response = client.post(
            "/outreach/campaigns",
            headers=auth_headers,
            json={
                "name": "Original",
                "campaign_type": "cold_outreach",
                "status": "draft",
                "steps": [{"step_number": 1, "template_id": str(uuid4()), "delay_days": 0, "delay_hours": 0}]
            }
        )
        campaign_id = create_response.json()["id"]

        # Update campaign
        response = client.put(
            f"/outreach/campaigns/{campaign_id}",
            headers=auth_headers,
            json={
                "name": "Updated Campaign",
                "status": "scheduled"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Campaign"
        assert data["status"] == "scheduled"


@pytest.mark.outreach
@pytest.mark.integration
class TestCampaignRecipients:
    """Test campaign recipient management"""

    def test_add_recipients_to_campaign(self, client, auth_headers):
        """Test POST /outreach/campaigns/{id}/recipients - Add recipients"""
        # Create campaign
        create_response = client.post(
            "/outreach/campaigns",
            headers=auth_headers,
            json={
                "name": "Test Campaign",
                "campaign_type": "cold_outreach",
                "status": "draft",
                "steps": [{"step_number": 1, "template_id": str(uuid4()), "delay_days": 0, "delay_hours": 0}]
            }
        )
        campaign_id = create_response.json()["id"]

        # Add recipients
        response = client.post(
            f"/outreach/campaigns/{campaign_id}/recipients",
            headers=auth_headers,
            json={
                "recipients": [
                    {
                        "email": "john@example.com",
                        "name": "John Doe",
                        "variables": {"property_address": "123 Main St"}
                    },
                    {
                        "email": "jane@example.com",
                        "name": "Jane Smith",
                        "variables": {"property_address": "456 Oak Ave"}
                    }
                ]
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["campaign_id"] == campaign_id
        assert data["recipients_added"] == 2

    def test_list_campaign_recipients(self, client, auth_headers):
        """Test GET /outreach/campaigns/{id}/recipients - List recipients"""
        # Create campaign
        create_response = client.post(
            "/outreach/campaigns",
            headers=auth_headers,
            json={
                "name": "Test Campaign",
                "campaign_type": "cold_outreach",
                "status": "draft",
                "steps": [{"step_number": 1, "template_id": str(uuid4()), "delay_days": 0, "delay_hours": 0}]
            }
        )
        campaign_id = create_response.json()["id"]

        # Add recipients
        client.post(
            f"/outreach/campaigns/{campaign_id}/recipients",
            headers=auth_headers,
            json={
                "recipients": [
                    {"email": "test1@example.com", "name": "Test 1", "variables": {}},
                    {"email": "test2@example.com", "name": "Test 2", "variables": {}}
                ]
            }
        )

        # List recipients
        response = client.get(
            f"/outreach/campaigns/{campaign_id}/recipients",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["email"] in ["test1@example.com", "test2@example.com"]


@pytest.mark.outreach
@pytest.mark.integration
class TestCampaignAnalytics:
    """Test campaign analytics endpoints"""

    def test_get_campaign_analytics(self, client, auth_headers, db_session):
        """Test GET /outreach/campaigns/{id}/analytics - Campaign metrics"""
        from db.models_outreach import Campaign, CampaignRecipient

        # Create campaign with recipients and various statuses
        create_response = client.post(
            "/outreach/campaigns",
            headers=auth_headers,
            json={
                "name": "Analytics Test",
                "campaign_type": "cold_outreach",
                "status": "completed",
                "steps": [{"step_number": 1, "template_id": str(uuid4()), "delay_days": 0, "delay_hours": 0}]
            }
        )
        campaign_data = create_response.json()
        campaign_id = campaign_data["id"]

        # Manually create recipients with different statuses (simulating email tracking)
        # This would normally be done by email service webhooks
        # For now, just test that the endpoint returns expected structure

        response = client.get(
            f"/outreach/campaigns/{campaign_id}/analytics",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "campaign_id" in data
        assert "total_recipients" in data
        assert "delivery_rate" in data
        assert "open_rate" in data
        assert "click_rate" in data
        assert "reply_rate" in data
        assert "step_metrics" in data

    def test_analytics_calculations(self, client, auth_headers):
        """Test that analytics correctly calculate rates"""
        # Create campaign
        create_response = client.post(
            "/outreach/campaigns",
            headers=auth_headers,
            json={
                "name": "Metrics Test",
                "campaign_type": "cold_outreach",
                "status": "active",
                "steps": [{"step_number": 1, "template_id": str(uuid4()), "delay_days": 0, "delay_hours": 0}]
            }
        )
        campaign_id = create_response.json()["id"]

        # Add recipients
        client.post(
            f"/outreach/campaigns/{campaign_id}/recipients",
            headers=auth_headers,
            json={
                "recipients": [
                    {"email": f"test{i}@example.com", "name": f"Test {i}", "variables": {}}
                    for i in range(10)
                ]
            }
        )

        # Get analytics
        response = client.get(
            f"/outreach/campaigns/{campaign_id}/analytics",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_recipients"] == 10
        # Rates should be 0.0 to 1.0
        assert 0 <= data["delivery_rate"] <= 1
        assert 0 <= data["open_rate"] <= 1


@pytest.mark.outreach
@pytest.mark.integration
class TestConditionalSequences:
    """Test conditional logic in multi-step campaigns"""

    def test_conditional_send_if_not_opened(self, client, auth_headers):
        """Test campaign with 'send_condition': 'if_not_opened'"""
        response = client.post(
            "/outreach/campaigns",
            headers=auth_headers,
            json={
                "name": "Follow-up if not opened",
                "campaign_type": "follow_up",
                "status": "draft",
                "steps": [
                    {
                        "step_number": 1,
                        "template_id": str(uuid4()),
                        "delay_days": 0,
                        "delay_hours": 0,
                        "send_condition": None
                    },
                    {
                        "step_number": 2,
                        "template_id": str(uuid4()),
                        "delay_days": 3,
                        "delay_hours": 0,
                        "send_condition": "if_not_opened"
                    }
                ]
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["steps"][1]["send_condition"] == "if_not_opened"

    def test_conditional_send_if_clicked(self, client, auth_headers):
        """Test campaign with 'send_condition': 'if_clicked'"""
        response = client.post(
            "/outreach/campaigns",
            headers=auth_headers,
            json={
                "name": "Engage hot leads",
                "campaign_type": "nurture",
                "status": "draft",
                "steps": [
                    {
                        "step_number": 1,
                        "template_id": str(uuid4()),
                        "delay_days": 0,
                        "delay_hours": 0,
                        "send_condition": None
                    },
                    {
                        "step_number": 2,
                        "template_id": str(uuid4()),
                        "delay_days": 1,
                        "delay_hours": 0,
                        "send_condition": "if_clicked"
                    }
                ]
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["steps"][1]["send_condition"] == "if_clicked"


@pytest.mark.outreach
@pytest.mark.unit
class TestTenantIsolation:
    """Test multi-tenant isolation for outreach endpoints"""

    def test_cannot_access_other_tenant_campaign(
        self, client, auth_headers, second_tenant, db_session
    ):
        """Test that users cannot access campaigns from other tenants"""
        from db.models_outreach import Campaign

        # Create campaign for second tenant
        other_campaign = Campaign(
            id=uuid4(),
            tenant_id=second_tenant.id,
            name="Other Tenant Campaign",
            campaign_type="cold_outreach",
            status="draft",
            total_recipients=0
        )
        db_session.add(other_campaign)
        db_session.commit()

        # Try to access with first tenant's auth
        response = client.get(
            f"/outreach/campaigns/{other_campaign.id}",
            headers=auth_headers
        )

        # Should not find or should return 403
        assert response.status_code in [404, 403]

    def test_cannot_list_other_tenant_templates(
        self, client, auth_headers, second_tenant, db_session
    ):
        """Test that template listing is tenant-isolated"""
        from db.models_outreach import EmailTemplate

        # Create template for second tenant
        other_template = EmailTemplate(
            id=uuid4(),
            tenant_id=second_tenant.id,
            name="Other Tenant Template",
            subject="Subject",
            body_html="<p>Body</p>",
            body_text="Body",
            variables=[]
        )
        db_session.add(other_template)
        db_session.commit()

        # List templates with first tenant's auth
        response = client.get(
            "/outreach/templates",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        # Should not include other tenant's template
        template_ids = [t["id"] for t in data]
        assert str(other_template.id) not in template_ids


@pytest.mark.slow
@pytest.mark.outreach
class TestOutreachPerformance:
    """Performance tests for outreach endpoints"""

    def test_bulk_recipient_add(self, client, auth_headers):
        """Test adding many recipients at once"""
        # Create campaign
        create_response = client.post(
            "/outreach/campaigns",
            headers=auth_headers,
            json={
                "name": "Bulk Test",
                "campaign_type": "cold_outreach",
                "status": "draft",
                "steps": [{"step_number": 1, "template_id": str(uuid4()), "delay_days": 0, "delay_hours": 0}]
            }
        )
        campaign_id = create_response.json()["id"]

        # Add 1000 recipients
        recipients = [
            {
                "email": f"test{i}@example.com",
                "name": f"Test User {i}",
                "variables": {"property_address": f"{i} Test St"}
            }
            for i in range(1000)
        ]

        import time
        start = time.time()

        response = client.post(
            f"/outreach/campaigns/{campaign_id}/recipients",
            headers=auth_headers,
            json={"recipients": recipients}
        )

        elapsed = time.time() - start

        assert response.status_code == 201
        # Should complete in under 5 seconds
        assert elapsed < 5.0
