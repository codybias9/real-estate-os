"""
MemoReady - Investor memo generation result
Emitted after successful PDF generation and storage
"""

from pydantic import BaseModel, Field


class MemoReady(BaseModel):
    """
    Event payload when investor memo PDF is ready.

    Emitted by: Docgen.Memo
    Consumed by: Frontend (displays link), Pipeline.State (updates timeline)
    """

    packet_url: str = Field(..., description="Presigned S3/MinIO URL for PDF download")
    etag: str = Field(..., description="Object storage ETag for cache validation")
    bytes: int = Field(..., ge=0, description="PDF file size in bytes")
    memo_hash: str = Field(..., description="Content hash (SHA256) for deduplication")
    page_count: int = Field(default=2, ge=1, description="Number of pages in PDF")
    template_version: str = Field(default="v1", description="Template version used")

    # Optional: generation metrics for observability
    generation_time_ms: int | None = Field(None, description="PDF generation time (milliseconds)")
