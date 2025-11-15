"""API Schemas - Re-export models from src."""

# Import all models from src/models
import sys
sys.path.insert(0, '/home/user/real-estate-os')

from src.models.property import (
    Property,
    PropertyCreate,
    PropertyUpdate,
    PropertyStatus,
    PropertyType,
    PropertyListResponse,
)
from src.models.enrichment import (
    PropertyEnrichment,
    EnrichmentCreate,
)
from src.models.score import (
    PropertyScore,
    ScoreCreate,
    ScoreFeatures,
    ScoreBreakdown,
)
from src.models.document import (
    GeneratedDocument,
    DocumentCreate,
    DocumentType,
    DocumentStatus,
)
from src.models.campaign import (
    Campaign,
    CampaignCreate,
    CampaignStatus,
    OutreachLog,
    OutreachStatus,
)

__all__ = [
    "Property",
    "PropertyCreate",
    "PropertyUpdate",
    "PropertyStatus",
    "PropertyType",
    "PropertyListResponse",
    "PropertyEnrichment",
    "EnrichmentCreate",
    "PropertyScore",
    "ScoreCreate",
    "ScoreFeatures",
    "ScoreBreakdown",
    "GeneratedDocument",
    "DocumentCreate",
    "DocumentType",
    "DocumentStatus",
    "Campaign",
    "CampaignCreate",
    "CampaignStatus",
    "OutreachLog",
    "OutreachStatus",
]
