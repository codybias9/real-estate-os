"""
Property Twin Search API Router.

Endpoints for finding similar properties using vector similarity search.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import logging

from api.auth import get_current_user, TokenData
from api.database import get_db
from api.rate_limit import rate_limit
from ml.similarity.property_twin_search import (
    PropertyTwinSearch,
    PropertyFeatures,
    PropertyTwin
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/twins",
    tags=["Property Twin Search"]
)

# Initialize twin search engine
twin_search = PropertyTwinSearch()


# ============================================================================
# Request/Response Models
# ============================================================================

class TwinSearchRequest(BaseModel):
    """Request model for twin search."""
    # Location
    latitude: float = Field(..., description="Property latitude")
    longitude: float = Field(..., description="Property longitude")
    city: str = Field(..., description="City name")
    state: str = Field(..., description="State code")
    zip_code: str = Field(..., description="ZIP code")

    # Physical characteristics
    building_sqft: Optional[int] = Field(None, description="Building square footage")
    lot_size_sqft: Optional[int] = Field(None, description="Lot size square footage")
    year_built: Optional[int] = Field(None, description="Year built")
    bedrooms: Optional[int] = Field(None, description="Number of bedrooms")
    bathrooms: Optional[float] = Field(None, description="Number of bathrooms")
    stories: Optional[int] = Field(None, description="Number of stories")
    parking_spaces: Optional[int] = Field(None, description="Parking spaces")

    # Property type
    property_type: str = Field("Residential", description="Property type")

    # Financial
    purchase_price: Optional[float] = Field(None, description="Purchase price")
    monthly_rent: Optional[float] = Field(None, description="Monthly rent")
    property_tax_annual: Optional[float] = Field(None, description="Annual property tax")

    # Condition
    condition_score: Optional[float] = Field(None, description="Condition score (1-10)")

    # Hazards
    composite_hazard_score: Optional[float] = Field(None, description="Composite hazard score (0-1)")

    # Search parameters
    limit: int = Field(10, ge=1, le=50, description="Maximum results to return")

    # Filters
    min_price: Optional[float] = Field(None, description="Minimum price filter")
    max_price: Optional[float] = Field(None, description="Maximum price filter")
    filter_city: Optional[str] = Field(None, description="Filter by city")
    filter_property_type: Optional[str] = Field(None, description="Filter by property type")


class TwinSearchResponse(BaseModel):
    """Response model for twin search."""
    property_id: str
    similarity_score: float
    address: str
    city: str
    state: str
    building_sqft: Optional[int]
    purchase_price: Optional[float]
    distance_miles: Optional[float]
    feature_breakdown: dict


class IndexPropertyRequest(BaseModel):
    """Request model for indexing a property."""
    property_id: str

    # Location
    latitude: float
    longitude: float
    city: str
    state: str
    zip_code: str

    # Physical
    building_sqft: Optional[int] = None
    lot_size_sqft: Optional[int] = None
    year_built: Optional[int] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[float] = None
    stories: Optional[int] = None
    parking_spaces: Optional[int] = None

    # Type and financial
    property_type: str = "Residential"
    purchase_price: Optional[float] = None
    monthly_rent: Optional[float] = None
    property_tax_annual: Optional[float] = None

    # Condition and hazards
    condition_score: Optional[float] = None
    composite_hazard_score: Optional[float] = None


class IndexPropertyResponse(BaseModel):
    """Response model for property indexing."""
    property_id: str
    status: str
    embedding_dimensions: int
    indexed_at: datetime


class TwinSearchSummaryResponse(BaseModel):
    """Summary response with twins."""
    subject_property: dict
    twins_found: int
    twins: List[TwinSearchResponse]
    search_timestamp: datetime


# ============================================================================
# Endpoints
# ============================================================================

@router.post(
    "/search",
    response_model=TwinSearchSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Search for property twins",
    description="Find similar properties using vector similarity search"
)
@rate_limit(requests_per_minute=20)
async def search_property_twins(
    request: TwinSearchRequest,
    user: TokenData = Depends(get_current_user)
):
    """
    Search for property twins (similar properties).

    Uses vector embeddings and similarity search to find properties with
    similar characteristics. Returns ranked results with similarity scores
    and feature-level explanations.

    **Search Parameters:**
    - Subject property features (location, physical, financial, condition)
    - Optional filters (price range, location, property type)
    - Result limit (1-50 properties)

    **Returns:**
    - List of similar properties with similarity scores (0-1)
    - Distance from subject property
    - Feature-level breakdown showing what drives similarity

    **Use Cases:**
    - Comparable property analysis
    - Market research
    - Portfolio analysis
    - Investment opportunity discovery
    """
    logger.info(f"Twin search request from user {user.user_id} for {request.city}, {request.state}")

    try:
        # Convert request to PropertyFeatures
        features = PropertyFeatures(
            latitude=request.latitude,
            longitude=request.longitude,
            city=request.city,
            state=request.state,
            zip_code=request.zip_code,
            building_sqft=request.building_sqft,
            lot_size_sqft=request.lot_size_sqft,
            year_built=request.year_built,
            bedrooms=request.bedrooms,
            bathrooms=request.bathrooms,
            stories=request.stories,
            parking_spaces=request.parking_spaces,
            property_type=request.property_type,
            purchase_price=request.purchase_price,
            monthly_rent=request.monthly_rent,
            property_tax_annual=request.property_tax_annual,
            condition_score=request.condition_score,
            composite_hazard_score=request.composite_hazard_score
        )

        # Build filters
        filters = {}
        if request.min_price:
            filters["min_price"] = request.min_price
        if request.max_price:
            filters["max_price"] = request.max_price
        if request.filter_city:
            filters["city"] = request.filter_city
        if request.filter_property_type:
            filters["property_type"] = request.filter_property_type

        # Execute search
        twins = twin_search.search_twins(
            subject_features=features,
            limit=request.limit,
            filters=filters if filters else None
        )

        # Convert to response models
        twin_responses = [
            TwinSearchResponse(
                property_id=twin.property_id,
                similarity_score=twin.similarity_score,
                address=twin.address,
                city=twin.city,
                state=twin.state,
                building_sqft=twin.building_sqft,
                purchase_price=twin.purchase_price,
                distance_miles=twin.distance_miles,
                feature_breakdown=twin.feature_breakdown
            )
            for twin in twins
        ]

        logger.info(f"Found {len(twins)} twins with avg similarity {sum(t.similarity_score for t in twins) / len(twins):.2%}")

        return TwinSearchSummaryResponse(
            subject_property={
                "city": request.city,
                "state": request.state,
                "building_sqft": request.building_sqft,
                "purchase_price": request.purchase_price,
                "property_type": request.property_type
            },
            twins_found=len(twins),
            twins=twin_responses,
            search_timestamp=datetime.utcnow()
        )

    except Exception as e:
        logger.error(f"Twin search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Twin search failed: {str(e)}"
        )


@router.post(
    "/index",
    response_model=IndexPropertyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Index a property for twin search",
    description="Add a property to the twin search index"
)
@rate_limit(requests_per_minute=100)
async def index_property(
    request: IndexPropertyRequest,
    user: TokenData = Depends(get_current_user)
):
    """
    Index a property for twin search.

    Generates vector embedding from property features and stores in
    Qdrant vector database for similarity search.

    **Process:**
    1. Convert property features to 128-dimensional embedding
    2. Store embedding in Qdrant with property metadata
    3. Return indexing confirmation

    **Note:** Properties are automatically indexed when created via the
    properties API. This endpoint is for manual indexing or re-indexing.
    """
    logger.info(f"Indexing property {request.property_id} for user {user.user_id}")

    try:
        # Convert request to PropertyFeatures
        features = PropertyFeatures(
            latitude=request.latitude,
            longitude=request.longitude,
            city=request.city,
            state=request.state,
            zip_code=request.zip_code,
            building_sqft=request.building_sqft,
            lot_size_sqft=request.lot_size_sqft,
            year_built=request.year_built,
            bedrooms=request.bedrooms,
            bathrooms=request.bathrooms,
            stories=request.stories,
            parking_spaces=request.parking_spaces,
            property_type=request.property_type,
            purchase_price=request.purchase_price,
            monthly_rent=request.monthly_rent,
            property_tax_annual=request.property_tax_annual,
            condition_score=request.condition_score,
            composite_hazard_score=request.composite_hazard_score
        )

        # Index property
        twin_search.index_property(
            property_id=request.property_id,
            features=features
        )

        logger.info(f"Successfully indexed property {request.property_id}")

        return IndexPropertyResponse(
            property_id=request.property_id,
            status="indexed",
            embedding_dimensions=128,
            indexed_at=datetime.utcnow()
        )

    except Exception as e:
        logger.error(f"Property indexing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Property indexing failed: {str(e)}"
        )


@router.get(
    "/status",
    summary="Get twin search index status",
    description="Get status and statistics of the twin search index"
)
@rate_limit(requests_per_minute=60)
async def get_index_status(
    user: TokenData = Depends(get_current_user)
):
    """
    Get twin search index status.

    Returns statistics about the vector database:
    - Total properties indexed
    - Embedding dimensions
    - Last update time
    - Index health
    """
    logger.info(f"Index status request from user {user.user_id}")

    # In production, query Qdrant for collection stats
    # from qdrant_client import QdrantClient
    # client = QdrantClient(twin_search.qdrant_url)
    # collection_info = client.get_collection(twin_search.collection_name)

    return {
        "status": "operational",
        "collection_name": twin_search.collection_name,
        "embedding_dimensions": 128,
        "properties_indexed": "N/A (mock)",
        "last_updated": datetime.utcnow(),
        "index_type": "Qdrant HNSW",
        "similarity_metric": "cosine"
    }
