"""
Lease Management API Endpoints.

Provides endpoints for:
- Uploading and processing lease documents
- Retrieving lease data
- Managing lease records
"""
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import date, datetime
import logging
import uuid
import tempfile
import os

from api.auth import get_current_user, User
from api.rate_limit import rate_limit
from api.minio_client import upload_file
from document_processing.lease_parser import lease_parser

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/leases",
    tags=["leases"]
)


class LeaseResponse(BaseModel):
    """Response model for lease data."""
    id: Optional[int] = None
    document_id: str
    tenant_name: str
    property_address: str
    unit_number: Optional[str] = None
    lease_start_date: Optional[date] = None
    lease_end_date: Optional[date] = None
    monthly_rent: Optional[float] = None
    security_deposit: Optional[float] = None
    lease_term_months: Optional[int] = None
    parking_spaces: Optional[int] = None
    utilities_included: Optional[str] = None
    pet_policy: Optional[str] = None
    late_fee: Optional[float] = None
    tenant_email: Optional[str] = None
    tenant_phone: Optional[str] = None
    confidence_score: float
    created_at: Optional[datetime] = None


class LeaseUploadResponse(BaseModel):
    """Response model for lease upload."""
    document_id: str
    file_name: str
    file_size: int
    storage_path: str
    processing_status: str
    message: str


class LeaseProcessingResult(BaseModel):
    """Response model for lease processing."""
    document_id: str
    lease_id: Optional[int] = None
    parsing_status: str
    lease_data: Optional[LeaseResponse] = None
    errors: Optional[List[str]] = None
    warnings: Optional[List[str]] = None


def process_lease_document_async(
    document_path: str,
    document_id: str,
    property_address: str,
    tenant_id: str
):
    """
    Background task to process lease document asynchronously.

    In production, this would trigger the Airflow DAG.
    For now, processes synchronously in background.
    """
    try:
        logger.info(f"Processing lease document {document_id}")

        # Read document text
        with open(document_path, 'r', encoding='utf-8', errors='ignore') as f:
            text = f.read()

        # Parse lease data
        lease_data = lease_parser.parse_text(
            text=text,
            document_id=document_id,
            property_address=property_address
        )

        logger.info(
            f"Parsed lease {document_id}: tenant={lease_data.tenant_name}, "
            f"rent=${lease_data.monthly_rent}, confidence={lease_data.confidence_score:.2f}"
        )

        # In production, would:
        # 1. Store in database
        # 2. Track provenance
        # 3. Emit lineage events
        # 4. Run data quality checks

        # For now, just log completion
        logger.info(f"Completed processing for {document_id}")

    except Exception as e:
        logger.error(f"Failed to process lease document {document_id}: {e}")
    finally:
        # Cleanup temp file
        if os.path.exists(document_path):
            os.remove(document_path)


@router.post("/upload", response_model=LeaseUploadResponse)
@rate_limit(max_requests=20, window_seconds=60)
async def upload_lease_document(
    file: UploadFile = File(...),
    property_address: str = Field(..., description="Property address for this lease"),
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(get_current_user)
):
    """
    Upload a lease document for processing.

    Accepts PDF, Word, or text files. The document will be:
    1. Stored in MinIO object storage
    2. Queued for text extraction and parsing
    3. Processed through data quality validation
    4. Stored in database with provenance tracking

    Processing happens asynchronously. Use the document_id to check status.
    """
    logger.info(f"Lease upload request from user {current_user.sub}")

    # Validate file type
    allowed_types = ['application/pdf', 'application/msword',
                     'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                     'text/plain']

    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. "
                   f"Allowed types: PDF, Word, Text"
        )

    # Validate file size (10MB limit)
    file_content = await file.read()
    file_size = len(file_content)

    if file_size > 10 * 1024 * 1024:  # 10MB
        raise HTTPException(
            status_code=400,
            detail="File size exceeds 10MB limit"
        )

    try:
        # Generate document ID
        document_id = f"lease_{uuid.uuid4().hex[:12]}"

        # Upload to MinIO
        storage_path = f"{current_user.tenant_id}/leases/{document_id}/{file.filename}"

        upload_result = upload_file(
            bucket_name="documents",
            object_name=storage_path,
            file_data=file_content,
            content_type=file.content_type,
            tenant_id=current_user.tenant_id
        )

        logger.info(f"Uploaded lease document to {storage_path}")

        # Save to temp file for processing
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.txt') as temp_file:
            temp_file.write(file_content)
            temp_path = temp_file.name

        # Queue background processing
        if background_tasks:
            background_tasks.add_task(
                process_lease_document_async,
                document_path=temp_path,
                document_id=document_id,
                property_address=property_address,
                tenant_id=current_user.tenant_id
            )

        return LeaseUploadResponse(
            document_id=document_id,
            file_name=file.filename,
            file_size=file_size,
            storage_path=storage_path,
            processing_status="queued",
            message="Document uploaded successfully and queued for processing"
        )

    except Exception as e:
        logger.error(f"Failed to upload lease document: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload document: {str(e)}"
        )


