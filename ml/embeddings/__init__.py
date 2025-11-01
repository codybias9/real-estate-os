"""
Embedding Management

Integration with Qdrant vector database for similarity search.
Wave 2.2 - Implemented.
"""

from ml.embeddings.qdrant_client import (
    QdrantVectorDB,
    PropertyEmbedding,
    SimilarProperty
)
from ml.embeddings.indexer import PropertyEmbeddingIndexer
from ml.embeddings.similarity_service import SimilaritySearchService

__all__ = [
    'QdrantVectorDB',
    'PropertyEmbedding',
    'SimilarProperty',
    'PropertyEmbeddingIndexer',
    'SimilaritySearchService'
]
