"""Property router with provenance endpoints

Provides API endpoints for:
- GET /properties/{id} - Property details with provenance
- GET /properties/{id}/provenance - Provenance statistics
- GET /properties/{id}/history/{field_path} - Field history
- GET /properties/{id}/scorecard - Latest scorecard with explainability
- GET /properties/{id}/similar - Find similar properties (Wave 2.3)
- POST /properties/recommend - Get personalized recommendations (Wave 2.3)
- POST /properties/{id}/feedback - Submit user feedback (Wave 2.3)
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc
from typing import List, Optional, Dict
from uuid import UUID
from datetime import datetime
import logging

from ..database import get_db
from ..schemas.provenance import (
    PropertyDetail,
    PropertyWithProvenance,
    FieldHistoryResponse,
    FieldProvenanceDetail,
    ProvenanceStatsResponse,
    ScoreExplainabilityDetail,
    FieldProvenanceBase
)

# Import models from both modules
import sys
sys.path.append('/home/user/real-estate-os')
from db.models_provenance import (
    Property,
    FieldProvenance,
    Scorecard,
    ScoreExplainability,
    OwnerEntity,
    PropertyOwnerLink,
    Deal
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/properties",
    tags=["properties"],
    responses={404: {"description": "Property not found"}},
)


# =====================================================================
# HELPER FUNCTIONS
# =====================================================================

def get_property_or_404(property_id: UUID, tenant_id: UUID, db: Session) -> Property:
    """Get property by ID or raise 404"""
    # Set tenant context for RLS
    db.execute(f"SET LOCAL app.current_tenant_id = '{tenant_id}'")

    property = db.query(Property).filter(
        Property.id == property_id,
        Property.tenant_id == tenant_id
    ).first()

    if not property:
        raise HTTPException(status_code=404, detail="Property not found")

    return property


def get_field_provenance_map(property_id: UUID, tenant_id: UUID, db: Session) -> dict:
    """
    Get latest provenance for all fields of a property

    Returns dict: {field_path: FieldProvenanceBase}
    """
    # Get latest version for each field
    subquery = db.query(
        FieldProvenance.field_path,
        func.max(FieldProvenance.version).label('max_version')
    ).filter(
        FieldProvenance.tenant_id == tenant_id,
        FieldProvenance.entity_type == 'property',
        FieldProvenance.entity_id == property_id
    ).group_by(FieldProvenance.field_path).subquery()

    # Get full provenance records for latest versions
    latest_provenances = db.query(FieldProvenance).join(
        subquery,
        (FieldProvenance.field_path == subquery.c.field_path) &
        (FieldProvenance.version == subquery.c.max_version)
    ).filter(
        FieldProvenance.tenant_id == tenant_id,
        FieldProvenance.entity_type == 'property',
        FieldProvenance.entity_id == property_id
    ).all()

    # Build map
    provenance_map = {}
    for prov in latest_provenances:
        provenance_map[prov.field_path] = FieldProvenanceBase(
            source_system=prov.source_system,
            source_url=prov.source_url,
            method=prov.method,
            confidence=prov.confidence,
            version=prov.version,
            extracted_at=prov.extracted_at
        )

    return provenance_map


def reconstruct_property_fields(property_id: UUID, tenant_id: UUID, db: Session) -> dict:
    """
    Reconstruct current property field values from provenance

    Returns dict of field_path -> value
    """
    # Get latest version for each field
    subquery = db.query(
        FieldProvenance.field_path,
        func.max(FieldProvenance.version).label('max_version')
    ).filter(
        FieldProvenance.tenant_id == tenant_id,
        FieldProvenance.entity_type == 'property',
        FieldProvenance.entity_id == property_id
    ).group_by(FieldProvenance.field_path).subquery()

    # Get values
    latest_values = db.query(
        FieldProvenance.field_path,
        FieldProvenance.value
    ).join(
        subquery,
        (FieldProvenance.field_path == subquery.c.field_path) &
        (FieldProvenance.version == subquery.c.max_version)
    ).filter(
        FieldProvenance.tenant_id == tenant_id,
        FieldProvenance.entity_type == 'property',
        FieldProvenance.entity_id == property_id
    ).all()

    # Reconstruct nested structure from dot notation
    fields = {}
    for field_path, value in latest_values:
        # Simple flat structure for now; can enhance to nested later
        fields[field_path] = value

    return fields


# =====================================================================
# ENDPOINTS
# =====================================================================

@router.get("/{property_id}", response_model=PropertyDetail)
def get_property(
    property_id: UUID,
    tenant_id: UUID = Query(..., description="Tenant ID for multi-tenant isolation"),
    include_provenance: bool = Query(True, description="Include provenance metadata"),
    db: Session = Depends(get_db)
):
    """
    Get property details with provenance

    Returns property with:
    - Basic information (address, parcel, lat/lon)
    - All field values from latest provenance
    - Provenance metadata for each field (source, confidence, etc.)
    - Related owners, scorecards, deals
    """
    logger.info(f"Fetching property {property_id} for tenant {tenant_id}")

    # Get property
    property = get_property_or_404(property_id, tenant_id, db)

    # Reconstruct fields from provenance
    fields = reconstruct_property_fields(property_id, tenant_id, db)

    # Get provenance map
    provenance_map = {}
    if include_provenance:
        provenance_map = get_field_provenance_map(property_id, tenant_id, db)

    # Get owners
    owner_links = db.query(PropertyOwnerLink).filter(
        PropertyOwnerLink.property_id == property_id,
        PropertyOwnerLink.tenant_id == tenant_id
    ).options(joinedload(PropertyOwnerLink.owner)).all()

    owners = [
        {
            "id": link.owner.id,
            "name": link.owner.name,
            "type": link.owner.type,
            "role": link.role,
            "confidence": link.confidence
        }
        for link in owner_links
    ]

    # Get scorecards
    scorecards = db.query(Scorecard).filter(
        Scorecard.property_id == property_id,
        Scorecard.tenant_id == tenant_id
    ).order_by(desc(Scorecard.created_at)).limit(5).all()

    scorecard_list = [
        {
            "id": sc.id,
            "model_version": sc.model_version,
            "score": sc.score,
            "grade": sc.grade,
            "confidence": sc.confidence,
            "created_at": sc.created_at
        }
        for sc in scorecards
    ]

    # Get deals
    deals = db.query(Deal).filter(
        Deal.property_id == property_id,
        Deal.tenant_id == tenant_id
    ).order_by(desc(Deal.created_at)).all()

    deal_list = [
        {
            "id": d.id,
            "stage": d.stage,
            "created_at": d.created_at,
            "updated_at": d.updated_at
        }
        for d in deals
    ]

    return PropertyDetail(
        id=property.id,
        tenant_id=property.tenant_id,
        canonical_address=property.canonical_address,
        parcel=property.parcel,
        lat=property.lat,
        lon=property.lon,
        fields=fields,
        provenance=provenance_map,
        created_at=property.created_at,
        updated_at=property.updated_at,
        owners=owners,
        scorecards=scorecard_list,
        deals=deal_list
    )


@router.get("/{property_id}/provenance", response_model=ProvenanceStatsResponse)
def get_provenance_stats(
    property_id: UUID,
    tenant_id: UUID = Query(..., description="Tenant ID"),
    db: Session = Depends(get_db)
):
    """
    Get provenance coverage statistics for a property

    Returns:
    - Total fields tracked
    - Coverage percentage
    - Breakdown by source system and method
    - Average confidence
    - Stale field count (not updated in 30 days)
    """
    logger.info(f"Fetching provenance stats for property {property_id}")

    # Verify property exists
    get_property_or_404(property_id, tenant_id, db)

    # Get all provenance records (latest versions)
    subquery = db.query(
        FieldProvenance.field_path,
        func.max(FieldProvenance.version).label('max_version')
    ).filter(
        FieldProvenance.tenant_id == tenant_id,
        FieldProvenance.entity_type == 'property',
        FieldProvenance.entity_id == property_id
    ).group_by(FieldProvenance.field_path).subquery()

    latest_provenances = db.query(FieldProvenance).join(
        subquery,
        (FieldProvenance.field_path == subquery.c.field_path) &
        (FieldProvenance.version == subquery.c.max_version)
    ).filter(
        FieldProvenance.tenant_id == tenant_id,
        FieldProvenance.entity_type == 'property',
        FieldProvenance.entity_id == property_id
    ).all()

    # Calculate statistics
    total_fields = len(latest_provenances)

    by_source_system = {}
    by_method = {}
    confidences = []
    stale_count = 0

    for prov in latest_provenances:
        # By source system
        if prov.source_system:
            by_source_system[prov.source_system] = by_source_system.get(prov.source_system, 0) + 1

        # By method
        if prov.method:
            by_method[prov.method] = by_method.get(prov.method, 0) + 1

        # Confidence
        if prov.confidence:
            confidences.append(float(prov.confidence))

        # Stale check (> 30 days)
        from datetime import datetime, timedelta
        if prov.extracted_at < datetime.now() - timedelta(days=30):
            stale_count += 1

    avg_confidence = sum(confidences) / len(confidences) if confidences else None

    return ProvenanceStatsResponse(
        total_fields=total_fields,
        fields_with_provenance=total_fields,  # All tracked fields have provenance by definition
        coverage_percentage=100.0 if total_fields > 0 else 0.0,
        by_source_system=by_source_system,
        by_method=by_method,
        avg_confidence=avg_confidence,
        stale_fields=stale_count
    )


@router.get("/{property_id}/history/{field_path:path}", response_model=FieldHistoryResponse)
def get_field_history(
    property_id: UUID,
    field_path: str,
    tenant_id: UUID = Query(..., description="Tenant ID"),
    limit: int = Query(10, ge=1, le=100, description="Max versions to return"),
    db: Session = Depends(get_db)
):
    """
    Get value history for a specific field

    Returns all versions of a field value in reverse chronological order.
    Useful for "See History" modal in UI.
    """
    logger.info(f"Fetching history for {property_id}/{field_path}")

    # Verify property exists
    get_property_or_404(property_id, tenant_id, db)

    # Get all versions for this field
    history_records = db.query(FieldProvenance).filter(
        FieldProvenance.tenant_id == tenant_id,
        FieldProvenance.entity_type == 'property',
        FieldProvenance.entity_id == property_id,
        FieldProvenance.field_path == field_path
    ).order_by(desc(FieldProvenance.version)).limit(limit).all()

    if not history_records:
        raise HTTPException(status_code=404, detail=f"No provenance found for field '{field_path}'")

    total_versions = db.query(func.count(FieldProvenance.id)).filter(
        FieldProvenance.tenant_id == tenant_id,
        FieldProvenance.entity_type == 'property',
        FieldProvenance.entity_id == property_id,
        FieldProvenance.field_path == field_path
    ).scalar()

    history = [
        FieldProvenanceDetail(
            id=h.id,
            entity_type=h.entity_type,
            entity_id=h.entity_id,
            field_path=h.field_path,
            value=h.value,
            source_system=h.source_system,
            source_url=h.source_url,
            method=h.method,
            confidence=h.confidence,
            version=h.version,
            extracted_at=h.extracted_at,
            created_at=h.created_at
        )
        for h in history_records
    ]

    return FieldHistoryResponse(
        property_id=property_id,
        field_path=field_path,
        history=history,
        total_versions=total_versions
    )


@router.get("/{property_id}/scorecard", response_model=ScoreExplainabilityDetail)
def get_latest_scorecard(
    property_id: UUID,
    tenant_id: UUID = Query(..., description="Tenant ID"),
    db: Session = Depends(get_db)
):
    """
    Get latest scorecard with explainability

    Returns:
    - Score and grade
    - SHAP values for all features
    - Top positive/negative drivers
    - Counterfactuals (minimal changes to flip grade)
    """
    logger.info(f"Fetching scorecard for property {property_id}")

    # Verify property exists
    get_property_or_404(property_id, tenant_id, db)

    # Get latest scorecard
    scorecard = db.query(Scorecard).filter(
        Scorecard.property_id == property_id,
        Scorecard.tenant_id == tenant_id
    ).order_by(desc(Scorecard.created_at)).first()

    if not scorecard:
        raise HTTPException(status_code=404, detail="No scorecard found for this property")

    # Get explainability
    explainability = db.query(ScoreExplainability).filter(
        ScoreExplainability.scorecard_id == scorecard.id,
        ScoreExplainability.tenant_id == tenant_id
    ).first()

    if not explainability:
        raise HTTPException(status_code=404, detail="No explainability data found for this scorecard")

    # Parse SHAP values
    shap_list = [
        {"feature": k, "value": v, "display_value": str(v)}
        for k, v in explainability.shap_values.items()
    ]

    # Parse drivers
    drivers_data = explainability.drivers
    top_positive = drivers_data.get('positive', [])
    top_negative = drivers_data.get('negative', [])

    # Parse counterfactuals
    counterfactuals_list = explainability.counterfactuals or []

    return ScoreExplainabilityDetail(
        id=explainability.id,
        scorecard_id=scorecard.id,
        shap_values=shap_list,
        top_positive_drivers=top_positive,
        top_negative_drivers=top_negative,
        counterfactuals=counterfactuals_list,
        created_at=explainability.created_at
    )

# =====================================================================
# WAVE 2.3: SIMILARITY SEARCH & USER FEEDBACK
# =====================================================================

@router.get("/{property_id}/similar")
def get_similar_properties(
    property_id: UUID,
    tenant_id: UUID = Query(..., description="Tenant ID"),
    top_k: int = Query(10, ge=1, le=50, description="Number of similar properties"),
    property_type: Optional[str] = Query(None, description="Filter by property type"),
    zipcode: Optional[str] = Query(None, description="Filter by zipcode"),
    db: Session = Depends(get_db)
):
    """
    Find properties similar to the given property using ML embeddings

    Uses Qdrant vector database to find properties with similar characteristics.
    Great for comp analysis and portfolio diversification.

    **Wave 2.3** - ML-powered similarity search
    """
    logger.info(f"Finding similar properties to {property_id}")

    # Verify property exists
    property = get_property_or_404(property_id, tenant_id, db)

    try:
        # Import Qdrant client
        from ml.embeddings.qdrant_client import QdrantVectorDB

        # Connect to Qdrant
        qdrant = QdrantVectorDB(host="localhost", port=6333)

        # Build filters
        filters = {}
        if property_type:
            filters['property_type'] = property_type
        if zipcode:
            filters['zipcode'] = zipcode

        # Find similar properties
        similar = qdrant.find_look_alikes(
            property_id=str(property_id),
            tenant_id=str(tenant_id),
            top_k=top_k,
            filters=filters if filters else None
        )

        # Format response
        results = []
        for prop in similar:
            results.append({
                "property_id": prop.property_id,
                "similarity_score": round(prop.similarity_score, 3),
                "listing_price": prop.metadata.get('listing_price'),
                "bedrooms": prop.metadata.get('bedrooms'),
                "bathrooms": prop.metadata.get('bathrooms'),
                "property_type": prop.metadata.get('property_type'),
                "zipcode": prop.metadata.get('zipcode'),
                "confidence": prop.metadata.get('confidence')
            })

        return {
            "property_id": str(property_id),
            "total_results": len(results),
            "similar_properties": results
        }

    except Exception as e:
        logger.error(f"Similarity search failed: {e}")
        # Fallback: Return empty results if Qdrant not available
        return {
            "property_id": str(property_id),
            "total_results": 0,
            "similar_properties": [],
            "error": "Similarity search service unavailable"
        }


@router.post("/recommend")
def get_recommendations(
    user_id: int = Body(..., embed=True, description="User ID"),
    tenant_id: UUID = Query(..., description="Tenant ID"),
    top_k: int = Body(10, embed=True, ge=1, le=50, description="Number of recommendations"),
    filters: Optional[Dict] = Body(None, embed=True, description="Optional filters"),
    db: Session = Depends(get_db)
):
    """
    Get personalized property recommendations for user

    Uses Portfolio Twin ML model to predict which properties match
    the user's investment criteria based on past behavior.

    **Wave 2.3** - Personalized recommendations
    """
    logger.info(f"Getting recommendations for user {user_id}")

    try:
        # Import Portfolio Twin service
        from ml.serving.portfolio_twin_service import PortfolioTwinService
        from pathlib import Path

        # Load model
        model_path = Path("ml/serving/models/portfolio_twin.pt")
        if not model_path.exists():
            raise HTTPException(
                status_code=503,
                detail="Recommendation service unavailable (model not trained yet)"
            )

        service = PortfolioTwinService(str(model_path))

        # TODO: Implement full recommendation pipeline
        # For now, return placeholder
        return {
            "user_id": user_id,
            "total_results": 0,
            "recommendations": [],
            "message": "Recommendation system coming soon (Wave 2.4)"
        }

    except Exception as e:
        logger.error(f"Recommendation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{property_id}/feedback")
def submit_feedback(
    property_id: UUID,
    feedback: str = Body(..., embed=True, description="Feedback type: 'like' or 'dislike'"),
    user_id: int = Body(..., embed=True, description="User ID"),
    tenant_id: UUID = Query(..., description="Tenant ID"),
    db: Session = Depends(get_db)
):
    """
    Submit user feedback on a property (thumbs up/down)

    Feedback is used to improve Portfolio Twin recommendations.
    Creates a record that can be used for model retraining.

    **Wave 2.3** - User feedback collection
    """
    logger.info(f"User {user_id} submitting feedback '{feedback}' for property {property_id}")

    # Validate feedback
    if feedback not in ['like', 'dislike']:
        raise HTTPException(
            status_code=400,
            detail="Feedback must be 'like' or 'dislike'"
        )

    # Verify property exists
    property = get_property_or_404(property_id, tenant_id, db)

    # TODO: Store feedback in database (needs UserFeedback table)
    # For now, just log it
    logger.info(f"Feedback recorded: user={user_id}, property={property_id}, feedback={feedback}")

    return {
        "property_id": str(property_id),
        "user_id": user_id,
        "feedback": feedback,
        "recorded_at": datetime.utcnow().isoformat(),
        "message": "Feedback recorded successfully (Wave 2.4 will store in database)"
    }

# =====================================================================
# WAVE 3.1: COMP-CRITIC ADVERSARIAL COMP ANALYSIS
# =====================================================================

@router.get("/{property_id}/comp-analysis")
def get_comp_analysis(
    property_id: UUID,
    tenant_id: UUID = Query(..., description="Tenant ID"),
    top_k: int = Query(20, ge=5, le=50, description="Number of comps"),
    property_type: Optional[str] = Query(None, description="Filter by property type"),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive comp analysis with negotiation leverage

    Uses Comp-Critic ML model to analyze property against comparables.
    Identifies over/undervalued properties and calculates negotiation leverage.

    **Wave 3.1** - Adversarial comp analysis
    """
    logger.info(f"Getting comp analysis for property {property_id}")

    # Verify property exists
    property = get_property_or_404(property_id, tenant_id, db)

    # Get property data
    fields = reconstruct_property_fields(property_id, tenant_id, db)

    try:
        # Import Comp-Critic service
        from ml.models.comp_critic import CompCriticAnalyzer, ComparableProperty
        from ml.embeddings.qdrant_client import QdrantVectorDB

        # Connect to Qdrant
        qdrant = QdrantVectorDB(host="localhost", port=6333)

        # Find similar properties
        filters = {}
        if property_type:
            filters['property_type'] = property_type

        similar = qdrant.find_look_alikes(
            property_id=str(property_id),
            tenant_id=str(tenant_id),
            top_k=top_k,
            filters=filters if filters else None
        )

        if not similar:
            return {
                "error": "No comparable properties found",
                "property_id": str(property_id),
                "num_comps": 0
            }

        # Convert to ComparableProperty objects
        comps = []
        for sim in similar:
            metadata = sim.metadata
            comps.append(ComparableProperty(
                property_id=sim.property_id,
                similarity_score=sim.similarity_score,
                listing_price=metadata.get('listing_price', 0),
                price_per_sqft=metadata.get('listing_price', 0) / max(metadata.get('square_footage', 1), 1),
                bedrooms=metadata.get('bedrooms', 3),
                bathrooms=metadata.get('bathrooms', 2.0),
                square_footage=metadata.get('square_footage', 2000),
                days_on_market=metadata.get('days_on_market', 0),
                property_type=metadata.get('property_type', 'Unknown')
            ))

        # Create subject property
        listing_price = float(fields.get('listing_price', 0))
        square_footage = int(fields.get('square_footage', 2000))

        subject = ComparableProperty(
            property_id=str(property_id),
            similarity_score=1.0,
            listing_price=listing_price,
            price_per_sqft=listing_price / square_footage if square_footage > 0 else 0,
            bedrooms=int(fields.get('bedrooms', 3)),
            bathrooms=float(fields.get('bathrooms', 2.0)),
            square_footage=square_footage,
            days_on_market=int(fields.get('days_on_market', 0)),
            property_type=str(fields.get('property_type', 'Unknown'))
        )

        # Run analysis
        analyzer = CompCriticAnalyzer()
        analysis = analyzer.analyze(
            subject_property=subject,
            comparable_properties=comps
        )

        # Format response
        return {
            "property_id": str(property_id),
            "subject_price": analysis.subject_price,
            "subject_price_per_sqft": analysis.subject_price_per_sqft,
            "num_comps": analysis.num_comps,
            "avg_comp_price": analysis.avg_comp_price,
            "avg_comp_price_per_sqft": analysis.avg_comp_price_per_sqft,
            "market_position": analysis.market_position.value,
            "price_deviation_percent": round(analysis.price_deviation_percent, 2),
            "negotiation_leverage": round(analysis.negotiation_leverage, 3),
            "negotiation_strategy": analysis.negotiation_strategy.value,
            "recommended_offer_range": {
                "min": round(analysis.recommended_offer_range[0], 2),
                "max": round(analysis.recommended_offer_range[1], 2)
            },
            "comps": [
                {
                    "property_id": comp.property_id,
                    "similarity_score": round(comp.similarity_score, 3),
                    "listing_price": comp.listing_price,
                    "price_per_sqft": round(comp.price_per_sqft, 2)
                }
                for comp in analysis.comps[:10]  # Top 10 comps
            ],
            "recommendations": analysis.recommendations,
            "risk_factors": analysis.risk_factors,
            "opportunities": analysis.opportunities
        }

    except Exception as e:
        logger.error(f"Comp analysis failed: {e}")
        return {
            "error": "Comp analysis service unavailable",
            "property_id": str(property_id),
            "message": str(e)
        }


