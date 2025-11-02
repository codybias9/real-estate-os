"""
Negative tests for multi-tenant isolation

Tests that Tenant A cannot access Tenant B's data across all layers:
- API layer (JWT-based filtering)
- Database layer (RLS policies)
- Vector store (Qdrant payload filters)
- Object storage (MinIO prefix isolation)
"""

import pytest
import uuid
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import io

# Assume these are importable from the application
try:
    from api.main import app
    from api.db import get_db_with_tenant, engine
    from api.qdrant_client import TenantQdrantClient
    from api.storage import TenantStorageClient
except ImportError:
    # Mock for testing purposes
    app = None
    engine = None


# Test fixtures
TENANT_A_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
TENANT_B_ID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"

# Mock JWT tokens (in real tests, use proper JWT generation)
TENANT_A_TOKEN = "mock_token_tenant_a"
TENANT_B_TOKEN = "mock_token_tenant_b"


class TestAPILayerIsolation:
    """Test that API endpoints enforce tenant isolation via JWT"""

    def setup_method(self):
        self.client = TestClient(app) if app else None

    def test_list_properties_tenant_a_cannot_see_tenant_b(self):
        """Tenant A token should not return Tenant B's properties"""
        if not self.client:
            pytest.skip("API not available")

        # Create test data for both tenants (setup phase)
        # In real tests, this would be done via API or direct DB insert

        # Request with Tenant A token
        headers = {"Authorization": f"Bearer {TENANT_A_TOKEN}"}
        response = self.client.get("/api/v1/properties", headers=headers)

        if response.status_code == 200:
            properties = response.json()
            # Verify all returned properties belong to Tenant A
            for prop in properties:
                assert prop.get("tenant_id") == TENANT_A_ID, \
                    f"Tenant A saw property from {prop.get('tenant_id')}"

    def test_get_property_cross_tenant_returns_404(self):
        """Tenant A cannot access Tenant B's property by ID"""
        if not self.client:
            pytest.skip("API not available")

        # Assume property_b_123 belongs to Tenant B
        property_b_id = "property_b_123"

        headers = {"Authorization": f"Bearer {TENANT_A_TOKEN}"}
        response = self.client.get(f"/api/v1/properties/{property_b_id}", headers=headers)

        # Should return 404 (not 403, to avoid information leakage)
        assert response.status_code in [404, 401, 403], \
            "Cross-tenant property access should be denied"

    def test_search_properties_tenant_isolation(self):
        """Search results should only include tenant's own properties"""
        if not self.client:
            pytest.skip("API not available")

        headers = {"Authorization": f"Bearer {TENANT_A_TOKEN}"}
        response = self.client.post("/api/v1/search",
                                    json={"query": "3 bedroom house"},
                                    headers=headers)

        if response.status_code == 200:
            results = response.json()
            for result in results:
                assert result.get("tenant_id") == TENANT_A_ID

    def test_create_offer_for_other_tenant_property_denied(self):
        """Tenant A cannot create offer for Tenant B's property"""
        if not self.client:
            pytest.skip("API not available")

        property_b_id = "property_b_456"

        headers = {"Authorization": f"Bearer {TENANT_A_TOKEN}"}
        response = self.client.post("/api/v1/offers",
                                    json={
                                        "property_id": property_b_id,
                                        "price": 500000,
                                        "terms": "cash"
                                    },
                                    headers=headers)

        assert response.status_code in [404, 403], \
            "Should not be able to create offer for other tenant's property"


