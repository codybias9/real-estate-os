"""MinIO client for PDF storage

Handles upload, download, and management of PDFs in S3-compatible object storage.
"""
import logging
import io
from typing import Optional, Dict, Any
from datetime import timedelta
from pathlib import Path

from minio import Minio
from minio.error import S3Error

logger = logging.getLogger(__name__)


class MinIOClient:
    """
    MinIO client for document storage

    Provides methods to:
    - Upload PDFs to MinIO
    - Generate presigned download URLs
    - List and manage documents
    """

    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket_name: str = "property-documents",
        secure: bool = False
    ):
        """
        Initialize MinIO client

        Args:
            endpoint: MinIO server endpoint (e.g., "minio:9000")
            access_key: MinIO access key
            secret_key: MinIO secret key
            bucket_name: Bucket name for storing documents
            secure: Use HTTPS (default: False for local)
        """
        self.endpoint = endpoint
        self.bucket_name = bucket_name

        try:
            # Initialize MinIO client
            self.client = Minio(
                endpoint,
                access_key=access_key,
                secret_key=secret_key,
                secure=secure
            )

            # Ensure bucket exists
            self._ensure_bucket()

            logger.info(f"MinIO client initialized: {endpoint}/{bucket_name}")

        except Exception as e:
            logger.error(f"Failed to initialize MinIO client: {e}")
            raise

    def _ensure_bucket(self):
        """Ensure bucket exists, create if not"""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                logger.info(f"Created bucket: {self.bucket_name}")
            else:
                logger.info(f"Bucket exists: {self.bucket_name}")

        except S3Error as e:
            logger.error(f"Failed to ensure bucket: {e}")
            raise

    def upload_pdf(
        self,
        pdf_bytes: bytes,
        object_name: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Upload PDF to MinIO

        Args:
            pdf_bytes: PDF content as bytes
            object_name: Object name/path in bucket (e.g., "investor_memos/123.pdf")
            metadata: Optional metadata dictionary

        Returns:
            Object name in bucket
        """
        logger.info(f"Uploading PDF to MinIO: {object_name} ({len(pdf_bytes)} bytes)")

        try:
            # Convert bytes to file-like object
            pdf_stream = io.BytesIO(pdf_bytes)

            # Upload to MinIO
            result = self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                data=pdf_stream,
                length=len(pdf_bytes),
                content_type="application/pdf",
                metadata=metadata or {}
            )

            logger.info(f"Upload successful: {result.object_name} (etag: {result.etag})")

            return object_name

        except S3Error as e:
            logger.error(f"Upload failed: {e}")
            raise RuntimeError(f"Failed to upload PDF to MinIO: {e}")

    def get_presigned_url(
        self,
        object_name: str,
        expires: timedelta = timedelta(hours=24)
    ) -> str:
        """
        Generate presigned URL for downloading PDF

        Args:
            object_name: Object name in bucket
            expires: URL expiration time (default: 24 hours)

        Returns:
            Presigned URL string
        """
        logger.info(f"Generating presigned URL for: {object_name}")

        try:
            url = self.client.presigned_get_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                expires=expires
            )

            logger.info(f"Presigned URL generated (expires in {expires})")

            return url

        except S3Error as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            raise RuntimeError(f"Failed to generate presigned URL: {e}")

    def download_pdf(self, object_name: str) -> bytes:
        """
        Download PDF from MinIO

        Args:
            object_name: Object name in bucket

        Returns:
            PDF content as bytes
        """
        logger.info(f"Downloading PDF from MinIO: {object_name}")

        try:
            response = self.client.get_object(
                bucket_name=self.bucket_name,
                object_name=object_name
            )

            pdf_bytes = response.read()
            response.close()
            response.release_conn()

            logger.info(f"Download successful ({len(pdf_bytes)} bytes)")

            return pdf_bytes

        except S3Error as e:
            logger.error(f"Download failed: {e}")
            raise RuntimeError(f"Failed to download PDF from MinIO: {e}")

    def delete_pdf(self, object_name: str) -> bool:
        """
        Delete PDF from MinIO

        Args:
            object_name: Object name in bucket

        Returns:
            True if deleted successfully
        """
        logger.info(f"Deleting PDF from MinIO: {object_name}")

        try:
            self.client.remove_object(
                bucket_name=self.bucket_name,
                object_name=object_name
            )

            logger.info("Delete successful")

            return True

        except S3Error as e:
            logger.error(f"Delete failed: {e}")
            return False

    def list_pdfs(self, prefix: str = "") -> list:
        """
        List PDFs in bucket

        Args:
            prefix: Optional prefix filter (e.g., "investor_memos/")

        Returns:
            List of object names
        """
        logger.info(f"Listing PDFs with prefix: {prefix or '(all)'}")

        try:
            objects = self.client.list_objects(
                bucket_name=self.bucket_name,
                prefix=prefix,
                recursive=True
            )

            object_names = [obj.object_name for obj in objects]

            logger.info(f"Found {len(object_names)} objects")

            return object_names

        except S3Error as e:
            logger.error(f"List failed: {e}")
            return []

    def get_object_stats(self, object_name: str) -> Dict[str, Any]:
        """
        Get object statistics

        Args:
            object_name: Object name in bucket

        Returns:
            Dictionary with object stats
        """
        logger.info(f"Getting stats for: {object_name}")

        try:
            stat = self.client.stat_object(
                bucket_name=self.bucket_name,
                object_name=object_name
            )

            stats = {
                'object_name': stat.object_name,
                'size': stat.size,
                'etag': stat.etag,
                'last_modified': stat.last_modified,
                'content_type': stat.content_type,
                'metadata': stat.metadata
            }

            logger.info(f"Stats retrieved: {stat.size} bytes")

            return stats

        except S3Error as e:
            logger.error(f"Failed to get stats: {e}")
            raise RuntimeError(f"Failed to get object stats: {e}")

    def health_check(self) -> bool:
        """
        Check MinIO connectivity

        Returns:
            True if connected and bucket accessible
        """
        try:
            # Try to list objects (lightweight operation)
            list(self.client.list_buckets())
            logger.info("MinIO health check: OK")
            return True

        except Exception as e:
            logger.error(f"MinIO health check failed: {e}")
            return False
