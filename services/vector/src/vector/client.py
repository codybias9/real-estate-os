"""
Qdrant Vector Database Client

Smoke test implementation for vector similarity search.
Useful for property similarity, semantic search, and memo generation.
"""

import os
from typing import List, Optional, Dict, Any
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter
import numpy as np


class VectorClient:
    """
    Qdrant vector database client.

    Features:
    - Store and search property embeddings
    - Similarity search for property recommendations
    - Semantic search for memos and documents
    """

    def __init__(
        self,
        url: Optional[str] = None,
        api_key: Optional[str] = None,
        collection_name: str = "properties",
        vector_size: int = 384,  # all-MiniLM-L6-v2 size
    ):
        """
        Initialize Qdrant client.

        Args:
            url: Qdrant server URL (defaults to localhost)
            api_key: Qdrant API key (for cloud)
            collection_name: Name of the collection
            vector_size: Dimension of vectors
        """
        self.url = url or os.getenv("QDRANT_URL", "http://localhost:6333")
        self.api_key = api_key or os.getenv("QDRANT_API_KEY")
        self.collection_name = collection_name
        self.vector_size = vector_size

        # Initialize client
        if self.api_key:
            self.client = QdrantClient(url=self.url, api_key=self.api_key)
        else:
            self.client = QdrantClient(url=self.url)

    def create_collection(self, distance: str = "Cosine") -> bool:
        """
        Create a collection for storing vectors.

        Args:
            distance: Distance metric (Cosine, Euclidean, Dot)

        Returns:
            True if successful
        """
        try:
            # Map distance string to enum
            distance_map = {
                "Cosine": Distance.COSINE,
                "Euclidean": Distance.EUCLID,
                "Dot": Distance.DOT,
            }

            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size, distance=distance_map[distance]
                ),
            )
            return True

        except Exception as e:
            print(f"Error creating collection: {e}")
            return False

    def collection_exists(self) -> bool:
        """
        Check if collection exists.

        Returns:
            True if collection exists
        """
        try:
            collections = self.client.get_collections().collections
            return any(c.name == self.collection_name for c in collections)
        except Exception:
            return False

    def upsert_property(
        self,
        property_id: str,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Insert or update property embedding.

        Args:
            property_id: Unique property ID
            embedding: Vector embedding (list of floats)
            metadata: Additional property metadata

        Returns:
            True if successful
        """
        try:
            # Convert property_id to int hash for Qdrant point ID
            point_id = hash(property_id) % (10**8)

            point = PointStruct(
                id=point_id, vector=embedding, payload=metadata or {}
            )

            self.client.upsert(
                collection_name=self.collection_name, points=[point], wait=True
            )

            return True

        except Exception as e:
            print(f"Error upserting property: {e}")
            return False

    def search_similar(
        self,
        query_vector: List[float],
        limit: int = 10,
        score_threshold: Optional[float] = None,
        filter_conditions: Optional[Filter] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar properties.

        Args:
            query_vector: Query embedding vector
            limit: Maximum number of results
            score_threshold: Minimum similarity score
            filter_conditions: Qdrant filter conditions

        Returns:
            List of similar properties with scores
        """
        try:
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=limit,
                score_threshold=score_threshold,
                query_filter=filter_conditions,
            )

            return [
                {
                    "property_id": result.id,
                    "score": result.score,
                    "metadata": result.payload,
                }
                for result in results
            ]

        except Exception as e:
            print(f"Error searching: {e}")
            return []

    def get_property(self, property_id: str) -> Optional[Dict[str, Any]]:
        """
        Get property by ID.

        Args:
            property_id: Property ID

        Returns:
            Property data or None
        """
        try:
            point_id = hash(property_id) % (10**8)

            result = self.client.retrieve(
                collection_name=self.collection_name, ids=[point_id]
            )

            if result:
                return {
                    "property_id": result[0].id,
                    "vector": result[0].vector,
                    "metadata": result[0].payload,
                }

            return None

        except Exception as e:
            print(f"Error getting property: {e}")
            return None

    def delete_property(self, property_id: str) -> bool:
        """
        Delete property from collection.

        Args:
            property_id: Property ID

        Returns:
            True if successful
        """
        try:
            point_id = hash(property_id) % (10**8)

            self.client.delete(
                collection_name=self.collection_name, points_selector=[point_id]
            )

            return True

        except Exception as e:
            print(f"Error deleting property: {e}")
            return False

    def count(self) -> int:
        """
        Get number of vectors in collection.

        Returns:
            Count of vectors
        """
        try:
            info = self.client.get_collection(collection_name=self.collection_name)
            return info.points_count or 0
        except Exception:
            return 0

    def delete_collection(self) -> bool:
        """
        Delete collection (use with caution!).

        Returns:
            True if successful
        """
        try:
            self.client.delete_collection(collection_name=self.collection_name)
            return True
        except Exception as e:
            print(f"Error deleting collection: {e}")
            return False


def create_dummy_embedding(dim: int = 384) -> List[float]:
    """
    Create a dummy embedding for testing.

    In production, use a real embedding model like:
    - sentence-transformers/all-MiniLM-L6-v2
    - OpenAI ada-002
    - Cohere embed-v3

    Args:
        dim: Embedding dimension

    Returns:
        Random normalized vector
    """
    vec = np.random.randn(dim)
    vec = vec / np.linalg.norm(vec)  # Normalize
    return vec.tolist()


# Global client instance
_vector_client: Optional[VectorClient] = None


def get_vector_client(
    collection_name: str = "properties", vector_size: int = 384
) -> VectorClient:
    """
    Get global vector client instance.

    Args:
        collection_name: Collection name
        vector_size: Vector dimension

    Returns:
        VectorClient instance
    """
    global _vector_client

    if _vector_client is None:
        _vector_client = VectorClient(
            collection_name=collection_name, vector_size=vector_size
        )

    return _vector_client
