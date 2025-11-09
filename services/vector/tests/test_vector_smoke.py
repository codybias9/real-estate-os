"""
Smoke tests for Qdrant vector integration

These are basic integration tests that require a running Qdrant instance.
If Qdrant is not available, tests will be skipped.
"""

import pytest
from vector import VectorClient, create_dummy_embedding


@pytest.fixture
def vector_client():
    """Create vector client for testing"""
    client = VectorClient(collection_name="test_properties", vector_size=384)

    # Clean up before test
    if client.collection_exists():
        client.delete_collection()

    yield client

    # Clean up after test
    if client.collection_exists():
        client.delete_collection()


def check_qdrant_available(client):
    """Check if Qdrant server is available"""
    try:
        client.client.get_collections()
        return True
    except Exception:
        return False


class TestQdrantSmoke:
    """Smoke tests for Qdrant integration"""

    def test_create_client(self):
        """Test creating Qdrant client"""
        client = VectorClient()
        assert client.collection_name == "properties"
        assert client.vector_size == 384

    def test_create_collection(self, vector_client):
        """Test creating collection"""
        if not check_qdrant_available(vector_client):
            pytest.skip("Qdrant not available")

        success = vector_client.create_collection()
        assert success is True
        assert vector_client.collection_exists() is True

    def test_upsert_property(self, vector_client):
        """Test upserting property embedding"""
        if not check_qdrant_available(vector_client):
            pytest.skip("Qdrant not available")

        # Create collection
        vector_client.create_collection()

        # Create dummy embedding
        embedding = create_dummy_embedding(384)

        # Upsert property
        success = vector_client.upsert_property(
            property_id="prop-123",
            embedding=embedding,
            metadata={
                "street": "123 Main St",
                "city": "Los Angeles",
                "state": "CA",
                "beds": 3,
                "baths": 2.0,
            },
        )

        assert success is True
        assert vector_client.count() == 1

    def test_search_similar(self, vector_client):
        """Test similarity search"""
        if not check_qdrant_available(vector_client):
            pytest.skip("Qdrant not available")

        # Create collection
        vector_client.create_collection()

        # Insert multiple properties
        for i in range(5):
            embedding = create_dummy_embedding(384)
            vector_client.upsert_property(
                property_id=f"prop-{i}",
                embedding=embedding,
                metadata={
                    "street": f"{i * 100} Main St",
                    "beds": 2 + i,
                },
            )

        # Search for similar properties
        query_vector = create_dummy_embedding(384)
        results = vector_client.search_similar(query_vector, limit=3)

        assert len(results) <= 3
        assert all("score" in r for r in results)
        assert all("metadata" in r for r in results)

    def test_get_property(self, vector_client):
        """Test getting property by ID"""
        if not check_qdrant_available(vector_client):
            pytest.skip("Qdrant not available")

        # Create collection
        vector_client.create_collection()

        # Insert property
        embedding = create_dummy_embedding(384)
        vector_client.upsert_property(
            property_id="prop-123", embedding=embedding, metadata={"city": "LA"}
        )

        # Get property
        result = vector_client.get_property("prop-123")

        assert result is not None
        assert result["metadata"]["city"] == "LA"

    def test_delete_property(self, vector_client):
        """Test deleting property"""
        if not check_qdrant_available(vector_client):
            pytest.skip("Qdrant not available")

        # Create collection
        vector_client.create_collection()

        # Insert property
        embedding = create_dummy_embedding(384)
        vector_client.upsert_property(
            property_id="prop-123", embedding=embedding
        )

        assert vector_client.count() == 1

        # Delete property
        success = vector_client.delete_property("prop-123")
        assert success is True
        assert vector_client.count() == 0

    def test_count(self, vector_client):
        """Test counting vectors"""
        if not check_qdrant_available(vector_client):
            pytest.skip("Qdrant not available")

        # Create collection
        vector_client.create_collection()

        # Initially empty
        assert vector_client.count() == 0

        # Add properties
        for i in range(10):
            embedding = create_dummy_embedding(384)
            vector_client.upsert_property(
                property_id=f"prop-{i}", embedding=embedding
            )

        assert vector_client.count() == 10

    def test_create_dummy_embedding(self):
        """Test dummy embedding creation"""
        embedding = create_dummy_embedding(384)

        assert len(embedding) == 384
        assert all(isinstance(x, float) for x in embedding)

        # Check normalization (should be unit vector)
        import numpy as np

        norm = np.linalg.norm(embedding)
        assert abs(norm - 1.0) < 0.001  # Close to 1.0

    def test_collection_not_exists(self, vector_client):
        """Test checking non-existent collection"""
        if not check_qdrant_available(vector_client):
            pytest.skip("Qdrant not available")

        # Don't create collection
        assert vector_client.collection_exists() is False

    def test_delete_collection(self, vector_client):
        """Test deleting collection"""
        if not check_qdrant_available(vector_client):
            pytest.skip("Qdrant not available")

        # Create and delete collection
        vector_client.create_collection()
        assert vector_client.collection_exists() is True

        success = vector_client.delete_collection()
        assert success is True
        assert vector_client.collection_exists() is False
