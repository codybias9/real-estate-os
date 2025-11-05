"""Storage service for file uploads and management."""

from minio import Minio
from minio.error import S3Error
from typing import Optional, BinaryIO
import io
from datetime import timedelta

from ..config import settings


class StorageService:
    """Storage service for managing file uploads via MinIO/S3."""

    def __init__(self):
        """Initialize storage service."""
        self.provider = settings.STORAGE_PROVIDER
        self.bucket = settings.MINIO_BUCKET

        if self.provider == "minio":
            self.client = Minio(
                settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=settings.MINIO_SECURE,
            )
            self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        """Ensure the storage bucket exists."""
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
                print(f"Created bucket: {self.bucket}")
        except S3Error as e:
            print(f"Error ensuring bucket exists: {e}")

    def upload_file(
        self,
        file_data: BinaryIO,
        object_name: str,
        content_type: Optional[str] = None,
    ) -> tuple[bool, Optional[str]]:
        """
        Upload a file to storage.

        Args:
            file_data: File data as binary stream
            object_name: Name/path for the object in storage
            content_type: MIME type of the file

        Returns:
            Tuple of (success: bool, url: Optional[str])
        """
        try:
            # For development/testing without MinIO
            if settings.DEBUG and self.provider == "mock":
                print(f"Mock upload: {object_name}")
                return True, f"http://localhost:9000/{self.bucket}/{object_name}"

            # Get file size
            file_data.seek(0, 2)  # Seek to end
            file_size = file_data.tell()
            file_data.seek(0)  # Seek back to start

            # Upload to MinIO
            self.client.put_object(
                self.bucket,
                object_name,
                file_data,
                file_size,
                content_type=content_type or "application/octet-stream",
            )

            # Generate URL
            url = self.get_url(object_name)

            return True, url

        except S3Error as e:
            print(f"Error uploading file: {e}")
            return False, None
        except Exception as e:
            print(f"Unexpected error uploading file: {e}")
            return False, None

    def get_url(self, object_name: str, expiry_hours: int = 24) -> str:
        """
        Get a presigned URL for accessing a file.

        Args:
            object_name: Name/path of the object in storage
            expiry_hours: How many hours the URL should be valid for

        Returns:
            Presigned URL
        """
        try:
            # For development/testing
            if settings.DEBUG and self.provider == "mock":
                return f"http://localhost:9000/{self.bucket}/{object_name}"

            url = self.client.presigned_get_object(
                self.bucket,
                object_name,
                expires=timedelta(hours=expiry_hours),
            )
            return url

        except S3Error as e:
            print(f"Error generating presigned URL: {e}")
            return f"/{self.bucket}/{object_name}"

    def delete_file(self, object_name: str) -> bool:
        """
        Delete a file from storage.

        Args:
            object_name: Name/path of the object to delete

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            # For development/testing
            if settings.DEBUG and self.provider == "mock":
                print(f"Mock delete: {object_name}")
                return True

            self.client.remove_object(self.bucket, object_name)
            return True

        except S3Error as e:
            print(f"Error deleting file: {e}")
            return False

    def list_files(self, prefix: Optional[str] = None) -> list:
        """
        List files in storage.

        Args:
            prefix: Optional prefix to filter files

        Returns:
            List of file objects
        """
        try:
            # For development/testing
            if settings.DEBUG and self.provider == "mock":
                return []

            objects = self.client.list_objects(self.bucket, prefix=prefix, recursive=True)
            return [obj.object_name for obj in objects]

        except S3Error as e:
            print(f"Error listing files: {e}")
            return []

    def download_file(self, object_name: str) -> Optional[bytes]:
        """
        Download a file from storage.

        Args:
            object_name: Name/path of the object to download

        Returns:
            File data as bytes, or None if error
        """
        try:
            # For development/testing
            if settings.DEBUG and self.provider == "mock":
                return b"Mock file content"

            response = self.client.get_object(self.bucket, object_name)
            data = response.read()
            response.close()
            response.release_conn()

            return data

        except S3Error as e:
            print(f"Error downloading file: {e}")
            return None


# Singleton instance
storage_service = StorageService()
