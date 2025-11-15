"""Generated document models."""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, HttpUrl


class DocumentType(str, Enum):
    """Type of generated document."""

    INVESTOR_MEMO = "investor_memo"
    MARKET_ANALYSIS = "market_analysis"
    FINANCIAL_PROJECTION = "financial_projection"
    PROPERTY_REPORT = "property_report"
    COMPARISON_REPORT = "comparison_report"


class DocumentStatus(str, Enum):
    """Status of document generation."""

    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentBase(BaseModel):
    """Base document model."""

    property_id: int = Field(..., description="Foreign key to property")
    document_type: DocumentType = Field(..., description="Type of document")

    # File information
    filename: str = Field(..., description="Generated filename")
    file_path: Optional[str] = Field(None, description="Path to file (local or S3)")
    file_url: Optional[HttpUrl] = Field(None, description="Public URL to download document")
    file_size: Optional[int] = Field(None, description="File size in bytes")
    mime_type: str = Field(default="application/pdf", description="MIME type")

    # Generation status
    status: DocumentStatus = Field(default=DocumentStatus.PENDING, description="Generation status")
    error_message: Optional[str] = Field(None, description="Error message if generation failed")

    # Generation metadata
    template_version: Optional[str] = Field(None, description="Version of template used")
    generated_by: Optional[str] = Field(None, description="System/user that generated document")
    generation_time_ms: Optional[int] = Field(None, description="Time taken to generate in milliseconds")

    # Additional metadata
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")


class DocumentCreate(DocumentBase):
    """Model for creating a document record."""
    pass


class GeneratedDocument(DocumentBase):
    """Full document model with database fields."""

    id: int = Field(..., description="Unique document ID")
    created_at: datetime = Field(..., description="Record creation timestamp")
    updated_at: datetime = Field(..., description="Record update timestamp")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "property_id": 1,
                "document_type": "investor_memo",
                "filename": "investor_memo_property_1_20240115.pdf",
                "file_path": "s3://documents/properties/1/investor_memo_20240115.pdf",
                "file_url": "https://minio.example.com/documents/properties/1/investor_memo_20240115.pdf",
                "file_size": 245678,
                "mime_type": "application/pdf",
                "status": "completed",
                "error_message": None,
                "template_version": "1.0.0",
                "generated_by": "system",
                "generation_time_ms": 1250,
                "metadata": {
                    "included_sections": ["overview", "financial", "market_analysis", "photos"],
                    "page_count": 8
                },
                "created_at": "2024-01-15T13:00:00",
                "updated_at": "2024-01-15T13:00:15"
            }
        }
