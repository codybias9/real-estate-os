"""
Docgen.Memo - PDF memo generation for property reports

Single-Writer Pattern: Only this agent publishes event.docgen.memo
"""

import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import UUID, uuid4

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

from contracts.property_record import PropertyRecord
from contracts.score_result import ScoreResult
from contracts.envelope import Envelope


class DocgenMemo:
    """
    Generates PDF memos for property investment reports.

    Features:
    - Renders PropertyRecord + ScoreResult into professional PDF
    - Stores PDFs in S3/MinIO with tenant isolation
    - Idempotent: same property + score → same PDF URL
    - Publishes event.docgen.memo for downstream consumers
    """

    def __init__(
        self,
        s3_bucket: str,
        s3_endpoint: Optional[str] = None,
        s3_access_key: Optional[str] = None,
        s3_secret_key: Optional[str] = None,
        s3_region: str = "us-east-1",
        template_dir: Optional[Path] = None,
    ):
        """
        Initialize memo generator.

        Args:
            s3_bucket: S3 bucket name for PDF storage
            s3_endpoint: S3 endpoint URL (for MinIO, defaults to AWS S3)
            s3_access_key: S3 access key (defaults to AWS credentials)
            s3_secret_key: S3 secret key (defaults to AWS credentials)
            s3_region: S3 region (default: us-east-1)
            template_dir: Custom template directory (defaults to bundled templates)
        """
        self.s3_bucket = s3_bucket
        self.s3_region = s3_region

        # Initialize S3 client
        s3_config = Config(signature_version="s3v4")
        self.s3_client = boto3.client(
            "s3",
            endpoint_url=s3_endpoint,
            aws_access_key_id=s3_access_key or os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=s3_secret_key or os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name=s3_region,
            config=s3_config,
        )

        # Ensure bucket exists
        self._ensure_bucket_exists()

        # Initialize Jinja2 template engine
        if template_dir is None:
            # Default to bundled templates
            template_dir = Path(__file__).parent.parent.parent / "templates"

        self.jinja_env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=True,
        )

    def _ensure_bucket_exists(self):
        """Create S3 bucket if it doesn't exist"""
        try:
            self.s3_client.head_bucket(Bucket=self.s3_bucket)
        except ClientError:
            # Bucket doesn't exist, create it
            try:
                if self.s3_region == "us-east-1":
                    self.s3_client.create_bucket(Bucket=self.s3_bucket)
                else:
                    self.s3_client.create_bucket(
                        Bucket=self.s3_bucket,
                        CreateBucketConfiguration={"LocationConstraint": self.s3_region},
                    )
            except ClientError as e:
                # Bucket might exist but we don't have head_bucket permission
                # Or it could be a real error - let it propagate
                if e.response["Error"]["Code"] != "BucketAlreadyOwnedByYou":
                    raise

    def _compute_memo_hash(
        self, property_record: PropertyRecord, score_result: ScoreResult
    ) -> str:
        """
        Compute deterministic hash for memo idempotency.

        Same property + score → same hash → same PDF URL.

        Args:
            property_record: Property data
            score_result: Score data

        Returns:
            16-character hex hash
        """
        # Hash based on APN + score + model version
        hash_input = (
            f"{property_record.apn}:"
            f"{score_result.score}:"
            f"{score_result.model_version}"
        )
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]

    def generate_memo(
        self,
        property_record: PropertyRecord,
        score_result: ScoreResult,
        tenant_id: str,
    ) -> tuple[str, Envelope]:
        """
        Generate PDF memo and store in S3.

        Args:
            property_record: Property data from Discovery.Resolver
            score_result: Score data from Score.Engine
            tenant_id: Tenant UUID for isolation

        Returns:
            Tuple of (pdf_url, envelope) where envelope contains event.docgen.memo

        Example:
            >>> memo_gen = DocgenMemo(s3_bucket="memos")
            >>> pdf_url, envelope = memo_gen.generate_memo(prop, score, tenant_id)
            >>> print(f"Memo: {pdf_url}")
        """
        # Compute idempotency hash
        memo_hash = self._compute_memo_hash(property_record, score_result)

        # Generate S3 key with tenant isolation
        s3_key = f"tenants/{tenant_id}/memos/{memo_hash}.pdf"

        # Check if PDF already exists (idempotency)
        try:
            self.s3_client.head_object(Bucket=self.s3_bucket, Key=s3_key)
            # PDF exists, return existing URL
            pdf_url = self._get_s3_url(s3_key)
            envelope = self._create_envelope(
                tenant_id=tenant_id,
                property_id=str(property_record.apn),
                pdf_url=pdf_url,
                memo_hash=memo_hash,
            )
            return (pdf_url, envelope)
        except ClientError:
            # PDF doesn't exist, generate it
            pass

        # Render HTML from template
        html_content = self._render_template(
            property_record=property_record,
            score_result=score_result,
            tenant_id=tenant_id,
        )

        # Generate PDF from HTML
        pdf_bytes = self._html_to_pdf(html_content)

        # Upload to S3
        self._upload_pdf(s3_key=s3_key, pdf_bytes=pdf_bytes, tenant_id=tenant_id)

        # Get PDF URL
        pdf_url = self._get_s3_url(s3_key)

        # Create event envelope
        envelope = self._create_envelope(
            tenant_id=tenant_id,
            property_id=str(property_record.apn),
            pdf_url=pdf_url,
            memo_hash=memo_hash,
        )

        return (pdf_url, envelope)

    def _render_template(
        self,
        property_record: PropertyRecord,
        score_result: ScoreResult,
        tenant_id: str,
    ) -> str:
        """
        Render Jinja2 template to HTML.

        Args:
            property_record: Property data
            score_result: Score data
            tenant_id: Tenant UUID

        Returns:
            Rendered HTML string
        """
        template = self.jinja_env.get_template("memo_template.html")

        context = {
            "property": property_record,
            "score": score_result,
            "tenant_id": tenant_id,
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        }

        return template.render(**context)

    def _html_to_pdf(self, html_content: str) -> bytes:
        """
        Convert HTML to PDF using WeasyPrint.

        Args:
            html_content: Rendered HTML string

        Returns:
            PDF as bytes
        """
        html = HTML(string=html_content)
        return html.write_pdf()

    def _upload_pdf(self, s3_key: str, pdf_bytes: bytes, tenant_id: str):
        """
        Upload PDF to S3 with metadata.

        Args:
            s3_key: S3 object key
            pdf_bytes: PDF content as bytes
            tenant_id: Tenant UUID for metadata
        """
        self.s3_client.put_object(
            Bucket=self.s3_bucket,
            Key=s3_key,
            Body=pdf_bytes,
            ContentType="application/pdf",
            Metadata={
                "tenant_id": tenant_id,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "generator": "docgen-memo-v1",
            },
        )

    def _get_s3_url(self, s3_key: str) -> str:
        """
        Get S3 URL for uploaded PDF.

        Args:
            s3_key: S3 object key

        Returns:
            S3 URL (either public URL or presigned URL)
        """
        # For production: use presigned URLs with expiration
        # For now: return S3 path (assumes bucket is configured for access)
        return f"s3://{self.s3_bucket}/{s3_key}"

    def _create_envelope(
        self, tenant_id: str, property_id: str, pdf_url: str, memo_hash: str
    ) -> Envelope:
        """
        Create event envelope for event.docgen.memo.

        Single-writer pattern: Only DocgenMemo publishes this subject.

        Args:
            tenant_id: Tenant UUID
            property_id: Property identifier (APN)
            pdf_url: S3 URL of generated PDF
            memo_hash: Idempotency hash

        Returns:
            Envelope with event.docgen.memo payload
        """
        return Envelope(
            id=uuid4(),
            tenant_id=UUID(tenant_id),
            subject="event.docgen.memo",
            idempotency_key=f"memo-{memo_hash}",
            correlation_id=uuid4(),  # Could link to original intake event
            causation_id=uuid4(),  # Could link to scoring event
            schema_version="1.0",
            at=datetime.now(timezone.utc),
            payload={
                "property_id": property_id,
                "pdf_url": pdf_url,
                "memo_hash": memo_hash,
                "status": "generated",
            },
        )

    def get_memo_url(self, tenant_id: str, memo_hash: str) -> Optional[str]:
        """
        Get URL for existing memo by hash.

        Args:
            tenant_id: Tenant UUID
            memo_hash: Memo idempotency hash

        Returns:
            PDF URL if exists, None otherwise
        """
        s3_key = f"tenants/{tenant_id}/memos/{memo_hash}.pdf"

        try:
            self.s3_client.head_object(Bucket=self.s3_bucket, Key=s3_key)
            return self._get_s3_url(s3_key)
        except ClientError:
            return None
