"""
Enrichment Hub - Orchestrates enrichment plugins
Single producer of: event.enrichment.features
"""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

try:
    from contracts import PropertyRecord, Envelope, Provenance
except ImportError:
    import sys
    sys.path.insert(0, '/home/user/real-estate-os/packages/contracts/src')
    from contracts import PropertyRecord, Envelope, Provenance

from .plugins.base import EnrichmentPlugin, PluginResult


logger = logging.getLogger(__name__)


class EnrichmentResult(BaseModel):
    """Result of full enrichment pipeline"""
    property_record: PropertyRecord
    plugins_executed: list[PluginResult]
    total_fields_updated: int
    total_provenance_added: int
    success: bool
    errors: list[str] = Field(default_factory=list)
    duration_ms: float | None = None


class EnrichmentHub:
    """
    Central hub for property enrichment.

    Responsibilities:
    - Register and manage enrichment plugins
    - Execute plugins in priority order
    - Handle plugin failures gracefully (continue on error)
    - Merge provenance from multiple sources
    - Resolve conflicts (prefer higher confidence)
    - Emit event.enrichment.features

    Conflict Resolution Strategy:
    1. If multiple plugins update same field, prefer higher confidence
    2. Store all provenance (even for overridden values)
    3. Latest update wins if confidence is equal
    """

    def __init__(self, tenant_id: UUID):
        self.tenant_id = tenant_id
        self.plugins: list[EnrichmentPlugin] = []
        self.logger = logging.getLogger(f"{__name__}.{tenant_id}")

    def register_plugin(self, plugin: EnrichmentPlugin) -> None:
        """Register an enrichment plugin"""
        self.plugins.append(plugin)
        # Sort plugins by priority
        self.plugins.sort()
        self.logger.info(f"Registered plugin: {plugin.name} (priority={plugin.priority.value})")

    async def enrich(self, record: PropertyRecord) -> EnrichmentResult:
        """
        Run all applicable plugins on a property record.

        Args:
            record: PropertyRecord to enrich (mutated in place)

        Returns:
            EnrichmentResult with summary of changes
        """
        start_time = datetime.utcnow()

        plugin_results: list[PluginResult] = []
        errors: list[str] = []
        total_fields_updated = set()
        total_provenance_added = []

        # Execute plugins in priority order
        for plugin in self.plugins:
            if not plugin.enabled:
                self.logger.debug(f"Skipping disabled plugin: {plugin.name}")
                continue

            if not plugin.can_enrich(record):
                self.logger.debug(f"Plugin {plugin.name} cannot enrich this record")
                continue

            try:
                self.logger.info(f"Executing plugin: {plugin.name}")
                result = await plugin.enrich(record)
                plugin_results.append(result)

                if result.success:
                    total_fields_updated.update(result.fields_updated)
                    total_provenance_added.extend(result.provenance_added)
                    self.logger.info(
                        f"Plugin {plugin.name} succeeded: {len(result.fields_updated)} fields updated"
                    )
                else:
                    errors.append(f"{plugin.name}: {result.error}")
                    self.logger.warning(f"Plugin {plugin.name} failed: {result.error}")

            except Exception as e:
                error_msg = f"{plugin.name}: Unexpected error: {str(e)}"
                errors.append(error_msg)
                self.logger.error(error_msg, exc_info=True)

        # Calculate duration
        end_time = datetime.utcnow()
        duration_ms = (end_time - start_time).total_seconds() * 1000

        # Overall success if at least one plugin succeeded
        success = len([r for r in plugin_results if r.success]) > 0

        return EnrichmentResult(
            property_record=record,
            plugins_executed=plugin_results,
            total_fields_updated=len(total_fields_updated),
            total_provenance_added=len(total_provenance_added),
            success=success,
            errors=errors,
            duration_ms=duration_ms
        )

    def create_enrichment_event(
        self,
        result: EnrichmentResult,
        correlation_id: UUID | None = None,
        causation_id: UUID | None = None
    ) -> Envelope[PropertyRecord]:
        """
        Create event.enrichment.features envelope.

        This is the single producer of enrichment events.
        """
        envelope_id = uuid4()

        envelope = Envelope[PropertyRecord](
            id=envelope_id,
            tenant_id=self.tenant_id,
            subject="event.enrichment.features",
            schema_version="1.0",
            idempotency_key=f"{result.property_record.source}:{result.property_record.source_id}:enriched",
            correlation_id=correlation_id or uuid4(),
            causation_id=causation_id or envelope_id,
            at=datetime.utcnow(),
            payload=result.property_record
        )

        return envelope

    def get_plugin(self, name: str) -> EnrichmentPlugin | None:
        """Get plugin by name"""
        return next((p for p in self.plugins if p.name == name), None)

    def enable_plugin(self, name: str) -> bool:
        """Enable a plugin by name"""
        plugin = self.get_plugin(name)
        if plugin:
            plugin.enabled = True
            return True
        return False

    def disable_plugin(self, name: str) -> bool:
        """Disable a plugin by name"""
        plugin = self.get_plugin(name)
        if plugin:
            plugin.enabled = False
            return True
        return False
