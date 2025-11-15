"""Property enrichment API routes."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
import sys
sys.path.insert(0, '/home/user/real-estate-os')

from api.database import get_db
from api.schemas import PropertyEnrichment, EnrichmentCreate
from db.models import PropertyEnrichment as EnrichmentModel, Property as PropertyModel

router = APIRouter(prefix="/api/properties", tags=["enrichment"])


@router.get("/{property_id}/enrichment", response_model=PropertyEnrichment)
def get_property_enrichment(
    property_id: int,
    db: Session = Depends(get_db),
):
    """Get enrichment data for a property."""

    # Check if property exists
    property_obj = db.query(PropertyModel).filter(PropertyModel.id == property_id).first()
    if not property_obj:
        raise HTTPException(status_code=404, detail=f"Property {property_id} not found")

    # Get enrichment
    enrichment = db.query(EnrichmentModel).filter(EnrichmentModel.property_id == property_id).first()

    if not enrichment:
        raise HTTPException(status_code=404, detail=f"Enrichment data not found for property {property_id}")

    return PropertyEnrichment.model_validate(enrichment)


@router.post("/{property_id}/enrich", status_code=202)
def trigger_enrichment(
    property_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Trigger enrichment for a property (async)."""

    # Check if property exists
    property_obj = db.query(PropertyModel).filter(PropertyModel.id == property_id).first()
    if not property_obj:
        raise HTTPException(status_code=404, detail=f"Property {property_id} not found")

    # Add background task to enrich property
    # For now, return accepted status
    # In production, this would trigger an Airflow DAG or Celery task

    return {
        "message": "Enrichment triggered",
        "property_id": property_id,
        "status": "pending",
    }


@router.put("/{property_id}/enrichment", response_model=PropertyEnrichment)
def create_or_update_enrichment(
    property_id: int,
    enrichment_data: EnrichmentCreate,
    db: Session = Depends(get_db),
):
    """Create or update enrichment data for a property."""

    # Check if property exists
    property_obj = db.query(PropertyModel).filter(PropertyModel.id == property_id).first()
    if not property_obj:
        raise HTTPException(status_code=404, detail=f"Property {property_id} not found")

    # Check if enrichment exists
    enrichment = db.query(EnrichmentModel).filter(EnrichmentModel.property_id == property_id).first()

    if enrichment:
        # Update existing
        update_data = enrichment_data.model_dump(exclude_unset=True, exclude={'property_id'})
        for field, value in update_data.items():
            setattr(enrichment, field, value)
    else:
        # Create new
        enrichment_dict = enrichment_data.model_dump()
        enrichment_dict['property_id'] = property_id
        enrichment = EnrichmentModel(**enrichment_dict)
        db.add(enrichment)

    # Update property status
    if property_obj.status == 'new':
        property_obj.status = 'enriched'

    db.commit()
    db.refresh(enrichment)

    return PropertyEnrichment.model_validate(enrichment)
