"""Data models for Real Estate OS platform."""

from .property import Property, PropertyCreate, PropertyUpdate, PropertyStatus, PropertyType
from .enrichment import PropertyEnrichment, EnrichmentCreate
from .score import PropertyScore, ScoreCreate, ScoreFeatures
from .document import GeneratedDocument, DocumentCreate, DocumentType
from .campaign import Campaign, CampaignCreate, OutreachLog, OutreachStatus

__all__ = [
    "Property",
    "PropertyCreate",
    "PropertyUpdate",
    "PropertyStatus",
    "PropertyType",
    "PropertyEnrichment",
    "EnrichmentCreate",
    "PropertyScore",
    "ScoreCreate",
    "ScoreFeatures",
    "GeneratedDocument",
    "DocumentCreate",
    "DocumentType",
    "Campaign",
    "CampaignCreate",
    "OutreachLog",
    "OutreachStatus",
]
