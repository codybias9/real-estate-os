"""
Feature Flag System
Controls external channel sending and other feature rollouts
"""

from enum import Enum
from typing import Dict, Any, Optional
from uuid import UUID
import structlog

logger = structlog.get_logger()


class FeatureFlag(str, Enum):
    """Available feature flags"""
    EMAIL_SENDING = "channel.email"
    SMS_SENDING = "channel.sms"
    POSTAL_SENDING = "channel.postal"
    AI_SCORING = "ai.scoring"
    EXTERNAL_DATA = "connectors.external"
    PORTFOLIO_METRICS = "metrics.portfolio"


class FeatureFlagStore:
    """
    Feature flag storage and retrieval
    Supports per-tenant and global flags
    """

    def __init__(self):
        # Global flags (apply to all tenants)
        self.global_flags: Dict[str, bool] = {
            FeatureFlag.EMAIL_SENDING: False,  # Start disabled
            FeatureFlag.SMS_SENDING: False,    # Start disabled
            FeatureFlag.POSTAL_SENDING: False, # Start disabled
            FeatureFlag.AI_SCORING: True,
            FeatureFlag.EXTERNAL_DATA: True,
            FeatureFlag.PORTFOLIO_METRICS: True,
        }

        # Per-tenant overrides {tenant_id: {flag: enabled}}
        self.tenant_flags: Dict[UUID, Dict[str, bool]] = {}

    def is_enabled(
        self,
        flag: FeatureFlag,
        tenant_id: Optional[UUID] = None,
    ) -> bool:
        """
        Check if feature flag is enabled

        Args:
            flag: Feature flag to check
            tenant_id: Optional tenant ID for tenant-specific flags

        Returns:
            True if enabled, False otherwise
        """
        # Check tenant override first
        if tenant_id and tenant_id in self.tenant_flags:
            if flag in self.tenant_flags[tenant_id]:
                enabled = self.tenant_flags[tenant_id][flag]
                logger.info(
                    "flag.check.tenant_override",
                    flag=flag,
                    tenant_id=str(tenant_id),
                    enabled=enabled,
                )
                return enabled

        # Fall back to global flag
        enabled = self.global_flags.get(flag, False)
        logger.info(
            "flag.check.global",
            flag=flag,
            tenant_id=str(tenant_id) if tenant_id else None,
            enabled=enabled,
        )
        return enabled

    def enable_for_tenant(self, flag: FeatureFlag, tenant_id: UUID):
        """Enable flag for specific tenant (canary/beta)"""
        if tenant_id not in self.tenant_flags:
            self.tenant_flags[tenant_id] = {}

        self.tenant_flags[tenant_id][flag] = True

        logger.info(
            "flag.enable.tenant",
            flag=flag,
            tenant_id=str(tenant_id),
        )

    def disable_for_tenant(self, flag: FeatureFlag, tenant_id: UUID):
        """Disable flag for specific tenant"""
        if tenant_id not in self.tenant_flags:
            self.tenant_flags[tenant_id] = {}

        self.tenant_flags[tenant_id][flag] = False

        logger.info(
            "flag.disable.tenant",
            flag=flag,
            tenant_id=str(tenant_id),
        )

    def enable_globally(self, flag: FeatureFlag):
        """Enable flag for all tenants"""
        self.global_flags[flag] = True

        logger.warning(
            "flag.enable.global",
            flag=flag,
        )

    def disable_globally(self, flag: FeatureFlag):
        """Disable flag for all tenants"""
        self.global_flags[flag] = False

        logger.warning(
            "flag.disable.global",
            flag=flag,
        )

    def get_all_flags(self, tenant_id: Optional[UUID] = None) -> Dict[str, bool]:
        """Get all flags (with tenant overrides if provided)"""
        flags = self.global_flags.copy()

        if tenant_id and tenant_id in self.tenant_flags:
            flags.update(self.tenant_flags[tenant_id])

        return flags


# Global instance
_flag_store = FeatureFlagStore()


def is_enabled(flag: FeatureFlag, tenant_id: Optional[UUID] = None) -> bool:
    """Convenience function to check flag"""
    return _flag_store.is_enabled(flag, tenant_id)


def require_flag(flag: FeatureFlag):
    """
    Decorator to require feature flag

    Usage:
        @require_flag(FeatureFlag.EMAIL_SENDING)
        async def send_email(...):
            ...
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Try to extract tenant_id from kwargs
            tenant_id = kwargs.get("tenant_id")

            if not _flag_store.is_enabled(flag, tenant_id):
                logger.warning(
                    "flag.blocked",
                    flag=flag,
                    function=func.__name__,
                    tenant_id=str(tenant_id) if tenant_id else None,
                )
                raise FeatureFlagDisabled(f"Feature {flag} is disabled")

            return await func(*args, **kwargs)

        return wrapper
    return decorator


class FeatureFlagDisabled(Exception):
    """Raised when feature flag is disabled"""
    pass
