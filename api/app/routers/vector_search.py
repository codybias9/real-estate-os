"""Vector Search Router
Portfolio twin search using Qdrant
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel

from ..database import get_db
from ..auth.hybrid_dependencies import get_current_user
from ..auth.models import User
from ..vector.qdrant_client import PropertyVectorStore
import sys
sys.path.append('/home/user/real-estate-os')
from ml.embeddings.property_encoder import PropertyEmbedder

router = APIRouter(
    prefix="/vector",
    tags=["vector-search"]
)


# ============================================================================
# Models
# ============================================================================

class SimilarPropertiesRequest(BaseModel):
    """Request for similar properties search"""
    property_id: Optional[UUID] = None  # Find twins of this property
    market: Optional[str] = None
    asset_type: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    limit: int = 20


class SimilarPropertyResult(BaseModel):
    """Similar property result"""
    property_id: str
    score: float
    address: Optional[str]
    list_price: Optional[float]
    sqft: Optional[float]
    market: Optional[str]


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/search/similar", response_model=List[SimilarPropertyResult])
async def search_similar_properties(
    request: SimilarPropertiesRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Find similar properties (portfolio twins)

    Uses vector embeddings to find properties similar to:
    - A specific property (if property_id provided)
    - Or based on filters

    Args:
        request: Search request with property_id or filters
        user: Current authenticated user
        db: Database session

    Returns:
        List of similar properties with similarity scores
    """

    # Initialize services
    vector_store = PropertyVectorStore()
    embedder = PropertyEmbedder("ml/models/property_encoder_v1.pth")

    # Get query embedding
    if request.property_id:
        # Search for twins of a specific property
        from db.models_provenance import Property

        property = db.query(Property).filter(
            Property.id == request.property_id,
            Property.tenant_id == user.tenant_id
        ).first()

        if not property:
            raise HTTPException(status_code=404, detail="Property not found")

        # Generate embedding from property features
        features = {
            "sqft": property.sqft,
            "lot_size": property.lot_size or 0,
            "year_built": property.year_built,
            "bedrooms": property.bedrooms or 0,
            "bathrooms": property.bathrooms or 0,
            "list_price": property.list_price,
            "price_per_sqft": property.list_price / property.sqft if property.sqft else 0,
            "days_on_market": property.dom or 0,
            "cap_rate": property.cap_rate_estimate or 0,
            "latitude": property.latitude,
            "longitude": property.longitude,
            "condition_score": property.condition_score or 5.0,
            "flood_risk": property.flood_risk_score or 0,
            "wildfire_risk": property.wildfire_risk_score or 0,
            "walk_score": property.walk_score or 0
        }

        query_embedding = embedder.encode(features)

    else:
        # Generic search - use average embedding for tenant
        # (In practice, would use user preferences or past selections)
        raise HTTPException(
            status_code=400,
            detail="property_id is required for similarity search"
        )

    # Build price range filter
    price_range = None
    if request.min_price or request.max_price:
        price_range = (
            request.min_price or 0,
            request.max_price or float('inf')
        )

    # Search vector store
    results = vector_store.search_similar(
        query_embedding=query_embedding,
        tenant_id=user.tenant_id,
        limit=request.limit,
        market=request.market,
        asset_type=request.asset_type,
        price_range=price_range
    )

    # Format response
    response = []
    for result in results:
        response.append(SimilarPropertyResult(
            property_id=result["property_id"],
            score=result["score"],
            address=result["payload"].get("address"),
            list_price=result["payload"].get("list_price"),
            sqft=result["payload"].get("sqft"),
            market=result["payload"].get("market")
        ))

    return response


@router.get("/collection/info")
async def get_collection_info(
    user: User = Depends(get_current_user)
):
    """Get vector collection statistics

    Returns:
        Collection info with point count, status, etc.
    """

    vector_store = PropertyVectorStore()
    info = vector_store.get_collection_info()

    return info
