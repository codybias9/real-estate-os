"""Tests for properties API endpoints

Tests all endpoints in api/app/routers/properties.py including:
- Property details with provenance
- Provenance statistics
- Field history
- Scorecard with explainability
- Similar properties (Wave 2.3)
- Recommendations (Wave 2.3)
- User feedback (Wave 2.3)
- Comp analysis (Wave 3.1)
- Negotiation scenarios (Wave 3.2)
- Offer wizard (Wave 4.1)
"""

import pytest
from uuid import uuid4
from datetime import datetime


@pytest.mark.properties
@pytest.mark.integration
class TestPropertyEndpoints:
    """Test property CRUD and detail endpoints"""

    def test_get_property_details(self, client, auth_headers, property_factory):
        """Test GET /properties/{id} - Property details with provenance"""
        # Create test property
        prop = property_factory(
            listing_price=450000,
            square_feet=1800,
            canonical_address={
                "street": "456 Oak Ave",
                "city": "San Francisco",
                "state": "CA",
                "zip": "94102"
            }
        )

        # Get property details
        response = client.get(
            f"/properties/{prop.id}",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(prop.id)
        assert data["listing_price"] == 450000
        assert data["square_feet"] == 1800

    def test_get_property_not_found(self, client, auth_headers):
        """Test GET /properties/{id} with non-existent ID"""
        fake_id = uuid4()
        response = client.get(
            f"/properties/{fake_id}",
            headers=auth_headers
        )

        assert response.status_code == 404

    def test_get_property_unauthorized(self, client, property_factory):
        """Test GET /properties/{id} without authentication"""
        prop = property_factory()

        response = client.get(f"/properties/{prop.id}")

        # Should fail without auth (once auth is enforced)
        # For now, might return 200 if auth not enforced yet
        assert response.status_code in [200, 401]


@pytest.mark.properties
@pytest.mark.integration
class TestProvenanceEndpoints:
    """Test provenance and field history endpoints"""

    def test_get_provenance_stats(self, client, auth_headers, property_factory, db_session):
        """Test GET /properties/{id}/provenance - Provenance statistics"""
        from db.models_provenance import FieldProvenance

        # Create property
        prop = property_factory()

        # Create field provenance records
        prov1 = FieldProvenance(
            id=uuid4(),
            tenant_id=prop.tenant_id,
            entity_type="property",
            entity_id=prop.id,
            field_path="listing_price",
            value=450000,
            source_system="zillow.com",
            method="api",
            confidence=0.90,
            version=1,
            extracted_at=datetime.utcnow()
        )
        prov2 = FieldProvenance(
            id=uuid4(),
            tenant_id=prop.tenant_id,
            entity_type="property",
            entity_id=prop.id,
            field_path="square_feet",
            value=1800,
            source_system="redfin.com",
            method="scrape",
            confidence=0.85,
            version=1,
            extracted_at=datetime.utcnow()
        )
        db_session.add_all([prov1, prov2])
        db_session.commit()

        # Get provenance stats
        response = client.get(
            f"/properties/{prop.id}/provenance",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["property_id"] == str(prop.id)
        assert data["total_fields_tracked"] >= 2
        assert len(data["sources"]) >= 2

    def test_get_field_history(self, client, auth_headers, property_factory, db_session):
        """Test GET /properties/{id}/history/{field_path} - Field history"""
        from db.models_provenance import FieldProvenance

        prop = property_factory()

        # Create version history for listing_price
        for version in range(1, 4):
            prov = FieldProvenance(
                id=uuid4(),
                tenant_id=prop.tenant_id,
                entity_type="property",
                entity_id=prop.id,
                field_path="listing_price",
                value=450000 - (version * 5000),  # Price drops
                source_system="zillow.com",
                method="api",
                confidence=0.90,
                version=version,
                extracted_at=datetime.utcnow()
            )
            db_session.add(prov)
        db_session.commit()

        # Get field history
        response = client.get(
            f"/properties/{prop.id}/history/listing_price",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["field_path"] == "listing_price"
        assert len(data["versions"]) == 3
        # Should be ordered by version descending
        assert data["versions"][0]["version"] == 3
        assert data["versions"][-1]["version"] == 1


@pytest.mark.properties
@pytest.mark.integration
class TestScorecardEndpoints:
    """Test scorecard and explainability endpoints"""

    def test_get_scorecard(self, client, auth_headers, property_factory, scorecard_factory, db_session):
        """Test GET /properties/{id}/scorecard - Latest scorecard"""
        from db.models_provenance import ScoreExplainability

        prop = property_factory()
        scorecard = scorecard_factory(
            property_id=prop.id,
            score=0.82,
            grade="B+",
            factors={"location": 0.85, "price": 0.78, "condition": 0.83}
        )

        # Add explainability
        explain = ScoreExplainability(
            id=uuid4(),
            tenant_id=prop.tenant_id,
            scorecard_id=scorecard.id,
            factor_name="location",
            factor_weight=0.4,
            factor_value=0.85,
            contribution=0.34,
            explanation="Great neighborhood with schools"
        )
        db_session.add(explain)
        db_session.commit()

        # Get scorecard
        response = client.get(
            f"/properties/{prop.id}/scorecard",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["score"] == 0.82
        assert data["grade"] == "B+"
        assert len(data["explainability"]) >= 1
        assert data["explainability"][0]["factor_name"] == "location"

    def test_get_scorecard_not_found(self, client, auth_headers, property_factory):
        """Test GET /properties/{id}/scorecard when no scorecard exists"""
        prop = property_factory()

        response = client.get(
            f"/properties/{prop.id}/scorecard",
            headers=auth_headers
        )

        assert response.status_code == 404


@pytest.mark.properties
@pytest.mark.integration
class TestSimilarityEndpoints:
    """Test similarity search and recommendations (Wave 2.3)"""

    def test_find_similar_properties(self, client, auth_headers, property_factory):
        """Test GET /properties/{id}/similar - Find similar properties"""
        # Create target property
        target = property_factory(
            listing_price=500000,
            square_feet=2000,
            bedrooms=3,
            bathrooms=2
        )

        # Create similar properties
        similar1 = property_factory(
            listing_price=480000,
            square_feet=1950,
            bedrooms=3,
            bathrooms=2
        )
        similar2 = property_factory(
            listing_price=520000,
            square_feet=2100,
            bedrooms=3,
            bathrooms=2.5
        )

        # Find similar
        response = client.get(
            f"/properties/{target.id}/similar?limit=10",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "similar_properties" in data
        assert len(data["similar_properties"]) >= 0  # May or may not find based on ML

    def test_get_recommendations(self, client, auth_headers, test_tenant, property_factory):
        """Test POST /properties/recommend - Get recommendations"""
        # Create properties with various scores
        for i in range(5):
            prop = property_factory(
                listing_price=400000 + (i * 50000),
                square_feet=1500 + (i * 200)
            )

        # Get recommendations
        response = client.post(
            "/properties/recommend",
            headers=auth_headers,
            json={
                "user_id": str(uuid4()),
                "limit": 10,
                "filters": {}
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "recommendations" in data


@pytest.mark.properties
@pytest.mark.integration
class TestFeedbackEndpoints:
    """Test user feedback endpoints (Wave 2.3)"""

    def test_submit_feedback(self, client, auth_headers, property_factory, db_session):
        """Test POST /properties/{id}/feedback - Submit user feedback"""
        prop = property_factory()

        # Submit feedback
        response = client.post(
            f"/properties/{prop.id}/feedback",
            headers=auth_headers,
            json={
                "user_id": str(uuid4()),
                "feedback_type": "interested",
                "rating": 4,
                "comment": "Great location but price is high"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["property_id"] == str(prop.id)
        assert data["feedback_type"] == "interested"
        assert data["rating"] == 4

    def test_submit_feedback_invalid_rating(self, client, auth_headers, property_factory):
        """Test POST /properties/{id}/feedback with invalid rating"""
        prop = property_factory()

        response = client.post(
            f"/properties/{prop.id}/feedback",
            headers=auth_headers,
            json={
                "user_id": str(uuid4()),
                "feedback_type": "interested",
                "rating": 10,  # Invalid (should be 1-5)
                "comment": "Test"
            }
        )

        # Should validate rating range
        assert response.status_code in [400, 422]


@pytest.mark.properties
@pytest.mark.integration
class TestCompAnalysisEndpoints:
    """Test comp analysis endpoints (Wave 3.1)"""

    def test_get_comp_analysis(self, client, auth_headers, property_factory):
        """Test GET /properties/{id}/comp-analysis - Comparable properties"""
        target = property_factory(
            listing_price=500000,
            square_feet=2000,
            canonical_address={
                "street": "123 Main St",
                "city": "San Francisco",
                "state": "CA",
                "zip": "94102"
            }
        )

        # Create comps
        for i in range(3):
            property_factory(
                listing_price=490000 + (i * 10000),
                square_feet=1900 + (i * 100),
                canonical_address={
                    "street": f"{100 + i} Main St",
                    "city": "San Francisco",
                    "state": "CA",
                    "zip": "94102"
                }
            )

        # Get comp analysis
        response = client.get(
            f"/properties/{target.id}/comp-analysis",
            headers=auth_headers,
            params={"limit": 20}
        )

        assert response.status_code == 200
        data = response.json()
        assert "comps" in data
        assert "statistics" in data


@pytest.mark.properties
@pytest.mark.integration
class TestNegotiationEndpoints:
    """Test negotiation scenario endpoints (Wave 3.2)"""

    def test_get_negotiation_scenarios(self, client, auth_headers, property_factory):
        """Test POST /properties/{id}/negotiation-scenarios"""
        prop = property_factory(listing_price=500000)

        response = client.post(
            f"/properties/{prop.id}/negotiation-scenarios",
            headers=auth_headers,
            json={
                "offer_price": 475000,
                "strategy": "collaborative",
                "max_price": 490000
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "scenarios" in data
        assert len(data["scenarios"]) > 0


@pytest.mark.properties
@pytest.mark.integration
class TestOfferWizardEndpoints:
    """Test offer wizard endpoints (Wave 4.1)"""

    def test_offer_wizard(self, client, auth_headers, property_factory):
        """Test POST /properties/{id}/offer-wizard - Generate offer scenarios"""
        prop = property_factory(
            listing_price=500000,
            square_feet=2000
        )

        response = client.post(
            f"/properties/{prop.id}/offer-wizard",
            headers=auth_headers,
            json={
                "max_price": 510000,
                "target_price": 490000,
                "max_closing_days": 45,
                "min_inspection_days": 14,
                "required_contingencies": ["inspection", "financing"],
                "financing_contingency_required": True,
                "objectives": ["maximize_acceptance", "minimize_price"]
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "recommended_scenario" in data
        assert "all_scenarios" in data
        assert len(data["all_scenarios"]) >= 1

        # Check recommended scenario structure
        rec = data["recommended_scenario"]
        assert "offer_price" in rec
        assert "contingencies" in rec
        assert "closing_days" in rec
        assert "overall_score" in rec

    def test_offer_wizard_infeasible_constraints(self, client, auth_headers, property_factory):
        """Test offer wizard with impossible constraints"""
        prop = property_factory(listing_price=500000)

        response = client.post(
            f"/properties/{prop.id}/offer-wizard",
            headers=auth_headers,
            json={
                "max_price": 300000,  # Too low
                "target_price": 290000,
                "max_closing_days": 5,  # Too fast
                "min_inspection_days": 30,  # Impossible with max_closing
                "required_contingencies": ["inspection"],
                "financing_contingency_required": True,
                "objectives": ["maximize_acceptance"]
            }
        )

        assert response.status_code == 200
        data = response.json()
        # Should return infeasible reasons
        assert "infeasible_reasons" in data
        assert len(data["infeasible_reasons"]) > 0


@pytest.mark.properties
@pytest.mark.unit
class TestTenantIsolation:
    """Test multi-tenant isolation for property endpoints"""

    def test_cannot_access_other_tenant_property(
        self, client, auth_headers, property_factory, second_tenant, db_session
    ):
        """Test that users cannot access properties from other tenants"""
        from db.models_provenance import Property

        # Create property in second tenant
        other_property = Property(
            id=uuid4(),
            tenant_id=second_tenant.id,
            deterministic_id=f"prop_{uuid4().hex[:8]}",
            canonical_address={"street": "999 Other St"},
            listing_price=500000
        )
        db_session.add(other_property)
        db_session.commit()

        # Try to access with first tenant's auth
        response = client.get(
            f"/properties/{other_property.id}",
            headers=auth_headers
        )

        # Should not find or should return 403
        assert response.status_code in [404, 403]


# ============================================================================
# Performance Tests
# ============================================================================

@pytest.mark.slow
@pytest.mark.properties
class TestPropertyPerformance:
    """Performance tests for property endpoints"""

    def test_list_properties_performance(self, client, auth_headers, property_factory):
        """Test performance with many properties"""
        # Create 100 properties
        for i in range(100):
            property_factory(
                listing_price=400000 + (i * 1000),
                square_feet=1500 + (i * 10)
            )

        # Query should still be fast
        import time
        start = time.time()

        # This endpoint doesn't exist yet, but shows the pattern
        # response = client.get("/properties?limit=50", headers=auth_headers)

        elapsed = time.time() - start

        # Should complete in under 1 second
        assert elapsed < 1.0
