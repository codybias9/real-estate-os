"""
Mock MinIO/S3 Object Storage Integration

Simulates object storage without requiring MinIO/S3 instance.
Files are stored in memory for demo purposes.
"""
import uuid
import logging
from typing import Optional, Dict, Any, BinaryIO
from datetime import datetime, timedelta
import hashlib
import base64

logger = logging.getLogger(__name__)

# ============================================================================
# MOCK DATA STORAGE (in-memory for demo purposes)
# ============================================================================

# Store files in memory with metadata
_mock_files = {}


def _generate_mock_etag(content: bytes) -> str:
    """Generate ETag from content (MD5 hash)"""
    return hashlib.md5(content).hexdigest()


def _generate_mock_url(key: str, bucket: str = "real-estate-os-files") -> str:
    """Generate mock URL for file access"""
    return f"https://mock-storage.demo.com/{bucket}/{key}"


# ============================================================================
# FILE UPLOAD
# ============================================================================

def upload_file(
    file_data: bytes,
    key: str,
    bucket: Optional[str] = None,
    content_type: Optional[str] = None,
    metadata: Optional[Dict[str, str]] = None,
    acl: str = "private"
) -> Dict[str, Any]:
    """
    Mock upload file to object storage

    Args:
        file_data: File content as bytes
        key: Object key/path (e.g., "memos/property-123.pdf")
        bucket: Bucket name (defaults to real-estate-os-files)
        content_type: MIME type (e.g., "application/pdf")
        metadata: Custom metadata key-value pairs
        acl: Access control (private, public-read, etc.)

    Returns:
        Dict with upload status, URL, ETag, and metadata
    """
    if not bucket:
        bucket = "real-estate-os-files"

    # Generate ETag
    etag = _generate_mock_etag(file_data)

    # Store in mock storage
    file_record = {
        "bucket": bucket,
        "key": key,
        "content": file_data,
        "content_type": content_type or "application/octet-stream",
        "content_length": len(file_data),
        "etag": etag,
        "metadata": metadata or {},
        "acl": acl,
        "uploaded_at": datetime.utcnow().isoformat(),
        "last_modified": datetime.utcnow().isoformat(),
        "version_id": str(uuid.uuid4())
    }

    # Use bucket:key as storage key
    storage_key = f"{bucket}:{key}"
    _mock_files[storage_key] = file_record

    url = _generate_mock_url(key, bucket)

    logger.info(
        f"[MOCK] File uploaded: {key} ({len(file_data)} bytes, "
        f"ETag: {etag}, Bucket: {bucket})"
    )

    return {
        "success": True,
        "bucket": bucket,
        "key": key,
        "url": url,
        "etag": etag,
        "content_length": len(file_data),
        "content_type": content_type,
        "version_id": file_record["version_id"]
    }


