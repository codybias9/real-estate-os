"""
Base plugin interface for enrichment
All enrichment plugins must implement EnrichmentPlugin
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field

# Import contracts
try:
    from contracts import PropertyRecord, Provenance
except ImportError:
    import sys
    sys.path.insert(0, '/home/user/real-estate-os/packages/contracts/src')
    from contracts import PropertyRecord, Provenance


class PluginPriority(int, Enum):
    """Plugin execution priority (lower number = higher priority)"""
    CRITICAL = 0  # Must run first (e.g., geocoding for address validation)
    HIGH = 10
    MEDIUM = 20
    LOW = 30


class PluginResult(BaseModel):
    """Result from a single plugin execution"""
    plugin_name: str = Field(..., description="Plugin identifier")
    success: bool = Field(..., description="Whether plugin succeeded")
    fields_updated: list[str] = Field(default_factory=list, description="List of fields updated")
    provenance_added: list[Provenance] = Field(default_factory=list, description="Provenance records added")
    error: str | None = Field(None, description="Error message if failed")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Plugin-specific metadata")


class EnrichmentPlugin(ABC):
    """
    Base class for all enrichment plugins.

    Plugins are composable and executed in priority order.
    Each plugin enriches specific fields and adds provenance.
    """

    def __init__(self, name: str, priority: PluginPriority = PluginPriority.MEDIUM):
        self.name = name
        self.priority = priority
        self.enabled = True

    @abstractmethod
    async def enrich(self, record: PropertyRecord) -> PluginResult:
        """
        Enrich a property record.

        Args:
            record: PropertyRecord to enrich (will be mutated in place)

        Returns:
            PluginResult with success status and fields updated
        """
        pass

    @abstractmethod
    def can_enrich(self, record: PropertyRecord) -> bool:
        """
        Check if this plugin can enrich the given record.

        Returns:
            True if plugin should be executed for this record
        """
        pass

    def get_required_fields(self) -> list[str]:
        """
        Get list of fields required by this plugin.

        Returns:
            List of field paths (e.g., ["address.line1", "address.zip"])
        """
        return []

    def __lt__(self, other: 'EnrichmentPlugin') -> bool:
        """Compare plugins by priority (for sorting)"""
        return self.priority.value < other.priority.value
