"""
Document Management API.

Handles:
- Document upload and storage (via MinIO)
- Document metadata and categorization
- Document retrieval and download
- Document OCR and text extraction status
"""
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
import logging
import uuid

from api.auth import get_current_user, User
from api.rate_limit import rate_limit
from api.minio_client import upload_file, download_file

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/documents",
    tags=["documents"]
)


class DocumentType(str, Enum):
    """Document type categories."""
    LEASE = "lease"
    DEED = "deed"
    TITLE = "title"
    INSPECTION = "inspection"
    APPRAISAL = "appraisal"
    INSURANCE = "insurance"
    CONTRACT = "contract"
    FINANCIAL = "financial"
    PHOTO = "photo"
    OTHER = "other"


class DocumentStatus(str, Enum):
    """Document processing status."""
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


class DocumentUploadResponse(BaseModel):
    """Response for document upload."""
    document_id: str
    file_name: str
    file_size: int
    content_type: str
    storage_path: str
    status: DocumentStatus
    message: str


class DocumentMetadata(BaseModel):
    """Document metadata model."""
    id: int
    document_id: str
    property_id: Optional[int]
    document_type: DocumentType
    file_name: str
    file_size: int
    content_type: str
    storage_path: str
    status: DocumentStatus
    ocr_text: Optional[str] = None
    extracted_data: Optional[dict] = None
    uploaded_by: str
    uploaded_at: datetime
    processed_at: Optional[datetime] = None


class DocumentUpdate(BaseModel):
    """Request for updating document metadata."""
    document_type: Optional[DocumentType] = None
    property_id: Optional[int] = None
    notes: Optional[str] = None


@router.post("/upload", response_model=DocumentUploadResponse, status_code=201)
@rate_limit(max_requests=20, window_seconds=60)
async def upload_document(
    file: UploadFile = File(...),
    document_type: DocumentType = Query(...),
    property_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user)
):
    """
    Upload a document to MinIO storage.

    Supported file types:
    - PDF, Word (doc/docx)
    - Images (jpg, png, tiff)
    - Text files

    Maximum file size: 50MB
    """
    logger.info(f"Document upload: {file.filename}, type: {document_type}")

    # Validate file size (50MB limit)
    file_content = await file.read()
    file_size = len(file_content)

    if file_size > 50 * 1024 * 1024:  # 50MB
        raise HTTPException(
            status_code=400,
            detail="File size exceeds 50MB limit"
        )

    # Validate file type
    allowed_types = [
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'image/jpeg',
        'image/png',
        'image/tiff',
        'text/plain'
    ]

    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}"
        )

    try:
        # Generate document ID
        document_id = f"doc_{uuid.uuid4().hex[:16]}"

        # Upload to MinIO
        storage_path = f"{current_user.tenant_id}/documents/{document_id}/{file.filename}"

        upload_result = upload_file(
            bucket_name="documents",
            object_name=storage_path,
            file_data=file_content,
            content_type=file.content_type,
            tenant_id=current_user.tenant_id
        )

        logger.info(f"Document uploaded to {storage_path}")

        # In production: Insert metadata to database
        # In production: Queue for OCR/text extraction if applicable

        return DocumentUploadResponse(
            document_id=document_id,
            file_name=file.filename,
            file_size=file_size,
            content_type=file.content_type,
            storage_path=storage_path,
            status=DocumentStatus.UPLOADED,
            message="Document uploaded successfully and queued for processing"
        )

    except Exception as e:
        logger.error(f"Document upload failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Upload failed: {str(e)}"
        )


@router.get("/", response_model=List[DocumentMetadata])
@rate_limit(max_requests=100, window_seconds=60)
async def list_documents(
    property_id: Optional[int] = None,
    document_type: Optional[DocumentType] = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user)
):
    """
    List documents with optional filters.

    Can filter by property_id and/or document_type.
    """
    logger.info(f"List documents: property_id={property_id}, type={document_type}")

    # In production: Query database with filters
    # In production: Apply RLS for tenant isolation

    raise HTTPException(
        status_code=501,
        detail="Database query not implemented. Endpoint structure ready."
    )


@router.get("/{document_id}", response_model=DocumentMetadata)
@rate_limit(max_requests=100, window_seconds=60)
async def get_document_metadata(
    document_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get document metadata by ID."""
    logger.info(f"Get document metadata: {document_id}")

    # In production: Query database

    raise HTTPException(
        status_code=501,
        detail="Database query not implemented. Endpoint structure ready."
    )


@router.get("/{document_id}/download")
@rate_limit(max_requests=50, window_seconds=60)
async def download_document_file(
    document_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Download document file from storage.

    Returns the file as a streaming response.
    """
    logger.info(f"Download document: {document_id}")

    # In production:
    # 1. Query database for document metadata
    # 2. Verify user has access (RLS)
    # 3. Download from MinIO using storage_path
    # 4. Stream response with appropriate headers

    raise HTTPException(
        status_code=501,
        detail="Download not implemented. Endpoint structure ready."
    )


@router.put("/{document_id}", response_model=DocumentMetadata)
@rate_limit(max_requests=20, window_seconds=60)
async def update_document_metadata(
    document_id: str,
    update: DocumentUpdate,
    current_user: User = Depends(get_current_user)
):
    """
    Update document metadata.

    Can change document type, associated property, or notes.
    """
    logger.info(f"Update document metadata: {document_id}")

    # In production: Update database

    raise HTTPException(
        status_code=501,
        detail="Update not implemented. Endpoint structure ready."
    )


@router.delete("/{document_id}", status_code=204)
@rate_limit(max_requests=10, window_seconds=60)
async def delete_document(
    document_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Delete document and its file from storage.

    Requires admin role.
    """
    if current_user.role not in ['admin', 'owner']:
        raise HTTPException(
            status_code=403,
            detail="Insufficient permissions. Admin role required."
        )

    logger.info(f"Delete document: {document_id}")

    # In production:
    # 1. Get document metadata from database
    # 2. Delete file from MinIO
    # 3. Delete metadata from database
    # 4. Log deletion in audit trail

    raise HTTPException(
        status_code=501,
        detail="Delete not implemented. Endpoint structure ready."
    )


@router.post("/{document_id}/reprocess", status_code=202)
@rate_limit(max_requests=10, window_seconds=60)
async def reprocess_document(
    document_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Reprocess document (re-run OCR/text extraction).

    Useful if initial processing failed or needs to be updated.
    """
    logger.info(f"Reprocess document: {document_id}")

    # In production:
    # 1. Verify document exists
    # 2. Queue for reprocessing (Airflow DAG trigger)
    # 3. Update status to PROCESSING
    # 4. Return accepted response

    raise HTTPException(
        status_code=501,
        detail="Reprocessing not implemented. Endpoint structure ready."
    )
