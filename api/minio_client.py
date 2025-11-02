"""
MinIO object storage client with mandatory tenant prefix isolation.

This client wraps the official MinIO client to enforce tenant-based prefix
isolation on all operations, preventing cross-tenant file access.
"""
from minio import Minio
from minio.error import S3Error
from typing import Optional, BinaryIO, Iterator
from datetime import timedelta
import logging
from io import BytesIO

from api.config import settings

logger = logging.getLogger(__name__)


class MinIOClient:
    """
    Wrapper around MinIO client that enforces tenant isolation via object prefixes.

    All object keys must be prefixed with {tenant_id}/.
    All operations validate tenant prefix before allowing access.
    """

    def __init__(
        self,
        endpoint: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        secure: Optional[bool] = None
    ):
        """
        Initialize MinIO client.

        Args:
            endpoint: MinIO server endpoint (defaults to settings)
            access_key: Access key (defaults to settings)
            secret_key: Secret key (defaults to settings)
            secure: Use HTTPS (defaults to settings)
        """
        self.endpoint = endpoint or settings.minio_endpoint
        self.access_key = access_key or settings.minio_access_key
        self.secret_key = secret_key or settings.minio_secret_key
        self.secure = secure if secure is not None else settings.minio_secure

        self._client = Minio(
            endpoint=self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure
        )

        logger.info(f"MinIO client initialized: {self.endpoint}")

    @property
    def client(self) -> Minio:
        """Get underlying MinIO client."""
        return self._client

    def _validate_tenant_prefix(
        self,
        object_name: str,
        tenant_id: str
    ) -> None:
        """
        Validate that object name starts with tenant prefix.

        Args:
            object_name: Object path
            tenant_id: Expected tenant UUID

        Raises:
            ValueError: If prefix doesn't match tenant
        """
        expected_prefix = f"{tenant_id}/"

        if not object_name.startswith(expected_prefix):
            raise ValueError(
                f"Object name must start with tenant prefix '{expected_prefix}'. "
                f"Got: '{object_name}'. "
                "This prevents cross-tenant file access."
            )

    def _build_object_path(
        self,
        tenant_id: str,
        path: str
    ) -> str:
        """
        Build full object path with tenant prefix.

        Args:
            tenant_id: Tenant UUID
            path: Relative path within tenant (e.g., "documents/lease.pdf")

        Returns:
            Full path: "{tenant_id}/documents/lease.pdf"
        """
        # Remove leading slash if present
        if path.startswith("/"):
            path = path[1:]

        return f"{tenant_id}/{path}"

    # ========================================================================
    # Bucket Management
    # ========================================================================

    def ensure_bucket(self, bucket_name: str) -> None:
        """
        Ensure bucket exists (create if not exists).

        Args:
            bucket_name: Bucket name
        """
        try:
            if not self._client.bucket_exists(bucket_name):
                self._client.make_bucket(bucket_name)
                logger.info(f"Created bucket: {bucket_name}")
            else:
                logger.debug(f"Bucket already exists: {bucket_name}")

        except S3Error as e:
            logger.error(f"Failed to ensure bucket {bucket_name}: {e}")
            raise

    def bucket_exists(self, bucket_name: str) -> bool:
        """Check if bucket exists."""
        try:
            return self._client.bucket_exists(bucket_name)
        except S3Error as e:
            logger.error(f"Failed to check bucket existence: {e}")
            return False

    # ========================================================================
    # Upload (Put Object)
    # ========================================================================

    def put_object(
        self,
        bucket_name: str,
        object_name: str,
        data: BinaryIO,
        length: int,
        tenant_id: str,
        content_type: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> str:
        """
        Upload object with tenant prefix validation.

        Args:
            bucket_name: Target bucket
            object_name: Object path (must start with {tenant_id}/)
            data: File-like object with data
            length: Data length in bytes
            tenant_id: Tenant UUID (REQUIRED)
            content_type: MIME type (optional)
            metadata: Custom metadata dict (optional)

        Returns:
            Full object path

        Raises:
            ValueError: If tenant prefix doesn't match
        """
        if not tenant_id:
            raise ValueError("tenant_id is REQUIRED for all put operations")

        # Validate tenant prefix
        self._validate_tenant_prefix(object_name, tenant_id)

        try:
            # Inject tenant_id into metadata
            if metadata is None:
                metadata = {}
            metadata["tenant_id"] = tenant_id

            # Upload to MinIO
            self._client.put_object(
                bucket_name=bucket_name,
                object_name=object_name,
                data=data,
                length=length,
                content_type=content_type,
                metadata=metadata
            )

            logger.info(
                f"Uploaded object: {bucket_name}/{object_name} "
                f"(tenant={tenant_id}, size={length} bytes)"
            )

            return object_name

        except S3Error as e:
            logger.error(f"Put object failed: {e}")
            raise

    def put_object_from_path(
        self,
        bucket_name: str,
        relative_path: str,
        file_path: str,
        tenant_id: str,
        content_type: Optional[str] = None
    ) -> str:
        """
        Upload file from filesystem with automatic tenant prefix.

        Args:
            bucket_name: Target bucket
            relative_path: Path within tenant (e.g., "documents/lease.pdf")
            file_path: Local file path
            tenant_id: Tenant UUID (REQUIRED)
            content_type: MIME type (optional)

        Returns:
            Full object path
        """
        import os

        # Build full object path with tenant prefix
        object_name = self._build_object_path(tenant_id, relative_path)

        # Upload file
        try:
            self._client.fput_object(
                bucket_name=bucket_name,
                object_name=object_name,
                file_path=file_path,
                content_type=content_type,
                metadata={"tenant_id": tenant_id}
            )

            file_size = os.path.getsize(file_path)

            logger.info(
                f"Uploaded file: {file_path} → {bucket_name}/{object_name} "
                f"(tenant={tenant_id}, size={file_size} bytes)"
            )

            return object_name

        except S3Error as e:
            logger.error(f"Put object from path failed: {e}")
            raise

    # ========================================================================
    # Download (Get Object)
    # ========================================================================

    def get_object(
        self,
        bucket_name: str,
        object_name: str,
        tenant_id: str
    ) -> bytes:
        """
        Download object with tenant prefix validation.

        Args:
            bucket_name: Bucket name
            object_name: Object path (must start with {tenant_id}/)
            tenant_id: Tenant UUID (REQUIRED)

        Returns:
            Object data as bytes

        Raises:
            ValueError: If tenant prefix doesn't match
        """
        if not tenant_id:
            raise ValueError("tenant_id is REQUIRED for all get operations")

        # Validate tenant prefix
        self._validate_tenant_prefix(object_name, tenant_id)

        try:
            # Get object
            response = self._client.get_object(
                bucket_name=bucket_name,
                object_name=object_name
            )

            # Read all data
            data = response.read()
            response.close()
            response.release_conn()

            logger.info(
                f"Downloaded object: {bucket_name}/{object_name} "
                f"(tenant={tenant_id}, size={len(data)} bytes)"
            )

            return data

        except S3Error as e:
            logger.error(f"Get object failed: {e}")
            raise

    def get_object_to_path(
        self,
        bucket_name: str,
        object_name: str,
        file_path: str,
        tenant_id: str
    ) -> None:
        """
        Download object to filesystem with tenant prefix validation.

        Args:
            bucket_name: Bucket name
            object_name: Object path (must start with {tenant_id}/)
            file_path: Local file path to write to
            tenant_id: Tenant UUID (REQUIRED)
        """
        if not tenant_id:
            raise ValueError("tenant_id is REQUIRED")

        # Validate tenant prefix
        self._validate_tenant_prefix(object_name, tenant_id)

        try:
            self._client.fget_object(
                bucket_name=bucket_name,
                object_name=object_name,
                file_path=file_path
            )

            logger.info(
                f"Downloaded object to file: {bucket_name}/{object_name} → {file_path} "
                f"(tenant={tenant_id})"
            )

        except S3Error as e:
            logger.error(f"Get object to path failed: {e}")
            raise

    # ========================================================================
    # List Objects (tenant-scoped)
    # ========================================================================

    def list_objects(
        self,
        bucket_name: str,
        tenant_id: str,
        prefix: Optional[str] = None,
        recursive: bool = True
    ) -> Iterator[dict]:
        """
        List objects belonging to tenant.

        Args:
            bucket_name: Bucket name
            tenant_id: Tenant UUID (REQUIRED)
            prefix: Additional prefix filter (within tenant)
            recursive: Recursive listing

        Yields:
            Dict with object info:
            {
                "object_name": "{tenant_id}/documents/file.pdf",
                "size": 12345,
                "last_modified": datetime,
                "etag": "..."
            }
        """
        if not tenant_id:
            raise ValueError("tenant_id is REQUIRED for list operations")

        try:
            # Build full prefix with tenant
            if prefix:
                full_prefix = self._build_object_path(tenant_id, prefix)
            else:
                full_prefix = f"{tenant_id}/"

            # List objects
            objects = self._client.list_objects(
                bucket_name=bucket_name,
                prefix=full_prefix,
                recursive=recursive
            )

            count = 0
            for obj in objects:
                count += 1
                yield {
                    "object_name": obj.object_name,
                    "size": obj.size,
                    "last_modified": obj.last_modified,
                    "etag": obj.etag,
                    "content_type": obj.content_type
                }

            logger.info(
                f"Listed {count} objects in {bucket_name} "
                f"(tenant={tenant_id}, prefix={full_prefix})"
            )

        except S3Error as e:
            logger.error(f"List objects failed: {e}")
            raise

    # ========================================================================
    # Delete
    # ========================================================================

    def remove_object(
        self,
        bucket_name: str,
        object_name: str,
        tenant_id: str
    ) -> None:
        """
        Delete object with tenant prefix validation.

        Args:
            bucket_name: Bucket name
            object_name: Object path (must start with {tenant_id}/)
            tenant_id: Tenant UUID (REQUIRED)
        """
        if not tenant_id:
            raise ValueError("tenant_id is REQUIRED for delete operations")

        # Validate tenant prefix
        self._validate_tenant_prefix(object_name, tenant_id)

        try:
            self._client.remove_object(
                bucket_name=bucket_name,
                object_name=object_name
            )

            logger.info(
                f"Deleted object: {bucket_name}/{object_name} "
                f"(tenant={tenant_id})"
            )

        except S3Error as e:
            logger.error(f"Remove object failed: {e}")
            raise

    def remove_objects(
        self,
        bucket_name: str,
        object_names: list[str],
        tenant_id: str
    ) -> None:
        """
        Delete multiple objects (batch) with tenant prefix validation.

        Args:
            bucket_name: Bucket name
            object_names: List of object paths (all must start with {tenant_id}/)
            tenant_id: Tenant UUID (REQUIRED)
        """
        if not tenant_id:
            raise ValueError("tenant_id is REQUIRED")

        # Validate all prefixes
        for object_name in object_names:
            self._validate_tenant_prefix(object_name, tenant_id)

        try:
            # Remove objects
            for del_err in self._client.remove_objects(bucket_name, object_names):
                logger.error(f"Error deleting object: {del_err}")

            logger.info(
                f"Deleted {len(object_names)} objects from {bucket_name} "
                f"(tenant={tenant_id})"
            )

        except S3Error as e:
            logger.error(f"Remove objects failed: {e}")
            raise

    # ========================================================================
    # Stat (Metadata)
    # ========================================================================

    def stat_object(
        self,
        bucket_name: str,
        object_name: str,
        tenant_id: str
    ) -> dict:
        """
        Get object metadata with tenant prefix validation.

        Args:
            bucket_name: Bucket name
            object_name: Object path (must start with {tenant_id}/)
            tenant_id: Tenant UUID (REQUIRED)

        Returns:
            Metadata dict
        """
        if not tenant_id:
            raise ValueError("tenant_id is REQUIRED")

        # Validate tenant prefix
        self._validate_tenant_prefix(object_name, tenant_id)

        try:
            stat = self._client.stat_object(
                bucket_name=bucket_name,
                object_name=object_name
            )

            return {
                "object_name": stat.object_name,
                "size": stat.size,
                "last_modified": stat.last_modified,
                "etag": stat.etag,
                "content_type": stat.content_type,
                "metadata": stat.metadata
            }

        except S3Error as e:
            logger.error(f"Stat object failed: {e}")
            raise

    # ========================================================================
    # Presigned URLs (temporary access)
    # ========================================================================

    def presigned_get_url(
        self,
        bucket_name: str,
        object_name: str,
        tenant_id: str,
        expires: timedelta = timedelta(hours=1)
    ) -> str:
        """
        Generate temporary download URL with tenant prefix validation.

        Args:
            bucket_name: Bucket name
            object_name: Object path (must start with {tenant_id}/)
            tenant_id: Tenant UUID (REQUIRED)
            expires: URL expiration time (default: 1 hour)

        Returns:
            Presigned URL
        """
        if not tenant_id:
            raise ValueError("tenant_id is REQUIRED")

        # Validate tenant prefix
        self._validate_tenant_prefix(object_name, tenant_id)

        try:
            url = self._client.presigned_get_object(
                bucket_name=bucket_name,
                object_name=object_name,
                expires=expires
            )

            logger.info(
                f"Generated presigned GET URL: {bucket_name}/{object_name} "
                f"(tenant={tenant_id}, expires={expires})"
            )

            return url

        except S3Error as e:
            logger.error(f"Presigned GET URL failed: {e}")
            raise

    def presigned_put_url(
        self,
        bucket_name: str,
        object_name: str,
        tenant_id: str,
        expires: timedelta = timedelta(hours=1)
    ) -> str:
        """
        Generate temporary upload URL with tenant prefix validation.

        Args:
            bucket_name: Bucket name
            object_name: Object path (must start with {tenant_id}/)
            tenant_id: Tenant UUID (REQUIRED)
            expires: URL expiration time (default: 1 hour)

        Returns:
            Presigned URL
        """
        if not tenant_id:
            raise ValueError("tenant_id is REQUIRED")

        # Validate tenant prefix
        self._validate_tenant_prefix(object_name, tenant_id)

        try:
            url = self._client.presigned_put_object(
                bucket_name=bucket_name,
                object_name=object_name,
                expires=expires
            )

            logger.info(
                f"Generated presigned PUT URL: {bucket_name}/{object_name} "
                f"(tenant={tenant_id}, expires={expires})"
            )

            return url

        except S3Error as e:
            logger.error(f"Presigned PUT URL failed: {e}")
            raise

    # ========================================================================
    # Health Check
    # ========================================================================

    def health_check(self) -> dict:
        """
        Check MinIO health and connectivity.

        Returns:
            Dict with status and info
        """
        try:
            # List buckets to verify connectivity
            buckets = self._client.list_buckets()

            return {
                "status": "healthy",
                "endpoint": self.endpoint,
                "buckets_count": len(buckets),
                "buckets": [b.name for b in buckets]
            }

        except S3Error as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "endpoint": self.endpoint,
                "error": str(e)
            }