@router.get("/{property_id}/negotiation-leverage")
def get_negotiation_leverage(
    property_id: UUID,
    tenant_id: UUID = Query(..., description="Tenant ID"),
    db: Session = Depends(get_db)
):
    """
    Get quick negotiation leverage score

    Returns leverage score (0-1) and recommended strategy.

    **Wave 3.1** - Quick leverage calculation
    """
    logger.info(f"Getting negotiation leverage for property {property_id}")

    # Verify property exists
    property = get_property_or_404(property_id, tenant_id, db)

    # Get comp analysis (cached for 1 hour)
    analysis_result = get_comp_analysis(property_id, tenant_id, 10, None, db)

    if "error" in analysis_result:
        return analysis_result

    return {
        "property_id": str(property_id),
        "negotiation_leverage": analysis_result.get('negotiation_leverage', 0.5),
        "negotiation_strategy": analysis_result.get('negotiation_strategy', 'moderate'),
        "market_position": analysis_result.get('market_position', 'fairly_valued'),
        "price_deviation_percent": analysis_result.get('price_deviation_percent', 0.0),
        "recommended_offer_range": analysis_result.get('recommended_offer_range', {}),
        "top_recommendation": analysis_result.get('recommendations', ['No analysis available'])[0]
    }


# =====================================================================
# WAVE 3.2: NEGOTIATION BRAIN ENDPOINTS
# =====================================================================

