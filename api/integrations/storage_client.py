"""
MinIO S3-Compatible Storage Client
Upload, download, and manage files in object storage
"""
import os
from typing import Optional, Dict, Any
from datetime import timedelta
from io import BytesIO
import logging

try:
    from minio import Minio
    from minio.error import S3Error
    MINIO_AVAILABLE = True
except ImportError:
    MINIO_AVAILABLE = False
    logging.warning("MinIO not installed - file storage will fail")

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL", "localhost:9000")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "minioadmin")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "minioadmin")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "real-estate-os-files")
S3_USE_SSL = os.getenv("S3_USE_SSL", "false").lower() == "true"

# Remove http:// or https:// prefix if present
if S3_ENDPOINT_URL.startswith("http://"):
    S3_ENDPOINT_URL = S3_ENDPOINT_URL.replace("http://", "")
    S3_USE_SSL = False
elif S3_ENDPOINT_URL.startswith("https://"):
    S3_ENDPOINT_URL = S3_ENDPOINT_URL.replace("https://", "")
    S3_USE_SSL = True

if not MINIO_AVAILABLE:
    logger.warning("MinIO not available - file operations will fail")
    minio_client = None
else:
    try:
        minio_client = Minio(
            S3_ENDPOINT_URL,
            access_key=S3_ACCESS_KEY,
            secret_key=S3_SECRET_KEY,
            secure=S3_USE_SSL
        )

        # Ensure bucket exists
        if not minio_client.bucket_exists(S3_BUCKET_NAME):
            minio_client.make_bucket(S3_BUCKET_NAME)
            logger.info(f"Created bucket: {S3_BUCKET_NAME}")

    except Exception as e:
        logger.error(f"Failed to initialize MinIO client: {str(e)}")
        minio_client = None

# ============================================================================
# FILE UPLOAD
# ============================================================================

