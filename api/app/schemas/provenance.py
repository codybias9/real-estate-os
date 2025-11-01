"""Pydantic schemas for provenance and property endpoints

These schemas define the API request/response models for:
- Property details with provenance
- Field history
- Score explainability
- Trust ledger events
"""
from pydantic import BaseModel, Field, UUID4, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal


# =====================================================================
# FIELD PROVENANCE
# =====================================================================

class FieldProvenanceBase(BaseModel):
    """Base provenance information for a field"""
    source_system: Optional[str] = Field(None, description="Source system (e.g., 'census_api', 'fsbo_scraper')")
    source_url: Optional[str] = Field(None, description="URL where data was extracted")
    method: Optional[str] = Field(None, description="Extraction method: 'scrape', 'api', 'manual', 'computed'")
    confidence: Optional[Decimal] = Field(None, ge=0, le=1, description="Confidence score (0-1)")
    version: int = Field(..., description="Version number of this field value")
    extracted_at: datetime = Field(..., description="When this value was extracted")


class FieldProvenanceDetail(FieldProvenanceBase):
    """Detailed provenance for a single field"""
    id: UUID4
    entity_type: str
    entity_id: UUID4
    field_path: str
    value: Any
    created_at: datetime

    model_config = {"from_attributes": True}


class FieldHistory(BaseModel):
    """History of values for a single field"""
    field_path: str
    current_value: Any
    current_version: int
    history: List[FieldProvenanceDetail] = Field(default_factory=list)
    total_versions: int


# =====================================================================
# PROPERTY
# =====================================================================

class PropertyAddress(BaseModel):
    """Structured address"""
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    county: Optional[str] = None
    full_address: Optional[str] = None


class PropertyBase(BaseModel):
    """Base property information"""
    canonical_address: Dict[str, Any]
    parcel: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None


class PropertyWithProvenance(PropertyBase):
    """Property with provenance metadata for all fields"""
    id: UUID4
    tenant_id: UUID4

    # Fields with provenance
    fields: Dict[str, Any] = Field(default_factory=dict, description="Property field values")
    provenance: Dict[str, FieldProvenanceBase] = Field(
        default_factory=dict,
        description="Provenance metadata for each field (key = field_path)"
    )

    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PropertyDetail(PropertyWithProvenance):
    """Complete property details including relationships"""
    owners: List['OwnerEntitySummary'] = Field(default_factory=list)
    scorecards: List['ScorecardSummary'] = Field(default_factory=list)
    deals: List['DealSummary'] = Field(default_factory=list)


# =====================================================================
# OWNER ENTITY
# =====================================================================

class OwnerEntitySummary(BaseModel):
    """Summary of owner entity"""
    id: UUID4
    name: str
    type: str  # 'person' or 'company'
    role: Optional[str] = None
    confidence: Optional[Decimal] = None

    model_config = {"from_attributes": True}


# =====================================================================
# SCORECARD & EXPLAINABILITY
# =====================================================================

class ScorecardSummary(BaseModel):
    """Summary of property scorecard"""
    id: UUID4
    model_version: str
    score: Decimal
    grade: Optional[str] = None
    confidence: Optional[Decimal] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ShapValue(BaseModel):
    """SHAP value for a single feature"""
    feature: str
    value: float
    display_value: str


class Driver(BaseModel):
    """Score driver (positive or negative)"""
    feature: str
    impact: float  # Positive or negative
    description: str


class Counterfactual(BaseModel):
    """Minimal change to flip grade"""
    field: str
    current_value: Any
    target_value: Any
    impact: str  # e.g., "Would upgrade from B to A"


class ScoreExplainabilityDetail(BaseModel):
    """Detailed score explainability"""
    id: UUID4
    scorecard_id: UUID4
    shap_values: List[ShapValue]
    top_positive_drivers: List[Driver]
    top_negative_drivers: List[Driver]
    counterfactuals: List[Counterfactual] = Field(default_factory=list)
    created_at: datetime

    model_config = {"from_attributes": True}


# =====================================================================
# DEAL
# =====================================================================

class DealSummary(BaseModel):
    """Summary of deal"""
    id: UUID4
    stage: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# =====================================================================
# TRUST LEDGER
# =====================================================================

class EvidenceEventCreate(BaseModel):
    """Create a new evidence event"""
    subject_type: Optional[str] = None
    subject_id: Optional[UUID4] = None
    kind: str = Field(..., description="Type of evidence: 'comps_rationale', 'consent', 'override', 'claim'")
    summary: Optional[str] = None
    uri: Optional[str] = None


class EvidenceEventDetail(EvidenceEventCreate):
    """Detailed evidence event"""
    id: UUID4
    tenant_id: UUID4
    created_by: Optional[UUID4] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# =====================================================================
# API RESPONSES
# =====================================================================

class ProvenanceStatsResponse(BaseModel):
    """Statistics about provenance coverage"""
    total_fields: int
    fields_with_provenance: int
    coverage_percentage: float
    by_source_system: Dict[str, int]
    by_method: Dict[str, int]
    avg_confidence: Optional[float] = None
    stale_fields: int  # Fields not updated in > 30 days


class FieldHistoryResponse(BaseModel):
    """Response for field history endpoint"""
    property_id: UUID4
    field_path: str
    history: List[FieldProvenanceDetail]
    total_versions: int


# Forward references resolution
PropertyDetail.model_rebuild()
