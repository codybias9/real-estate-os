"""Integration tests for Real Estate OS API."""

import pytest
from fastapi import status


@pytest.mark.integration
class TestUserWorkflow:
    """Test complete user workflow from registration to operations."""

    def test_complete_user_workflow(self, client, organization):
        """Test complete workflow: register -> login -> create property -> create lead -> create deal."""

        # 1. Register user
        register_response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "workflow@example.com",
                "password": "Workflow123!@#",
                "first_name": "Work",
                "last_name": "Flow",
                "organization_name": "Test Org",
            },
        )

        assert register_response.status_code == status.HTTP_201_CREATED
        access_token = register_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # 2. Get current user
        me_response = client.get("/api/v1/auth/me", headers=headers)
        assert me_response.status_code == status.HTTP_200_OK
        user = me_response.json()
        assert user["email"] == "workflow@example.com"

        # 3. Create a property
        property_response = client.post(
            "/api/v1/properties",
            headers=headers,
            json={
                "address": "789 Workflow St",
                "city": "Workflow City",
                "state": "CA",
                "zip_code": "12345",
                "property_type": "single_family",
                "status": "available",
                "price": 450000,
                "bedrooms": 3,
                "bathrooms": 2,
                "square_feet": 1800,
            },
        )

        assert property_response.status_code == status.HTTP_201_CREATED
        property_id = property_response.json()["id"]

        # 4. Create a lead
        lead_response = client.post(
            "/api/v1/leads",
            headers=headers,
            json={
                "first_name": "Potential",
                "last_name": "Buyer",
                "email": "buyer@example.com",
                "phone": "555-1111",
                "source": "website",
                "status": "new",
            },
        )

        assert lead_response.status_code == status.HTTP_201_CREATED
        lead_id = lead_response.json()["id"]

        # 5. Add lead activity
        activity_response = client.post(
            f"/api/v1/leads/{lead_id}/activities",
            headers=headers,
            json={
                "activity_type": "call",
                "description": "Initial contact call",
            },
        )

        assert activity_response.status_code == status.HTTP_201_CREATED

        # 6. Create a deal
        from datetime import date, timedelta

        deal_response = client.post(
            "/api/v1/deals",
            headers=headers,
            json={
                "property_id": property_id,
                "lead_id": lead_id,
                "deal_type": "sell",
                "stage": "qualified",
                "value": 450000,
                "probability": 60,
                "expected_close_date": (date.today() + timedelta(days=30)).isoformat(),
            },
        )

        assert deal_response.status_code == status.HTTP_201_CREATED
        deal_id = deal_response.json()["id"]

        # 7. Get analytics dashboard
        analytics_response = client.get(
            "/api/v1/analytics/dashboard",
            headers=headers,
        )

        assert analytics_response.status_code == status.HTTP_200_OK
        analytics = analytics_response.json()
        assert analytics["total_properties"] >= 1
        assert analytics["total_leads"] >= 1
        assert analytics["total_deals"] >= 1


@pytest.mark.integration
class TestPropertyLifecycle:
    """Test complete property lifecycle."""

    def test_property_lifecycle(self, client, auth_headers, sample_property_data):
        """Test property: create -> add images -> add valuation -> update status -> delete."""

        # 1. Create property
        create_response = client.post(
            "/api/v1/properties",
            headers=auth_headers,
            json=sample_property_data,
        )

        assert create_response.status_code == status.HTTP_201_CREATED
        property_id = create_response.json()["id"]

        # 2. Add images
        for i in range(3):
            image_response = client.post(
                f"/api/v1/properties/{property_id}/images",
                headers=auth_headers,
                json={
                    "url": f"https://example.com/image{i}.jpg",
                    "title": f"Image {i}",
                    "is_primary": i == 0,
                },
            )
            assert image_response.status_code == status.HTTP_201_CREATED

        # 3. Add valuation
        from datetime import datetime

        valuation_response = client.post(
            f"/api/v1/properties/{property_id}/valuations",
            headers=auth_headers,
            json={
                "value": 800000,
                "valuation_date": datetime.utcnow().isoformat(),
                "source": "appraisal",
            },
        )

        assert valuation_response.status_code == status.HTTP_201_CREATED

        # 4. Add note
        note_response = client.post(
            f"/api/v1/properties/{property_id}/notes",
            headers=auth_headers,
            json={"content": "Great property in good location"},
        )

        assert note_response.status_code == status.HTTP_201_CREATED

        # 5. Add activity
        activity_response = client.post(
            f"/api/v1/properties/{property_id}/activities",
            headers=auth_headers,
            json={
                "activity_type": "showing",
                "description": "Property showing completed",
            },
        )

        assert activity_response.status_code == status.HTTP_201_CREATED

        # 6. Update status
        update_response = client.put(
            f"/api/v1/properties/{property_id}",
            headers=auth_headers,
            json={"status": "under_contract"},
        )

        assert update_response.status_code == status.HTTP_200_OK
        assert update_response.json()["status"] == "under_contract"

        # 7. Get complete property details
        get_response = client.get(
            f"/api/v1/properties/{property_id}",
            headers=auth_headers,
        )

        assert get_response.status_code == status.HTTP_200_OK
        property_data = get_response.json()
        assert property_data["id"] == property_id
        assert property_data["status"] == "under_contract"

        # 8. Delete property
        delete_response = client.delete(
            f"/api/v1/properties/{property_id}",
            headers=auth_headers,
        )

        assert delete_response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.integration
