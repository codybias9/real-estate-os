"""
Similarity Search Service

FastAPI endpoints for property similarity search using Qdrant.

Endpoints:
- POST /search/similar - Find similar properties to query embedding
- GET /search/look-alikes/{property_id} - Find properties similar to a given property
- POST /search/recommend-for-user - Get personalized recommendations

Part of Wave 2.2 - Qdrant similarity search.
"""

from fastapi import FastAPI, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
import numpy as np
from uuid import UUID
import logging

from ml.embeddings.qdrant_client import QdrantVectorDB, SimilarProperty
from ml.serving.portfolio_twin_service import PortfolioTwinService


logger = logging.getLogger(__name__)


# Request/Response models
class SimilaritySearchRequest(BaseModel):
    """Request for similarity search"""
    query_embedding: List[float] = Field(..., min_items=16, max_items=16)
    top_k: int = Field(default=10, ge=1, le=100)
    filters: Optional[Dict] = None

    class Config:
        schema_extra = {
            "example": {
                "query_embedding": [0.1] * 16,
                "top_k": 10,
                "filters": {
                    "property_type": "Single Family",
                    "zipcode": "94102"
                }
            }
        }


class SimilarPropertyResponse(BaseModel):
    """Similar property result"""
    property_id: str
    similarity_score: float = Field(..., ge=0.0, le=1.0)
    listing_price: Optional[float] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[float] = None
    property_type: Optional[str] = None
    zipcode: Optional[str] = None


class SimilaritySearchResponse(BaseModel):
    """Response with similar properties"""
    results: List[SimilarPropertyResponse]
    total_results: int


class LookAlikesRequest(BaseModel):
    """Request for look-alike properties"""
    property_id: str
    top_k: int = Field(default=10, ge=1, le=100)
    filters: Optional[Dict] = None


class UserRecommendationRequest(BaseModel):
    """Request for user-specific recommendations"""
    user_id: int
    candidate_property_ids: Optional[List[str]] = None
    top_k: int = Field(default=10, ge=1, le=100)
    filters: Optional[Dict] = None


class UserRecommendationResponse(BaseModel):
    """Response with user recommendations"""
    user_id: int
    recommendations: List[SimilarPropertyResponse]


# Similarity Search Service
class SimilaritySearchService:
    """
    Service for property similarity search

    Combines Qdrant vector search with Portfolio Twin user preferences.
    """

    def __init__(
        self,
        qdrant_host: str = "localhost",
        qdrant_port: int = 6333,
        portfolio_twin: Optional[PortfolioTwinService] = None
    ):
        """
        Initialize service

        Args:
            qdrant_host: Qdrant server host
            qdrant_port: Qdrant server port
            portfolio_twin: Portfolio Twin service for user recommendations
        """
        self.qdrant = QdrantVectorDB(host=qdrant_host, port=qdrant_port)
        self.portfolio_twin = portfolio_twin

        logger.info("Similarity search service initialized")

    def search_similar(
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
            tenant_id: Tenant ID
            top_k: Number of results
            filters: Optional filters

        Returns:
            List of similar properties
        """
        return self.qdrant.search_similar_properties(
            query_embedding=query_embedding,
            tenant_id=tenant_id,
            top_k=top_k,
            filters=filters
        )

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
            top_k: Number of results
            filters: Optional filters

        Returns:
            List of similar properties
        """
        return self.qdrant.find_look_alikes(
            property_id=property_id,
            tenant_id=tenant_id,
            top_k=top_k,
            filters=filters
        )

    def recommend_for_user(
        self,
        user_id: int,
        tenant_id: str,
        candidate_property_ids: Optional[List[str]] = None,
        top_k: int = 10,
        filters: Optional[Dict] = None
    ) -> List[SimilarProperty]:
        """
        Get personalized property recommendations for user

        Combines user preferences (Portfolio Twin) with vector similarity.

        Args:
            user_id: User ID
            tenant_id: Tenant ID
            candidate_property_ids: Optional list of candidate properties
            top_k: Number of recommendations
            filters: Optional filters

        Returns:
            List of recommended properties
        """
        if self.portfolio_twin is None:
            raise ValueError("Portfolio Twin service not available")

        # TODO: Get user embedding from Portfolio Twin
        # For now, use a placeholder approach:
        # 1. If candidate_property_ids provided, score them with Portfolio Twin
        # 2. Otherwise, do vector search with user's average liked property embedding

        # Placeholder: Just return similar properties
        # In production, this would:
        # - Get user's learned embedding from Portfolio Twin
        # - Search Qdrant with that embedding
        # - Re-rank results with Portfolio Twin affinity scores

        logger.warning("User-specific recommendations not fully implemented yet")

        return []


# FastAPI app
app = FastAPI(
    title="Property Similarity Search",
    description="Vector similarity search for properties using Qdrant",
    version="1.0.0"
)

# Global service instance
service: Optional[SimilaritySearchService] = None


@app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    global service

    try:
        # Create service
        service = SimilaritySearchService(
            qdrant_host="localhost",
            qdrant_port=6333
        )

        # Try to load Portfolio Twin
        try:
            from ml.serving.portfolio_twin_service import PortfolioTwinService
            from pathlib import Path

            model_path = Path("ml/serving/models/portfolio_twin.pt")
            if model_path.exists():
                portfolio_twin = PortfolioTwinService(str(model_path))
                service.portfolio_twin = portfolio_twin
                logger.info("Loaded Portfolio Twin for user recommendations")
        except Exception as e:
            logger.warning(f"Could not load Portfolio Twin: {e}")

        logger.info("Similarity search service started")
    except Exception as e:
        logger.error(f"Failed to start service: {e}")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy" if service is not None else "not_initialized",
        "service": "similarity_search",
        "version": "1.0.0"
    }


