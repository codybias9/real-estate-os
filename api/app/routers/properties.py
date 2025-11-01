"""Property router with provenance endpoints

Provides API endpoints for:
- GET /properties/{id} - Property details with provenance
- GET /properties/{id}/provenance - Provenance statistics
- GET /properties/{id}/history/{field_path} - Field history
- GET /properties/{id}/scorecard - Latest scorecard with explainability
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc
from typing import List, Optional
from uuid import UUID
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
