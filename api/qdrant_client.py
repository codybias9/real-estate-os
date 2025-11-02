"""
Qdrant vector database client with mandatory tenant isolation.

This client wraps the official Qdrant client to enforce tenant_id filtering
on all search operations, preventing cross-tenant data leakage.
"""
from qdrant_client import QdrantClient as BaseQdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, Filter, FieldCondition,
    MatchValue, SearchRequest, PointIdsList, UpdateResult, CountResult
)
from typing import List, Dict, Any, Optional, Union
from uuid import UUID
import logging
import numpy as np

from api.config import settings

logger = logging.getLogger(__name__)


class QdrantClient:
    """
    Wrapper around Qdrant client that enforces tenant isolation.

    All search operations require a tenant_id parameter.
    All vectors are automatically tagged with tenant_id in payload.
    """

    def __init__(self, url: Optional[str] = None, api_key: Optional[str] = None):
        """
        Initialize Qdrant client.

        Args:
            url: Qdrant server URL (defaults to settings)
            api_key: Qdrant API key (defaults to settings)
        """
        self.url = url or settings.qdrant_url
        self.api_key = api_key or settings.qdrant_api_key

        self._client = BaseQdrantClient(
            url=self.url,
            api_key=self.api_key,
            timeout=settings.qdrant_timeout
        )

        logger.info(f"Qdrant client initialized: {self.url}")

    @property
    def client(self) -> BaseQdrantClient:
        """Get underlying Qdrant client."""
        return self._client

    # ========================================================================
    # Collection Management
    # ========================================================================

    def create_collection(
        self,
        collection_name: str,
        vector_size: int,
        distance: Distance = Distance.COSINE,
        on_disk_payload: bool = False
    ) -> None:
        """
        Create a collection for storing vectors.

        Args:
            collection_name: Name of the collection
            vector_size: Dimension of vectors (e.g., 768 for sentence transformers)
            distance: Distance metric (COSINE, DOT, EUCLID)
            on_disk_payload: Store payload on disk (for large datasets)
        """
        try:
            self._client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=distance,
                    on_disk=on_disk_payload
                )
            )
            logger.info(f"Created collection: {collection_name} (vector_size={vector_size})")

        except Exception as e:
            if "already exists" in str(e).lower():
                logger.warning(f"Collection {collection_name} already exists")
            else:
                logger.error(f"Failed to create collection {collection_name}: {e}")
                raise

    def collection_exists(self, collection_name: str) -> bool:
        """Check if collection exists."""
        try:
            collections = self._client.get_collections().collections
            return any(c.name == collection_name for c in collections)
        except Exception as e:
            logger.error(f"Failed to check collection existence: {e}")
            return False

    def delete_collection(self, collection_name: str) -> None:
        """Delete a collection."""
        try:
            self._client.delete_collection(collection_name=collection_name)
            logger.info(f"Deleted collection: {collection_name}")
        except Exception as e:
            logger.error(f"Failed to delete collection {collection_name}: {e}")
            raise

    # ========================================================================
    # Upsert (Insert/Update) with Tenant Isolation
    # ========================================================================

    def upsert(
        self,
        collection_name: str,
        points: List[Dict[str, Any]],
        tenant_id: str
    ) -> UpdateResult:
        """
        Upsert vectors with automatic tenant_id tagging.

        Args:
            collection_name: Target collection
            points: List of point dictionaries:
                [
                    {
                        "id": "prop_123",
                        "vector": [0.1, 0.2, ...],
                        "payload": {"address": "123 Main St", "price": 500000}
                    },
                    ...
                ]
            tenant_id: Tenant UUID (automatically added to all payloads)

        Returns:
            UpdateResult with operation status

        Raises:
            ValueError: If tenant_id is missing or points malformed
        """
        if not tenant_id:
            raise ValueError("tenant_id is required for all upsert operations")

        if not points:
            raise ValueError("points list cannot be empty")

        try:
            # Convert to PointStruct with tenant_id injection
            qdrant_points = []
            for point in points:
                if "id" not in point or "vector" not in point:
                    raise ValueError(f"Point must have 'id' and 'vector': {point}")

                # Inject tenant_id into payload
                payload = point.get("payload", {})
                payload["tenant_id"] = tenant_id

                qdrant_points.append(PointStruct(
                    id=point["id"],
                    vector=point["vector"],
                    payload=payload
                ))

            # Upsert to Qdrant
            result = self._client.upsert(
                collection_name=collection_name,
                points=qdrant_points
            )

            logger.info(
                f"Upserted {len(points)} points to {collection_name} "
                f"(tenant={tenant_id})"
            )

            return result

        except Exception as e:
            logger.error(f"Upsert failed: {e}")
            raise

    # ========================================================================
    # Search with Mandatory Tenant Filtering
    # ========================================================================

    def search(
        self,
        collection_name: str,
        query_vector: Union[List[float], np.ndarray],
        tenant_id: str,
        limit: int = 10,
        score_threshold: Optional[float] = None,
        additional_filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar vectors with mandatory tenant filtering.

        Args:
            collection_name: Collection to search
            query_vector: Query vector (e.g., embedding of search text)
            tenant_id: Tenant UUID (REQUIRED - prevents cross-tenant search)
            limit: Maximum results to return
            score_threshold: Minimum similarity score (0.0 to 1.0)
            additional_filters: Additional payload filters (e.g., {"price": {"gte": 100000}})

        Returns:
            List of results:
            [
                {
                    "id": "prop_123",
                    "score": 0.92,
                    "payload": {"address": "123 Main St", "tenant_id": "tenant_alpha", ...}
                },
                ...
            ]

        Raises:
            ValueError: If tenant_id is missing
        """
        if not tenant_id:
            raise ValueError(
                "tenant_id is REQUIRED for all search operations. "
                "This prevents cross-tenant data leakage."
            )

        try:
            # Build tenant filter (MANDATORY)
            must_conditions = [
                FieldCondition(
                    key="tenant_id",
                    match=MatchValue(value=tenant_id)
                )
            ]

            # Add additional filters if provided
            if additional_filters:
                # TODO: Convert additional_filters dict to FieldCondition objects
                pass  # For now, only tenant_id filter

            query_filter = Filter(must=must_conditions)

            # Convert numpy array to list if needed
            if isinstance(query_vector, np.ndarray):
                query_vector = query_vector.tolist()

            # Execute search
            search_result = self._client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                query_filter=query_filter,
                limit=limit,
                score_threshold=score_threshold,
                with_payload=True,
                with_vectors=False  # Don't return vectors (large)
            )

            # Convert to simple dict format
            results = []
            for hit in search_result:
                results.append({
                    "id": str(hit.id),
                    "score": float(hit.score),
                    "payload": hit.payload
                })

            logger.info(
                f"Search returned {len(results)} results from {collection_name} "
                f"(tenant={tenant_id}, limit={limit})"
            )

            return results

        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise

    def search_batch(
        self,
        collection_name: str,
        query_vectors: List[Union[List[float], np.ndarray]],
        tenant_id: str,
        limit: int = 10,
        score_threshold: Optional[float] = None
    ) -> List[List[Dict[str, Any]]]:
        """
        Batch search for multiple query vectors.

        Args:
            collection_name: Collection to search
            query_vectors: List of query vectors
            tenant_id: Tenant UUID (REQUIRED)
            limit: Maximum results per query
            score_threshold: Minimum similarity score

        Returns:
            List of result lists (one per query)
        """
        if not tenant_id:
            raise ValueError("tenant_id is REQUIRED for batch search")

        try:
            # Build tenant filter
            query_filter = Filter(
                must=[
                    FieldCondition(
                        key="tenant_id",
                        match=MatchValue(value=tenant_id)
                    )
                ]
            )

            # Convert numpy arrays to lists
            query_vectors = [
                v.tolist() if isinstance(v, np.ndarray) else v
                for v in query_vectors
            ]

            # Build search requests
            search_requests = [
                SearchRequest(
                    vector=query_vector,
                    filter=query_filter,
                    limit=limit,
                    score_threshold=score_threshold,
                    with_payload=True,
                    with_vector=False
                )
                for query_vector in query_vectors
            ]

            # Execute batch search
            batch_results = self._client.search_batch(
                collection_name=collection_name,
                requests=search_requests
            )

            # Convert to simple format
            all_results = []
            for search_result in batch_results:
                results = []
                for hit in search_result:
                    results.append({
                        "id": str(hit.id),
                        "score": float(hit.score),
                        "payload": hit.payload
                    })
                all_results.append(results)

            logger.info(
                f"Batch search completed: {len(query_vectors)} queries, "
                f"tenant={tenant_id}"
            )

            return all_results

        except Exception as e:
            logger.error(f"Batch search failed: {e}")
            raise

    # ========================================================================
    # Retrieve by ID (with tenant verification)
    # ========================================================================

    def retrieve(
        self,
        collection_name: str,
        ids: List[str],
        tenant_id: str
    ) -> List[Dict[str, Any]]:
        """
        Retrieve points by ID with tenant verification.

        Args:
            collection_name: Collection name
            ids: List of point IDs
            tenant_id: Tenant UUID (REQUIRED)

        Returns:
            List of points that belong to the tenant

        Note:
            Points not belonging to tenant are filtered out (RLS behavior)
        """
        if not tenant_id:
            raise ValueError("tenant_id is REQUIRED for retrieve operations")

        try:
            # Retrieve points
            points = self._client.retrieve(
                collection_name=collection_name,
                ids=ids,
                with_payload=True,
                with_vectors=False
            )

            # Filter to only tenant's points (RLS-style)
            tenant_points = []
            for point in points:
                if point.payload.get("tenant_id") == tenant_id:
                    tenant_points.append({
                        "id": str(point.id),
                        "payload": point.payload
                    })

            logger.info(
                f"Retrieved {len(tenant_points)}/{len(points)} points "
                f"for tenant {tenant_id}"
            )

            return tenant_points

        except Exception as e:
            logger.error(f"Retrieve failed: {e}")
            raise

    # ========================================================================
    # Delete (with tenant verification)
    # ========================================================================

    def delete(
        self,
        collection_name: str,
        ids: List[str],
        tenant_id: str
    ) -> UpdateResult:
        """
        Delete points by ID (only if they belong to tenant).

        Args:
            collection_name: Collection name
            ids: List of point IDs to delete
            tenant_id: Tenant UUID (REQUIRED)

        Returns:
            UpdateResult

        Security:
            First verifies points belong to tenant, then deletes.
            Cannot delete other tenants' points.
        """
        if not tenant_id:
            raise ValueError("tenant_id is REQUIRED for delete operations")

        try:
            # First, retrieve points to verify ownership
            owned_points = self.retrieve(collection_name, ids, tenant_id)
            owned_ids = [p["id"] for p in owned_points]

            if not owned_ids:
                logger.warning(
                    f"Delete requested for {len(ids)} points but none belong to "
                    f"tenant {tenant_id}"
                )
                return UpdateResult(operation_id=0, status="completed")

            # Delete only owned points
            result = self._client.delete(
                collection_name=collection_name,
                points_selector=PointIdsList(points=owned_ids)
            )

            logger.info(
                f"Deleted {len(owned_ids)} points from {collection_name} "
                f"(tenant={tenant_id})"
            )

            return result

        except Exception as e:
            logger.error(f"Delete failed: {e}")
            raise

    # ========================================================================
    # Count (tenant-scoped)
    # ========================================================================

    def count(
        self,
        collection_name: str,
        tenant_id: str
    ) -> int:
        """
        Count points belonging to tenant.

        Args:
            collection_name: Collection name
            tenant_id: Tenant UUID (REQUIRED)

        Returns:
            Count of points for this tenant
        """
        if not tenant_id:
            raise ValueError("tenant_id is REQUIRED for count operations")

        try:
            # Count with tenant filter
            result = self._client.count(
                collection_name=collection_name,
                count_filter=Filter(
                    must=[
                        FieldCondition(
                            key="tenant_id",
                            match=MatchValue(value=tenant_id)
                        )
                    ]
                ),
                exact=True
            )

            count = result.count

            logger.info(f"Count: {count} points in {collection_name} (tenant={tenant_id})")

            return count

        except Exception as e:
            logger.error(f"Count failed: {e}")
            raise

    # ========================================================================
    # Health Check
    # ========================================================================

    def health_check(self) -> Dict[str, Any]:
        """
        Check Qdrant health and connectivity.

        Returns:
            Dict with status and metrics
        """
        try:
            # Get collections to verify connectivity
            collections = self._client.get_collections().collections

            return {
                "status": "healthy",
                "url": self.url,
                "collections_count": len(collections),
                "collections": [c.name for c in collections]
            }

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "url": self.url,
                "error": str(e)
            }


# Global Qdrant client instance
qdrant_client = QdrantClient()
