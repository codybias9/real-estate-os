"""
Discovery.Resolver - Normalize scraped data to PropertyRecord
Emits: event.discovery.intake
"""

from .resolver import DiscoveryResolver, IntakeResult, IntakeStatus

__all__ = ["DiscoveryResolver", "IntakeResult", "IntakeStatus"]
