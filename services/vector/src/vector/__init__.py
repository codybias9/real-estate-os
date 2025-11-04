"""
Vector Database Service

Qdrant integration for vector similarity search.

Use cases:
- Property similarity search
- Semantic search for memos and documents
- Recommendation systems
"""

from .client import VectorClient, get_vector_client, create_dummy_embedding

__all__ = [
    "VectorClient",
    "get_vector_client",
    "create_dummy_embedding",
]
