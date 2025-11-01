"""
Comp-Critic Service

FastAPI service for comparative market analysis and negotiation leverage.

Endpoints:
- POST /analyze/comp-critic - Full comp analysis
- GET /analyze/{property_id}/leverage - Negotiation leverage score
- GET /analyze/{property_id}/market-position - Market position

Part of Wave 3.1 - Comp-Critic service.
"""

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Tuple
from uuid import UUID
import logging

from ml.models.comp_critic import (
    CompCriticAnalyzer,
    ComparableProperty,
    CompAnalysis,
    MarketPosition,
    NegotiationStrategy
)
from ml.embeddings.qdrant_client import QdrantVectorDB
from ml.models.portfolio_twin import PropertyFeatures


logger = logging.getLogger(__name__)


# Request/Response models
class CompAnalysisRequest(BaseModel):
    """Request for comp analysis"""
    property_id: str
    top_k: int = Field(default=20, ge=5, le=50, description="Number of comps to analyze")
    property_type: Optional[str] = Field(None, description="Filter comps by property type")
    zipcode: Optional[str] = Field(None, description="Filter comps by zipcode")

    class Config:
        schema_extra = {
            "example": {
                "property_id": "123e4567-e89b-12d3-a456-426614174000",
                "top_k": 20,
                "property_type": "Single Family"
            }
        }


class ComparablePropertyResponse(BaseModel):
    """Comparable property in response"""
    property_id: str
    similarity_score: float
    listing_price: float
    price_per_sqft: float
    bedrooms: int
    bathrooms: float
    square_footage: int
    days_on_market: int
    property_type: str
    leverage_contribution: Optional[float] = None


class CompAnalysisResponse(BaseModel):
    """Response with full comp analysis"""
    property_id: str
    subject_price: float
    subject_price_per_sqft: float

    # Comp statistics
    num_comps: int
    avg_comp_price: float
    avg_comp_price_per_sqft: float
    median_comp_price: float
    median_comp_price_per_sqft: float

    # Market position
    market_position: str  # overvalued/fairly_valued/undervalued
    price_deviation_percent: float
    price_deviation_std_dev: float

    # Negotiation
    negotiation_leverage: float
    negotiation_strategy: str  # aggressive/moderate/cautious
    recommended_offer_range: Tuple[float, float]

    # Comps
    comps: List[ComparablePropertyResponse]
    outlier_comps: List[ComparablePropertyResponse]

    # Recommendations
    recommendations: List[str]
    risk_factors: List[str]
    opportunities: List[str]


class LeverageScoreResponse(BaseModel):
    """Quick leverage score response"""
    property_id: str
    negotiation_leverage: float
    negotiation_strategy: str
    recommended_discount_percent: float


class MarketPositionResponse(BaseModel):
    """Market position response"""
    property_id: str
    market_position: str
    price_deviation_percent: float
    is_good_deal: bool


