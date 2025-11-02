"""
Real Estate Platform - Canonical Contracts
Defines the message envelope and payload schemas for event-driven architecture.
"""

from .envelope import Envelope
from .property_record import PropertyRecord, Address, Geo, Owner, OwnerType, Attributes, Provenance
from .score_result import ScoreResult, ScoreReason, ScoreDirection
from .memo_ready import MemoReady
from .outreach_status import OutreachStatus, OutreachChannel, OutreachStatusType

__all__ = [
    "Envelope",
    "PropertyRecord",
    "Address",
    "Geo",
    "Owner",
    "OwnerType",
    "Attributes",
    "Provenance",
    "ScoreResult",
    "ScoreReason",
    "ScoreDirection",
    "MemoReady",
    "OutreachStatus",
    "OutreachChannel",
    "OutreachStatusType",
]
