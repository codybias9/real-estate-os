"""
Negotiation Brain FastAPI Service

Wave 3.2 Part 4: REST API for negotiation recommendations

Endpoints:
- POST /negotiate/recommend - Get comprehensive negotiation recommendation
- POST /negotiate/offer-scenarios - Get multiple offer scenarios
- POST /negotiate/generate-message - Generate templated negotiation message

This service is deployed separately from the main API (like other ML services)
and is called by the main API endpoints.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID

from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from ml.models.negotiation_brain import (
    NegotiationBrain,
    PropertyContext,
    BuyerConstraints,
    NegotiationStrategy,
    NegotiationRecommendation
)
from ml.models.offer_recommendations import (
    OfferRecommendationEngine,
    OfferConstraints,
    OfferPreferences,
    MarketContext as OfferMarketContext
)
from ml.utils.messaging_templates import MessageGenerator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Negotiation Brain Service",
    description="Strategic negotiation recommendation engine for Real Estate OS",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global service instances
negotiation_brain: Optional[NegotiationBrain] = None
offer_engine: Optional[OfferRecommendationEngine] = None
message_generator: Optional[MessageGenerator] = None


# =============================================================================
# REQUEST/RESPONSE SCHEMAS
# =============================================================================

class NegotiationRequest(BaseModel):
    """Request for negotiation recommendation"""
    property_id: str = Field(..., description="Property ID")

    # Property context
    listing_price: float = Field(..., description="Listing price")
    price_per_sqft: float = Field(..., description="Price per square foot")
    days_on_market: int = Field(..., description="Days on market")
    market_position: str = Field(..., description="overvalued/fairly_valued/undervalued")
    price_deviation_percent: float = Field(..., description="Price deviation from comps")
    negotiation_leverage: float = Field(..., description="Leverage score 0-1")
    avg_comp_price: float = Field(..., description="Average comparable price")
    num_comps: int = Field(..., description="Number of comparables")

    property_type: str = Field("Single Family", description="Property type")
    bedrooms: int = Field(3, description="Bedrooms")
    bathrooms: float = Field(2.0, description="Bathrooms")
    square_footage: int = Field(..., description="Square footage")
    condition: Optional[str] = Field(None, description="excellent/good/fair/poor")

    # Seller signals
    price_reductions: int = Field(0, description="Number of price reductions")
    price_reduction_amount: float = Field(0.0, description="Total price reduction amount")
    listing_history_days: int = Field(0, description="Total days including relists")

    # Market conditions
    inventory_months: Optional[float] = Field(None, description="Months of inventory")
    recent_sales_trend: Optional[str] = Field(None, description="increasing/stable/decreasing")

    # Buyer constraints
    max_budget: float = Field(..., description="Buyer's maximum budget")
    preferred_budget: float = Field(..., description="Buyer's preferred budget")
    financing_type: str = Field("conventional", description="Financing type")
    down_payment_percent: float = Field(20.0, description="Down payment percentage")
    desired_closing_timeline_days: int = Field(45, description="Desired closing timeline")
    flexibility: str = Field("moderate", description="flexible/moderate/inflexible")
    contingencies_required: Optional[List[str]] = Field(
        default=["inspection", "financing", "appraisal"],
        description="Required contingencies"
    )


class TalkingPointResponse(BaseModel):
    """Talking point for negotiation"""
    category: str
    point: str
    evidence: str
    weight: float


class CounterOfferStrategyResponse(BaseModel):
    """Counter-offer strategy details"""
    initial_counter_max_increase: float
    walk_away_price: float
    concession_strategy: str
    alternative_concessions: List[str]


class DealStructureResponse(BaseModel):
    """Deal structure details"""
    contingencies: List[str]
    inspection_period_days: int
    closing_timeline_days: int
    earnest_money_percent: float
    escalation_clause: bool
    appraisal_gap_coverage: Optional[float] = None
    seller_concessions_target: Optional[float] = None


class NegotiationResponse(BaseModel):
    """Response with negotiation recommendation"""
    property_id: str

    # Strategy
    strategy: str
    strategy_confidence: float
    strategy_rationale: str

    # Offers
    recommended_initial_offer: float
    recommended_max_offer: float
    walk_away_price: float
    offer_justification: str

    # Market context
    market_condition: str
    seller_motivation: str

    # Tactical guidance
    talking_points: List[TalkingPointResponse]
    counter_offer_strategy: CounterOfferStrategyResponse
    deal_structure: DealStructureResponse

    # Risks and opportunities
    key_risks: List[str]
    key_opportunities: List[str]

    # Timeline
    recommended_response_time: str

    # Metadata
    created_at: str


class OfferScenariosRequest(BaseModel):
    """Request for offer scenario analysis"""
    property_id: str
    listing_price: float
    market_value_estimate: float
    market_value_confidence: float = 0.8
    days_on_market: int
    price_reductions: int = 0
    competing_offers_likelihood: float = 0.3
    seller_motivation_score: float = 0.5
    market_velocity: str = "warm"  # hot/warm/cool/cold

    # Buyer constraints
    min_offer: float
    max_offer: float
    target_price: float
    target_closing_days: int = 45
    risk_tolerance: str = "moderate"  # conservative/moderate/aggressive


class OfferScenarioResponse(BaseModel):
    """Single offer scenario"""
    offer_amount: float
    acceptance_probability: float
    value_score: float
    constraint_score: float
    overall_score: float
    recommended_contingencies: List[str]
    recommended_closing_days: int
    escalation_clause_amount: Optional[float] = None
    rationale: str


class OfferScenariosResponse(BaseModel):
    """Response with multiple offer scenarios"""
    property_id: str
    recommended_offer: OfferScenarioResponse
    conservative_offer: OfferScenarioResponse
    aggressive_offer: OfferScenarioResponse
    balanced_offer: OfferScenarioResponse
    key_factors: List[str]
    warnings: List[str]


class MessageGenerationRequest(BaseModel):
    """Request for message generation"""
    message_type: str = Field(..., description="initial_offer/counter_response/inspection/quick")

    # Common fields
    buyer_agent_name: str
    listing_agent_name: Optional[str] = None
    property_address: Optional[str] = None
    tone: str = Field("professional", description="professional/friendly/formal")

    # For initial_offer
    negotiation_data: Optional[Dict[str, Any]] = None
    buyer_name: Optional[str] = None
    additional_context: Optional[str] = None

    # For counter_response
    original_offer: Optional[float] = None
    counter_offer: Optional[float] = None
    response_offer: Optional[float] = None
    strategy: Optional[str] = None
    talking_points_data: Optional[List[Dict]] = None
    concessions: Optional[List[str]] = None

    # For inspection
    repair_requests: Optional[List[Dict[str, Any]]] = None
    total_repair_estimate: Optional[float] = None
    requested_credit: Optional[float] = None

    # For quick messages
    quick_message_context: Optional[Dict[str, Any]] = None


class MessageGenerationResponse(BaseModel):
    """Response with generated message"""
    message_type: str
    message: str
    generated_at: str


# =============================================================================
# SERVICE INITIALIZATION
# =============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    global negotiation_brain, offer_engine, message_generator

    logger.info("Initializing Negotiation Brain Service...")

    try:
        # Initialize Negotiation Brain
        negotiation_brain = NegotiationBrain()
        logger.info("✓ Negotiation Brain initialized")

        # Initialize Offer Engine
        offer_engine = OfferRecommendationEngine()
        logger.info("✓ Offer Recommendation Engine initialized")

        # Initialize Message Generator
        message_generator = MessageGenerator(tone="professional")
        logger.info("✓ Message Generator initialized")

        logger.info("Negotiation Brain Service ready!")

    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Negotiation Brain Service...")


# =============================================================================
# HEALTH CHECK
# =============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "negotiation_brain",
        "version": "1.0.0",
        "brain_ready": negotiation_brain is not None,
        "offer_engine_ready": offer_engine is not None,
        "message_generator_ready": message_generator is not None
    }


# =============================================================================
# NEGOTIATION ENDPOINTS
# =============================================================================

@app.post("/negotiate/recommend", response_model=NegotiationResponse)
async def get_negotiation_recommendation(
    request: NegotiationRequest,
    tenant_id: UUID = Query(..., description="Tenant ID")
):
    """
    Get comprehensive negotiation recommendation

    Analyzes property, market, and buyer data to provide strategic
    negotiation recommendations including strategy, offers, talking points,
    and deal structure.
    """
    if negotiation_brain is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    logger.info(f"Generating negotiation recommendation for property {request.property_id}")

    try:
        # Build property context
        property_context = PropertyContext(
            property_id=request.property_id,
            listing_price=request.listing_price,
            price_per_sqft=request.price_per_sqft,
            days_on_market=request.days_on_market,
            market_position=request.market_position,
            price_deviation_percent=request.price_deviation_percent,
            negotiation_leverage=request.negotiation_leverage,
            avg_comp_price=request.avg_comp_price,
            num_comps=request.num_comps,
            property_type=request.property_type,
            bedrooms=request.bedrooms,
            bathrooms=request.bathrooms,
            square_footage=request.square_footage,
            condition=request.condition,
            price_reductions=request.price_reductions,
            price_reduction_amount=request.price_reduction_amount,
            listing_history_days=request.listing_history_days,
            inventory_months=request.inventory_months,
            recent_sales_trend=request.recent_sales_trend
        )

        # Build buyer constraints
        buyer_constraints = BuyerConstraints(
            max_budget=request.max_budget,
            preferred_budget=request.preferred_budget,
            financing_type=request.financing_type,
            down_payment_percent=request.down_payment_percent,
            contingencies_required=request.contingencies_required,
            desired_closing_timeline_days=request.desired_closing_timeline_days,
            flexibility=request.flexibility
        )

        # Generate recommendation
        recommendation = negotiation_brain.recommend(property_context, buyer_constraints)

        # Convert to response format
        return NegotiationResponse(
            property_id=recommendation.property_id,
            strategy=recommendation.strategy.value,
            strategy_confidence=recommendation.strategy_confidence,
            strategy_rationale=recommendation.strategy_rationale,
            recommended_initial_offer=recommendation.recommended_initial_offer,
            recommended_max_offer=recommendation.recommended_max_offer,
            walk_away_price=recommendation.walk_away_price,
            offer_justification=recommendation.offer_justification,
            market_condition=recommendation.market_condition.value,
            seller_motivation=recommendation.seller_motivation.value,
            talking_points=[
                TalkingPointResponse(
                    category=tp.category,
                    point=tp.point,
                    evidence=tp.evidence,
                    weight=tp.weight
                )
                for tp in recommendation.talking_points
            ],
            counter_offer_strategy=CounterOfferStrategyResponse(
                initial_counter_max_increase=recommendation.counter_offer_strategy.initial_counter_max_increase,
                walk_away_price=recommendation.counter_offer_strategy.walk_away_price,
                concession_strategy=recommendation.counter_offer_strategy.concession_strategy,
                alternative_concessions=recommendation.counter_offer_strategy.alternative_concessions
            ),
            deal_structure=DealStructureResponse(
                contingencies=recommendation.deal_structure.contingencies,
                inspection_period_days=recommendation.deal_structure.inspection_period_days,
                closing_timeline_days=recommendation.deal_structure.closing_timeline_days,
                earnest_money_percent=recommendation.deal_structure.earnest_money_percent,
                escalation_clause=recommendation.deal_structure.escalation_clause,
                appraisal_gap_coverage=recommendation.deal_structure.appraisal_gap_coverage,
                seller_concessions_target=recommendation.deal_structure.seller_concessions_target
            ),
            key_risks=recommendation.key_risks,
            key_opportunities=recommendation.key_opportunities,
            recommended_response_time=recommendation.recommended_response_time,
            created_at=recommendation.created_at.isoformat()
        )

    except Exception as e:
        logger.error(f"Failed to generate recommendation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/negotiate/offer-scenarios", response_model=OfferScenariosResponse)
async def get_offer_scenarios(
    request: OfferScenariosRequest,
    tenant_id: UUID = Query(..., description="Tenant ID")
):
    """
    Get multiple offer scenarios with acceptance probabilities

    Provides conservative, balanced, and aggressive offer options
    with scoring and justification.
    """
    if offer_engine is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    logger.info(f"Generating offer scenarios for property {request.property_id}")

    try:
        # Build constraints
        constraints = OfferConstraints(
            min_offer=request.min_offer,
            max_offer=request.max_offer
        )

        # Build preferences
        preferences = OfferPreferences(
            target_price=request.target_price,
            target_closing_days=request.target_closing_days,
            risk_tolerance=request.risk_tolerance
        )

        # Build market context
        market_context = OfferMarketContext(
            listing_price=request.listing_price,
            market_value_estimate=request.market_value_estimate,
            market_value_confidence=request.market_value_confidence,
            days_on_market=request.days_on_market,
            price_reductions=request.price_reductions,
            competing_offers_likelihood=request.competing_offers_likelihood,
            seller_motivation_score=request.seller_motivation_score,
            market_velocity=request.market_velocity
        )

        # Generate recommendations
        recommendation = offer_engine.recommend(
            property_id=request.property_id,
            constraints=constraints,
            preferences=preferences,
            market_context=market_context
        )

        # Convert scenarios to response format
        def scenario_to_response(scenario) -> OfferScenarioResponse:
            return OfferScenarioResponse(
                offer_amount=scenario.offer_amount,
                acceptance_probability=scenario.acceptance_probability,
                value_score=scenario.value_score,
                constraint_score=scenario.constraint_score,
                overall_score=scenario.overall_score,
                recommended_contingencies=scenario.recommended_contingencies,
                recommended_closing_days=scenario.recommended_closing_days,
                escalation_clause_amount=scenario.escalation_clause_amount,
                rationale=scenario.rationale
            )

        return OfferScenariosResponse(
            property_id=recommendation.property_id,
            recommended_offer=scenario_to_response(recommendation.recommended_offer),
            conservative_offer=scenario_to_response(recommendation.conservative_offer),
            aggressive_offer=scenario_to_response(recommendation.aggressive_offer),
            balanced_offer=scenario_to_response(recommendation.balanced_offer),
            key_factors=recommendation.key_factors,
            warnings=recommendation.warnings
        )

    except Exception as e:
        logger.error(f"Failed to generate offer scenarios: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/negotiate/generate-message", response_model=MessageGenerationResponse)
async def generate_negotiation_message(
    request: MessageGenerationRequest,
    tenant_id: UUID = Query(..., description="Tenant ID")
):
    """
    Generate templated negotiation message

    Supports:
    - initial_offer: Initial offer letter with justification
    - counter_response: Response to seller counter-offer
    - inspection: Post-inspection negotiation
    - quick: Quick messages (showing request, inspection scheduling, etc.)
    """
    if message_generator is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    logger.info(f"Generating {request.message_type} message")

    try:
        message = ""

        if request.message_type == "initial_offer":
            # This would need the full negotiation recommendation object
            # For now, return placeholder
            message = f"""Generated initial offer letter for {request.property_address}