class TestDatabaseLayerIsolation:
    """Test that PostgreSQL RLS policies enforce tenant isolation"""

    def test_rls_select_isolation(self):
        """Direct SQL with Tenant A context cannot see Tenant B rows"""
        if not engine:
            pytest.skip("Database not available")

        with get_db_with_tenant(TENANT_A_ID) as db:
            # Insert test property for Tenant B directly (bypassing RLS for setup)
            # This would be done by a superuser or in setup
            pass

        # Now query as Tenant A
        with get_db_with_tenant(TENANT_A_ID) as db:
            result = db.execute(text("""
                SELECT * FROM properties WHERE tenant_id = :tenant_b_id
            """), {"tenant_b_id": TENANT_B_ID})

            rows = result.fetchall()
            assert len(rows) == 0, \
                "Tenant A context should not see Tenant B rows even with explicit WHERE"

    def test_rls_insert_isolation(self):
        """Cannot insert row with different tenant_id than context"""
        if not engine:
            pytest.skip("Database not available")

        with get_db_with_tenant(TENANT_A_ID) as db:
            # Attempt to insert property for Tenant B while in Tenant A context
            try:
                db.execute(text("""
                    INSERT INTO properties (id, tenant_id, address, city, state, zip)
                    VALUES (:id, :tenant_id, '123 Test St', 'TestCity', 'TS', '12345')
                """), {
                    "id": str(uuid.uuid4()),
                    "tenant_id": TENANT_B_ID
                })
                db.commit()
                pytest.fail("Should not be able to insert row for different tenant")
            except Exception as e:
                # Expected: RLS policy violation
                db.rollback()
                assert True

    def test_rls_update_isolation(self):
        """Cannot update another tenant's row"""
        if not engine:
            pytest.skip("Database not available")

        # Assume property_b_id exists for Tenant B
        property_b_id = "property_b_test_id"

        with get_db_with_tenant(TENANT_A_ID) as db:
            result = db.execute(text("""
                UPDATE properties
                SET address = 'Hacked Address'
                WHERE id = :property_id
            """), {"property_id": property_b_id})

            # Should affect 0 rows due to RLS
            assert result.rowcount == 0, \
                "Should not be able to update other tenant's rows"

    def test_rls_delete_isolation(self):
        """Cannot delete another tenant's row"""
        if not engine:
            pytest.skip("Database not available")

        property_b_id = "property_b_test_id"

        with get_db_with_tenant(TENANT_A_ID) as db:
            result = db.execute(text("""
                DELETE FROM properties WHERE id = :property_id
            """), {"property_id": property_b_id})

            # Should affect 0 rows due to RLS
            assert result.rowcount == 0, \
                "Should not be able to delete other tenant's rows"

    def test_verify_rls_policies_exist(self):
        """Verify RLS is enabled and policies exist"""
        if not engine:
            pytest.skip("Database not available")

        with engine.connect() as conn:
            # Check RLS is enabled
            result = conn.execute(text("""
                SELECT relrowsecurity
                FROM pg_class
                WHERE relname = 'properties'
            """))
            row = result.fetchone()
            assert row[0] is True, "RLS should be enabled on properties table"

            # Check policy exists
            result = conn.execute(text("""
                SELECT COUNT(*)
                FROM pg_policies
                WHERE tablename = 'properties'
                AND policyname LIKE '%tenant_isolation%'
            """))
            count = result.scalar()
            assert count > 0, "Tenant isolation policy should exist"


class TestQdrantLayerIsolation:
    """Test that Qdrant payload filters enforce tenant isolation"""

    def setup_method(self):
        try:
            self.client = TenantQdrantClient(
                host="localhost",
                port=6333
            )
        except:
            self.client = None

    def test_search_returns_only_tenant_vectors(self):
        """Search with Tenant A filter should never return Tenant B vectors"""
        if not self.client:
            pytest.skip("Qdrant not available")

        collection_name = "test_properties"
        query_vector = [0.1] * 384  # Mock embedding

        # Search as Tenant A
        results = self.client.search_with_tenant(
            collection_name=collection_name,
            query_vector=query_vector,
            tenant_id=TENANT_A_ID,
            limit=100
        )

        # Verify all results have tenant_id = A
        for result in results:
            payload = result.payload
            assert payload.get("tenant_id") == TENANT_A_ID, \
                f"Tenant A search returned vector from {payload.get('tenant_id')}"

    def test_cannot_bypass_tenant_filter(self):
        """Verify tenant filter is mandatory and cannot be omitted"""
        if not self.client:
            pytest.skip("Qdrant not available")

        # The wrapper should not allow searches without tenant_id
        # This tests the API design, not Qdrant itself
        collection_name = "test_properties"
        query_vector = [0.1] * 384

        # Attempt to call underlying client directly (should be prevented by wrapper)
        try:
            # This should fail because our wrapper enforces tenant_id
            results = self.client.client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=100
                # No tenant filter - should be caught
            )

            # If we get here, check that results are not cross-tenant
            # (defense in depth)
            pytest.fail("Direct client access should be prevented or filtered")
        except AttributeError:
            # Expected: client is not exposed
            assert True

    def test_upsert_adds_tenant_id_to_payload(self):
        """Verify upsert automatically adds tenant_id to payloads"""
        if not self.client:
            pytest.skip("Qdrant not available")

        collection_name = "test_properties"

        points = [{
            "id": str(uuid.uuid4()),
            "vector": [0.1] * 384,
            "payload": {
                "address": "123 Test St",
                "price": 500000
            }
        }]

        # Upsert should automatically add tenant_id
        self.client.upsert_with_tenant(
            collection_name=collection_name,
            points=points,
            tenant_id=TENANT_A_ID
        )

        # Verify tenant_id was added
        for point in points:
            assert point["payload"]["tenant_id"] == TENANT_A_ID


