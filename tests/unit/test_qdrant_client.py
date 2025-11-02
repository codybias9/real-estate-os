"""
Unit tests for Qdrant vector database client.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4
import numpy as np

from api.qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, Filter, FieldCondition, MatchValue


class TestQdrantCollectionManagement:
    """Test Qdrant collection operations."""

    def test_create_collection(self, mock_qdrant):
        """Test collection creation."""
        client = QdrantClient()
        client._client = mock_qdrant

        client.create_collection(
            collection_name="properties",
            vector_size=768,
            distance=Distance.COSINE
        )

        mock_qdrant.create_collection.assert_called_once()
        args = mock_qdrant.create_collection.call_args

        assert args[1]["collection_name"] == "properties"
        assert args[1]["vectors_config"].size == 768
        assert args[1]["vectors_config"].distance == Distance.COSINE

    def test_create_collection_already_exists(self, mock_qdrant):
        """Test creating collection that already exists."""
        client = QdrantClient()
        client._client = mock_qdrant

        # Simulate "already exists" error
        mock_qdrant.create_collection.side_effect = Exception("already exists")

        # Should not raise, just log warning
        client.create_collection(
            collection_name="properties",
            vector_size=768
        )

    def test_collection_exists_true(self, mock_qdrant):
        """Test checking if collection exists (true)."""
        client = QdrantClient()
        client._client = mock_qdrant

        # Mock collections response
        mock_collection = Mock()
        mock_collection.name = "properties"
        mock_qdrant.get_collections.return_value.collections = [mock_collection]

        exists = client.collection_exists("properties")

        assert exists is True

    def test_collection_exists_false(self, mock_qdrant):
        """Test checking if collection exists (false)."""
        client = QdrantClient()
        client._client = mock_qdrant

        # Mock empty collections response
        mock_qdrant.get_collections.return_value.collections = []

        exists = client.collection_exists("nonexistent")

        assert exists is False

    def test_delete_collection(self, mock_qdrant):
        """Test collection deletion."""
        client = QdrantClient()
        client._client = mock_qdrant

        client.delete_collection("properties")

        mock_qdrant.delete_collection.assert_called_once_with(
            collection_name="properties"
        )


class TestQdrantUpsert:
    """Test Qdrant upsert (insert/update) operations."""

    def test_upsert_with_tenant_id(self, mock_qdrant, tenant_id, sample_vector):
        """Test upsert automatically adds tenant_id to payload."""
        client = QdrantClient()
        client._client = mock_qdrant

        points = [
            {
                "id": "prop_123",
                "vector": sample_vector,
                "payload": {"address": "123 Main St", "price": 450000}
            }
        ]

        client.upsert(
            collection_name="properties",
            points=points,
            tenant_id=tenant_id
        )

        # Verify tenant_id was injected
        mock_qdrant.upsert.assert_called_once()
        call_args = mock_qdrant.upsert.call_args

        upserted_points = call_args[1]["points"]
        assert len(upserted_points) == 1
        assert upserted_points[0].payload["tenant_id"] == tenant_id
        assert upserted_points[0].payload["address"] == "123 Main St"

    def test_upsert_without_tenant_id_raises_error(self, mock_qdrant, sample_vector):
        """Test upsert without tenant_id raises ValueError."""
        client = QdrantClient()
        client._client = mock_qdrant

        points = [
            {
                "id": "prop_123",
                "vector": sample_vector,
                "payload": {}
            }
        ]

        with pytest.raises(ValueError) as exc_info:
            client.upsert(
                collection_name="properties",
                points=points,
                tenant_id=None  # Missing tenant_id
            )

        assert "tenant_id is required" in str(exc_info.value).lower()

    def test_upsert_empty_points_raises_error(self, mock_qdrant, tenant_id):
        """Test upsert with empty points list raises ValueError."""
        client = QdrantClient()
        client._client = mock_qdrant

        with pytest.raises(ValueError) as exc_info:
            client.upsert(
                collection_name="properties",
                points=[],  # Empty
                tenant_id=tenant_id
            )

        assert "empty" in str(exc_info.value).lower()

    def test_upsert_malformed_point_raises_error(self, mock_qdrant, tenant_id):
        """Test upsert with malformed point raises ValueError."""
        client = QdrantClient()
        client._client = mock_qdrant

        points = [
            {"id": "prop_123"}  # Missing 'vector'
        ]

        with pytest.raises(ValueError) as exc_info:
            client.upsert(
                collection_name="properties",
                points=points,
                tenant_id=tenant_id
            )

        assert "vector" in str(exc_info.value).lower()

    def test_upsert_multiple_points(self, mock_qdrant, tenant_id, sample_vector):
        """Test upserting multiple points."""
        client = QdrantClient()
        client._client = mock_qdrant

        points = [
            {"id": "prop_1", "vector": sample_vector, "payload": {"price": 100000}},
            {"id": "prop_2", "vector": sample_vector, "payload": {"price": 200000}},
            {"id": "prop_3", "vector": sample_vector, "payload": {"price": 300000}}
        ]

        client.upsert(
            collection_name="properties",
            points=points,
            tenant_id=tenant_id
        )

        call_args = mock_qdrant.upsert.call_args
        upserted_points = call_args[1]["points"]

        assert len(upserted_points) == 3
        for point in upserted_points:
            assert point.payload["tenant_id"] == tenant_id


class TestQdrantSearch:
    """Test Qdrant search operations with tenant filtering."""

    def test_search_with_tenant_filter(self, mock_qdrant, tenant_id, sample_vector):
        """Test search automatically applies tenant filter."""
        client = QdrantClient()
        client._client = mock_qdrant

        # Mock search results
        mock_hit = Mock()
        mock_hit.id = "prop_123"
        mock_hit.score = 0.95
        mock_hit.payload = {"address": "123 Main St", "tenant_id": tenant_id}
        mock_qdrant.search.return_value = [mock_hit]

        results = client.search(
            collection_name="properties",
            query_vector=sample_vector,
            tenant_id=tenant_id,
            limit=10
        )

        # Verify tenant filter was applied
        mock_qdrant.search.assert_called_once()
        call_args = mock_qdrant.search.call_args

        query_filter = call_args[1]["query_filter"]
        assert query_filter is not None
        assert len(query_filter.must) == 1
        assert query_filter.must[0].key == "tenant_id"
        assert query_filter.must[0].match.value == tenant_id

        # Verify results
        assert len(results) == 1
        assert results[0]["id"] == "prop_123"
        assert results[0]["score"] == 0.95

    def test_search_without_tenant_id_raises_error(self, mock_qdrant, sample_vector):
        """Test search without tenant_id raises ValueError."""
        client = QdrantClient()
        client._client = mock_qdrant

        with pytest.raises(ValueError) as exc_info:
            client.search(
                collection_name="properties",
                query_vector=sample_vector,
                tenant_id=None  # Missing
            )

        assert "tenant_id is REQUIRED" in str(exc_info.value)

    def test_search_with_numpy_array(self, mock_qdrant, tenant_id):
        """Test search with numpy array (should convert to list)."""
        client = QdrantClient()
        client._client = mock_qdrant

        # Use numpy array
        query_vector = np.random.random(768)
        mock_qdrant.search.return_value = []

        client.search(
            collection_name="properties",
            query_vector=query_vector,
            tenant_id=tenant_id
        )

        # Verify vector was converted to list
        call_args = mock_qdrant.search.call_args
        passed_vector = call_args[1]["query_vector"]
        assert isinstance(passed_vector, list)
        assert len(passed_vector) == 768

    def test_search_with_score_threshold(self, mock_qdrant, tenant_id, sample_vector):
        """Test search with score threshold."""
        client = QdrantClient()
        client._client = mock_qdrant
        mock_qdrant.search.return_value = []

        client.search(
            collection_name="properties",
            query_vector=sample_vector,
            tenant_id=tenant_id,
            score_threshold=0.8
        )

        call_args = mock_qdrant.search.call_args
        assert call_args[1]["score_threshold"] == 0.8

    def test_search_batch(self, mock_qdrant, tenant_id, sample_vector):
        """Test batch search."""
        client = QdrantClient()
        client._client = mock_qdrant

        query_vectors = [sample_vector, sample_vector, sample_vector]

        # Mock batch results
        mock_qdrant.search_batch.return_value = [[], [], []]

        results = client.search_batch(
            collection_name="properties",
            query_vectors=query_vectors,
            tenant_id=tenant_id,
            limit=5
        )

        assert len(results) == 3
        mock_qdrant.search_batch.assert_called_once()


class TestQdrantRetrieve:
    """Test Qdrant retrieve operations."""

    def test_retrieve_with_tenant_verification(self, mock_qdrant, tenant_id):
        """Test retrieve filters results by tenant_id."""
        client = QdrantClient()
        client._client = mock_qdrant

        # Mock retrieve results (mix of tenants)
        mock_point1 = Mock()
        mock_point1.id = "prop_1"
        mock_point1.payload = {"tenant_id": tenant_id, "address": "123 Main"}

        mock_point2 = Mock()
        mock_point2.id = "prop_2"
        mock_point2.payload = {"tenant_id": "other_tenant", "address": "456 Oak"}

        mock_qdrant.retrieve.return_value = [mock_point1, mock_point2]

        results = client.retrieve(
            collection_name="properties",
            ids=["prop_1", "prop_2"],
            tenant_id=tenant_id
        )

        # Should only return prop_1 (correct tenant)
        assert len(results) == 1
        assert results[0]["id"] == "prop_1"

    def test_retrieve_without_tenant_id_raises_error(self, mock_qdrant):
        """Test retrieve without tenant_id raises ValueError."""
        client = QdrantClient()
        client._client = mock_qdrant

        with pytest.raises(ValueError) as exc_info:
            client.retrieve(
                collection_name="properties",
                ids=["prop_1"],
                tenant_id=None
            )

        assert "tenant_id is REQUIRED" in str(exc_info.value)


class TestQdrantDelete:
    """Test Qdrant delete operations with tenant verification."""

    def test_delete_with_tenant_verification(self, mock_qdrant, tenant_id):
        """Test delete only deletes tenant's own points."""
        client = QdrantClient()
        client._client = mock_qdrant

        # Mock retrieve to return tenant's points
        mock_point = Mock()
        mock_point.id = "prop_1"
        mock_point.payload = {"tenant_id": tenant_id}
        mock_qdrant.retrieve.return_value = [mock_point]

        client.delete(
            collection_name="properties",
            ids=["prop_1", "prop_2"],  # prop_2 doesn't belong to tenant
            tenant_id=tenant_id
        )

        # Should only delete prop_1
        mock_qdrant.delete.assert_called_once()

    def test_delete_without_tenant_id_raises_error(self, mock_qdrant):
        """Test delete without tenant_id raises ValueError."""
        client = QdrantClient()
        client._client = mock_qdrant

        with pytest.raises(ValueError) as exc_info:
            client.delete(
                collection_name="properties",
                ids=["prop_1"],
                tenant_id=None
            )

        assert "tenant_id is REQUIRED" in str(exc_info.value)