# Comp-Critic Service
class CompCriticService:
    """
    Service for comparative market analysis

    Integrates with Qdrant for finding comps and Portfolio Twin for
    property features.
    """

    def __init__(
        self,
        qdrant_host: str = "localhost",
        qdrant_port: int = 6333
    ):
        """Initialize service"""
        self.qdrant = QdrantVectorDB(host=qdrant_host, port=qdrant_port)
        self.analyzer = CompCriticAnalyzer(
            min_comps=5,
            max_comps=20,
            min_similarity=0.6
        )

        logger.info("Comp-Critic service initialized")

    def _convert_similar_to_comparable(
        self,
        similar_property: 'SimilarProperty'
    ) -> ComparableProperty:
        """Convert Qdrant SimilarProperty to ComparableProperty"""
        metadata = similar_property.metadata

        return ComparableProperty(
            property_id=similar_property.property_id,
            similarity_score=similar_property.similarity_score,
            listing_price=metadata.get('listing_price', 0),
            price_per_sqft=metadata.get('listing_price', 0) / max(metadata.get('square_footage', 1), 1),
            bedrooms=metadata.get('bedrooms', 3),
            bathrooms=metadata.get('bathrooms', 2.0),
            square_footage=metadata.get('square_footage', 2000),
            days_on_market=metadata.get('days_on_market', 0),
            property_type=metadata.get('property_type', 'Unknown')
        )

    def analyze_property(
        self,
        property_id: str,
        tenant_id: str,
        subject_data: Dict,
        top_k: int = 20,
        property_type: Optional[str] = None,
        zipcode: Optional[str] = None
    ) -> CompAnalysis:
        """
        Perform comp analysis on property

        Args:
            property_id: Property ID
            tenant_id: Tenant ID
            subject_data: Subject property data (price, sqft, etc.)
            top_k: Number of comps to analyze
            property_type: Optional property type filter
            zipcode: Optional zipcode filter

        Returns:
            CompAnalysis with market position and recommendations
        """
        # Build filters
        filters = {}
        if property_type:
            filters['property_type'] = property_type
        if zipcode:
            filters['zipcode'] = zipcode

        # Find similar properties from Qdrant
        similar_properties = self.qdrant.find_look_alikes(
            property_id=property_id,
            tenant_id=tenant_id,
            top_k=top_k,
            filters=filters if filters else None
        )

        if not similar_properties:
            raise ValueError("No comparable properties found")

        # Convert to ComparableProperty objects
        comps = [self._convert_similar_to_comparable(sp) for sp in similar_properties]

        # Create subject property
        subject = ComparableProperty(
            property_id=property_id,
            similarity_score=1.0,
            listing_price=subject_data.get('listing_price', 0),
            price_per_sqft=subject_data.get('listing_price', 0) / max(subject_data.get('square_footage', 1), 1),
            bedrooms=subject_data.get('bedrooms', 3),
            bathrooms=subject_data.get('bathrooms', 2.0),
            square_footage=subject_data.get('square_footage', 2000),
            days_on_market=subject_data.get('days_on_market', 0),
            property_type=subject_data.get('property_type', 'Unknown')
        )

        # Run analysis
        analysis = self.analyzer.analyze(
            subject_property=subject,
            comparable_properties=comps
        )

        return analysis

    def get_leverage_score(
        self,
        property_id: str,
        tenant_id: str,
        subject_data: Dict
    ) -> Dict:
        """Get quick leverage score"""
        analysis = self.analyze_property(
            property_id=property_id,
            tenant_id=tenant_id,
            subject_data=subject_data,
            top_k=10  # Quick analysis with fewer comps
        )

        # Calculate discount based on market position
        if analysis.market_position == MarketPosition.OVERVALUED:
            discount = abs(analysis.price_deviation_percent)
        elif analysis.market_position == MarketPosition.UNDERVALUED:
            discount = 2.0  # Minimal room
        else:
            discount = 5.0  # Standard negotiation

        return {
            'property_id': property_id,
            'negotiation_leverage': analysis.negotiation_leverage,
            'negotiation_strategy': analysis.negotiation_strategy.value,
            'recommended_discount_percent': discount
        }

    def get_market_position(
        self,
        property_id: str,
        tenant_id: str,
        subject_data: Dict
    ) -> Dict:
        """Get market position"""
        analysis = self.analyze_property(
            property_id=property_id,
            tenant_id=tenant_id,
            subject_data=subject_data,
            top_k=10
        )

        is_good_deal = (
            analysis.market_position == MarketPosition.UNDERVALUED
            or (analysis.market_position == MarketPosition.FAIRLY_VALUED
                and analysis.negotiation_leverage >= 0.6)
        )

        return {
            'property_id': property_id,
            'market_position': analysis.market_position.value,
            'price_deviation_percent': analysis.price_deviation_percent,
            'is_good_deal': is_good_deal
        }


# FastAPI app
app = FastAPI(
    title="Comp-Critic Service",
    description="Adversarial comparative market analysis",
    version="1.0.0"
)

# Global service instance
service: Optional[CompCriticService] = None


@app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    global service

    try:
        service = CompCriticService(
            qdrant_host="localhost",
            qdrant_port=6333
        )
        logger.info("Comp-Critic service started")
    except Exception as e:
        logger.error(f"Failed to start service: {e}")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy" if service is not None else "not_initialized",
        "service": "comp_critic",
        "version": "1.0.0"
    }