@app.post("/search/similar", response_model=SimilaritySearchResponse)
async def search_similar(
    request: SimilaritySearchRequest,
    tenant_id: UUID = Query(..., description="Tenant ID")
):
    """
    Search for similar properties using query embedding

    Useful for:
    - Finding properties similar to an embedding
    - Custom similarity queries
    """
    if service is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    try:
        query_emb = np.array(request.query_embedding, dtype=np.float32)

        results = service.search_similar(
            query_embedding=query_emb,
            tenant_id=str(tenant_id),
            top_k=request.top_k,
            filters=request.filters
        )

        # Format response
        similar_properties = [
            SimilarPropertyResponse(
                property_id=r.property_id,
                similarity_score=r.similarity_score,
                listing_price=r.metadata.get('listing_price'),
                bedrooms=r.metadata.get('bedrooms'),
                bathrooms=r.metadata.get('bathrooms'),
                property_type=r.metadata.get('property_type'),
                zipcode=r.metadata.get('zipcode')
            )
            for r in results
        ]

        return SimilaritySearchResponse(
            results=similar_properties,
            total_results=len(similar_properties)
        )
    except Exception as e:
        logger.error(f"Similarity search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/search/look-alikes/{property_id}", response_model=SimilaritySearchResponse)
async def get_look_alikes(
    property_id: str,
    tenant_id: UUID = Query(..., description="Tenant ID"),
    top_k: int = Query(10, ge=1, le=100, description="Number of results"),
    property_type: Optional[str] = Query(None, description="Filter by property type"),
    zipcode: Optional[str] = Query(None, description="Filter by zipcode")
):
    """
    Find properties similar to a given property

    Great for:
    - "Properties like this one"
    - Comp analysis
    - Portfolio diversification
    """
    if service is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    try:
        # Build filters
        filters = {}
        if property_type:
            filters['property_type'] = property_type
        if zipcode:
            filters['zipcode'] = zipcode

        results = service.find_look_alikes(
            property_id=property_id,
            tenant_id=str(tenant_id),
            top_k=top_k,
            filters=filters if filters else None
        )

        # Format response
        similar_properties = [
            SimilarPropertyResponse(
                property_id=r.property_id,
                similarity_score=r.similarity_score,
                listing_price=r.metadata.get('listing_price'),
                bedrooms=r.metadata.get('bedrooms'),
                bathrooms=r.metadata.get('bathrooms'),
                property_type=r.metadata.get('property_type'),
                zipcode=r.metadata.get('zipcode')
            )
            for r in results
        ]

        return SimilaritySearchResponse(
            results=similar_properties,
            total_results=len(similar_properties)
        )
    except Exception as e:
        logger.error(f"Look-alikes search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search/recommend", response_model=UserRecommendationResponse)
async def recommend_for_user(
    request: UserRecommendationRequest,
    tenant_id: UUID = Query(..., description="Tenant ID")
):
    """
    Get personalized property recommendations for user

    Combines:
    - User's learned preferences (Portfolio Twin)
    - Vector similarity (Qdrant)
    - Optional filters

    Returns properties ranked by user affinity.
    """
    if service is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    try:
        results = service.recommend_for_user(
            user_id=request.user_id,
            tenant_id=str(tenant_id),
            candidate_property_ids=request.candidate_property_ids,
            top_k=request.top_k,
            filters=request.filters
        )

        # Format response
        recommendations = [
            SimilarPropertyResponse(
                property_id=r.property_id,
                similarity_score=r.similarity_score,
                listing_price=r.metadata.get('listing_price'),
                bedrooms=r.metadata.get('bedrooms'),
                bathrooms=r.metadata.get('bathrooms'),
                property_type=r.metadata.get('property_type'),
                zipcode=r.metadata.get('zipcode')
            )
            for r in results
        ]

        return UserRecommendationResponse(
            user_id=request.user_id,
            recommendations=recommendations
        )
    except Exception as e:
        logger.error(f"User recommendation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
