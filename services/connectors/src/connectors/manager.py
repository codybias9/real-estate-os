"""
Connector Manager

Orchestrates multiple data connectors with:
- Fallback logic (ATTOM → Regrid → OpenAddresses)
- Cost tracking
- Policy Kernel integration for budget management
"""

from typing import List, Optional, Dict, Any
from enum import Enum

from .base import BaseConnector, ConnectorResponse, ConnectorType
from .attom import get_attom_connector
from .regrid import get_regrid_connector
from .openaddresses import get_openaddresses_connector


class ConnectorStrategy(str, Enum):
    """Connector selection strategy"""

    COST_OPTIMIZED = "cost_optimized"  # Cheapest first
    QUALITY_OPTIMIZED = "quality_optimized"  # Best data first
    BALANCED = "balanced"  # Balance cost and quality


class ConnectorManager:
    """
    Manages multiple data connectors with fallback logic.

    Features:
    - Automatic fallback when primary connector fails
    - Cost tracking and budget management
    - Policy Kernel integration
    - Connector health monitoring
    """

    def __init__(
        self,
        strategy: ConnectorStrategy = ConnectorStrategy.BALANCED,
        max_cost_per_property: float = 0.20,
    ):
        """
        Initialize connector manager.

        Args:
            strategy: Connector selection strategy
            max_cost_per_property: Maximum cost per property lookup (USD)
        """
        self.strategy = strategy
        self.max_cost_per_property = max_cost_per_property

        # Initialize connectors
        self.connectors: Dict[ConnectorType, BaseConnector] = {
            ConnectorType.ATTOM: get_attom_connector(),
            ConnectorType.REGRID: get_regrid_connector(),
            ConnectorType.OPENADDRESSES: get_openaddresses_connector(),
        }

        # Total cost tracking
        self._total_cost = 0.0
        self._successful_requests = 0
        self._failed_requests = 0

    def get_connector_order(self) -> List[ConnectorType]:
        """
        Get connector order based on strategy.

        Returns:
            List of connector types in priority order
        """
        if self.strategy == ConnectorStrategy.COST_OPTIMIZED:
            # Cheapest first: OpenAddresses → Regrid → ATTOM
            return [
                ConnectorType.OPENADDRESSES,
                ConnectorType.REGRID,
                ConnectorType.ATTOM,
            ]
        elif self.strategy == ConnectorStrategy.QUALITY_OPTIMIZED:
            # Best data first: ATTOM → Regrid → OpenAddresses
            return [
                ConnectorType.ATTOM,
                ConnectorType.REGRID,
                ConnectorType.OPENADDRESSES,
            ]
        else:  # BALANCED
            # Balance: Regrid → ATTOM → OpenAddresses
            return [
                ConnectorType.REGRID,
                ConnectorType.ATTOM,
                ConnectorType.OPENADDRESSES,
            ]

    async def get_property_data(
        self,
        apn: str,
        state: str,
        county: Optional[str] = None,
        preferred_connector: Optional[ConnectorType] = None,
    ) -> ConnectorResponse:
        """
        Get property data with automatic fallback.

        Tries connectors in order until one succeeds or all fail.

        Args:
            apn: Assessor's Parcel Number
            state: State code
            county: County name (optional)
            preferred_connector: Override strategy and use specific connector first

        Returns:
            ConnectorResponse from first successful connector
        """
        # Get connector order
        if preferred_connector:
            # Try preferred first, then fallback to others
            connector_order = [preferred_connector] + [
                c for c in self.get_connector_order() if c != preferred_connector
            ]
        else:
            connector_order = self.get_connector_order()

        last_error = "All connectors failed"
        cumulative_cost = 0.0

        for connector_type in connector_order:
            connector = self.connectors.get(connector_type)

            if not connector:
                continue

            # Check if we've exceeded budget
            if cumulative_cost >= self.max_cost_per_property:
                break

            try:
                # Attempt to get property data
                response = await connector.get_property_data(apn, state, county)

                # Track cost
                cumulative_cost += response.cost
                self._total_cost += response.cost

                # If successful, return immediately
                if response.success:
                    self._successful_requests += 1
                    return response

                # If failed, try next connector
                last_error = response.error or "Unknown error"

            except Exception as e:
                last_error = str(e)
                continue

        # All connectors failed
        self._failed_requests += 1

        return ConnectorResponse(
            success=False,
            connector=connector_order[0] if connector_order else ConnectorType.ATTOM,
            error=f"All connectors failed. Last error: {last_error}",
            cost=cumulative_cost,
        )

    async def health_check_all(self) -> Dict[str, bool]:
        """
        Check health of all connectors.

        Returns:
            Dictionary mapping connector type to health status
        """
        results = {}

        for connector_type, connector in self.connectors.items():
            try:
                healthy = await connector.health_check()
                results[connector_type.value] = healthy
            except Exception:
                results[connector_type.value] = False

        return results

    def get_stats(self) -> Dict[str, Any]:
        """
        Get connector manager statistics.

        Returns:
            Dictionary with request counts, costs, and connector stats
        """
        return {
            "strategy": self.strategy.value,
            "total_cost": round(self._total_cost, 2),
            "max_cost_per_property": self.max_cost_per_property,
            "successful_requests": self._successful_requests,
            "failed_requests": self._failed_requests,
            "success_rate": (
                round(
                    self._successful_requests
                    / (self._successful_requests + self._failed_requests),
                    2,
                )
                if (self._successful_requests + self._failed_requests) > 0
                else 0.0
            ),
            "connectors": {
                connector_type.value: connector.get_stats()
                for connector_type, connector in self.connectors.items()
            },
        }

    def reset_stats(self):
        """Reset statistics for all connectors"""
        self._total_cost = 0.0
        self._successful_requests = 0
        self._failed_requests = 0

        for connector in self.connectors.values():
            connector._request_count = 0
            connector._total_cost = 0.0