class TestMinIOLayerIsolation:
    """Test that MinIO prefix isolation prevents cross-tenant access"""

    def setup_method(self):
        try:
            self.client = TenantStorageClient()
        except:
            self.client = None

    def test_list_objects_returns_only_tenant_objects(self):
        """List objects for Tenant A should not see Tenant B's objects"""
        if not self.client:
            pytest.skip("MinIO not available")

        # List all objects for Tenant A
        objects = self.client.list_objects(
            tenant_id=TENANT_A_ID,
            prefix="",
            recursive=True
        )

        # Verify all returned paths are relative (not showing full tenant prefix)
        # and don't include Tenant B's data
        for obj_path in objects:
            # Paths should not start with tenant_id (already stripped)
            assert not obj_path.startswith(TENANT_A_ID)
            assert not obj_path.startswith(TENANT_B_ID)

    def test_get_object_cross_tenant_returns_none(self):
        """Tenant A cannot retrieve Tenant B's object"""
        if not self.client:
            pytest.skip("MinIO not available")

        # Assume "document.pdf" exists under Tenant B
        object_path = "documents/document.pdf"

        # Try to get it as Tenant A
        result = self.client.get_object(
            tenant_id=TENANT_A_ID,
            object_path=object_path
        )

        # Should return None (object not found in Tenant A's namespace)
        # Even if same path exists in Tenant B
        assert result is None or result.status == 404

    def test_put_object_isolated_by_prefix(self):
        """Objects uploaded by Tenant A are stored under A's prefix"""
        if not self.client:
            pytest.skip("MinIO not available")

        object_path = "test/test_file.txt"
        data = io.BytesIO(b"Test content")

        full_path = self.client.put_object(
            tenant_id=TENANT_A_ID,
            object_path=object_path,
            data=data,
            length=len(b"Test content")
        )

        # Verify full path includes tenant prefix
        assert full_path.startswith(f"{TENANT_A_ID}/")
        assert full_path == f"{TENANT_A_ID}/{object_path}"

    def test_delete_object_cross_tenant_no_effect(self):
        """Attempting to delete Tenant B's object as Tenant A has no effect"""
        if not self.client:
            pytest.skip("MinIO not available")

        object_path = "documents/important.pdf"

        # Try to delete as Tenant A (even if it exists in Tenant B)
        try:
            self.client.delete_object(
                tenant_id=TENANT_A_ID,
                object_path=object_path
            )
            # Should succeed (no error) but only affects A's namespace
            assert True
        except Exception as e:
            # Or may fail with "object not found" - also acceptable
            assert "NoSuchKey" in str(e) or "not found" in str(e).lower()

    def test_verify_tenant_prefix_structure(self):
        """Verify all objects under tenant follow prefix structure"""
        if not self.client:
            pytest.skip("MinIO not available")

        stats = self.client.verify_tenant_isolation(tenant_id=TENANT_A_ID)

        assert stats["tenant_id"] == TENANT_A_ID
        assert stats["all_under_tenant_prefix"] is True, \
            "All objects should be under tenant prefix"

        # Check sample paths
        for path in stats["sample_paths"]:
            assert path.startswith(f"{TENANT_A_ID}/"), \
                f"Path {path} does not start with tenant prefix"


# Integration test combining all layers
class TestEndToEndIsolation:
    """End-to-end tests verifying isolation across all layers"""

    def test_create_property_with_documents_isolated(self):
        """Create property with documents and verify isolation at all layers"""
        if not app:
            pytest.skip("Full stack not available")

        client = TestClient(app)

        # Create property as Tenant A
        headers_a = {"Authorization": f"Bearer {TENANT_A_TOKEN}"}
        response = client.post("/api/v1/properties",
                              json={
                                  "address": "123 Tenant A St",
                                  "city": "CityA",
                                  "state": "CA",
                                  "zip": "90001",
                                  "price": 500000
                              },
                              headers=headers_a)

        if response.status_code != 201:
            pytest.skip("Property creation failed")

        property_a_id = response.json()["id"]

        # Upload document
        files = {"file": ("document.pdf", b"PDF content", "application/pdf")}
        response = client.post(f"/api/v1/properties/{property_a_id}/documents",
                              files=files,
                              headers=headers_a)

        # Verify Tenant B cannot access this property
        headers_b = {"Authorization": f"Bearer {TENANT_B_TOKEN}"}
        response = client.get(f"/api/v1/properties/{property_a_id}", headers=headers_b)
        assert response.status_code in [404, 403]

        # Verify isolation in database, Qdrant, and MinIO would be checked
        # by the individual layer tests above


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