@router.post("/{property_id}/negotiation-strategy")
def get_negotiation_strategy(
    property_id: UUID,
    tenant_id: UUID = Query(..., description="Tenant ID"),
    max_budget: float = Body(..., embed=True, description="Buyer's maximum budget"),
    preferred_budget: float = Body(..., embed=True, description="Buyer's preferred budget"),
    financing_type: str = Body("conventional", embed=True, description="Financing type"),
    down_payment_percent: float = Body(20.0, embed=True, description="Down payment percentage"),
    desired_closing_days: int = Body(45, embed=True, description="Desired closing timeline"),
    flexibility: str = Body("moderate", embed=True, description="flexible/moderate/inflexible"),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive negotiation strategy recommendation

    Uses Negotiation Brain to analyze property, market conditions, and buyer
    constraints to provide strategic guidance including:
    - Recommended negotiation strategy (aggressive/moderate/cautious)
    - Optimal offer range with justification
    - Talking points and leverage indicators
    - Counter-offer response strategies
    - Deal structure recommendations

    **Wave 3.2** - Negotiation Brain integration
    """
    logger.info(f"Generating negotiation strategy for property {property_id}")

    # Verify property exists
    property = get_property_or_404(property_id, tenant_id, db)

    # Get property fields
    fields = reconstruct_property_fields(property_id, tenant_id, db)

    # Get comp analysis for market context
    comp_analysis = get_comp_analysis(property_id, tenant_id, 20, None, db)

    if "error" in comp_analysis:
        return {
            "error": "Cannot generate negotiation strategy without market analysis",
            "property_id": str(property_id),
            "message": comp_analysis.get("message", "Comp analysis unavailable")
        }

    try:
        # Import Negotiation Brain
        from ml.models.negotiation_brain import (
            NegotiationBrain,
            PropertyContext,
            BuyerConstraints
        )

        # Build property context from comp analysis and fields
        property_context = PropertyContext(
            property_id=str(property_id),
            listing_price=float(fields.get('listing_price', 0)),
            price_per_sqft=comp_analysis.get('subject_price_per_sqft', 0),
            days_on_market=int(fields.get('days_on_market', 0)),
            market_position=comp_analysis.get('market_position', 'fairly_valued'),
            price_deviation_percent=comp_analysis.get('price_deviation_percent', 0),
            negotiation_leverage=comp_analysis.get('negotiation_leverage', 0.5),
            avg_comp_price=comp_analysis.get('avg_comp_price', 0),
            num_comps=comp_analysis.get('num_comps', 0),
            property_type=str(fields.get('property_type', 'Single Family')),
            bedrooms=int(fields.get('bedrooms', 3)),
            bathrooms=float(fields.get('bathrooms', 2.0)),
            square_footage=int(fields.get('square_footage', 2000)),
            condition=fields.get('condition'),
            price_reductions=int(fields.get('price_reductions', 0)),
            price_reduction_amount=float(fields.get('price_reduction_amount', 0)),
            listing_history_days=int(fields.get('listing_history_days', 0))
        )

        # Build buyer constraints
        buyer_constraints = BuyerConstraints(
            max_budget=max_budget,
            preferred_budget=preferred_budget,
            financing_type=financing_type,
            down_payment_percent=down_payment_percent,
            contingencies_required=["inspection", "financing", "appraisal"],
            desired_closing_timeline_days=desired_closing_days,
            flexibility=flexibility
        )

        # Generate recommendation
        brain = NegotiationBrain()
        recommendation = brain.recommend(property_context, buyer_constraints)

        # Format response
        return {
            "property_id": recommendation.property_id,
            "strategy": recommendation.strategy.value,
            "strategy_confidence": round(recommendation.strategy_confidence, 3),
            "strategy_rationale": recommendation.strategy_rationale,
            "recommended_initial_offer": round(recommendation.recommended_initial_offer, 2),
            "recommended_max_offer": round(recommendation.recommended_max_offer, 2),
            "walk_away_price": round(recommendation.walk_away_price, 2),
            "offer_justification": recommendation.offer_justification,
            "market_condition": recommendation.market_condition.value,
            "seller_motivation": recommendation.seller_motivation.value,
            "talking_points": [
                {
                    "category": tp.category,
                    "point": tp.point,
                    "evidence": tp.evidence,
                    "weight": round(tp.weight, 2)
                }
                for tp in recommendation.talking_points
            ],
            "counter_offer_strategy": {
                "initial_counter_max_increase": round(recommendation.counter_offer_strategy.initial_counter_max_increase, 2),
                "walk_away_price": round(recommendation.counter_offer_strategy.walk_away_price, 2),
                "concession_strategy": recommendation.counter_offer_strategy.concession_strategy,
                "alternative_concessions": recommendation.counter_offer_strategy.alternative_concessions
            },
            "deal_structure": {
                "contingencies": recommendation.deal_structure.contingencies,
                "inspection_period_days": recommendation.deal_structure.inspection_period_days,
                "closing_timeline_days": recommendation.deal_structure.closing_timeline_days,
                "earnest_money_percent": recommendation.deal_structure.earnest_money_percent,
                "escalation_clause": recommendation.deal_structure.escalation_clause,
                "appraisal_gap_coverage": recommendation.deal_structure.appraisal_gap_coverage,
                "seller_concessions_target": recommendation.deal_structure.seller_concessions_target
            },
            "key_risks": recommendation.key_risks,
            "key_opportunities": recommendation.key_opportunities,
            "recommended_response_time": recommendation.recommended_response_time,
            "created_at": recommendation.created_at.isoformat()
        }

    except Exception as e:
        logger.error(f"Negotiation strategy generation failed: {e}")
        return {
            "error": "Negotiation strategy service unavailable",
            "property_id": str(property_id),
            "message": str(e)
        }


# =====================================================================
# WAVE 4.1: OFFER WIZARD ENDPOINT
# =====================================================================

@router.post("/{property_id}/offer-wizard")
def get_offer_scenarios(
    property_id: UUID,
    tenant_id: UUID = Query(..., description="Tenant ID"),
    max_price: float = Body(..., embed=True, description="Maximum price (hard constraint)"),
    target_price: float = Body(..., embed=True, description="Target price (soft preference)"),
    max_closing_days: int = Body(60, embed=True, description="Maximum closing days"),
    target_closing_days: int = Body(30, embed=True, description="Target closing days"),
    min_inspection_days: int = Body(7, embed=True, description="Minimum inspection period"),
    financing_required: bool = Body(True, embed=True, description="Financing contingency required"),
    risk_tolerance: str = Body("moderate", embed=True, description="Risk tolerance: low/moderate/high"),
    objectives: List[str] = Body(
        ["maximize_acceptance", "minimize_price"],
        embed=True,
        description="Ordered objectives"
    ),
    db: Session = Depends(get_db)
):
    """
    Generate optimal offer scenarios using constraint satisfaction and multi-objective optimization

    Returns ranked deal structures optimized for buyer's objectives while respecting hard constraints.

    **Wave 4.1** - Offer Wizard
    """
    logger.info(f"Generating offer scenarios for property {property_id}")

    # Verify property exists
    property = get_property_or_404(property_id, tenant_id, db)
    fields = reconstruct_property_fields(property_id, tenant_id, db)

    # Get market analysis for context
    comp_analysis = get_comp_analysis(property_id, tenant_id, 20, None, db)

    if "error" in comp_analysis:
        return {
            "error": "Cannot generate offer scenarios without market analysis",
            "property_id": str(property_id),
            "message": comp_analysis.get("message", "Comp analysis unavailable")
        }

    try:
        from ml.models.offer_wizard import (
            OfferWizard,
            HardConstraints,
            SoftPreferences,
            MarketInputs,
            ObjectiveType
        )

        # Build hard constraints
        hard_constraints = HardConstraints(
            max_price=max_price,
            max_closing_days=max_closing_days,
            min_inspection_days=min_inspection_days,
            required_contingencies=["inspection"],
            financing_contingency_required=financing_required
        )

        # Build soft preferences
        objective_map = {
            "minimize_price": ObjectiveType.MINIMIZE_PRICE,
            "maximize_acceptance": ObjectiveType.MAXIMIZE_ACCEPTANCE,
            "minimize_risk": ObjectiveType.MINIMIZE_RISK,
            "minimize_time": ObjectiveType.MINIMIZE_TIME,
            "maximize_flexibility": ObjectiveType.MAXIMIZE_FLEXIBILITY
        }
        parsed_objectives = [objective_map.get(obj, ObjectiveType.MAXIMIZE_ACCEPTANCE) for obj in objectives]

        soft_preferences = SoftPreferences(
            target_price=target_price,
            target_closing_days=target_closing_days,
            preferred_contingencies=["inspection", "financing", "appraisal"],
            risk_tolerance=risk_tolerance,
            objectives=parsed_objectives
        )

        # Build market inputs
        market_inputs = MarketInputs(
            listing_price=float(fields.get('listing_price', 0)),
            estimated_market_value=comp_analysis.get('avg_comp_price', 0),
            days_on_market=int(fields.get('days_on_market', 0)),
            competing_offers_likelihood=0.3,  # Default
            seller_motivation=comp_analysis.get('negotiation_leverage', 0.5),
            market_velocity="warm",  # Default
            property_condition=fields.get('condition', 'good')
        )

        # Run Offer Wizard
        wizard = OfferWizard()
        result = wizard.create_offer_scenarios(
            hard_constraints,
            soft_preferences,
            market_inputs
        )

        # Format response
        if not result.recommended:
            return {
                "property_id": str(property_id),
                "error": "No feasible scenarios found",
                "infeasible_reasons": result.infeasible_reasons,
                "market_summary": result.market_summary
            }

        return {
            "property_id": str(property_id),
            "market_summary": result.market_summary,
            "recommended_scenario": {
                "name": result.recommended.name,
                "rank": result.recommended.rank,
                "offer_price": result.recommended.deal.offer_price,
                "earnest_money": result.recommended.deal.earnest_money,
                "closing_days": result.recommended.deal.closing_days,
                "inspection_period_days": result.recommended.deal.inspection_period_days,
                "contingencies": result.recommended.deal.contingencies,
                "escalation_clause": result.recommended.deal.escalation_clause,
                "escalation_max": result.recommended.deal.escalation_max,
                "appraisal_gap_coverage": result.recommended.deal.appraisal_gap_coverage,
                "deal_risk": result.recommended.deal.deal_risk.value,
                "acceptance_probability": round(result.recommended.deal.acceptance_probability, 3),
                "competitive_score": round(result.recommended.deal.competitive_score, 3),
                "scores": {
                    "price": round(result.recommended.price_score, 3),
                    "acceptance": round(result.recommended.acceptance_score, 3),
                    "risk": round(result.recommended.risk_score, 3),
                    "time": round(result.recommended.time_score, 3),
                    "flexibility": round(result.recommended.flexibility_score, 3),
                    "overall": round(result.recommended.overall_score, 3)
                },
                "strengths": result.recommended.strengths,
                "weaknesses": result.recommended.weaknesses,
                "tradeoffs": result.recommended.tradeoffs
            },
            "all_scenarios": [
                {
                    "name": scenario.name,
                    "rank": scenario.rank,
                    "offer_price": scenario.deal.offer_price,
                    "closing_days": scenario.deal.closing_days,
                    "contingencies": scenario.deal.contingencies,
                    "acceptance_probability": round(scenario.deal.acceptance_probability, 3),
                    "overall_score": round(scenario.overall_score, 3),
                    "strengths": scenario.strengths,
                    "weaknesses": scenario.weaknesses
                }
                for scenario in result.scenarios
            ],
            "infeasible_reasons": result.infeasible_reasons,
            "created_at": result.created_at.isoformat()
        }

    except Exception as e:
        logger.error(f"Offer Wizard failed: {e}")
        return {
            "error": "Offer Wizard service unavailable",
            "property_id": str(property_id),
            "message": str(e)
        }
