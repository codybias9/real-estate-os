"""
Memo Generation Background Tasks
Async PDF generation and file upload
"""
from celery import shared_task
from datetime import datetime, timedelta
import logging
from typing import Dict, Any, List

from api.celery_app import celery_app, get_db_session
from api.integrations import (
    generate_property_memo,
    generate_offer_packet,
    upload_file,
    get_file_url,
    get_memo_path,
    get_packet_path
)
from db.models import Property, PropertyTimeline

logger = logging.getLogger(__name__)

# ============================================================================
# MEMO GENERATION TASKS
# ============================================================================

@celery_app.task(bind=True, name="api.tasks.memo_tasks.generate_memo_async")
def generate_memo_async(self, property_id: int, template: str = "default") -> Dict[str, Any]:
    """
    Generate property memo PDF asynchronously

    Args:
        property_id: Property ID
        template: Template style (default, minimal, detailed)

    Returns:
        Dict with memo_url, file_size, and property_id

    Raises:
        Exception: If generation or upload fails
    """
    logger.info(f"Starting memo generation for property {property_id}")

    # Get database session
    with next(get_db_session()) as db:
        # Fetch property
        property = db.query(Property).filter(Property.id == property_id).first()

        if not property:
            raise ValueError(f"Property {property_id} not found")

        try:
            # Prepare property data
            property_data = {
                "address": property.address,
                "city": property.city,
                "state": property.state,
                "zip_code": property.zip_code,
                "beds": property.beds,
                "baths": property.baths,
                "sqft": property.sqft,
                "year_built": property.year_built,
                "assessed_value": property.assessed_value,
                "market_value_estimate": property.market_value_estimate,
                "arv": property.arv,
                "repair_estimate": property.repair_estimate,
                "bird_dog_score": property.bird_dog_score,
                "propensity_to_sell": property.propensity_to_sell,
                "score_reasons": property.score_reasons or []
            }

            # Generate PDF
            logger.info(f"Generating PDF for property {property_id}")
            pdf_bytes = generate_property_memo(property_data, template)

            # Upload to storage
            object_name = get_memo_path(property_id)
            logger.info(f"Uploading memo to storage: {object_name}")

            upload_result = upload_file(
                pdf_bytes,
                object_name,
                content_type="application/pdf",
                metadata={
                    "property_id": str(property_id),
                    "template": template,
                    "generated_at": datetime.utcnow().isoformat(),
                    "task_id": self.request.id
                }
            )

            # Generate signed URL (30 day expiration)
            memo_url = get_file_url(object_name, expires=timedelta(days=30))

            # Update property
            property.memo_url = memo_url
            property.memo_generated_at = datetime.utcnow()
            property.updated_at = datetime.utcnow()

            # Create timeline event
            timeline = PropertyTimeline(
                property_id=property_id,
                event_type="memo_generated",
                event_title="Memo Generated",
                event_description=f"Investment memo generated ({template} template)",
                metadata={
                    "memo_url": memo_url,
                    "file_size": upload_result["size"],
                    "template": template,
                    "task_id": self.request.id
                }
            )
            db.add(timeline)

            db.commit()

            logger.info(f"Memo generation completed for property {property_id}")

            return {
                "success": True,
                "property_id": property_id,
                "memo_url": memo_url,
                "file_size": upload_result["size"],
                "object_name": object_name
            }

        except Exception as e:
            logger.error(f"Failed to generate memo for property {property_id}: {str(e)}")
            db.rollback()
            raise