[Template would be fully populated with negotiation data]

This is a placeholder - full implementation requires passing NegotiationRecommendation object.
"""

        elif request.message_type == "counter_response":
            if not all([request.original_offer, request.counter_offer, request.response_offer]):
                raise HTTPException(status_code=400, detail="Missing offer amounts for counter response")

            from ml.models.negotiation_brain import TalkingPoint
            strategy = NegotiationStrategy(request.strategy or "moderate")
            talking_points = []

            message = message_generator.generate_counter_response(
                original_offer=request.original_offer,
                counter_offer=request.counter_offer,
                response_offer=request.response_offer,
                strategy=strategy,
                talking_points=talking_points,
                buyer_agent_name=request.buyer_agent_name,
                listing_agent_name=request.listing_agent_name,
                concessions=request.concessions,
                tone=request.tone
            )

        elif request.message_type == "inspection":
            if not all([request.repair_requests, request.total_repair_estimate, request.requested_credit]):
                raise HTTPException(status_code=400, detail="Missing inspection data")

            message = message_generator.generate_inspection_negotiation(
                repair_requests=request.repair_requests,
                total_repair_estimate=request.total_repair_estimate,
                requested_credit=request.requested_credit,
                buyer_agent_name=request.buyer_agent_name,
                listing_agent_name=request.listing_agent_name,
                property_address=request.property_address or "",
                tone=request.tone
            )

        elif request.message_type == "quick":
            if not request.quick_message_context:
                raise HTTPException(status_code=400, detail="Missing quick message context")

            message = message_generator.generate_quick_message(
                message_type=request.quick_message_context.get('type', 'request_showing'),
                context=request.quick_message_context
            )

        else:
            raise HTTPException(status_code=400, detail=f"Unknown message type: {request.message_type}")

        return MessageGenerationResponse(
            message_type=request.message_type,
            message=message,
            generated_at=datetime.utcnow().isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8004,  # Different port from other ML services
        log_level="info"
    )