@app.post("/analyze/comp-critic", response_model=CompAnalysisResponse)
async def analyze_comp_critic(
    request: CompAnalysisRequest,
    tenant_id: UUID = Query(..., description="Tenant ID"),
    # Subject property data (would come from database in production)
    listing_price: float = Query(..., description="Subject property listing price"),
    square_footage: int = Query(..., description="Subject property square footage"),
    bedrooms: int = Query(3, description="Bedrooms"),
    bathrooms: float = Query(2.0, description="Bathrooms"),
    days_on_market: int = Query(0, description="Days on market")
):
    """
    Perform comprehensive comp analysis

    Returns market position, negotiation leverage, and recommendations.
    """
    if service is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    try:
        subject_data = {
            'listing_price': listing_price,
            'square_footage': square_footage,
            'bedrooms': bedrooms,
            'bathrooms': bathrooms,
            'days_on_market': days_on_market,
            'property_type': request.property_type or 'Unknown'
        }

        analysis = service.analyze_property(
            property_id=request.property_id,
            tenant_id=str(tenant_id),
            subject_data=subject_data,
            top_k=request.top_k,
            property_type=request.property_type,
            zipcode=request.zipcode
        )

        # Format response
        comps_response = [
            ComparablePropertyResponse(
                property_id=comp.property_id,
                similarity_score=comp.similarity_score,
                listing_price=comp.listing_price,
                price_per_sqft=comp.price_per_sqft,
                bedrooms=comp.bedrooms,
                bathrooms=comp.bathrooms,
                square_footage=comp.square_footage,
                days_on_market=comp.days_on_market,
                property_type=comp.property_type
            )
            for comp in analysis.comps
        ]

        outliers_response = [
            ComparablePropertyResponse(
                property_id=comp.property_id,
                similarity_score=comp.similarity_score,
                listing_price=comp.listing_price,
                price_per_sqft=comp.price_per_sqft,
                bedrooms=comp.bedrooms,
                bathrooms=comp.bathrooms,
                square_footage=comp.square_footage,
                days_on_market=comp.days_on_market,
                property_type=comp.property_type
            )
            for comp in analysis.outlier_comps
        ]

        return CompAnalysisResponse(
            property_id=analysis.property_id,
            subject_price=analysis.subject_price,
            subject_price_per_sqft=analysis.subject_price_per_sqft,
            num_comps=analysis.num_comps,
            avg_comp_price=analysis.avg_comp_price,
            avg_comp_price_per_sqft=analysis.avg_comp_price_per_sqft,
            median_comp_price=analysis.median_comp_price,
            median_comp_price_per_sqft=analysis.median_comp_price_per_sqft,
            market_position=analysis.market_position.value,
            price_deviation_percent=analysis.price_deviation_percent,
            price_deviation_std_dev=analysis.price_deviation_std_dev,
            negotiation_leverage=analysis.negotiation_leverage,
            negotiation_strategy=analysis.negotiation_strategy.value,
            recommended_offer_range=analysis.recommended_offer_range,
            comps=comps_response,
            outlier_comps=outliers_response,
            recommendations=analysis.recommendations,
            risk_factors=analysis.risk_factors,
            opportunities=analysis.opportunities
        )

    except Exception as e:
        logger.error(f"Comp analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/analyze/{property_id}/leverage", response_model=LeverageScoreResponse)
async def get_leverage_score(
    property_id: str,
    tenant_id: UUID = Query(..., description="Tenant ID"),
    listing_price: float = Query(...),
    square_footage: int = Query(...),
    bedrooms: int = Query(3),
    bathrooms: float = Query(2.0),
    days_on_market: int = Query(0)
):
    """
    Get quick negotiation leverage score

    Faster endpoint for just leverage calculation.
    """
    if service is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    try:
        subject_data = {
            'listing_price': listing_price,
            'square_footage': square_footage,
            'bedrooms': bedrooms,
            'bathrooms': bathrooms,
            'days_on_market': days_on_market
        }

        result = service.get_leverage_score(
            property_id=property_id,
            tenant_id=str(tenant_id),
            subject_data=subject_data
        )

        return LeverageScoreResponse(**result)

    except Exception as e:
        logger.error(f"Leverage calculation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/analyze/{property_id}/market-position", response_model=MarketPositionResponse)
async def get_market_position(
    property_id: str,
    tenant_id: UUID = Query(...),
    listing_price: float = Query(...),
    square_footage: int = Query(...),
    bedrooms: int = Query(3),
    bathrooms: float = Query(2.0)
):
    """
    Get market position (over/under/fairly valued)

    Quick endpoint for market position only.
    """
    if service is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    try:
        subject_data = {
            'listing_price': listing_price,
            'square_footage': square_footage,
            'bedrooms': bedrooms,
            'bathrooms': bathrooms,
            'days_on_market': 0
        }

        result = service.get_market_position(
            property_id=property_id,
            tenant_id=str(tenant_id),
            subject_data=subject_data
        )

        return MarketPositionResponse(**result)

    except Exception as e:
        logger.error(f"Market position failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
