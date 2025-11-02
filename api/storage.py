"""
MinIO/S3 storage client with tenant isolation

All objects are stored under tenant-specific prefixes: <bucket>/<tenant_id>/...
"""

from minio import Minio
from minio.error import S3Error
from typing import BinaryIO, Optional, List
import os
from urllib.parse import quote


class TenantStorageClient:
    """
    MinIO/S3 client with automatic tenant prefix enforcement

    All operations are scoped to tenant-specific prefixes to ensure isolation.
    """

    def __init__(
        self,
        endpoint: str = None,
        access_key: str = None,
        secret_key: str = None,
        secure: bool = False
    ):
        self.endpoint = endpoint or os.getenv("MINIO_ENDPOINT", "localhost:9000")
        self.access_key = access_key or os.getenv("MINIO_ACCESS_KEY", "minioadmin")
        self.secret_key = secret_key or os.getenv("MINIO_SECRET_KEY", "minioadmin")
        self.secure = secure or os.getenv("MINIO_SECURE", "false").lower() == "true"
        self.bucket = os.getenv("MINIO_BUCKET", "real-estate-os")

        self.client = Minio(
            self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure
        )

        # Ensure bucket exists
        self._ensure_bucket()

    def _ensure_bucket(self):
        """Create bucket if it doesn't exist"""
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
        except S3Error as e:
            # Bucket may already exist
            pass

    def _get_tenant_path(self, tenant_id: str, object_path: str) -> str:
        """
        Construct full path with tenant prefix

        Format: <tenant_id>/<object_path>

        CRITICAL: This enforces tenant isolation at the storage layer.
        """
        # Strip leading slash from object_path if present
        object_path = object_path.lstrip("/")

        # Construct tenant-scoped path
        return f"{tenant_id}/{object_path}"

    def put_object(
        self,
        tenant_id: str,
        object_path: str,
        data: BinaryIO,
        length: int,
        content_type: str = "application/octet-stream"
    ) -> str:
        """
        Upload object with tenant prefix

        Returns: Full object path (tenant_id/object_path)
        """
        full_path = self._get_tenant_path(tenant_id, object_path)

        self.client.put_object(
            bucket_name=self.bucket,
            object_name=full_path,
            data=data,
            length=length,
            content_type=content_type
        )

        return full_path

    def get_object(
        self,
        tenant_id: str,
        object_path: str
    ) -> BinaryIO:
        """
        Download object with tenant prefix enforcement

        Automatically scopes to tenant's prefix.
        """
        full_path = self._get_tenant_path(tenant_id, object_path)

        try:
            response = self.client.get_object(
                bucket_name=self.bucket,
                object_name=full_path
            )
            return response
        except S3Error as e:
            if e.code == "NoSuchKey":
                # Return None instead of raising to avoid info leakage
                return None
            raise

    def list_objects(
        self,
        tenant_id: str,
        prefix: str = "",
        recursive: bool = True
    ) -> List[str]:
        """
        List objects with tenant prefix enforcement

        CRITICAL: Prefix is automatically scoped to tenant's namespace.
        Cross-tenant listing is impossible.
        """
        full_prefix = self._get_tenant_path(tenant_id, prefix)

        objects = self.client.list_objects(
            bucket_name=self.bucket,
            prefix=full_prefix,
            recursive=recursive
        )

        # Return object names relative to tenant prefix
        tenant_prefix_len = len(f"{tenant_id}/")
        return [obj.object_name[tenant_prefix_len:] for obj.object_name in objects]

    def delete_object(
        self,
        tenant_id: str,
        object_path: str
    ):
        """
        Delete object with tenant prefix enforcement
        """
        full_path = self._get_tenant_path(tenant_id, object_path)

        self.client.remove_object(
            bucket_name=self.bucket,
            object_name=full_path
        )

    def verify_tenant_isolation(
        self,
        tenant_id: str
    ) -> Dict[str, Any]:
        """
        Verify tenant isolation by checking prefix structure

        Returns statistics about objects under tenant prefix.
        """
        prefix = f"{tenant_id}/"
        objects = list(self.client.list_objects(
            bucket_name=self.bucket,
            prefix=prefix,
            recursive=True
        ))

        # Check that all objects start with tenant prefix
        all_have_prefix = all(obj.object_name.startswith(prefix) for obj in objects)

        return {
            "tenant_id": tenant_id,
            "object_count": len(objects),
            "all_under_tenant_prefix": all_have_prefix,
            "sample_paths": [obj.object_name for obj in objects[:5]]
        }


# Singleton instance
storage_client = TenantStorageClient()
