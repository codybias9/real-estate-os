"""
Enrichment.Hub - Plugin-based property data enrichment
Emits: event.enrichment.features
"""

from .hub import EnrichmentHub, EnrichmentResult
from .plugins.base import EnrichmentPlugin, PluginResult, PluginPriority
from .plugins.geocode import GeocodePlugin
from .plugins.basic_attrs import BasicAttrsPlugin

__all__ = [
    "EnrichmentHub",
    "EnrichmentResult",
    "EnrichmentPlugin",
    "PluginResult",
    "PluginPriority",
    "GeocodePlugin",
    "BasicAttrsPlugin",
]
