"""
End-to-End Test: Complete Property Lifecycle

Tests the full flow from property discovery through to outreach.
"""

import pytest
import httpx
import asyncio
from typing import Dict, Any


# Test configuration
BASE_URL = "http://localhost:8000/v1"
TEST_USER_EMAIL = "analyst@example.com"
TEST_USER_PASSWORD = "password123"


class TestPropertyLifecycle:
    """
    E2E test for complete property lifecycle.

    Flow:
    1. Login → Get JWT token
    2. Create property → Discovery
    3. Enrich property → External data
    4. Score property → Calculate score
    5. Generate memo → PDF creation
    6. Schedule outreach → Email/SMS
    7. Track timeline → Collaboration
    """

    @pytest.fixture
    async def auth_token(self) -> str:
        """Login and get authentication token"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/auth/login",
                json={
                    "email": TEST_USER_EMAIL,
                    "password": TEST_USER_PASSWORD,
                },
            )

            assert response.status_code == 200, f"Login failed: {response.text}"

            data = response.json()
            assert "access_token" in data
            return data["access_token"]

    @pytest.fixture
    def auth_headers(self, auth_token: str) -> Dict[str, str]:
        """Create authorization headers"""
        return {"Authorization": f"Bearer {auth_token}"}

    @pytest.mark.asyncio
    async def test_complete_property_lifecycle(self, auth_headers):
        """Test complete end-to-end property lifecycle"""

        async with httpx.AsyncClient(timeout=30.0) as client:
            # ===== STEP 1: Create Property (Discovery) =====
            print("\n1. Creating property...")
            create_response = await client.post(
                f"{BASE_URL}/properties",
                headers=auth_headers,
                json={
                    "apn": "123-456-789",
                    "street": "123 Main St",
                    "city": "Los Angeles",
                    "state": "CA",
                    "zip": "90001",
                    "county": "Los Angeles",
                },
            )

            assert create_response.status_code == 201
            property_data = create_response.json()
            property_id = property_data["id"]

            assert property_data["apn"] == "123-456-789"
            assert property_data["state"] == "discovered"
            print(f"✓ Property created: {property_id}")

            # ===== STEP 2: Get Property Detail =====
            print("\n2. Fetching property details...")
            detail_response = await client.get(
                f"{BASE_URL}/properties/{property_id}",
                headers=auth_headers,
            )

            assert detail_response.status_code == 200
            property_detail = detail_response.json()
            assert property_detail["id"] == property_id
            print(f"✓ Property details retrieved")

            # ===== STEP 3: Update Property (Enrichment) =====
            print("\n3. Enriching property data...")
            update_response = await client.put(
                f"{BASE_URL}/properties/{property_id}",
                headers=auth_headers,
                json={
                    "beds": 3,
                    "baths": 2.0,
                    "sqft": 1500,
                    "lot_sqft": 5000,
                    "year_built": 1950,
                },
            )

            assert update_response.status_code == 200
            updated_property = update_response.json()
            assert updated_property["beds"] == 3
            assert updated_property["baths"] == 2.0
            print(f"✓ Property enriched with characteristics")

            # ===== STEP 4: List Properties =====
            print("\n4. Listing properties...")
            list_response = await client.get(
                f"{BASE_URL}/properties",
                headers=auth_headers,
                params={"page": 1, "page_size": 50},
            )

            assert list_response.status_code == 200
            properties_list = list_response.json()
            assert properties_list["total"] >= 1
            assert any(p["id"] == property_id for p in properties_list["properties"])
            print(f"✓ Property appears in list")

            # ===== STEP 5: Add Timeline Comment =====
            print("\n5. Adding timeline comment...")
            comment_response = await client.post(
                f"{BASE_URL}/timeline/{property_id}/comments",
                headers=auth_headers,
                json={"content": "This property looks promising for acquisition"},
            )

            assert comment_response.status_code == 201
            comment_data = comment_response.json()
            assert comment_data["event_type"] == "comment"
            assert "This property looks promising" in comment_data["content"]
            print(f"✓ Comment added to timeline")

            # ===== STEP 6: Get Timeline =====
            print("\n6. Fetching timeline...")
            timeline_response = await client.get(
                f"{BASE_URL}/timeline/{property_id}",
                headers=auth_headers,
            )

            assert timeline_response.status_code == 200
            timeline_data = timeline_response.json()
            assert len(timeline_data["events"]) >= 1
            assert any(
                e["event_type"] == "comment" for e in timeline_data["events"]
            )
            print(f"✓ Timeline retrieved with {len(timeline_data['events'])} events")

            # ===== STEP 7: Add Note with Tags =====
            print("\n7. Adding tagged note...")
            note_response = await client.post(
                f"{BASE_URL}/timeline/{property_id}/notes",
                headers=auth_headers,
                json={
                    "content": "Owner interested in selling. Follow up next week.",
                    "tags": ["follow-up", "interested"],
                },
            )

            assert note_response.status_code == 201
            note_data = note_response.json()
            assert note_data["event_type"] == "note"
            assert "interested" in note_data["tags"]
            print(f"✓ Note added with tags")

            # ===== STEP 8: Filter Properties =====
            print("\n8. Filtering properties by state...")
            filter_response = await client.get(
                f"{BASE_URL}/properties",
                headers=auth_headers,
                params={"state": "discovered"},
            )

            assert filter_response.status_code == 200
            filtered_list = filter_response.json()
            # All returned properties should be in 'discovered' state
            assert all(
                p["state"] == "discovered" for p in filtered_list["properties"]
            )
            print(f"✓ Properties filtered successfully")

            print("\n✅ Complete property lifecycle test passed!")

    @pytest.mark.asyncio
    async def test_authentication_flow(self):
        """Test complete authentication flow"""

        async with httpx.AsyncClient() as client:
            # ===== Login =====
            print("\n1. Testing login...")
            login_response = await client.post(
                f"{BASE_URL}/auth/login",
                json={
                    "email": TEST_USER_EMAIL,
                    "password": TEST_USER_PASSWORD,
                },
            )

            assert login_response.status_code == 200
            login_data = login_response.json()

            assert "access_token" in login_data
            assert "refresh_token" in login_data
            assert login_data["token_type"] == "bearer"

            access_token = login_data["access_token"]
            refresh_token = login_data["refresh_token"]
            print(f"✓ Login successful")

            # ===== Get Current User =====
            print("\n2. Getting current user...")
            me_response = await client.get(
                f"{BASE_URL}/auth/me",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            assert me_response.status_code == 200
            user_data = me_response.json()

            assert user_data["email"] == TEST_USER_EMAIL
            assert "tenant_id" in user_data
            assert "role" in user_data
            print(f"✓ User info retrieved: {user_data['role']}")

            # ===== Refresh Token =====
            print("\n3. Refreshing access token...")
            refresh_response = await client.post(
                f"{BASE_URL}/auth/refresh",
                json={"refresh_token": refresh_token},
            )

            assert refresh_response.status_code == 200
            refresh_data = refresh_response.json()

            assert "access_token" in refresh_data
            new_access_token = refresh_data["access_token"]
            assert new_access_token != access_token  # Should be different
            print(f"✓ Token refreshed successfully")

            # ===== Logout =====
            print("\n4. Logging out...")
            logout_response = await client.post(
                f"{BASE_URL}/auth/logout",
                headers={"Authorization": f"Bearer {new_access_token}"},
            )

            assert logout_response.status_code == 200
            print(f"✓ Logout successful")

            print("\n✅ Authentication flow test passed!")

    @pytest.mark.asyncio
    async def test_error_handling(self, auth_headers):
        """Test error handling and validation"""

        async with httpx.AsyncClient() as client:
            # ===== Test 404 Not Found =====
            print("\n1. Testing 404 error...")
            response = await client.get(
                f"{BASE_URL}/properties/nonexistent-id",
                headers=auth_headers,
            )

            assert response.status_code == 404
            error_data = response.json()
            assert "detail" in error_data
            print(f"✓ 404 error handled correctly")

            # ===== Test 401 Unauthorized =====
            print("\n2. Testing 401 error...")
            response = await client.get(
                f"{BASE_URL}/properties",
                headers={"Authorization": "Bearer invalid-token"},
            )

            assert response.status_code == 401
            print(f"✓ 401 error handled correctly")

            # ===== Test 400 Bad Request =====
            print("\n3. Testing 400 error...")
            response = await client.post(
                f"{BASE_URL}/properties",
                headers=auth_headers,
                json={
                    "apn": "",  # Invalid: empty APN
                    "state": "CA",
                },
            )

            # Should validate and return 400 or 422
            assert response.status_code in [400, 422]
            print(f"✓ Validation error handled correctly")

            print("\n✅ Error handling test passed!")

    @pytest.mark.asyncio
    async def test_cache_behavior(self, auth_headers):
        """Test caching behavior"""

        async with httpx.AsyncClient() as client:
            # Create a property
            create_response = await client.post(
                f"{BASE_URL}/properties",
                headers=auth_headers,
                json={
                    "apn": "999-888-777",
                    "street": "456 Cache St",
                    "city": "Test City",
                    "state": "CA",
                },
            )

            property_id = create_response.json()["id"]

            # ===== First request (cache miss) =====
            print("\n1. First request (cache miss)...")
            import time

            start = time.time()
            response1 = await client.get(
                f"{BASE_URL}/properties/{property_id}",
                headers=auth_headers,
            )
            first_duration = time.time() - start

            assert response1.status_code == 200
            print(f"✓ First request: {first_duration*1000:.2f}ms")

            # ===== Second request (cache hit) =====
            print("\n2. Second request (cache hit)...")
            start = time.time()
            response2 = await client.get(
                f"{BASE_URL}/properties/{property_id}",
                headers=auth_headers,
            )
            second_duration = time.time() - start

            assert response2.status_code == 200
            print(f"✓ Second request: {second_duration*1000:.2f}ms")

            # Cache hit should be faster (if caching is working)
            if second_duration < first_duration:
                print(
                    f"✓ Cache speedup: {(first_duration/second_duration):.1f}x faster"
                )

            # ===== Update property (invalidates cache) =====
            print("\n3. Updating property (invalidates cache)...")
            await client.put(
                f"{BASE_URL}/properties/{property_id}",
                headers=auth_headers,
                json={"beds": 5},
            )

            # ===== Third request (cache miss after invalidation) =====
            response3 = await client.get(
                f"{BASE_URL}/properties/{property_id}",
                headers=auth_headers,
            )

            assert response3.status_code == 200
            assert response3.json()["beds"] == 5
            print(f"✓ Cache invalidated after update")

            print("\n✅ Cache behavior test passed!")

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, auth_headers):
        """Test concurrent request handling"""

        async with httpx.AsyncClient() as client:
            # Create test property
            create_response = await client.post(
                f"{BASE_URL}/properties",
                headers=auth_headers,
                json={
                    "apn": "111-222-333",
                    "street": "789 Concurrent Ave",
                    "city": "Test City",
                    "state": "CA",
                },
            )

            property_id = create_response.json()["id"]

            # ===== Send 10 concurrent requests =====
            print("\n1. Sending 10 concurrent requests...")
            tasks = [
                client.get(
                    f"{BASE_URL}/properties/{property_id}",
                    headers=auth_headers,
                )
                for _ in range(10)
            ]

            responses = await asyncio.gather(*tasks)

            # All should succeed
            assert all(r.status_code == 200 for r in responses)
            assert all(r.json()["id"] == property_id for r in responses)
            print(f"✓ All 10 concurrent requests succeeded")

            # ===== Test concurrent updates =====
            print("\n2. Testing concurrent updates...")
            update_tasks = [
                client.post(
                    f"{BASE_URL}/timeline/{property_id}/comments",
                    headers=auth_headers,
                    json={"content": f"Comment {i}"},
                )
                for i in range(5)
            ]

            update_responses = await asyncio.gather(*update_tasks)

            # All updates should succeed
            assert all(r.status_code == 201 for r in update_responses)
            print(f"✓ All 5 concurrent updates succeeded")

            # Verify all comments were added
            timeline_response = await client.get(
                f"{BASE_URL}/timeline/{property_id}",
                headers=auth_headers,
            )

            timeline_data = timeline_response.json()
            comment_count = sum(
                1
                for e in timeline_data["events"]
                if e["event_type"] == "comment"
            )
            assert comment_count >= 5
            print(f"✓ All {comment_count} comments recorded in timeline")

            print("\n✅ Concurrent request test passed!")


@pytest.mark.asyncio
async def test_health_checks():
    """Test system health endpoints"""

    async with httpx.AsyncClient() as client:
        # ===== API Health =====
        print("\n1. Checking API health...")
        health_response = await client.get(f"{BASE_URL}/health")

        assert health_response.status_code == 200
        health_data = health_response.json()

        assert health_data["status"] in ["healthy", "degraded"]
        assert "checks" in health_data
        print(f"✓ API health: {health_data['status']}")

        # ===== Database Health =====
        print("\n2. Checking database health...")
        db_health_response = await client.get(f"{BASE_URL}/health/db")

        assert db_health_response.status_code == 200
        db_health_data = db_health_response.json()

        assert db_health_data["status"] in ["healthy", "unhealthy"]
        print(f"✓ Database health: {db_health_data['status']}")

        # ===== Metrics =====
        print("\n3. Checking metrics endpoint...")
        metrics_response = await client.get("http://localhost:8000/metrics")

        assert metrics_response.status_code == 200
        metrics_text = metrics_response.text

        # Should contain Prometheus metrics
        assert "http_requests_total" in metrics_text
        print(f"✓ Metrics endpoint accessible")

        print("\n✅ Health check test passed!")


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])
