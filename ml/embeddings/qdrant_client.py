"""
Qdrant Vector Database Client

Client for managing property embeddings in Qdrant.

Collections:
- property_embeddings: Property vectors from Portfolio Twin encoder
- user_embeddings: User preference vectors (optional)

Part of Wave 2.2 - Qdrant vector database integration.
"""

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    SearchParams
)
from typing import List, Dict, Optional, Tuple
import numpy as np
from uuid import UUID
import logging
from dataclasses import dataclass


logger = logging.getLogger(__name__)


@dataclass
class PropertyEmbedding:
    """Property embedding with metadata"""
    property_id: str
    embedding: np.ndarray
    tenant_id: str
    listing_price: Optional[float] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[float] = None
    property_type: Optional[str] = None
    zipcode: Optional[str] = None
    confidence: float = 1.0


@dataclass
class SimilarProperty:
    """Similar property result"""
    property_id: str
    similarity_score: float
    metadata: Dict


class QdrantVectorDB:
    """
    Qdrant vector database client

    Manages property and user embeddings with efficient similarity search.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6333,
        grpc_port: int = 6334,
        prefer_grpc: bool = True,
        api_key: Optional[str] = None
    ):
        """
        Initialize Qdrant client

        Args:
            host: Qdrant server host
            port: HTTP API port
            grpc_port: gRPC port (faster)
            prefer_grpc: Use gRPC if available
            api_key: API key for Qdrant Cloud (optional)
        """
        self.client = QdrantClient(
            host=host,
            port=port,
            grpc_port=grpc_port,
            prefer_grpc=prefer_grpc,
            api_key=api_key
        )

        logger.info(f"Connected to Qdrant at {host}:{port}")

        # Collection names
        self.PROPERTY_COLLECTION = "property_embeddings"
        self.USER_COLLECTION = "user_embeddings"

    def create_collections(
        self,
        embedding_dim: int = 16,
        recreate: bool = False
    ):
        """
        Create Qdrant collections

        Args:
            embedding_dim: Dimension of embeddings
            recreate: If True, delete and recreate existing collections
        """
        # Property embeddings collection
        if recreate or not self.client.collection_exists(self.PROPERTY_COLLECTION):
            if recreate and self.client.collection_exists(self.PROPERTY_COLLECTION):
                self.client.delete_collection(self.PROPERTY_COLLECTION)
                logger.info(f"Deleted existing collection: {self.PROPERTY_COLLECTION}")

            self.client.create_collection(
                collection_name=self.PROPERTY_COLLECTION,
                vectors_config=VectorParams(
                    size=embedding_dim,
                    distance=Distance.COSINE  # Cosine similarity
                )
            )
            logger.info(f"Created collection: {self.PROPERTY_COLLECTION}")

            # Create payload indexes for filtering
            self.client.create_payload_index(
                collection_name=self.PROPERTY_COLLECTION,
                field_name="tenant_id",
                field_schema="keyword"
            )
            self.client.create_payload_index(
                collection_name=self.PROPERTY_COLLECTION,
                field_name="property_type",
                field_schema="keyword"
            )
            self.client.create_payload_index(
                collection_name=self.PROPERTY_COLLECTION,
                field_name="zipcode",
                field_schema="keyword"
            )
            self.client.create_payload_index(
                collection_name=self.PROPERTY_COLLECTION,
                field_name="listing_price",
                field_schema="float"
            )

            logger.info("Created payload indexes for filtering")

        # User embeddings collection
        if recreate or not self.client.collection_exists(self.USER_COLLECTION):
            if recreate and self.client.collection_exists(self.USER_COLLECTION):
                self.client.delete_collection(self.USER_COLLECTION)
                logger.info(f"Deleted existing collection: {self.USER_COLLECTION}")

            self.client.create_collection(
                collection_name=self.USER_COLLECTION,
                vectors_config=VectorParams(
                    size=embedding_dim,
                    distance=Distance.COSINE
                )
            )
            logger.info(f"Created collection: {self.USER_COLLECTION}")

            self.client.create_payload_index(
                collection_name=self.USER_COLLECTION,
                field_name="tenant_id",
                field_schema="keyword"
            )

    def index_property(
        self,
        property_embedding: PropertyEmbedding
    ) -> str:
        """
        Index a single property embedding

        Args:
            property_embedding: Property embedding with metadata

        Returns:
            Point ID (property_id)
        """
        # Prepare payload (metadata)
        payload = {
            "property_id": property_embedding.property_id,
            "tenant_id": property_embedding.tenant_id,
            "confidence": property_embedding.confidence
        }

        # Add optional fields
        if property_embedding.listing_price is not None:
            payload["listing_price"] = float(property_embedding.listing_price)
        if property_embedding.bedrooms is not None:
            payload["bedrooms"] = int(property_embedding.bedrooms)
        if property_embedding.bathrooms is not None:
            payload["bathrooms"] = float(property_embedding.bathrooms)
        if property_embedding.property_type:
            payload["property_type"] = property_embedding.property_type
        if property_embedding.zipcode:
            payload["zipcode"] = property_embedding.zipcode

        # Create point
        point = PointStruct(
            id=property_embedding.property_id,
            vector=property_embedding.embedding.tolist(),
            payload=payload
        )

        # Upsert (insert or update)
        self.client.upsert(
            collection_name=self.PROPERTY_COLLECTION,
            points=[point]
        )

        return property_embedding.property_id

    def index_properties_batch(
        self,
        property_embeddings: List[PropertyEmbedding],
        batch_size: int = 100
    ) -> int:
        """
        Index multiple property embeddings in batches

        Args:
            property_embeddings: List of property embeddings
            batch_size: Batch size for upserting

        Returns:
            Number of properties indexed
        """
        total_indexed = 0

        for i in range(0, len(property_embeddings), batch_size):
            batch = property_embeddings[i:i + batch_size]

            # Prepare points
            points = []
            for prop_emb in batch:
                payload = {
                    "property_id": prop_emb.property_id,
                    "tenant_id": prop_emb.tenant_id,
                    "confidence": prop_emb.confidence
                }

                if prop_emb.listing_price is not None:
                    payload["listing_price"] = float(prop_emb.listing_price)
                if prop_emb.bedrooms is not None:
                    payload["bedrooms"] = int(prop_emb.bedrooms)
                if prop_emb.bathrooms is not None:
                    payload["bathrooms"] = float(prop_emb.bathrooms)
                if prop_emb.property_type:
                    payload["property_type"] = prop_emb.property_type
                if prop_emb.zipcode:
                    payload["zipcode"] = prop_emb.zipcode

                point = PointStruct(
                    id=prop_emb.property_id,
                    vector=prop_emb.embedding.tolist(),
                    payload=payload
                )
                points.append(point)

            # Upsert batch
            self.client.upsert(
                collection_name=self.PROPERTY_COLLECTION,
                points=points
            )

            total_indexed += len(batch)
            logger.info(f"Indexed {total_indexed}/{len(property_embeddings)} properties")

        return total_indexed

    def search_similar_properties(
        self,
        query_embedding: np.ndarray,
        tenant_id: str,
        top_k: int = 10,
        filters: Optional[Dict] = None
    ) -> List[SimilarProperty]:
        """
        Search for similar properties

        Args:
            query_embedding: Query vector
            tenant_id: Tenant ID for filtering
            top_k: Number of results
            filters: Optional filters (property_type, zipcode, price_range, etc.)

        Returns:
            List of similar properties with scores
        """
        # Build filter conditions
        filter_conditions = [
            FieldCondition(
                key="tenant_id",
                match=MatchValue(value=tenant_id)
            )
        ]

        # Add optional filters
        if filters:
            if "property_type" in filters:
                filter_conditions.append(
                    FieldCondition(
                        key="property_type",
                        match=MatchValue(value=filters["property_type"])
                    )
                )
            if "zipcode" in filters:
                filter_conditions.append(
                    FieldCondition(
                        key="zipcode",
                        match=MatchValue(value=filters["zipcode"])
                    )
                )
            # TODO: Add range filters for price, bedrooms, etc.

        # Create filter
        search_filter = Filter(must=filter_conditions) if filter_conditions else None

        # Search
        results = self.client.search(
            collection_name=self.PROPERTY_COLLECTION,
            query_vector=query_embedding.tolist(),
            query_filter=search_filter,
            limit=top_k
        )

        # Parse results
        similar_properties = []
        for result in results:
            similar_properties.append(SimilarProperty(
                property_id=result.id,
                similarity_score=result.score,
                metadata=result.payload
            ))

        return similar_properties

    def find_look_alikes(
        self,
        property_id: str,
        tenant_id: str,
        top_k: int = 10,
        filters: Optional[Dict] = None
    ) -> List[SimilarProperty]:
        """
        Find properties similar to a given property

        Args:
            property_id: Reference property ID
            tenant_id: Tenant ID
            top_k: Number of results (excludes the query property)
            filters: Optional filters

        Returns:
            List of similar properties
        """
        # Retrieve the property's embedding
        try:
            point = self.client.retrieve(
                collection_name=self.PROPERTY_COLLECTION,
                ids=[property_id]
            )

            if not point:
                logger.warning(f"Property {property_id} not found in Qdrant")
                return []

            query_embedding = np.array(point[0].vector)

            # Search (top_k + 1 to exclude self)
            results = self.search_similar_properties(
                query_embedding=query_embedding,
                tenant_id=tenant_id,
                top_k=top_k + 1,
                filters=filters
            )

            # Remove the query property itself
            results = [r for r in results if r.property_id != property_id][:top_k]

            return results

        except Exception as e:
            logger.error(f"Error finding look-alikes: {e}")
            return []

    def delete_property(self, property_id: str):
        """Delete a property embedding"""
        self.client.delete(
            collection_name=self.PROPERTY_COLLECTION,
            points_selector=[property_id]
        )
        logger.info(f"Deleted property {property_id} from Qdrant")

    def get_collection_info(self, collection_name: str) -> Dict:
        """Get collection statistics"""
        info = self.client.get_collection(collection_name)
        return {
            "vectors_count": info.vectors_count,
            "indexed_vectors_count": info.indexed_vectors_count,
            "points_count": info.points_count,
            "status": info.status
        }

    def scroll_properties(
        self,
        tenant_id: str,
        batch_size: int = 100,
        offset: Optional[str] = None
    ) -> Tuple[List[Dict], Optional[str]]:
        """
        Scroll through properties (pagination)

        Args:
            tenant_id: Tenant ID
            batch_size: Number of results per page
            offset: Pagination offset

        Returns:
            (properties, next_offset)
        """
        filter_condition = Filter(
            must=[
                FieldCondition(
                    key="tenant_id",
                    match=MatchValue(value=tenant_id)
                )
            ]
        )

        results, next_offset = self.client.scroll(
            collection_name=self.PROPERTY_COLLECTION,
            scroll_filter=filter_condition,
            limit=batch_size,
            offset=offset
        )

        properties = [
            {
                "property_id": result.id,
                **result.payload
            }
            for result in results
        ]

        return properties, next_offset
