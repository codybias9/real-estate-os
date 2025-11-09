"""
Provider configuration and tier management
Defines the hybrid data ladder: Open → Paid → Scrape
"""

from enum import Enum
from pydantic import BaseModel, Field


class ProviderTier(str, Enum):
    """
    Data provider tier in the hybrid ladder.

    Priority (highest to lowest):
    1. OPEN - Free, no restrictions (OpenAddresses, county open data)
    2. PAID - Licensed APIs with usage limits (ATTOM, Regrid, RESO)
    3. SCRAPE - Last resort, respect robots.txt/ToS (30+ day cache)
    """
    OPEN = "open"
    PAID = "paid"
    SCRAPE = "scrape"


class ProviderConfig(BaseModel):
    """
    Provider configuration with cost controls.

    Used by Policy.Kernel to enforce:
    - Source priority (prefer higher tier)
    - Cost caps per tenant
    - Rate limits
    - Cooldown periods
    """

    name: str = Field(..., description="Provider name (e.g., 'attom', 'regrid')")
    tier: ProviderTier = Field(..., description="Provider tier")
    cost_per_call_cents: int = Field(default=0, ge=0, description="Cost per API call (cents)")
    daily_quota: int | None = Field(None, description="Max calls per day (None = unlimited)")
    cooldown_seconds: int = Field(default=0, description="Minimum seconds between calls")

    # Trust/quality metrics
    confidence: float = Field(default=1.0, ge=0, le=1, description="Data quality confidence")
    license_url: str | None = Field(None, description="License/terms URL")

    def is_free(self) -> bool:
        """Check if provider is free"""
        return self.cost_per_call_cents == 0

    def is_scraper(self) -> bool:
        """Check if provider is a scraper"""
        return self.tier == ProviderTier.SCRAPE


# Default provider configurations
DEFAULT_PROVIDERS = [
    # Open tier
    ProviderConfig(
        name="openaddresses",
        tier=ProviderTier.OPEN,
        confidence=0.7,
        license_url="https://openaddresses.io/license"
    ),

    # Paid tier
    ProviderConfig(
        name="attom",
        tier=ProviderTier.PAID,
        cost_per_call_cents=5,
        daily_quota=10000,
        cooldown_seconds=1,
        confidence=0.95,
        license_url="https://api.attomdata.com/terms"
    ),
    ProviderConfig(
        name="regrid",
        tier=ProviderTier.PAID,
        cost_per_call_cents=3,
        daily_quota=15000,
        cooldown_seconds=1,
        confidence=0.92,
        license_url="https://regrid.com/terms"
    ),

    # Scrape tier (last resort)
    ProviderConfig(
        name="clark_county_assessor",
        tier=ProviderTier.SCRAPE,
        cooldown_seconds=30,
        confidence=0.85
    ),
]
