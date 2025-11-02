"""
Unit tests for MinIO object storage client with tenant isolation.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4
from io import BytesIO

from api.minio_client import MinioClient


class TestMinIOPrefixValidation:
    """Test tenant prefix validation."""

    def test_validate_tenant_prefix_valid(self, mock_minio, tenant_id):
        """Test valid tenant prefix passes validation."""
        client = MinioClient()
        client._client = mock_minio

        # Should not raise
        object_name = f"{tenant_id}/documents/lease.pdf"
        client._validate_tenant_prefix(object_name, tenant_id)

    def test_validate_tenant_prefix_invalid(self, mock_minio, tenant_id):
        """Test invalid tenant prefix raises ValueError."""
        client = MinioClient()
        client._client = mock_minio

        # Wrong tenant prefix
        object_name = "other_tenant/documents/lease.pdf"

        with pytest.raises(ValueError) as exc_info:
            client._validate_tenant_prefix(object_name, tenant_id)

        assert "must start with tenant prefix" in str(exc_info.value).lower()

    def test_validate_tenant_prefix_missing(self, mock_minio, tenant_id):
        """Test missing tenant prefix raises ValueError."""
        client = MinioClient()
        client._client = mock_minio

        # No tenant prefix
        object_name = "documents/lease.pdf"

        with pytest.raises(ValueError) as exc_info:
            client._validate_tenant_prefix(object_name, tenant_id)

        assert "must start with tenant prefix" in str(exc_info.value).lower()


class TestMinIOUpload:
    """Test MinIO upload operations."""

    def test_upload_file_with_valid_prefix(self, mock_minio, tenant_id):
        """Test uploading file with valid tenant prefix."""
        client = MinioClient()
        client._client = mock_minio

        bucket_name = "documents"
        object_name = f"{tenant_id}/leases/lease_001.pdf"
        file_path = "/tmp/lease.pdf"

        client.upload_file(
            bucket_name=bucket_name,
            object_name=object_name,
            file_path=file_path,
            tenant_id=tenant_id
        )

        # Verify MinIO client was called
        mock_minio.fput_object.assert_called_once_with(
            bucket_name=bucket_name,
            object_name=object_name,
            file_path=file_path,
            content_type=None
        )

    def test_upload_file_with_invalid_prefix_raises_error(self, mock_minio, tenant_id):
        """Test uploading file with invalid prefix raises ValueError."""
        client = MinioClient()
        client._client = mock_minio

        object_name = "other_tenant/leases/lease_001.pdf"

        with pytest.raises(ValueError):
            client.upload_file(
                bucket_name="documents",
                object_name=object_name,
                file_path="/tmp/lease.pdf",
                tenant_id=tenant_id
            )

    def test_upload_file_with_content_type(self, mock_minio, tenant_id):
        """Test uploading file with content type."""
        client = MinioClient()
        client._client = mock_minio

        object_name = f"{tenant_id}/images/property.jpg"

        client.upload_file(
            bucket_name="images",
            object_name=object_name,
            file_path="/tmp/property.jpg",
            tenant_id=tenant_id,
            content_type="image/jpeg"
        )

        call_args = mock_minio.fput_object.call_args
        assert call_args[1]["content_type"] == "image/jpeg"

    def test_upload_bytes_with_valid_prefix(self, mock_minio, tenant_id):
        """Test uploading bytes data."""
        client = MinioClient()
        client._client = mock_minio

        object_name = f"{tenant_id}/reports/report_001.pdf"
        data = b"PDF file contents"

        client.upload_bytes(
            bucket_name="reports",
            object_name=object_name,
            data=data,
            tenant_id=tenant_id
        )

        # Verify MinIO put_object was called
        mock_minio.put_object.assert_called_once()
        call_args = mock_minio.put_object.call_args

        assert call_args[1]["bucket_name"] == "reports"
        assert call_args[1]["object_name"] == object_name
        assert call_args[1]["length"] == len(data)


class TestMinIODownload:
    """Test MinIO download operations."""

    def test_download_file_with_valid_prefix(self, mock_minio, tenant_id):
        """Test downloading file with valid tenant prefix."""
        client = MinioClient()
        client._client = mock_minio

        object_name = f"{tenant_id}/leases/lease_001.pdf"
        destination = "/tmp/downloaded_lease.pdf"

        client.download_file(
            bucket_name="documents",
            object_name=object_name,
            file_path=destination,
            tenant_id=tenant_id
        )

        mock_minio.fget_object.assert_called_once_with(
            bucket_name="documents",
            object_name=object_name,
            file_path=destination
        )

    def test_download_file_with_invalid_prefix_raises_error(self, mock_minio, tenant_id):
        """Test downloading file with invalid prefix raises ValueError."""
        client = MinioClient()
        client._client = mock_minio

        object_name = "other_tenant/leases/lease_001.pdf"

        with pytest.raises(ValueError):
            client.download_file(
                bucket_name="documents",
                object_name=object_name,
                file_path="/tmp/lease.pdf",
                tenant_id=tenant_id
            )

    def test_download_bytes_with_valid_prefix(self, mock_minio, tenant_id):
        """Test downloading file as bytes."""
        client = MinioClient()
        client._client = mock_minio

        object_name = f"{tenant_id}/reports/report_001.pdf"

        # Mock response
        mock_response = Mock()
        mock_response.read.return_value = b"PDF contents"
        mock_minio.get_object.return_value = mock_response

        data = client.download_bytes(
            bucket_name="reports",
            object_name=object_name,
            tenant_id=tenant_id
        )

        assert data == b"PDF contents"
        mock_minio.get_object.assert_called_once_with(
            bucket_name="reports",
            object_name=object_name
        )


class TestMinIOList:
    """Test MinIO list operations."""

    def test_list_objects_with_tenant_prefix(self, mock_minio, tenant_id):
        """Test listing objects filters by tenant prefix."""
        client = MinioClient()
        client._client = mock_minio

        # Mock objects
        mock_obj1 = Mock()
        mock_obj1.object_name = f"{tenant_id}/docs/file1.pdf"
        mock_obj2 = Mock()
        mock_obj2.object_name = f"{tenant_id}/docs/file2.pdf"

        mock_minio.list_objects.return_value = [mock_obj1, mock_obj2]

        objects = client.list_objects(
            bucket_name="documents",
            tenant_id=tenant_id,
            prefix="docs/"
        )

        # Verify prefix includes tenant_id
        call_args = mock_minio.list_objects.call_args
        assert tenant_id in call_args[1]["prefix"]

        assert len(objects) == 2

    def test_list_objects_tenant_isolation(self, mock_minio, tenant_id):
        """Test list objects are isolated by tenant."""
        client = MinioClient()
        client._client = mock_minio

        # Should only list objects with tenant prefix
        client.list_objects(
            bucket_name="documents",
            tenant_id=tenant_id
        )

        call_args = mock_minio.list_objects.call_args
        assert call_args[1]["prefix"].startswith(f"{tenant_id}/")


class TestMinIODelete:
    """Test MinIO delete operations."""

    def test_delete_object_with_valid_prefix(self, mock_minio, tenant_id):
        """Test deleting object with valid tenant prefix."""
        client = MinioClient()
        client._client = mock_minio

        object_name = f"{tenant_id}/docs/old_file.pdf"

        client.delete_object(
            bucket_name="documents",
            object_name=object_name,
            tenant_id=tenant_id
        )

        mock_minio.remove_object.assert_called_once_with(
            bucket_name="documents",
            object_name=object_name
        )

    def test_delete_object_with_invalid_prefix_raises_error(self, mock_minio, tenant_id):
        """Test deleting object with invalid prefix raises ValueError."""
        client = MinioClient()
        client._client = mock_minio

        object_name = "other_tenant/docs/file.pdf"

        with pytest.raises(ValueError):
            client.delete_object(
                bucket_name="documents",
                object_name=object_name,
                tenant_id=tenant_id
            )


class TestMinIOPresignedURLs:
    """Test MinIO presigned URL generation."""

    def test_get_presigned_url_with_valid_prefix(self, mock_minio, tenant_id):
        """Test generating presigned URL with valid prefix."""
        client = MinioClient()
        client._client = mock_minio

        object_name = f"{tenant_id}/docs/file.pdf"
        mock_minio.presigned_get_object.return_value = "https://minio.example.com/presigned-url"

        url = client.get_presigned_url(
            bucket_name="documents",
            object_name=object_name,
            tenant_id=tenant_id,
            expires_seconds=3600
        )

        assert url == "https://minio.example.com/presigned-url"
        mock_minio.presigned_get_object.assert_called_once()

    def test_get_presigned_url_with_invalid_prefix_raises_error(self, mock_minio, tenant_id):
        """Test generating presigned URL with invalid prefix raises ValueError."""
        client = MinioClient()
        client._client = mock_minio

        object_name = "other_tenant/docs/file.pdf"

        with pytest.raises(ValueError):
            client.get_presigned_url(
                bucket_name="documents",
                object_name=object_name,
                tenant_id=tenant_id
            )


class TestMinIOBucketOperations:
    """Test MinIO bucket operations."""

    def test_bucket_exists_true(self, mock_minio):
        """Test bucket exists returns True."""
        client = MinioClient()
        client._client = mock_minio

        mock_minio.bucket_exists.return_value = True

        exists = client.bucket_exists("documents")

        assert exists is True
        mock_minio.bucket_exists.assert_called_once_with("documents")

    def test_bucket_exists_false(self, mock_minio):
        """Test bucket exists returns False."""
        client = MinioClient()
        client._client = mock_minio

        mock_minio.bucket_exists.return_value = False

        exists = client.bucket_exists("nonexistent")

        assert exists is False

    def test_create_bucket(self, mock_minio):
        """Test bucket creation."""
        client = MinioClient()
        client._client = mock_minio

        client.create_bucket("new-bucket")

        mock_minio.make_bucket.assert_called_once_with("new-bucket")


# ============================================================================
# Test Statistics
# ============================================================================
# Total tests in this module: 21
