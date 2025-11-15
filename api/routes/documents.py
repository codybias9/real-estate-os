"""Document generation API routes."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Response
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import os
import sys
sys.path.insert(0, '/home/user/real-estate-os')

from api.database import get_db
from api.schemas import GeneratedDocument, DocumentCreate, DocumentType
from db.models import GeneratedDocument as DocumentModel, Property as PropertyModel
from agents.docgen.service import DocumentService

router = APIRouter(prefix="/api/properties", tags=["documents"])


@router.get("/{property_id}/documents", response_model=List[GeneratedDocument])
def list_property_documents(
    property_id: int,
    db: Session = Depends(get_db),
):
    """List all documents for a property."""

    # Check if property exists
    property_obj = db.query(PropertyModel).filter(PropertyModel.id == property_id).first()
    if not property_obj:
        raise HTTPException(status_code=404, detail=f"Property {property_id} not found")

    # Get documents
    documents = db.query(DocumentModel).filter(DocumentModel.property_id == property_id).all()

    return [GeneratedDocument.model_validate(doc) for doc in documents]


@router.get("/{property_id}/memo", response_model=GeneratedDocument)
def get_property_memo(
    property_id: int,
    generate_if_missing: bool = True,
    db: Session = Depends(get_db),
):
    """Get investor memo for a property (generates if not exists)."""

    # Check if property exists
    property_obj = db.query(PropertyModel).filter(PropertyModel.id == property_id).first()
    if not property_obj:
        raise HTTPException(status_code=404, detail=f"Property {property_id} not found")

    # Check if memo exists
    memo = db.query(DocumentModel).filter(
        DocumentModel.property_id == property_id,
        DocumentModel.document_type == DocumentType.INVESTOR_MEMO
    ).first()

    if not memo and generate_if_missing:
        # Create placeholder document record
        # In production, this would trigger PDF generation
        memo_data = {
            "property_id": property_id,
            "document_type": DocumentType.INVESTOR_MEMO,
            "filename": f"investor_memo_{property_id}.pdf",
            "file_path": f"/documents/properties/{property_id}/investor_memo.pdf",
            "file_url": f"http://localhost:8000/api/properties/{property_id}/memo.pdf",
            "status": "pending",
            "generated_by": "system",
        }
        memo = DocumentModel(**memo_data)
        db.add(memo)
        db.commit()
        db.refresh(memo)

    if not memo:
        raise HTTPException(status_code=404, detail=f"Investor memo not found for property {property_id}")

    return GeneratedDocument.model_validate(memo)


@router.post("/{property_id}/generate-memo", status_code=202)
def generate_property_memo(
    property_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Trigger investor memo generation for a property."""

    # Check if property exists
    property_obj = db.query(PropertyModel).filter(PropertyModel.id == property_id).first()
    if not property_obj:
        raise HTTPException(status_code=404, detail=f"Property {property_id} not found")

    # Generate PDF using document service
    try:
        service = DocumentService(db)
        document = service.generate_investor_memo(property_id)

        return {
            "message": "Memo generated successfully",
            "property_id": property_id,
            "document_id": document.id,
            "file_path": document.file_path,
            "status": "completed",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate memo: {str(e)}")


@router.get("/{property_id}/memo.pdf")
def download_property_memo(
    property_id: int,
    db: Session = Depends(get_db),
):
    """Download investor memo PDF."""

    # Check if property exists
    property_obj = db.query(PropertyModel).filter(PropertyModel.id == property_id).first()
    if not property_obj:
        raise HTTPException(status_code=404, detail=f"Property {property_id} not found")

    # Get most recent memo
    memo = db.query(DocumentModel).filter(
        DocumentModel.property_id == property_id,
        DocumentModel.document_type == "investor_memo"
    ).order_by(DocumentModel.generated_at.desc()).first()

    if not memo or not memo.file_path:
        raise HTTPException(status_code=404, detail=f"PDF not available for property {property_id}")

    # Check if file exists
    if not os.path.exists(memo.file_path):
        raise HTTPException(status_code=404, detail=f"PDF file not found at {memo.file_path}")

    # Return the actual PDF file
    return FileResponse(
        path=memo.file_path,
        media_type="application/pdf",
        filename=f"investor_memo_{property_id}.pdf"
    )