# Global MinIO client instance
minio_client = MinIOClient()


def upload_file(
    bucket: str,
    object_name: str,
    file_path: str,
    tenant_id: str,
    content_type: str = "application/octet-stream"
) -> dict:
    """
    Wrapper function for uploading files.
    
    Args:
        bucket: Bucket name
        object_name: Object name (relative to tenant prefix)
        file_path: Path to file to upload
        tenant_id: Tenant UUID
        content_type: Content type
        
    Returns:
        dict with upload result
    """
    full_object_name = minio_client._build_object_path(tenant_id, object_name)
    result = minio_client.put_object_from_path(
        bucket_name=bucket,
        object_name=full_object_name,
        file_path=file_path,
        tenant_id=tenant_id,
        content_type=content_type
    )
    return result


def download_file(
    bucket: str,
    object_name: str,
    file_path: str,
    tenant_id: str
) -> dict:
    """
    Wrapper function for downloading files.
    
    Args:
        bucket: Bucket name
        object_name: Object name (relative to tenant prefix)
        file_path: Local path to save file
        tenant_id: Tenant UUID
        
    Returns:
        dict with download result
    """
    full_object_name = minio_client._build_object_path(tenant_id, object_name)
    result = minio_client.get_object_to_path(
        bucket_name=bucket,
        object_name=full_object_name,
        file_path=file_path,
        tenant_id=tenant_id
    )
    return result
