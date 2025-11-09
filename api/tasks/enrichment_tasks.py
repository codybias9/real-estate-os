"""
Property Enrichment Background Tasks
Async data fetching from external sources
"""
from celery import shared_task
from datetime import datetime
import logging
from typing import Dict, Any, List, Optional
import random

from api.celery_app import celery_app, get_db_session
from db.models import (
    Property, PropertyProvenance, PropertyTimeline,
    PropensitySignal, BudgetTracking, OpenDataSource
)

logger = logging.getLogger(__name__)

# ============================================================================
# PROPERTY ENRICHMENT TASKS
# ============================================================================

@celery_app.task(bind=True, name="api.tasks.enrichment_tasks.enrich_property_async")
def enrich_property_async(
    self,
    property_id: int,
    sources: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Enrich property with data from external sources

    Args:
        property_id: Property ID
        sources: List of source names to use (None = all active sources)

    Returns:
        Dict with enrichment results and field counts
    """
    logger.info(f"Starting property enrichment for property {property_id}")

    with next(get_db_session()) as db:
        # Fetch property
        property = db.query(Property).filter(Property.id == property_id).first()

        if not property:
            raise ValueError(f"Property {property_id} not found")

        # Get active data sources
        query = db.query(OpenDataSource).filter(OpenDataSource.is_active == True)
        if sources:
            query = query.filter(OpenDataSource.name.in_(sources))

        data_sources = query.all()

        if not data_sources:
            logger.warning(f"No active data sources found for enrichment")
            return {"success": False, "error": "No data sources available"}

        enrichment_results = {
            "property_id": property_id,
            "sources_used": [],
            "fields_updated": [],
            "total_cost": 0.0,
            "errors": []
        }

        try:
            for source in data_sources:
                logger.info(f"Enriching property {property_id} from source: {source.name}")

                try:
                    # Fetch data from source
                    source_data = _fetch_from_source(property, source)

                    if source_data:
                        # Update property fields
                        fields_updated = _apply_enrichment_data(property, source_data, source)

                        # Track provenance
                        for field_name, value in fields_updated.items():
                            provenance = PropertyProvenance(
                                property_id=property_id,
                                field_name=field_name,
                                source_name=source.name,
                                source_tier="free" if source.cost_per_request == 0 else "paid",
                                license_type=source.license_type,
                                cost=source.cost_per_request,
                                fetched_at=datetime.utcnow()
                            )
                            db.add(provenance)

                        # Track budget
                        if source.cost_per_request > 0:
                            team = property.team
                            budget = BudgetTracking(
                                team_id=team.id,
                                provider=source.name,
                                date=datetime.utcnow().date(),
                                requests_made=1,
                                cost=source.cost_per_request,
                                monthly_cap=team.monthly_budget_cap
                            )
                            db.add(budget)

                            enrichment_results["total_cost"] += source.cost_per_request

                        enrichment_results["sources_used"].append(source.name)
                        enrichment_results["fields_updated"].extend(fields_updated.keys())

                except Exception as e:
                    logger.error(f"Failed to enrich from source {source.name}: {str(e)}")
                    enrichment_results["errors"].append({
                        "source": source.name,
                        "error": str(e)
                    })

            # Update property metadata
            property.data_quality_score = _calculate_data_quality(property)
            property.updated_at = datetime.utcnow()

            # Create timeline event
            timeline = PropertyTimeline(
                property_id=property_id,
                event_type="data_enriched",
                event_title="Property Data Enriched",
                event_description=f"Updated {len(enrichment_results['fields_updated'])} fields from {len(enrichment_results['sources_used'])} sources",
                metadata={
                    "sources": enrichment_results["sources_used"],
                    "fields": enrichment_results["fields_updated"],
                    "cost": enrichment_results["total_cost"],
                    "task_id": self.request.id
                }
            )
            db.add(timeline)

            db.commit()

            logger.info(f"Property enrichment completed for property {property_id}")

            enrichment_results["success"] = True
            return enrichment_results

        except Exception as e:
            logger.error(f"Failed to enrich property {property_id}: {str(e)}")
            db.rollback()
            raise


@celery_app.task(bind=True, name="api.tasks.enrichment_tasks.batch_enrich_properties")
def batch_enrich_properties(
    self,
    property_ids: List[int],
    sources: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Enrich multiple properties in batch

    Args:
        property_ids: List of property IDs
        sources: Data sources to use

    Returns:
        Dict with batch results
    """
    logger.info(f"Starting batch enrichment for {len(property_ids)} properties")

    results = {
        "total": len(property_ids),
        "successful": 0,
        "failed": 0,
        "results": []
    }

    for property_id in property_ids:
        try:
            result = enrich_property_async.delay(property_id, sources)

            results["successful"] += 1
            results["results"].append({
                "property_id": property_id,
                "status": "queued",
                "task_id": result.id
            })

        except Exception as e:
            logger.error(f"Failed to queue enrichment for property {property_id}: {str(e)}")
            results["failed"] += 1
            results["results"].append({
                "property_id": property_id,
                "status": "failed",
                "error": str(e)
            })

    return results


@celery_app.task(bind=True, name="api.tasks.enrichment_tasks.update_propensity_scores")
def update_propensity_scores(self, property_ids: Optional[List[int]] = None) -> Dict[str, Any]:
    """
    Update propensity to sell scores for properties

    Uses signals like:
    - Property tax delinquency
    - Foreclosure notices
    - Permit activity
    - Owner age/life events
    - Market conditions

    Args:
        property_ids: Specific property IDs (None = all properties)

    Returns:
        Dict with update results
    """
    logger.info("Starting propensity score update")

    with next(get_db_session()) as db:
        # Get properties to update
        query = db.query(Property)
        if property_ids:
            query = query.filter(Property.id.in_(property_ids))

        properties = query.all()

        results = {
            "total": len(properties),
            "updated": 0,
            "failed": 0
        }

        for property in properties:
            try:
                # Calculate propensity signals
                signals = _calculate_propensity_signals(property)

                # Store signals
                for signal in signals:
                    propensity_signal = PropensitySignal(
                        property_id=property.id,
                        signal_type=signal["type"],
                        signal_value=signal.get("value"),
                        weight=signal.get("weight", 0.5),
                        reasoning=signal.get("reasoning"),
                        detected_at=datetime.utcnow()
                    )
                    db.add(propensity_signal)

                # Calculate overall propensity score
                propensity_score = _calculate_propensity_score(signals)
                property.propensity_to_sell = propensity_score
                property.propensity_signals = [
                    {
                        "type": s["type"],
                        "weight": s.get("weight", 0.5),
                        "reasoning": s.get("reasoning", "")
                    }
                    for s in signals
                ]

                property.updated_at = datetime.utcnow()

                results["updated"] += 1

            except Exception as e:
                logger.error(f"Failed to update propensity for property {property.id}: {str(e)}")
                results["failed"] += 1

        db.commit()

        logger.info(f"Propensity score update completed: {results['updated']} updated, {results['failed']} failed")

        return results


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _fetch_from_source(property: Property, source: OpenDataSource) -> Optional[Dict[str, Any]]:
    """
    Fetch data from external source

    In production, this would make actual API calls to:
    - ATTOM Data
    - Regrid
    - OpenAddresses
    - etc.

    For now, returns simulated data
    """
    # TODO: Implement actual API calls to data providers
    # For now, return simulated data

    if source.name == "ATTOM":
        return {
            "assessed_value": random.randint(150000, 500000),
            "market_value_estimate": random.randint(200000, 600000),
            "year_built": random.randint(1950, 2020),
            "sqft": random.randint(1000, 3000),
            "beds": random.randint(2, 5),
            "baths": random.uniform(1, 3)
        }

    elif source.name == "Regrid":
        return {
            "apn": f"APN{random.randint(1000000, 9999999)}",
            "lot_size": random.uniform(0.1, 2.0),
            "latitude": 34.0522 + random.uniform(-0.5, 0.5),
            "longitude": -118.2437 + random.uniform(-0.5, 0.5)
        }

    return None


def _apply_enrichment_data(
    property: Property,
    data: Dict[str, Any],
    source: OpenDataSource
) -> Dict[str, Any]:
    """
    Apply enrichment data to property

    Only updates fields that are currently None or have lower quality

    Returns dict of updated fields
    """
    updated_fields = {}

    for field_name, value in data.items():
        if hasattr(property, field_name):
            current_value = getattr(property, field_name)

            # Only update if current value is None or empty
            if current_value is None or current_value == "":
                setattr(property, field_name, value)
                updated_fields[field_name] = value

    return updated_fields


def _calculate_data_quality(property: Property) -> float:
    """
    Calculate data quality score (0-1) based on field completeness
    """
    important_fields = [
        "address", "city", "state", "zip_code",
        "beds", "baths", "sqft", "year_built",
        "assessed_value", "owner_name"
    ]

    filled_count = sum(
        1 for field in important_fields
        if getattr(property, field, None) is not None
    )

    return filled_count / len(important_fields)


def _calculate_propensity_signals(property: Property) -> List[Dict[str, Any]]:
    """
    Calculate propensity signals for a property

    In production, this would check:
    - Tax delinquency records
    - Foreclosure filings
    - Permit activity
    - Owner demographics
    - Market trends

    For now, returns simulated signals
    """
    signals = []

    # TODO: Implement real signal detection
    # For now, return random signals for demonstration

    signal_types = [
        ("tax_delinquent", "Property has unpaid property taxes", 0.8),
        ("high_equity", "Owner has >50% equity in property", 0.6),
        ("owner_age", "Owner is retirement age (65+)", 0.5),
        ("vacant", "Property appears vacant", 0.7),
        ("distressed", "Property shows signs of distress", 0.9),
        ("inherited", "Property recently inherited", 0.6),
        ("divorce", "Owner recently divorced", 0.7),
        ("out_of_state", "Owner lives out of state", 0.5)
    ]

    # Randomly select 2-4 signals
    num_signals = random.randint(2, 4)
    selected = random.sample(signal_types, num_signals)

    for signal_type, reasoning, weight in selected:
        signals.append({
            "type": signal_type,
            "reasoning": reasoning,
            "weight": weight
        })

    return signals


def _calculate_propensity_score(signals: List[Dict[str, Any]]) -> float:
    """
    Calculate overall propensity score from signals

    Weighted average of all signal weights
    """
    if not signals:
        return 0.0

    total_weight = sum(s.get("weight", 0.5) for s in signals)
    return min(total_weight / len(signals), 1.0)
