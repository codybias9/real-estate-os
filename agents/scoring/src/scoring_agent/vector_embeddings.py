"""Vector embeddings for semantic property search

Uses Qdrant vector database for storing and searching property embeddings.
"""
import logging
from typing import List, Dict, Any, Optional
import uuid
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, Filter,
    FieldCondition, MatchValue, SearchParams
)
import numpy as np

logger = logging.getLogger(__name__)


class PropertyVectorStore:
    """
    Vector store for property embeddings using Qdrant

    Enables:
    - Semantic similarity search
    - Hybrid search (filters + vectors)
    - Property recommendations
    - Clustering and analysis
    """

    COLLECTION_NAME = "properties"
    VECTOR_SIZE = 35  # Size of our feature vector

    def __init__(
        self,
        qdrant_host: str = "localhost",
        qdrant_port: int = 6333,
        qdrant_url: Optional[str] = None
    ):
        """
        Initialize Qdrant client

        Args:
            qdrant_host: Qdrant server host
            qdrant_port: Qdrant server port
            qdrant_url: Full Qdrant URL (overrides host/port)
        """
        if qdrant_url:
            self.client = QdrantClient(url=qdrant_url)
        else:
            self.client = QdrantClient(host=qdrant_host, port=qdrant_port)

        self._ensure_collection_exists()

        logger.info(f"PropertyVectorStore initialized")

    def _ensure_collection_exists(self):
        """Create collection if it doesn't exist"""
        try:
            self.client.get_collection(self.COLLECTION_NAME)
            logger.info(f"Collection '{self.COLLECTION_NAME}' exists")
        except:
            # Collection doesn't exist, create it
            logger.info(f"Creating collection '{self.COLLECTION_NAME}'")

            self.client.create_collection(
                collection_name=self.COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=self.VECTOR_SIZE,
                    distance=Distance.COSINE  # Cosine similarity
                )
            )

            logger.info(f"Collection '{self.COLLECTION_NAME}' created")

    def store_property_vector(
        self,
        prospect_id: int,
        feature_vector: List[float],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Store property feature vector in Qdrant

        Args:
            prospect_id: Database prospect ID
            feature_vector: List of feature values
            metadata: Additional metadata to store with vector

        Returns:
            Point ID (UUID) in Qdrant
        """
        # Generate UUID for Qdrant point
        point_id = str(uuid.uuid4())

        # Prepare payload (metadata)
        payload = {
            "prospect_id": prospect_id,
            **(metadata or {})
        }

        # Create point
        point = PointStruct(
            id=point_id,
            vector=feature_vector,
            payload=payload
        )

        # Upsert to Qdrant
        self.client.upsert(
            collection_name=self.COLLECTION_NAME,
            points=[point]
        )

        logger.debug(f"Stored vector for prospect {prospect_id}: {point_id}")

        return point_id

    def search_similar_properties(
        self,
        feature_vector: List[float],
        limit: int = 10,
        score_threshold: Optional[float] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Find similar properties based on feature vector

        Args:
            feature_vector: Query feature vector
            limit: Maximum number of results
            score_threshold: Minimum similarity score (0-1)
            filters: Additional filters (e.g., {"state": "NV"})

        Returns:
            List of similar properties with scores
        """
        # Build filter if provided
        query_filter = None
        if filters:
            conditions = []
            for key, value in filters.items():
                conditions.append(
                    FieldCondition(
                        key=key,
                        match=MatchValue(value=value)
                    )
                )
            query_filter = Filter(must=conditions) if conditions else None

        # Search
        results = self.client.search(
            collection_name=self.COLLECTION_NAME,
            query_vector=feature_vector,
            limit=limit,
            score_threshold=score_threshold,
            query_filter=query_filter,
            with_payload=True
        )

        # Format results
        similar_properties = []
        for result in results:
            similar_properties.append({
                'point_id': result.id,
                'similarity_score': result.score,
                'prospect_id': result.payload.get('prospect_id'),
                'metadata': result.payload
            })

        logger.debug(f"Found {len(similar_properties)} similar properties")

        return similar_properties

    def get_property_vector(self, point_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve property vector and metadata by point ID

        Args:
            point_id: Qdrant point ID

        Returns:
            Dictionary with vector and payload
        """
        try:
            points = self.client.retrieve(
                collection_name=self.COLLECTION_NAME,
                ids=[point_id],
                with_vectors=True,
                with_payload=True
            )

            if points:
                point = points[0]
                return {
                    'point_id': point.id,
                    'vector': point.vector,
                    'payload': point.payload
                }

            return None

        except Exception as e:
            logger.error(f"Failed to retrieve point {point_id}: {e}")
            return None

    def delete_property_vector(self, point_id: str) -> bool:
        """
        Delete property vector from Qdrant

        Args:
            point_id: Qdrant point ID

        Returns:
            True if deleted successfully
        """
        try:
            self.client.delete(
                collection_name=self.COLLECTION_NAME,
                points_selector=[point_id]
            )

            logger.debug(f"Deleted vector {point_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete point {point_id}: {e}")
            return False

    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the collection

        Returns:
            Dictionary with collection stats
        """
        try:
            info = self.client.get_collection(self.COLLECTION_NAME)

            return {
                'total_points': info.points_count,
                'vector_size': info.config.params.vectors.size,
                'distance_metric': info.config.params.vectors.distance.name,
                'indexed': info.status.name
            }

        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {}


class PropertyEmbedder:
    """
    Creates embeddings for properties

    Currently uses feature vectors directly as embeddings.
    Future enhancements:
    - Text embeddings from descriptions (Sentence Transformers)
    - Image embeddings from property photos (ResNet, CLIP)
    - Hybrid embeddings (combine multiple modalities)
    """

    def __init__(self):
        pass

    def embed_property_features(self, feature_vector: List[float]) -> List[float]:
        """
        Create embedding from feature vector

        Currently this is a pass-through, but could be enhanced with:
        - Dimensionality reduction (PCA, UMAP)
        - Feature normalization
        - Learned embeddings (autoencoder)

        Args:
            feature_vector: Raw feature values

        Returns:
            Embedding vector
        """
        # Normalize features to [0, 1] range for better similarity search
        # This is a simple min-max normalization
        vector_array = np.array(feature_vector)

        # Avoid division by zero
        vector_min = vector_array.min()
        vector_max = vector_array.max()

        if vector_max > vector_min:
            normalized = (vector_array - vector_min) / (vector_max - vector_min)
        else:
            normalized = vector_array

        return normalized.tolist()

    def embed_property_text(self, description: str) -> List[float]:
        """
        Create embedding from property description text

        Future implementation with Sentence Transformers:
        - Use pre-trained model (all-MiniLM-L6-v2)
        - Generate 384-dimensional embeddings
        - Enable semantic search by description

        Args:
            description: Property description text

        Returns:
            Text embedding vector
        """
        # Placeholder for future implementation
        logger.warning("Text embeddings not yet implemented")
        return [0.0] * 384  # Standard sentence transformer size

    def embed_property_image(self, image_path: str) -> List[float]:
        """
        Create embedding from property image

        Future implementation with ResNet or CLIP:
        - Extract visual features
        - Enable search by similar appearance
        - Detect property condition

        Args:
            image_path: Path to property image

        Returns:
            Image embedding vector
        """
        # Placeholder for future implementation
        logger.warning("Image embeddings not yet implemented")
        return [0.0] * 512  # ResNet feature size

    def create_hybrid_embedding(
        self,
        feature_vector: List[float],
        description: Optional[str] = None,
        image_path: Optional[str] = None
    ) -> List[float]:
        """
        Create hybrid embedding combining multiple modalities

        Future enhancement: Concatenate or weight different embedding types

        Args:
            feature_vector: Numerical features
            description: Property description
            image_path: Property image

        Returns:
            Combined embedding vector
        """
        # For now, just use feature embedding
        return self.embed_property_features(feature_vector)