@router.post("/parse", response_model=LeaseProcessingResult)
@rate_limit(max_requests=10, window_seconds=60)
async def parse_lease_text(
    text: str = Field(..., description="Raw lease document text"),
    property_address: str = Field(..., description="Property address"),
    document_id: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Parse lease data from raw text.

    This endpoint provides synchronous parsing of lease text.
    Use this for testing or when you already have extracted text.
    """
    logger.info(f"Parse lease text request from user {current_user.sub}")

    if not document_id:
        document_id = f"lease_{uuid.uuid4().hex[:12]}"

    try:
        # Parse lease data
        lease_data = lease_parser.parse_text(
            text=text,
            document_id=document_id,
            property_address=property_address
        )

        # Convert to response model
        from dataclasses import asdict
        lease_dict = asdict(lease_data)

        lease_response = LeaseResponse(**lease_dict)

        # Validate quality
        warnings = []
        if lease_data.confidence_score < 0.7:
            warnings.append(
                f"Low confidence score ({lease_data.confidence_score:.2f}). "
                "Manual review recommended."
            )

        if lease_data.tenant_name == "Unknown":
            warnings.append("Tenant name not found in document")

        if not lease_data.monthly_rent:
            warnings.append("Monthly rent amount not found")

        logger.info(
            f"Parsed lease: tenant={lease_data.tenant_name}, "
            f"rent=${lease_data.monthly_rent}, "
            f"confidence={lease_data.confidence_score:.2f}"
        )

        return LeaseProcessingResult(
            document_id=document_id,
            parsing_status="success",
            lease_data=lease_response,
            warnings=warnings if warnings else None
        )

    except Exception as e:
        logger.error(f"Failed to parse lease text: {e}")
        return LeaseProcessingResult(
            document_id=document_id,
            parsing_status="failed",
            errors=[str(e)]
        )


@router.get("/{document_id}", response_model=LeaseResponse)
@rate_limit(max_requests=100, window_seconds=60)
async def get_lease(
    document_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get lease data by document ID.
    """
    logger.info(f"Get lease request for {document_id}")

    # In production, would query database
    # For now, return mock response
    raise HTTPException(
        status_code=501,
        detail="Database query not implemented. Use /parse endpoint for now."
    )


@router.get("/", response_model=List[LeaseResponse])
@rate_limit(max_requests=100, window_seconds=60)
async def list_leases(
    property_address: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user)
):
    """
    List leases with optional filtering.
    """
    logger.info(f"List leases request from user {current_user.sub}")

    # In production, would query database with filters
    raise HTTPException(
        status_code=501,
        detail="Database query not implemented. Use /parse endpoint for now."
    )


@router.delete("/{document_id}")
@rate_limit(max_requests=10, window_seconds=60)
async def delete_lease(
    document_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Delete a lease record.

    Requires admin role.
    """
    if current_user.role not in ['admin', 'owner']:
        raise HTTPException(
            status_code=403,
            detail="Insufficient permissions. Admin role required."
        )

    logger.info(f"Delete lease request for {document_id}")

    # In production, would:
    # 1. Delete from database
    # 2. Delete from MinIO
    # 3. Update provenance records
    # 4. Emit lineage event

    raise HTTPException(
        status_code=501,
        detail="Delete operation not implemented yet"
    )