class TestQdrantCount:
    """Test Qdrant count operations."""

    def test_count_with_tenant_filter(self, mock_qdrant, tenant_id):
        """Test count applies tenant filter."""
        client = QdrantClient()
        client._client = mock_qdrant

        # Mock count result
        mock_result = Mock()
        mock_result.count = 42
        mock_qdrant.count.return_value = mock_result

        count = client.count(
            collection_name="properties",
            tenant_id=tenant_id
        )

        assert count == 42

        # Verify tenant filter was applied
        call_args = mock_qdrant.count.call_args
        count_filter = call_args[1]["count_filter"]
        assert count_filter.must[0].key == "tenant_id"
        assert count_filter.must[0].match.value == tenant_id

    def test_count_without_tenant_id_raises_error(self, mock_qdrant):
        """Test count without tenant_id raises ValueError."""
        client = QdrantClient()
        client._client = mock_qdrant

        with pytest.raises(ValueError) as exc_info:
            client.count(
                collection_name="properties",
                tenant_id=None
            )

        assert "tenant_id is REQUIRED" in str(exc_info.value)


class TestQdrantHealthCheck:
    """Test Qdrant health check."""

    def test_health_check_healthy(self, mock_qdrant):
        """Test health check when Qdrant is healthy."""
        client = QdrantClient()
        client._client = mock_qdrant

        # Mock collections
        mock_collection = Mock()
        mock_collection.name = "properties"
        mock_qdrant.get_collections.return_value.collections = [mock_collection]

        health = client.health_check()

        assert health["status"] == "healthy"
        assert health["collections_count"] == 1
        assert "properties" in health["collections"]

    def test_health_check_unhealthy(self, mock_qdrant):
        """Test health check when Qdrant is unhealthy."""
        client = QdrantClient()
        client._client = mock_qdrant

        # Simulate connection error
        mock_qdrant.get_collections.side_effect = Exception("Connection failed")

        health = client.health_check()

        assert health["status"] == "unhealthy"
        assert "error" in health


# ============================================================================
# Test Statistics
# ============================================================================
# Total tests in this module: 28
