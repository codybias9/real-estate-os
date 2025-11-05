"""Tests for property endpoints."""

import pytest
from fastapi import status
from ..models import Property


@pytest.mark.property
@pytest.mark.unit
class TestPropertyEndpoints:
    """Test property CRUD operations."""

    def test_create_property(self, client, auth_headers, sample_property_data):
        """Test property creation."""
        response = client.post(
            "/api/v1/properties",
            headers=auth_headers,
            json=sample_property_data,
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["address"] == sample_property_data["address"]
        assert data["city"] == sample_property_data["city"]
        assert data["price"] == sample_property_data["price"]

    def test_create_property_unauthorized(self, client, sample_property_data):
        """Test property creation without authentication."""
        response = client.post(
            "/api/v1/properties",
            json=sample_property_data,
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_properties(self, client, auth_headers, test_property):
        """Test listing properties."""
        response = client.get("/api/v1/properties", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert data["total"] >= 1

    def test_list_properties_pagination(self, client, auth_headers, db_session, test_user, organization):
        """Test property list pagination."""
        from ..models.property import PropertyType, PropertyStatus

        # Create multiple properties
        for i in range(15):
            prop = Property(
                organization_id=organization.id,
                created_by=test_user.id,
                address=f"{i} Test St",
                city="Test City",
                state="CA",
                zip_code="12345",
                property_type=PropertyType.SINGLE_FAMILY,
                status=PropertyStatus.AVAILABLE,
                price=100000 * (i + 1),
            )
            db_session.add(prop)
        db_session.commit()

        # Get first page
        response = client.get(
            "/api/v1/properties?page=1&page_size=10",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 10
        assert data["total"] >= 15
        assert data["pages"] >= 2

    def test_get_property(self, client, auth_headers, test_property):
        """Test getting a specific property."""
        response = client.get(
            f"/api/v1/properties/{test_property.id}",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == test_property.id
        assert data["address"] == test_property.address

    def test_get_nonexistent_property(self, client, auth_headers):
        """Test getting a nonexistent property."""
        response = client.get(
            "/api/v1/properties/99999",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_property(self, client, auth_headers, test_property):
        """Test updating a property."""
        updated_data = {
            "price": 600000,
            "status": "under_contract",
        }

        response = client.put(
            f"/api/v1/properties/{test_property.id}",
            headers=auth_headers,
            json=updated_data,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["price"] == 600000
        assert data["status"] == "under_contract"

    def test_delete_property(self, client, auth_headers, test_property):
        """Test deleting a property (soft delete)."""
        response = client.delete(
            f"/api/v1/properties/{test_property.id}",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify property is soft deleted
        get_response = client.get(
            f"/api/v1/properties/{test_property.id}",
            headers=auth_headers,
        )

        assert get_response.status_code == status.HTTP_404_NOT_FOUND

    def test_filter_properties_by_city(self, client, auth_headers, test_property):
        """Test filtering properties by city."""
        response = client.get(
            f"/api/v1/properties?city={test_property.city}",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) >= 1
        assert all(item["city"] == test_property.city for item in data["items"])

    def test_filter_properties_by_price_range(self, client, auth_headers, test_property):
        """Test filtering properties by price range."""
        response = client.get(
            "/api/v1/properties?min_price=400000&max_price=600000",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        for item in data["items"]:
            if item["price"]:
                assert 400000 <= item["price"] <= 600000

    def test_search_properties(self, client, auth_headers, test_property):
        """Test searching properties."""
        response = client.get(
            f"/api/v1/properties?search=Test",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) >= 1


@pytest.mark.property
@pytest.mark.unit
class TestPropertyImages:
    """Test property image endpoints."""

    def test_add_property_image(self, client, auth_headers, test_property):
        """Test adding an image to a property."""
        image_data = {
            "url": "https://example.com/image.jpg",
            "title": "Front view",
            "is_primary": True,
        }

        response = client.post(
            f"/api/v1/properties/{test_property.id}/images",
            headers=auth_headers,
            json=image_data,
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["url"] == image_data["url"]
        assert data["title"] == image_data["title"]

    def test_list_property_images(self, client, auth_headers, test_property):
        """Test listing property images."""
        # Add an image first
        client.post(
            f"/api/v1/properties/{test_property.id}/images",
            headers=auth_headers,
            json={"url": "https://example.com/image1.jpg"},
        )

        response = client.get(
            f"/api/v1/properties/{test_property.id}/images",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_delete_property_image(self, client, auth_headers, test_property):
        """Test deleting a property image."""
        # Add an image first
        create_response = client.post(
            f"/api/v1/properties/{test_property.id}/images",
            headers=auth_headers,
            json={"url": "https://example.com/image.jpg"},
        )

        image_id = create_response.json()["id"]

        # Delete the image
        response = client.delete(
            f"/api/v1/properties/{test_property.id}/images/{image_id}",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.property
@pytest.mark.unit
class TestPropertyValuations:
    """Test property valuation endpoints."""

    def test_add_property_valuation(self, client, auth_headers, test_property):
        """Test adding a valuation to a property."""
        from datetime import datetime

        valuation_data = {
            "value": 550000,
            "valuation_date": datetime.utcnow().isoformat(),
            "source": "manual",
            "notes": "Updated market value",
        }

        response = client.post(
            f"/api/v1/properties/{test_property.id}/valuations",
            headers=auth_headers,
            json=valuation_data,
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["value"] == valuation_data["value"]
        assert data["source"] == valuation_data["source"]

    def test_list_property_valuations(self, client, auth_headers, test_property):
        """Test listing property valuations."""
        response = client.get(
            f"/api/v1/properties/{test_property.id}/valuations",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)


@pytest.mark.property
@pytest.mark.unit
class TestPropertyNotes:
    """Test property notes endpoints."""

    def test_add_property_note(self, client, auth_headers, test_property):
        """Test adding a note to a property."""
        note_data = {"content": "This is a test note"}

        response = client.post(
            f"/api/v1/properties/{test_property.id}/notes",
            headers=auth_headers,
            json=note_data,
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["content"] == note_data["content"]

    def test_list_property_notes(self, client, auth_headers, test_property):
        """Test listing property notes."""
        response = client.get(
            f"/api/v1/properties/{test_property.id}/notes",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)


@pytest.mark.property
@pytest.mark.unit
class TestPropertyActivities:
    """Test property activity endpoints."""

    def test_add_property_activity(self, client, auth_headers, test_property):
        """Test adding an activity to a property."""
        activity_data = {
            "activity_type": "viewing",
            "description": "Property viewing scheduled",
        }

        response = client.post(
            f"/api/v1/properties/{test_property.id}/activities",
            headers=auth_headers,
            json=activity_data,
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["activity_type"] == activity_data["activity_type"]

    def test_list_property_activities(self, client, auth_headers, test_property):
        """Test listing property activities."""
        response = client.get(
            f"/api/v1/properties/{test_property.id}/activities",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
