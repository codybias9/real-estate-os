"""
Data Provider Integrations

Implements the "Open Data Ladder" strategy:
1. Free government sources (FEMA, USGS, County GIS)
2. Free community sources (OpenAddresses, OSM, Overture)
3. Computed/derived data
4. Paid sources only when necessary (ATTOM, Regrid)

Each provider module implements a common interface for consistency.
"""

from .base import (
    DataProvider,
    EnrichmentResult,
    ProviderError,
    RateLimitError,
    AuthenticationError
)

# Free Government Sources
from .fema import FEMAProvider
from .usgs import USGSProvider

# Free Community Sources
from .openaddresses import OpenAddressesProvider
from .osm import OpenStreetMapProvider
from .overture import OvertureProvider
from .ms_buildings import MSBuildingFootprintsProvider

# Paid Sources
from .attom import ATTOMProvider
from .regrid import RegridProvider

# Provider registry
PROVIDERS = {
    # Government (free)
    "FEMA_NFHL": FEMAProvider,
    "USGS_Earthquake": USGSProvider,

    # Community (free)
    "OpenAddresses": OpenAddressesProvider,
    "OpenStreetMap": OpenStreetMapProvider,
    "Overture_Maps": OvertureProvider,
    "MS_Building_Footprints": MSBuildingFootprintsProvider,

    # Paid
    "ATTOM": ATTOMProvider,
    "Regrid": RegridProvider,
}


def get_provider(name: str, **config) -> DataProvider:
    """
    Get data provider instance by name

    Args:
        name: Provider name (e.g., "ATTOM", "OpenAddresses")
        **config: Provider-specific configuration

    Returns:
        DataProvider instance

    Raises:
        ValueError: If provider name not found

    Example:
        provider = get_provider("ATTOM", api_key=os.getenv("ATTOM_API_KEY"))
        result = provider.enrich_property(address="123 Main St", city="Los Angeles", state="CA")
    """
    if name not in PROVIDERS:
        raise ValueError(f"Unknown provider: {name}. Available: {list(PROVIDERS.keys())}")

    provider_class = PROVIDERS[name]
    return provider_class(**config)


__all__ = [
    "DataProvider",
    "EnrichmentResult",
    "ProviderError",
    "RateLimitError",
    "AuthenticationError",
    "get_provider",
    "PROVIDERS",
    # Individual providers
    "FEMAProvider",
    "USGSProvider",
    "OpenAddressesProvider",
    "OpenStreetMapProvider",
    "OvertureProvider",
    "MSBuildingFootprintsProvider",
    "ATTOMProvider",
    "RegridProvider",
]