@celery_app.task(bind=True, name="api.tasks.memo_tasks.generate_packet_async")
def generate_packet_async(
    self,
    property_id: int,
    deal_id: int,
    include_comps: bool = True
) -> Dict[str, Any]:
    """
    Generate comprehensive offer packet PDF asynchronously

    Args:
        property_id: Property ID
        deal_id: Deal ID
        include_comps: Whether to include comparable properties

    Returns:
        Dict with packet_url, file_size, and property_id
    """
    logger.info(f"Starting packet generation for property {property_id}, deal {deal_id}")

    with next(get_db_session()) as db:
        from db.models import Deal

        # Fetch property and deal
        property = db.query(Property).filter(Property.id == property_id).first()
        deal = db.query(Deal).filter(Deal.id == deal_id).first()

        if not property:
            raise ValueError(f"Property {property_id} not found")
        if not deal:
            raise ValueError(f"Deal {deal_id} not found")

        try:
            # Prepare property data
            property_data = {
                "address": property.address,
                "city": property.city,
                "state": property.state,
                "zip_code": property.zip_code,
                "beds": property.beds,
                "baths": property.baths,
                "sqft": property.sqft,
                "year_built": property.year_built,
                "assessed_value": property.assessed_value,
                "market_value_estimate": property.market_value_estimate,
                "arv": property.arv,
                "repair_estimate": property.repair_estimate,
                "bird_dog_score": property.bird_dog_score,
                "propensity_to_sell": property.propensity_to_sell,
                "score_reasons": property.score_reasons or []
            }

            # Prepare deal data
            deal_data = {
                "offer_price": deal.offer_price,
                "arv": deal.arv,
                "repair_cost": deal.repair_cost,
                "assignment_fee": deal.assignment_fee,
                "expected_margin": deal.expected_margin,
                "closing_timeline": "30 days",  # TODO: Add to deal model
                "contingencies": "Standard inspection, financing"
            }

            # Get comps if requested
            comps = []
            if include_comps:
                # TODO: Implement comparable properties lookup
                pass

            # Generate PDF
            logger.info(f"Generating offer packet for property {property_id}")
            pdf_bytes = generate_offer_packet(property_data, deal_data, comps)

            # Upload to storage
            object_name = get_packet_path(property_id)
            logger.info(f"Uploading packet to storage: {object_name}")

            upload_result = upload_file(
                pdf_bytes,
                object_name,
                content_type="application/pdf",
                metadata={
                    "property_id": str(property_id),
                    "deal_id": str(deal_id),
                    "generated_at": datetime.utcnow().isoformat(),
                    "task_id": self.request.id
                }
            )

            # Generate signed URL
            packet_url = get_file_url(object_name, expires=timedelta(days=30))

            # Update property
            property.packet_url = packet_url
            property.updated_at = datetime.utcnow()

            # Create timeline event
            timeline = PropertyTimeline(
                property_id=property_id,
                event_type="packet_generated",
                event_title="Offer Packet Generated",
                event_description=f"Comprehensive offer packet created for deal #{deal_id}",
                metadata={
                    "packet_url": packet_url,
                    "file_size": upload_result["size"],
                    "deal_id": deal_id,
                    "task_id": self.request.id
                }
            )
            db.add(timeline)

            db.commit()

            logger.info(f"Packet generation completed for property {property_id}")

            return {
                "success": True,
                "property_id": property_id,
                "deal_id": deal_id,
                "packet_url": packet_url,
                "file_size": upload_result["size"],
                "object_name": object_name
            }

        except Exception as e:
            logger.error(f"Failed to generate packet for property {property_id}: {str(e)}")
            db.rollback()
            raise


@celery_app.task(bind=True, name="api.tasks.memo_tasks.batch_generate_memos")
def batch_generate_memos(self, property_ids: List[int], template: str = "default") -> Dict[str, Any]:
    """
    Generate memos for multiple properties in batch

    Args:
        property_ids: List of property IDs
        template: Template style

    Returns:
        Dict with success/failure counts and results
    """
    logger.info(f"Starting batch memo generation for {len(property_ids)} properties")

    results = {
        "total": len(property_ids),
        "successful": 0,
        "failed": 0,
        "results": []
    }

    for property_id in property_ids:
        try:
            # Chain to individual memo generation task
            result = generate_memo_async.delay(property_id, template)

            results["successful"] += 1
            results["results"].append({
                "property_id": property_id,
                "status": "queued",
                "task_id": result.id
            })

        except Exception as e:
            logger.error(f"Failed to queue memo generation for property {property_id}: {str(e)}")
            results["failed"] += 1
            results["results"].append({
                "property_id": property_id,
                "status": "failed",
                "error": str(e)
            })

    logger.info(f"Batch memo generation queued: {results['successful']} successful, {results['failed']} failed")

    return results