def upload_file_from_path(
    file_path: str,
    key: str,
    bucket: Optional[str] = None,
    content_type: Optional[str] = None,
    metadata: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Mock upload file from filesystem path

    Args:
        file_path: Local file path
        key: Object key/path
        bucket: Bucket name
        content_type: MIME type
        metadata: Custom metadata

    Returns:
        Upload result dict
    """
    try:
        with open(file_path, "rb") as f:
            file_data = f.read()

        return upload_file(
            file_data=file_data,
            key=key,
            bucket=bucket,
            content_type=content_type,
            metadata=metadata
        )

    except FileNotFoundError:
        logger.error(f"[MOCK] File not found: {file_path}")
        return {
            "success": False,
            "error": f"File not found: {file_path}"
        }


# ============================================================================
# FILE DOWNLOAD / ACCESS
# ============================================================================

def get_file_url(
    key: str,
    bucket: Optional[str] = None,
    expires_in: int = 3600,
    public: bool = False
) -> str:
    """
    Mock get file URL (with optional pre-signed URL)

    Args:
        key: Object key/path
        bucket: Bucket name
        expires_in: URL expiration in seconds (for pre-signed URLs)
        public: Whether URL should be public or pre-signed

    Returns:
        URL to access the file
    """
    if not bucket:
        bucket = "real-estate-os-files"

    storage_key = f"{bucket}:{key}"

    if storage_key not in _mock_files:
        logger.warning(f"[MOCK] File not found: {key} in bucket {bucket}")
        return f"https://mock-storage.demo.com/{bucket}/{key}?error=not_found"

    # Generate mock URL
    base_url = _generate_mock_url(key, bucket)

    if public:
        return base_url

    # Add mock pre-signed parameters
    expiration = int((datetime.utcnow() + timedelta(seconds=expires_in)).timestamp())
    signature = hashlib.md5(f"{key}:{expiration}".encode()).hexdigest()[:16]

    presigned_url = f"{base_url}?Expires={expiration}&Signature={signature}"

    logger.info(f"[MOCK] Generated URL for {key} (expires in {expires_in}s)")

    return presigned_url


def download_file(
    key: str,
    bucket: Optional[str] = None
) -> Optional[bytes]:
    """
    Mock download file content

    Args:
        key: Object key/path
        bucket: Bucket name

    Returns:
        File content as bytes, or None if not found
    """
    if not bucket:
        bucket = "real-estate-os-files"

    storage_key = f"{bucket}:{key}"

    if storage_key not in _mock_files:
        logger.warning(f"[MOCK] File not found for download: {key}")
        return None

    file_record = _mock_files[storage_key]
    logger.info(f"[MOCK] Downloaded file: {key} ({file_record['content_length']} bytes)")

    return file_record["content"]


def get_file_metadata(
    key: str,
    bucket: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Mock get file metadata without downloading content

    Args:
        key: Object key/path
        bucket: Bucket name

    Returns:
        File metadata dict, or None if not found
    """
    if not bucket:
        bucket = "real-estate-os-files"

    storage_key = f"{bucket}:{key}"

    if storage_key not in _mock_files:
        logger.warning(f"[MOCK] File not found: {key}")
        return None

    file_record = _mock_files[storage_key]

    return {
        "bucket": file_record["bucket"],
        "key": file_record["key"],
        "content_type": file_record["content_type"],
        "content_length": file_record["content_length"],
        "etag": file_record["etag"],
        "metadata": file_record["metadata"],
        "uploaded_at": file_record["uploaded_at"],
        "last_modified": file_record["last_modified"],
        "version_id": file_record["version_id"]
    }


# ============================================================================
# FILE MANAGEMENT
# ============================================================================

def delete_file(
    key: str,
    bucket: Optional[str] = None
) -> Dict[str, Any]:
    """
    Mock delete file from storage

    Args:
        key: Object key/path
        bucket: Bucket name

    Returns:
        Deletion result dict
    """
    if not bucket:
        bucket = "real-estate-os-files"

    storage_key = f"{bucket}:{key}"

    if storage_key not in _mock_files:
        logger.warning(f"[MOCK] File not found for deletion: {key}")
        return {
            "success": False,
            "error": "File not found"
        }

    del _mock_files[storage_key]

    logger.info(f"[MOCK] Deleted file: {key} from bucket {bucket}")

    return {
        "success": True,
        "bucket": bucket,
        "key": key
    }


def list_files(
    prefix: str = "",
    bucket: Optional[str] = None,
    max_keys: int = 1000
) -> Dict[str, Any]:
    """
    Mock list files in bucket with optional prefix

    Args:
        prefix: Key prefix filter (e.g., "memos/")
        bucket: Bucket name
        max_keys: Maximum number of keys to return

    Returns:
        Dict with list of files and metadata
    """
    if not bucket:
        bucket = "real-estate-os-files"

    # Filter files by bucket and prefix
    matching_files = []
    for storage_key, file_record in _mock_files.items():
        stored_bucket, stored_key = storage_key.split(":", 1)

        if stored_bucket == bucket and stored_key.startswith(prefix):
            matching_files.append({
                "key": stored_key,
                "size": file_record["content_length"],
                "etag": file_record["etag"],
                "last_modified": file_record["last_modified"]
            })

    # Limit results
    matching_files = matching_files[:max_keys]

    logger.info(
        f"[MOCK] Listed {len(matching_files)} files in {bucket} "
        f"with prefix '{prefix}'"
    )

    return {
        "bucket": bucket,
        "prefix": prefix,
        "files": matching_files,
        "count": len(matching_files),
        "is_truncated": len(matching_files) >= max_keys
    }


def copy_file(
    source_key: str,
    dest_key: str,
    source_bucket: Optional[str] = None,
    dest_bucket: Optional[str] = None
) -> Dict[str, Any]:
    """
    Mock copy file within or between buckets

    Args:
        source_key: Source object key
        dest_key: Destination object key
        source_bucket: Source bucket name
        dest_bucket: Destination bucket name

    Returns:
        Copy result dict
    """
    if not source_bucket:
        source_bucket = "real-estate-os-files"
    if not dest_bucket:
        dest_bucket = source_bucket

    source_storage_key = f"{source_bucket}:{source_key}"

    if source_storage_key not in _mock_files:
        logger.warning(f"[MOCK] Source file not found: {source_key}")
        return {
            "success": False,
            "error": "Source file not found"
        }

    # Copy file record
    source_record = _mock_files[source_storage_key]
    dest_storage_key = f"{dest_bucket}:{dest_key}"

    _mock_files[dest_storage_key] = {
        **source_record,
        "bucket": dest_bucket,
        "key": dest_key,
        "uploaded_at": datetime.utcnow().isoformat(),
        "version_id": str(uuid.uuid4())
    }

    logger.info(f"[MOCK] Copied {source_key} -> {dest_key}")

    return {
        "success": True,
        "source_bucket": source_bucket,
        "source_key": source_key,
        "dest_bucket": dest_bucket,
        "dest_key": dest_key,
        "url": _generate_mock_url(dest_key, dest_bucket)
    }


# ============================================================================
# BUCKET OPERATIONS
# ============================================================================

def create_bucket(bucket: str) -> Dict[str, Any]:
    """
    Mock create bucket (no-op since we store everything in memory)

    Args:
        bucket: Bucket name to create

    Returns:
        Creation result
    """
    logger.info(f"[MOCK] Bucket created (no-op): {bucket}")

    return {
        "success": True,
        "bucket": bucket,
        "created_at": datetime.utcnow().isoformat()
    }


def bucket_exists(bucket: str) -> bool:
    """
    Mock check if bucket exists

    In mock mode, all buckets "exist"

    Args:
        bucket: Bucket name

    Returns:
        Always True in mock mode
    """
    return True


# ============================================================================
# INSPECTION / DEBUG HELPERS
# ============================================================================

def get_all_mock_files() -> Dict[str, Any]:
    """Get all mock files (for testing/debugging)"""
    return {
        key: {
            "bucket": record["bucket"],
            "key": record["key"],
            "content_length": record["content_length"],
            "etag": record["etag"],
            "content_type": record["content_type"],
            "uploaded_at": record["uploaded_at"]
        }
        for key, record in _mock_files.items()
    }


def get_storage_stats() -> Dict[str, Any]:
    """Get mock storage statistics"""
    total_files = len(_mock_files)
    total_bytes = sum(r["content_length"] for r in _mock_files.values())

    # Group by bucket
    buckets = {}
    for storage_key, record in _mock_files.items():
        bucket = record["bucket"]
        if bucket not in buckets:
            buckets[bucket] = {"files": 0, "bytes": 0}
        buckets[bucket]["files"] += 1
        buckets[bucket]["bytes"] += record["content_length"]

    return {
        "total_files": total_files,
        "total_bytes": total_bytes,
        "total_mb": round(total_bytes / 1024 / 1024, 2),
        "buckets": buckets
    }


def clear_mock_data():
    """Clear all mock storage data (for testing)"""
    global _mock_files
    _mock_files = {}
    logger.info("[MOCK] Cleared all mock storage data")