class PolicyKernelIntegration:
    """
    Integration with Policy Kernel for budget management.

    The Policy Kernel tracks API costs and enforces budget limits per tenant.
    """

    def __init__(self, tenant_id: str, monthly_budget: float = 100.0):
        """
        Initialize Policy Kernel integration.

        Args:
            tenant_id: Tenant ID
            monthly_budget: Monthly API budget in USD
        """
        self.tenant_id = tenant_id
        self.monthly_budget = monthly_budget
        self._spent_this_month = 0.0

    def can_make_request(self, estimated_cost: float) -> bool:
        """
        Check if request is within budget.

        Args:
            estimated_cost: Estimated cost of request

        Returns:
            True if request can be made within budget
        """
        return (self._spent_this_month + estimated_cost) <= self.monthly_budget

    def record_cost(self, actual_cost: float):
        """
        Record actual cost of request.

        Args:
            actual_cost: Actual cost in USD
        """
        self._spent_this_month += actual_cost

    def get_remaining_budget(self) -> float:
        """
        Get remaining budget for the month.

        Returns:
            Remaining budget in USD
        """
        return max(0.0, self.monthly_budget - self._spent_this_month)

    def get_usage_stats(self) -> Dict[str, Any]:
        """
        Get budget usage statistics.

        Returns:
            Dictionary with budget info
        """
        return {
            "tenant_id": self.tenant_id,
            "monthly_budget": self.monthly_budget,
            "spent_this_month": round(self._spent_this_month, 2),
            "remaining": round(self.get_remaining_budget(), 2),
            "usage_percentage": round(
                (self._spent_this_month / self.monthly_budget) * 100, 1
            )
            if self.monthly_budget > 0
            else 0.0,
        }


# Global connector manager instance
_connector_manager: Optional[ConnectorManager] = None


def get_connector_manager(
    strategy: ConnectorStrategy = ConnectorStrategy.BALANCED,
) -> ConnectorManager:
    """
    Get global connector manager instance.

    Args:
        strategy: Connector selection strategy

    Returns:
        ConnectorManager instance
    """
    global _connector_manager

    if _connector_manager is None:
        _connector_manager = ConnectorManager(strategy=strategy)

    return _connector_manager
