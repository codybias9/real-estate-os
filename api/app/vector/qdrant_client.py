"""Qdrant Client for Vector Search
Portfolio twin search with tenant filtering
"""

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct,
    Filter, FieldCondition, MatchValue, Range,
    SearchParams
)
from typing import List, Dict, Optional
from uuid import UUID
import numpy as np
import os
import logging

logger = logging.getLogger(__name__)


class PropertyVectorStore:
    """Vector store for property embeddings"""

    COLLECTION_NAME = "properties"
    VECTOR_DIM = 128

    def __init__(self):
        self.client = QdrantClient(
            host=os.getenv("QDRANT_HOST", "localhost"),
            port=int(os.getenv("QDRANT_PORT", "6333"))
        )

        # Ensure collection exists
        self._ensure_collection()

    def _ensure_collection(self):
        """Create collection if it doesn't exist"""

        # Check if collection exists
        collections = self.client.get_collections().collections
        collection_names = [c.name for c in collections]

        if self.COLLECTION_NAME not in collection_names:
            logger.info(f"Creating collection: {self.COLLECTION_NAME}")

            self.client.create_collection(
                collection_name=self.COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=self.VECTOR_DIM,
                    distance=Distance.COSINE
                )
            )

            # Create payload indexes for fast filtering
            self._create_payload_indexes()

    def _create_payload_indexes(self):
        """Create indexes on payload fields for fast filtering"""

        # Index tenant_id (CRITICAL for multi-tenancy)
        self.client.create_payload_index(
            collection_name=self.COLLECTION_NAME,
            field_name="tenant_id",
            field_schema="keyword"
        )

        # Index market
        self.client.create_payload_index(
            collection_name=self.COLLECTION_NAME,
            field_name="market",
            field_schema="keyword"
        )

        # Index asset_type
        self.client.create_payload_index(
            collection_name=self.COLLECTION_NAME,
            field_name="asset_type",
            field_schema="keyword"
        )

        # Index price_band
        self.client.create_payload_index(
            collection_name=self.COLLECTION_NAME,
            field_name="price_band",
            field_schema="keyword"
        )

        # Index sqft_band
        self.client.create_payload_index(
            collection_name=self.COLLECTION_NAME,
            field_name="sqft_band",
            field_schema="keyword"
        )

        logger.info("Payload indexes created")

    def upsert_property(
        self,
        property_id: UUID,
        embedding: np.ndarray,
        tenant_id: UUID,
        metadata: Dict
    ):
        """Upsert property embedding

        Args:
            property_id: Unique property ID
            embedding: 128-dim embedding vector
            tenant_id: Tenant ID (for isolation)
            metadata: Additional metadata (market, asset_type, etc.)
        """

        # Create point
        point = PointStruct(
            id=str(property_id),
            vector=embedding.tolist(),
            payload={
                "tenant_id": str(tenant_id),
                "market": metadata.get("market"),
                "asset_type": metadata.get("asset_type"),
                "price_band": self._get_price_band(metadata.get("list_price", 0)),
                "sqft_band": self._get_sqft_band(metadata.get("sqft", 0)),
                "list_price": metadata.get("list_price"),
                "sqft": metadata.get("sqft"),
                "address": metadata.get("address"),
                "status": metadata.get("status", "active")
            }
        )

        # Upsert
        self.client.upsert(
            collection_name=self.COLLECTION_NAME,
            points=[point]
        )

        logger.info(f"Upserted property: {property_id}")

    def upsert_batch(self, properties: List[Dict]):
        """Upsert batch of properties

        Args:
            properties: List of dicts with property_id, embedding, tenant_id, metadata
        """

        points = []
        for prop in properties:
            metadata = prop.get("metadata", {})

            point = PointStruct(
                id=str(prop["property_id"]),
                vector=prop["embedding"].tolist(),
                payload={
                    "tenant_id": str(prop["tenant_id"]),
                    "market": metadata.get("market"),
                    "asset_type": metadata.get("asset_type"),
                    "price_band": self._get_price_band(metadata.get("list_price", 0)),
                    "sqft_band": self._get_sqft_band(metadata.get("sqft", 0)),
                    "list_price": metadata.get("list_price"),
                    "sqft": metadata.get("sqft"),
                    "address": metadata.get("address"),
                    "status": metadata.get("status", "active")
                }
            )
            points.append(point)

        # Batch upsert
        self.client.upsert(
            collection_name=self.COLLECTION_NAME,
            points=points
        )

        logger.info(f"Upserted {len(points)} properties")

    def search_similar(
        self,
        query_embedding: np.ndarray,
        tenant_id: UUID,
        limit: int = 20,
        market: Optional[str] = None,
        asset_type: Optional[str] = None,
        price_range: Optional[tuple] = None
    ) -> List[Dict]:
        """Search for similar properties with tenant filtering

        Args:
            query_embedding: Query embedding vector
            tenant_id: Tenant ID (REQUIRED for isolation)
            limit: Number of results
            market: Optional market filter
            asset_type: Optional asset type filter
            price_range: Optional (min, max) price filter

        Returns:
            List of similar properties with scores
        """

        # Build filter (ALWAYS include tenant_id)
        must_conditions = [
            FieldCondition(
                key="tenant_id",
                match=MatchValue(value=str(tenant_id))
            )
        ]

        # Add optional filters
        if market:
            must_conditions.append(
                FieldCondition(
                    key="market",
                    match=MatchValue(value=market)
                )
            )

        if asset_type:
            must_conditions.append(
                FieldCondition(
                    key="asset_type",
                    match=MatchValue(value=asset_type)
                )
            )

        if price_range:
            min_price, max_price = price_range
            must_conditions.append(
                FieldCondition(
                    key="list_price",
                    range=Range(gte=min_price, lte=max_price)
                )
            )

        # Search
        results = self.client.search(
            collection_name=self.COLLECTION_NAME,
            query_vector=query_embedding.tolist(),
            query_filter=Filter(must=must_conditions),
            limit=limit,
            with_payload=True,
            search_params=SearchParams(hnsw_ef=128, exact=False)
        )

        # Format results
        formatted_results = []
        for result in results:
            formatted_results.append({
                "property_id": result.id,
                "score": result.score,
                "payload": result.payload
            })

        logger.info(f"Found {len(formatted_results)} similar properties for tenant {tenant_id}")

        return formatted_results

    def delete_property(self, property_id: UUID):
        """Delete property from vector store"""

        self.client.delete(
            collection_name=self.COLLECTION_NAME,
            points_selector=[str(property_id)]
        )

        logger.info(f"Deleted property: {property_id}")

    def get_collection_info(self) -> Dict:
        """Get collection statistics"""

        info = self.client.get_collection(collection_name=self.COLLECTION_NAME)

        return {
            "name": self.COLLECTION_NAME,
            "vectors_count": info.vectors_count,
            "points_count": info.points_count,
            "status": info.status,
            "optimizer_status": info.optimizer_status
        }

    def _get_price_band(self, price: float) -> str:
        """Categorize price into band for filtering"""
        if price < 200000:
            return "under_200k"
        elif price < 400000:
            return "200k_400k"
        elif price < 600000:
            return "400k_600k"
        elif price < 1000000:
            return "600k_1m"
        else:
            return "over_1m"

    def _get_sqft_band(self, sqft: float) -> str:
        """Categorize sqft into band for filtering"""
        if sqft < 1000:
            return "under_1000"
        elif sqft < 1500:
            return "1000_1500"
        elif sqft < 2000:
            return "1500_2000"
        elif sqft < 3000:
            return "2000_3000"
        else:
            return "over_3000"
