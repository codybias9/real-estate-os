"""Data propensity router for data signals, enrichment, and provenance tracking."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from enum import Enum
import random

router = APIRouter(prefix="/data-propensity", tags=["data-propensity"])


# ============================================================================
# Enums
# ============================================================================

class SignalType(str, Enum):
    """Type of data signal."""
    distress = "distress"
    motivation = "motivation"
    equity = "equity"
    market_timing = "market_timing"
    legal = "legal"
    financial = "financial"


class SignalStrength(str, Enum):
    """Strength of a signal."""
    strong = "strong"
    moderate = "moderate"
    weak = "weak"


class DataSource(str, Enum):
    """Source of enrichment data."""
    county_assessor = "county_assessor"
    mls = "mls"
    public_records = "public_records"
    tax_records = "tax_records"
    mortgage_records = "mortgage_records"
    court_records = "court_records"
    utility_data = "utility_data"
    web_scraping = "web_scraping"
    third_party_api = "third_party_api"
    manual_entry = "manual_entry"


class DataQuality(str, Enum):
    """Quality level of data."""
    verified = "verified"
    high_confidence = "high_confidence"
    medium_confidence = "medium_confidence"
    low_confidence = "low_confidence"
    unverified = "unverified"


# ============================================================================
# Schemas
# ============================================================================

class DataSignal(BaseModel):
    """Individual data signal indicating opportunity or risk."""
    id: str
    property_id: str
    signal_type: SignalType
    strength: SignalStrength
    title: str
    description: str
    detected_date: str
    data_source: DataSource
    confidence_score: float = Field(..., ge=0, le=1, description="Confidence 0-1")
    impact_score: float = Field(..., ge=0, le=10, description="Potential impact 0-10")
    actionable: bool = Field(description="Whether this signal suggests immediate action")
    metadata: Optional[Dict[str, Any]] = None


class SignalsSummary(BaseModel):
    """Summary of all signals for a property."""
    property_id: str
    total_signals: int
    strong_signals: int
    moderate_signals: int
    weak_signals: int
    signals_by_type: Dict[str, int]
    overall_propensity_score: float = Field(..., ge=0, le=100, description="Overall likelihood to sell")
    last_updated: str


class DataProvenance(BaseModel):
    """Provenance tracking for a piece of data."""
    field_name: str
    value: Any
    source: DataSource
    source_identifier: Optional[str] = Field(None, description="ID or reference in source system")
    acquired_date: str
    last_verified: Optional[str] = None
    confidence: DataQuality
    cost: Optional[float] = Field(None, description="Cost to acquire this data")


class PropertyDataProvenance(BaseModel):
    """Complete provenance for all property data."""
    property_id: str
    total_fields: int
    enriched_fields: int
    completeness_score: float = Field(..., ge=0, le=100)
    provenance_records: List[DataProvenance]
    last_enrichment: str
    next_enrichment_scheduled: Optional[str]


class EnrichmentRequest(BaseModel):
    """Request to enrich property data."""
    property_id: str
    data_sources: List[DataSource] = Field(description="Sources to use for enrichment")
    priority: str = Field(default="normal", description="normal, high, urgent")


class EnrichmentResult(BaseModel):
    """Result of data enrichment."""
    property_id: str
    fields_enriched: int
    fields_updated: int
    new_signals_detected: int
    enrichment_time: float = Field(description="Time taken in seconds")
    sources_used: List[DataSource]
    cost: float
    next_recommended_enrichment: str


class ProvenanceUpdate(BaseModel):
    """Request to update data provenance."""
    property_id: str
    field_name: str
    value: Any
    source: DataSource
    source_identifier: Optional[str] = None
    confidence: DataQuality


# ============================================================================
# Mock Data Store
# ============================================================================

PROPERTY_SIGNALS: Dict[str, List[Dict]] = {
    "prop_001": [
        {
            "id": "sig_001",
            "property_id": "prop_001",
            "signal_type": "distress",
            "strength": "strong",
            "title": "Tax Delinquency Detected",
            "description": "Property has 18 months of unpaid property taxes totaling $14,350",
            "detected_date": "2025-11-08T10:00:00",
            "data_source": "tax_records",
            "confidence_score": 0.95,
            "impact_score": 9.0,
            "actionable": True,
            "metadata": {
                "amount_owed": 14350,
                "months_delinquent": 18,
                "lien_filed": True
            }
        },
        {
            "id": "sig_002",
            "property_id": "prop_001",
            "signal_type": "distress",
            "strength": "moderate",
            "title": "Code Violations",
            "description": "2 open code violations: exterior maintenance, overgrown vegetation",
            "detected_date": "2025-10-25T14:30:00",
            "data_source": "public_records",
            "confidence_score": 0.88,
            "impact_score": 6.0,
            "actionable": True,
            "metadata": {
                "violation_count": 2,
                "violation_types": ["exterior_maintenance", "vegetation"],
                "fines_pending": 500
            }
        },
        {
            "id": "sig_003",
            "property_id": "prop_001",
            "signal_type": "equity",
            "strength": "strong",
            "title": "High Equity Position",
            "description": "Estimated 65% equity ($568,750) - owner purchased in 2005",
            "detected_date": "2025-11-01T09:00:00",
            "data_source": "county_assessor",
            "confidence_score": 0.82,
            "impact_score": 8.0,
            "actionable": True,
            "metadata": {
                "current_value": 875000,
                "mortgage_balance": 306250,
                "equity_amount": 568750,
                "equity_percentage": 0.65
            }
        },
        {
            "id": "sig_004",
            "property_id": "prop_001",
            "signal_type": "motivation",
            "strength": "moderate",
            "title": "Owner Out of State",
            "description": "Owner address is in Texas - property likely investment/rental",
            "detected_date": "2025-10-30T11:00:00",
            "data_source": "public_records",
            "confidence_score": 0.90,
            "impact_score": 7.0,
            "actionable": True,
            "metadata": {
                "owner_state": "TX",
                "property_state": "CA",
                "absentee_landlord": True
            }
        },
        {
            "id": "sig_005",
            "property_id": "prop_001",
            "signal_type": "financial",
            "strength": "weak",
            "title": "Utility Shut-Off Notice",
            "description": "Water service shut-off notice filed 3 months ago",
            "detected_date": "2025-09-15T16:00:00",
            "data_source": "utility_data",
            "confidence_score": 0.75,
            "impact_score": 5.0,
            "actionable": False,
            "metadata": {
                "utility_type": "water",
                "months_ago": 3,
                "status": "resolved"
            }
        }
    ]
}

PROPERTY_PROVENANCE: Dict[str, List[Dict]] = {
    "prop_001": [
        {
            "field_name": "assessed_value",
            "value": 850000,
            "source": "county_assessor",
            "source_identifier": "APN-12345678",
            "acquired_date": "2025-11-01T10:00:00",
            "last_verified": "2025-11-01T10:00:00",
            "confidence": "verified",
            "cost": 0.0
        },
        {
            "field_name": "owner_name",
            "value": "John Smith",
            "source": "public_records",
            "source_identifier": "DEED-2023-00456",
            "acquired_date": "2025-11-01T10:15:00",
            "last_verified": "2025-11-01T10:15:00",
            "confidence": "verified",
            "cost": 0.0
        },
        {
            "field_name": "mortgage_balance",
            "value": 306250,
            "source": "third_party_api",
            "source_identifier": "attom-prop-12345",
            "acquired_date": "2025-11-05T14:30:00",
            "last_verified": "2025-11-05T14:30:00",
            "confidence": "high_confidence",
            "cost": 0.50
        },
        {
            "field_name": "bedrooms",
            "value": 3,
            "source": "county_assessor",
            "source_identifier": "APN-12345678",
            "acquired_date": "2025-11-01T10:00:00",
            "last_verified": "2025-11-01T10:00:00",
            "confidence": "verified",
            "cost": 0.0
        },
        {
            "field_name": "bathrooms",
            "value": 2.5,
            "source": "county_assessor",
            "source_identifier": "APN-12345678",
            "acquired_date": "2025-11-01T10:00:00",
            "last_verified": "2025-11-01T10:00:00",
            "confidence": "verified",
            "cost": 0.0
        },
        {
            "field_name": "square_feet",
            "value": 2200,
            "source": "county_assessor",
            "source_identifier": "APN-12345678",
            "acquired_date": "2025-11-01T10:00:00",
            "last_verified": "2025-11-01T10:00:00",
            "confidence": "verified",
            "cost": 0.0
        },
        {
            "field_name": "year_built",
            "value": 1985,
            "source": "county_assessor",
            "source_identifier": "APN-12345678",
            "acquired_date": "2025-11-01T10:00:00",
            "last_verified": "2025-11-01T10:00:00",
            "confidence": "verified",
            "cost": 0.0
        },
        {
            "field_name": "last_sale_date",
            "value": "2005-06-15",
            "source": "public_records",
            "source_identifier": "DEED-2005-00234",
            "acquired_date": "2025-11-01T10:15:00",
            "last_verified": "2025-11-01T10:15:00",
            "confidence": "verified",
            "cost": 0.0
        },
        {
            "field_name": "last_sale_price",
            "value": 425000,
            "source": "public_records",
            "source_identifier": "DEED-2005-00234",
            "acquired_date": "2025-11-01T10:15:00",
            "last_verified": "2025-11-01T10:15:00",
            "confidence": "verified",
            "cost": 0.0
        },
        {
            "field_name": "zoning",
            "value": "R-1",
            "source": "county_assessor",
            "source_identifier": "APN-12345678",
            "acquired_date": "2025-11-01T10:00:00",
            "last_verified": "2025-11-01T10:00:00",
            "confidence": "verified",
            "cost": 0.0
        },
        {
            "field_name": "lot_size",
            "value": 6500,
            "source": "county_assessor",
            "source_identifier": "APN-12345678",
            "acquired_date": "2025-11-01T10:00:00",
            "last_verified": "2025-11-01T10:00:00",
            "confidence": "verified",
            "cost": 0.0
        },
        {
            "field_name": "estimated_rent",
            "value": 3500,
            "source": "third_party_api",
            "source_identifier": "rentometer-12345",
            "acquired_date": "2025-11-08T09:00:00",
            "last_verified": "2025-11-08T09:00:00",
            "confidence": "medium_confidence",
            "cost": 0.25
        }
    ]
}


# ============================================================================
# Data Signals Endpoints
# ============================================================================

@router.get("/properties/{property_id}/signals", response_model=List[DataSignal])
def get_property_signals(
    property_id: str,
    signal_type: Optional[SignalType] = None,
    min_strength: Optional[SignalStrength] = None
):
    """
    Get data signals for a property.

    Signals indicate opportunities, risks, or owner motivations based on
    enrichment data. Can filter by type and minimum strength.
    """
    if property_id not in PROPERTY_SIGNALS:
        return []

    signals = PROPERTY_SIGNALS[property_id]

    # Filter by type
    if signal_type:
        signals = [s for s in signals if s["signal_type"] == signal_type.value]

    # Filter by strength
    if min_strength:
        strength_order = {"weak": 0, "moderate": 1, "strong": 2}
        min_level = strength_order[min_strength.value]
        signals = [
            s for s in signals
            if strength_order[s["strength"]] >= min_level
        ]

    return [DataSignal(**signal) for signal in signals]


@router.get("/properties/{property_id}/signals/summary", response_model=SignalsSummary)
def get_signals_summary(property_id: str):
    """
    Get summary of all signals for a property.

    Returns counts by type and strength, plus overall propensity score.
    """
    if property_id not in PROPERTY_SIGNALS:
        return SignalsSummary(
            property_id=property_id,
            total_signals=0,
            strong_signals=0,
            moderate_signals=0,
            weak_signals=0,
            signals_by_type={},
            overall_propensity_score=50.0,
            last_updated=datetime.now().isoformat()
        )

    signals = PROPERTY_SIGNALS[property_id]

    # Count by strength
    strong = sum(1 for s in signals if s["strength"] == "strong")
    moderate = sum(1 for s in signals if s["strength"] == "moderate")
    weak = sum(1 for s in signals if s["strength"] == "weak")

    # Count by type
    by_type = {}
    for signal in signals:
        sig_type = signal["signal_type"]
        by_type[sig_type] = by_type.get(sig_type, 0) + 1

    # Calculate overall propensity score (0-100)
    # Weighted by strength and impact
    total_score = 0
    for signal in signals:
        strength_weight = {"weak": 0.5, "moderate": 1.0, "strong": 2.0}
        score = signal["impact_score"] * strength_weight[signal["strength"]]
        total_score += score

    # Normalize to 0-100
    propensity_score = min(100, (total_score / len(signals)) * 10) if signals else 50.0

    return SignalsSummary(
        property_id=property_id,
        total_signals=len(signals),
        strong_signals=strong,
        moderate_signals=moderate,
        weak_signals=weak,
        signals_by_type=by_type,
        overall_propensity_score=round(propensity_score, 1),
        last_updated=datetime.now().isoformat()
    )


# ============================================================================
# Data Provenance Endpoints
# ============================================================================

@router.get("/properties/{property_id}/provenance", response_model=PropertyDataProvenance)
def get_property_provenance(property_id: str):
    """
    Get data provenance for all property fields.

    Shows where each piece of data came from, when it was acquired,
    and confidence level.
    """
    if property_id not in PROPERTY_PROVENANCE:
        return PropertyDataProvenance(
            property_id=property_id,
            total_fields=50,
            enriched_fields=0,
            completeness_score=0.0,
            provenance_records=[],
            last_enrichment=datetime.now().isoformat(),
            next_enrichment_scheduled=None
        )

    provenance = PROPERTY_PROVENANCE[property_id]

    # Calculate completeness (mock: assume 50 total possible fields)
    total_fields = 50
    enriched = len(provenance)
    completeness = (enriched / total_fields) * 100

    return PropertyDataProvenance(
        property_id=property_id,
        total_fields=total_fields,
        enriched_fields=enriched,
        completeness_score=round(completeness, 1),
        provenance_records=[DataProvenance(**p) for p in provenance],
        last_enrichment=max(p["acquired_date"] for p in provenance),
        next_enrichment_scheduled=(datetime.now() + timedelta(days=30)).isoformat()
    )


@router.post("/provenance/update-source", status_code=200)
def update_data_source(update: ProvenanceUpdate):
    """
    Update data provenance for a property field.

    Records the source, confidence, and acquisition details for a data point.
    """
    if update.property_id not in PROPERTY_PROVENANCE:
        PROPERTY_PROVENANCE[update.property_id] = []

    provenance = PROPERTY_PROVENANCE[update.property_id]

    # Check if field already has provenance
    existing = next(
        (p for p in provenance if p["field_name"] == update.field_name),
        None
    )

    new_record = {
        "field_name": update.field_name,
        "value": update.value,
        "source": update.source.value,
        "source_identifier": update.source_identifier,
        "acquired_date": datetime.now().isoformat(),
        "last_verified": datetime.now().isoformat(),
        "confidence": update.confidence.value,
        "cost": 0.0  # Could be calculated based on source
    }

    if existing:
        # Update existing record
        provenance.remove(existing)
        provenance.append(new_record)
    else:
        # Add new record
        provenance.append(new_record)

    return {
        "success": True,
        "property_id": update.property_id,
        "field_name": update.field_name,
        "source": update.source.value,
        "message": "Provenance updated successfully"
    }


# ============================================================================
# Data Enrichment Endpoints
# ============================================================================

@router.post("/properties/{property_id}/enrich", response_model=EnrichmentResult)
def enrich_property_data(property_id: str, request: EnrichmentRequest):
    """
    Trigger data enrichment for a property.

    Pulls data from specified sources to fill gaps in property information.
    Detects new signals based on enriched data.
    """
    # Mock enrichment process
    fields_enriched = random.randint(5, 15)
    fields_updated = random.randint(2, 8)
    new_signals = random.randint(0, 3)
    enrichment_time = random.uniform(2.5, 8.5)

    # Mock cost calculation
    cost_per_source = {
        "county_assessor": 0.0,
        "public_records": 0.0,
        "tax_records": 0.0,
        "mortgage_records": 0.25,
        "third_party_api": 0.50,
        "mls": 1.00
    }

    total_cost = sum(cost_per_source.get(src.value, 0.0) for src in request.data_sources)

    return EnrichmentResult(
        property_id=property_id,
        fields_enriched=fields_enriched,
        fields_updated=fields_updated,
        new_signals_detected=new_signals,
        enrichment_time=round(enrichment_time, 2),
        sources_used=request.data_sources,
        cost=round(total_cost, 2),
        next_recommended_enrichment=(datetime.now() + timedelta(days=30)).isoformat()
    )


@router.get("/enrichment/stats")
def get_enrichment_stats():
    """
    Get statistics about data enrichment across all properties.

    Shows enrichment rates, costs, and data quality metrics.
    """
    return {
        "total_properties": 12487,
        "fully_enriched": 9115,
        "partially_enriched": 2847,
        "not_enriched": 525,
        "average_completeness": 73.2,
        "total_enrichment_cost_30d": round(random.uniform(500, 1500), 2),
        "average_cost_per_property": round(random.uniform(0.50, 2.00), 2),
        "enrichment_jobs_24h": random.randint(50, 200),
        "failed_enrichments_24h": random.randint(2, 10),
        "sources_used": {
            "county_assessor": random.randint(1000, 2000),
            "public_records": random.randint(800, 1500),
            "third_party_api": random.randint(300, 800),
            "tax_records": random.randint(500, 1200),
            "mls": random.randint(100, 400)
        },
        "average_enrichment_time": round(random.uniform(3.0, 7.0), 2)
    }


@router.get("/signals/trending")
def get_trending_signals(days: int = 30, limit: int = 10):
    """
    Get trending signals across all properties.

    Shows which signal types are appearing most frequently recently.
    """
    signal_types = ["distress", "motivation", "equity", "market_timing", "legal", "financial"]

    trending = []
    for sig_type in signal_types:
        trending.append({
            "signal_type": sig_type,
            "count_last_period": random.randint(20, 150),
            "count_previous_period": random.randint(15, 120),
            "trend_direction": random.choice(["up", "down", "stable"]),
            "change_percentage": round(random.uniform(-20, 40), 1),
            "average_strength": random.choice(["weak", "moderate", "strong"])
        })

    # Sort by count
    trending.sort(key=lambda x: x["count_last_period"], reverse=True)

    return trending[:limit]