def upload_file(
    file_data: bytes,
    object_name: str,
    content_type: str = "application/octet-stream",
    metadata: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Upload a file to MinIO storage

    Args:
        file_data: File content as bytes
        object_name: Object key/path in bucket (e.g., "memos/property-123.pdf")
        content_type: MIME type of the file
        metadata: Optional metadata to attach to object

    Returns:
        Dict with object_name, bucket, size, and success flag

    Raises:
        Exception: If MinIO not available or upload fails
    """
    if not minio_client:
        raise Exception("MinIO storage not configured")

    try:
        # Upload file
        file_stream = BytesIO(file_data)
        file_size = len(file_data)

        result = minio_client.put_object(
            S3_BUCKET_NAME,
            object_name,
            file_stream,
            file_size,
            content_type=content_type,
            metadata=metadata
        )

        logger.info(f"Uploaded file to MinIO: {object_name} ({file_size} bytes)")

        return {
            "success": True,
            "object_name": object_name,
            "bucket": S3_BUCKET_NAME,
            "size": file_size,
            "etag": result.etag,
            "version_id": result.version_id
        }

    except S3Error as e:
        logger.error(f"Failed to upload file to MinIO: {str(e)}")
        raise Exception(f"Storage error: {str(e)}")


def upload_file_from_path(
    file_path: str,
    object_name: Optional[str] = None,
    content_type: str = "application/octet-stream"
) -> Dict[str, Any]:
    """
    Upload a file from filesystem path

    Args:
        file_path: Path to file on disk
        object_name: Object key (defaults to filename)
        content_type: MIME type

    Returns:
        Upload result dict
    """
    if not object_name:
        object_name = os.path.basename(file_path)

    with open(file_path, "rb") as f:
        file_data = f.read()

    return upload_file(file_data, object_name, content_type)


# ============================================================================
# FILE DOWNLOAD
# ============================================================================

def download_file(object_name: str) -> bytes:
    """
    Download a file from MinIO storage

    Args:
        object_name: Object key/path in bucket

    Returns:
        File content as bytes

    Raises:
        Exception: If file not found or download fails
    """
    if not minio_client:
        raise Exception("MinIO storage not configured")

    try:
        response = minio_client.get_object(S3_BUCKET_NAME, object_name)
        file_data = response.read()
        response.close()
        response.release_conn()

        logger.info(f"Downloaded file from MinIO: {object_name}")

        return file_data

    except S3Error as e:
        if e.code == "NoSuchKey":
            raise Exception(f"File not found: {object_name}")
        else:
            logger.error(f"Failed to download file from MinIO: {str(e)}")
            raise Exception(f"Storage error: {str(e)}")


# ============================================================================
# SIGNED URLS
# ============================================================================

def get_file_url(
    object_name: str,
    expires: timedelta = timedelta(hours=1),
    public: bool = False
) -> str:
    """
    Get a signed URL for accessing a file

    Args:
        object_name: Object key/path in bucket
        expires: URL expiration time (default: 1 hour)
        public: If True, make object publicly accessible (not recommended)

    Returns:
        Signed URL string

    Raises:
        Exception: If MinIO not available
    """
    if not minio_client:
        raise Exception("MinIO storage not configured")

    try:
        # Generate presigned URL
        url = minio_client.presigned_get_object(
            S3_BUCKET_NAME,
            object_name,
            expires=expires
        )

        logger.info(f"Generated signed URL for {object_name} (expires in {expires})")

        return url

    except S3Error as e:
        logger.error(f"Failed to generate signed URL: {str(e)}")
        raise Exception(f"Storage error: {str(e)}")


def get_upload_url(
    object_name: str,
    expires: timedelta = timedelta(minutes=15)
) -> str:
    """
    Get a signed URL for uploading a file (PUT request)

    Useful for client-side direct uploads

    Args:
        object_name: Object key/path in bucket
        expires: URL expiration time (default: 15 minutes)

    Returns:
        Signed upload URL string
    """
    if not minio_client:
        raise Exception("MinIO storage not configured")

    try:
        url = minio_client.presigned_put_object(
            S3_BUCKET_NAME,
            object_name,
            expires=expires
        )

        logger.info(f"Generated upload URL for {object_name}")

        return url

    except S3Error as e:
        logger.error(f"Failed to generate upload URL: {str(e)}")
        raise Exception(f"Storage error: {str(e)}")


# ============================================================================
# FILE MANAGEMENT
# ============================================================================

def delete_file(object_name: str) -> bool:
    """
    Delete a file from MinIO storage

    Args:
        object_name: Object key/path in bucket

    Returns:
        True if successful

    Raises:
        Exception: If MinIO not available or deletion fails
    """
    if not minio_client:
        raise Exception("MinIO storage not configured")

    try:
        minio_client.remove_object(S3_BUCKET_NAME, object_name)

        logger.info(f"Deleted file from MinIO: {object_name}")

        return True

    except S3Error as e:
        logger.error(f"Failed to delete file from MinIO: {str(e)}")
        raise Exception(f"Storage error: {str(e)}")


def file_exists(object_name: str) -> bool:
    """
    Check if a file exists in storage

    Args:
        object_name: Object key/path in bucket

    Returns:
        True if file exists, False otherwise
    """
    if not minio_client:
        return False

    try:
        minio_client.stat_object(S3_BUCKET_NAME, object_name)
        return True
    except S3Error:
        return False


def get_file_info(object_name: str) -> Optional[Dict[str, Any]]:
    """
    Get metadata about a file

    Args:
        object_name: Object key/path in bucket

    Returns:
        Dict with size, content_type, last_modified, etag, metadata
        or None if file not found
    """
    if not minio_client:
        return None

    try:
        stat = minio_client.stat_object(S3_BUCKET_NAME, object_name)

        return {
            "object_name": object_name,
            "bucket": S3_BUCKET_NAME,
            "size": stat.size,
            "content_type": stat.content_type,
            "last_modified": stat.last_modified,
            "etag": stat.etag,
            "metadata": stat.metadata,
            "version_id": stat.version_id
        }

    except S3Error as e:
        if e.code == "NoSuchKey":
            return None
        else:
            logger.error(f"Failed to get file info: {str(e)}")
            return None


def list_files(prefix: str = "", max_results: int = 1000) -> list:
    """
    List files in bucket with optional prefix filter

    Args:
        prefix: Object key prefix to filter by (e.g., "memos/")
        max_results: Maximum number of results to return

    Returns:
        List of object names
    """
    if not minio_client:
        return []

    try:
        objects = minio_client.list_objects(
            S3_BUCKET_NAME,
            prefix=prefix,
            recursive=True
        )

        files = []
        for obj in objects:
            files.append(obj.object_name)
            if len(files) >= max_results:
                break

        return files

    except S3Error as e:
        logger.error(f"Failed to list files: {str(e)}")
        return []


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_memo_path(property_id: int, filename: Optional[str] = None) -> str:
    """
    Generate standard path for property memo

    Args:
        property_id: Property ID
        filename: Optional custom filename

    Returns:
        Object key path (e.g., "memos/property-123-2024-01-15.pdf")
    """
    from datetime import datetime

    if not filename:
        timestamp = datetime.utcnow().strftime("%Y-%m-%d-%H%M%S")
        filename = f"property-{property_id}-{timestamp}.pdf"

    return f"memos/{filename}"


def get_packet_path(property_id: int, filename: Optional[str] = None) -> str:
    """Generate standard path for offer packet"""
    from datetime import datetime

    if not filename:
        timestamp = datetime.utcnow().strftime("%Y-%m-%d-%H%M%S")
        filename = f"packet-{property_id}-{timestamp}.pdf"

    return f"packets/{filename}"


def get_artifact_path(deal_room_id: int, filename: str) -> str:
    """Generate standard path for deal room artifacts"""
    return f"deal-rooms/{deal_room_id}/{filename}"
