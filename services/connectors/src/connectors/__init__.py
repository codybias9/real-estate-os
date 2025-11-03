"""
Data Connectors Service

External data connectors for Real Estate OS with fallback logic,
cost tracking, and Policy Kernel integration.

Connectors:
- ATTOM: Premium property data (~$0.08/call)
- Regrid: Parcel boundaries and data (~$0.02/call)
- OpenAddresses: Free address geocoding (limited data)
"""

from .base import (
    BaseConnector,
    ConnectorType,
    ConnectorStatus,
    ConnectorConfig,
    ConnectorResponse,
    PropertyData,
)
from .attom import ATTOMConnector, get_attom_connector
from .regrid import RegridConnector, get_regrid_connector
from .openaddresses import OpenAddressesConnector, get_openaddresses_connector
from .manager import (
    ConnectorManager,
    ConnectorStrategy,
    PolicyKernelIntegration,
    get_connector_manager,
)

__all__ = [
    # Base classes
    "BaseConnector",
    "ConnectorType",
    "ConnectorStatus",
    "ConnectorConfig",
    "ConnectorResponse",
    "PropertyData",
    # Connectors
    "ATTOMConnector",
    "get_attom_connector",
    "RegridConnector",
    "get_regrid_connector",
    "OpenAddressesConnector",
    "get_openaddresses_connector",
    # Manager
    "ConnectorManager",
    "ConnectorStrategy",
    "get_connector_manager",
    # Policy Kernel
    "PolicyKernelIntegration",
]