class TestCampaignFlow:
    """Test campaign creation and execution."""

    def test_campaign_flow(self, client, auth_headers, test_lead, db_session):
        """Test campaign: create template -> create campaign -> add recipients -> send."""

        # 1. Create campaign template
        template_response = client.post(
            "/api/v1/campaigns/templates",
            headers=auth_headers,
            json={
                "name": "Welcome Email",
                "campaign_type": "email",
                "subject": "Welcome to Real Estate OS",
                "content": "Hi {{first_name}}, welcome to our platform!",
            },
        )

        assert template_response.status_code == status.HTTP_201_CREATED
        template_id = template_response.json()["id"]

        # 2. Create campaign
        campaign_response = client.post(
            "/api/v1/campaigns",
            headers=auth_headers,
            json={
                "name": "Welcome Campaign",
                "campaign_type": "email",
                "status": "draft",
                "subject": "Welcome!",
                "content": "Welcome to Real Estate OS!",
                "template_id": template_id,
            },
        )

        assert campaign_response.status_code == status.HTTP_201_CREATED
        campaign_id = campaign_response.json()["id"]

        # 3. Send campaign (this would trigger background task in production)
        send_response = client.post(
            f"/api/v1/campaigns/{campaign_id}/send",
            headers=auth_headers,
            json={
                "lead_ids": [test_lead.id],
                "send_now": False,
            },
        )

        assert send_response.status_code == status.HTTP_200_OK

        # 4. Get campaign stats
        stats_response = client.get(
            "/api/v1/campaigns/stats",
            headers=auth_headers,
        )

        assert stats_response.status_code == status.HTTP_200_OK


@pytest.mark.integration
class TestDealPipeline:
    """Test deal pipeline progression."""

    def test_deal_progression(self, client, auth_headers, test_property, test_lead):
        """Test deal progression through stages."""

        from datetime import date, timedelta

        # 1. Create deal
        deal_response = client.post(
            "/api/v1/deals",
            headers=auth_headers,
            json={
                "property_id": test_property.id,
                "lead_id": test_lead.id,
                "deal_type": "sell",
                "stage": "lead",
                "value": 500000,
                "probability": 25,
                "expected_close_date": (date.today() + timedelta(days=60)).isoformat(),
            },
        )

        assert deal_response.status_code == status.HTTP_201_CREATED
        deal_id = deal_response.json()["id"]

        # 2. Progress through stages
        stages = ["qualified", "contract", "inspection", "financing", "closing"]

        for stage in stages:
            update_response = client.put(
                f"/api/v1/deals/{deal_id}",
                headers=auth_headers,
                json={
                    "stage": stage,
                    "probability": 50 + (stages.index(stage) * 10),
                },
            )

            assert update_response.status_code == status.HTTP_200_OK
            assert update_response.json()["stage"] == stage

        # 3. Add transactions
        transaction_response = client.post(
            f"/api/v1/deals/{deal_id}/transactions",
            headers=auth_headers,
            json={
                "deal_id": deal_id,
                "transaction_type": "commission",
                "amount": 15000,
                "description": "Agent commission",
                "transaction_date": date.today().isoformat(),
            },
        )

        assert transaction_response.status_code == status.HTTP_201_CREATED

        # 4. Close deal
        close_response = client.put(
            f"/api/v1/deals/{deal_id}",
            headers=auth_headers,
            json={"stage": "closed_won"},
        )

        assert close_response.status_code == status.HTTP_200_OK

        # 5. Get deal analytics
        deal_stats_response = client.get(
            "/api/v1/analytics/deals",
            headers=auth_headers,
        )

        assert deal_stats_response.status_code == status.HTTP_200_OK
        stats = deal_stats_response.json()
        assert stats["total_deals"] >= 1


@pytest.mark.integration
class TestMultiTenancy:
    """Test multi-tenancy isolation."""

    def test_organization_isolation(self, client, db_session):
        """Test that users from different organizations can't access each other's data."""

        from ..models import Organization
        from ..services.auth import AuthService

        # Create two organizations
        org1 = Organization(name="Org 1", slug="org1")
        org2 = Organization(name="Org 2", slug="org2")
        db_session.add(org1)
        db_session.add(org2)
        db_session.flush()

        # Create users in each organization
        from ..models import User

        user1 = User(
            organization_id=org1.id,
            email="user1@org1.com",
            hashed_password=AuthService.hash_password("Pass123!@#"),
            first_name="User",
            last_name="One",
            is_active=True,
            is_verified=True,
        )

        user2 = User(
            organization_id=org2.id,
            email="user2@org2.com",
            hashed_password=AuthService.hash_password("Pass123!@#"),
            first_name="User",
            last_name="Two",
            is_active=True,
            is_verified=True,
        )

        db_session.add(user1)
        db_session.add(user2)
        db_session.commit()

        # Login as user1 and create property
        login1 = client.post(
            "/api/v1/auth/login",
            json={"email": "user1@org1.com", "password": "Pass123!@#"},
        )

        headers1 = {"Authorization": f"Bearer {login1.json()['access_token']}"}

        property_response = client.post(
            "/api/v1/properties",
            headers=headers1,
            json={
                "address": "Private Property",
                "city": "City1",
                "state": "CA",
                "zip_code": "12345",
                "property_type": "single_family",
                "status": "available",
                "price": 300000,
            },
        )

        property_id = property_response.json()["id"]

        # Login as user2 and try to access user1's property
        login2 = client.post(
            "/api/v1/auth/login",
            json={"email": "user2@org2.com", "password": "Pass123!@#"},
        )

        headers2 = {"Authorization": f"Bearer {login2.json()['access_token']}"}

        # Should not be able to access
        get_response = client.get(
            f"/api/v1/properties/{property_id}",
            headers=headers2,
        )

        assert get_response.status_code == status.HTTP_404_NOT_FOUND
