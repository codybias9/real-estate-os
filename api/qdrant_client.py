"""
Qdrant client with tenant isolation

All searches are automatically filtered by tenant_id to ensure data isolation.
"""

from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from typing import List, Dict, Any, Optional
import os


class TenantQdrantClient:
    """
    Qdrant client wrapper that enforces tenant isolation

    All upserts include tenant_id in payload.
    All searches automatically filter by tenant_id.
    """

    def __init__(self, url: str = None):
        self.url = url or os.getenv("QDRANT_URL", "http://localhost:6333")
        self.client = QdrantClient(url=self.url)

    def upsert_with_tenant(
        self,
        collection_name: str,
        points: List[Dict[str, Any]],
        tenant_id: str
    ):
        """
        Upsert points with tenant_id enforcement

        Automatically adds tenant_id to each point's payload.
        """
        # Ensure all points have tenant_id in payload
        for point in points:
            if "payload" not in point:
                point["payload"] = {}
            point["payload"]["tenant_id"] = tenant_id

        self.client.upsert(
            collection_name=collection_name,
            points=points
        )

    def search_with_tenant(
        self,
        collection_name: str,
        query_vector: List[float],
        tenant_id: str,
        limit: int = 10,
        additional_filters: Optional[Filter] = None
    ) -> List[Dict[str, Any]]:
        """
        Search with automatic tenant filtering

        CRITICAL: tenant_id filter is mandatory and enforced server-side.
        """
        # Build mandatory tenant filter
        tenant_filter = Filter(
            must=[
                FieldCondition(
                    key="tenant_id",
                    match=MatchValue(value=tenant_id)
                )
            ]
        )

        # Merge with additional filters if provided
        if additional_filters and additional_filters.must:
            tenant_filter.must.extend(additional_filters.must)

        # Perform search with tenant filter
        results = self.client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            query_filter=tenant_filter,
            limit=limit
        )

        return results

    def verify_tenant_isolation(
        self,
        collection_name: str,
        tenant_id: str
    ) -> Dict[str, Any]:
        """
        Verify that collection has tenant_id in all payloads

        Returns statistics about tenant isolation in the collection.
        """
        # Scroll through collection and check tenant_id presence
        offset = None
        total_points = 0
        points_with_tenant = 0
        points_for_this_tenant = 0

        while True:
            points, offset = self.client.scroll(
                collection_name=collection_name,
                limit=100,
                offset=offset
            )

            if not points:
                break

            for point in points:
                total_points += 1
                if "tenant_id" in point.payload:
                    points_with_tenant += 1
                    if point.payload["tenant_id"] == tenant_id:
                        points_for_this_tenant += 1

        return {
            "collection": collection_name,
            "total_points": total_points,
            "points_with_tenant_id": points_with_tenant,
            "points_for_tenant": points_for_this_tenant,
            "isolation_complete": points_with_tenant == total_points,
            "coverage_pct": (points_with_tenant / total_points * 100) if total_points > 0 else 0
        }

    def create_tenant_aware_collection(
        self,
        collection_name: str,
        vector_size: int,
        distance: str = "Cosine"
    ):
        """
        Create collection with tenant_id payload schema

        Ensures tenant_id is indexed for fast filtering.
        """
        from qdrant_client.models import VectorParams, Distance, PayloadSchemaType

        # Map distance string to enum
        distance_map = {
            "Cosine": Distance.COSINE,
            "Euclidean": Distance.EUCLID,
            "Dot": Distance.DOT
        }

        self.client.recreate_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=vector_size,
                distance=distance_map.get(distance, Distance.COSINE)
            )
        )

        # Create payload index on tenant_id for fast filtering
        self.client.create_payload_index(
            collection_name=collection_name,
            field_name="tenant_id",
            field_schema=PayloadSchemaType.KEYWORD
        )


# Singleton instance
qdrant_client = TenantQdrantClient()
