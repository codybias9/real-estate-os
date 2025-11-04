"""
Storage Provider Implementations

MinIOProvider: Local S3-compatible storage for development
S3Provider: AWS S3 for production
"""
import logging
from abc import ABC, abstractmethod
from datetime import timedelta
from typing import Optional, BinaryIO
from minio import Minio
from minio.error import S3Error

from api.config import get_config

logger = logging.getLogger(__name__)


class StorageProvider(ABC):
    """Abstract storage provider interface"""

    @abstractmethod
    def put_object(self, object_name: str, data: BinaryIO, length: int, content_type: str = "application/octet-stream") -> str:
        """Upload object and return key"""
        pass

    @abstractmethod
    def get_presigned_url(self, object_name: str, expiry: int = 3600) -> str:
        """Get presigned URL for object download"""
        pass

    @abstractmethod
    def delete_object(self, object_name: str) -> bool:
        """Delete object"""
        pass


class MinIOProvider(StorageProvider):
    """
    MinIO storage provider for local development

    Connects to MinIO at localhost:9000 with bucket 'memos'
    """

    def __init__(self):
        self.config = get_config()
        self.client = Minio(
            self.config.MINIO_ENDPOINT,
            access_key=self.config.MINIO_ACCESS_KEY,
            secret_key=self.config.MINIO_SECRET_KEY,
            secure=self.config.MINIO_SECURE
        )
        self.bucket = self.config.MINIO_BUCKET

        # Ensure bucket exists
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
                logger.info(f"Created MinIO bucket: {self.bucket}")
            else:
                logger.info(f"MinIO bucket exists: {self.bucket}")
        except S3Error as e:
            logger.error(f"MinIO bucket error: {e}")

        logger.info(f"MinIOProvider initialized: {self.config.MINIO_ENDPOINT}/{self.bucket}")

    def put_object(self, object_name: str, data: BinaryIO, length: int, content_type: str = "application/octet-stream") -> str:
        """Upload object to MinIO"""
        try:
            self.client.put_object(
                self.bucket,
                object_name,
                data,
                length,
                content_type=content_type
            )
            logger.info(f"Uploaded to MinIO: {object_name}")
            return object_name
        except S3Error as e:
            logger.error(f"MinIO upload failed: {e}")
            raise

    def get_presigned_url(self, object_name: str, expiry: int = 3600) -> str:
        """Get presigned URL for object"""
        try:
            url = self.client.presigned_get_object(
                self.bucket,
                object_name,
                expires=timedelta(seconds=expiry)
            )
            logger.info(f"Generated presigned URL for: {object_name}")
            return url
        except S3Error as e:
            logger.error(f"MinIO presigned URL failed: {e}")
            raise

    def delete_object(self, object_name: str) -> bool:
        """Delete object from MinIO"""
        try:
            self.client.remove_object(self.bucket, object_name)
            logger.info(f"Deleted from MinIO: {object_name}")
            return True
        except S3Error as e:
            logger.error(f"MinIO delete failed: {e}")
            return False


class S3Provider(StorageProvider):
    """
    AWS S3 storage provider for production

    Requires AWS credentials in configuration
    """

    def __init__(self):
        self.config = get_config()
        # TODO: Initialize boto3 S3 client
        logger.info("S3Provider initialized (implementation pending)")

    def put_object(self, object_name: str, data: BinaryIO, length: int, content_type: str = "application/octet-stream") -> str:
        """Upload object to S3"""
        logger.warning("S3Provider.put_object not yet implemented")
        return object_name

    def get_presigned_url(self, object_name: str, expiry: int = 3600) -> str:
        """Get presigned URL for S3 object"""
        logger.warning("S3Provider.get_presigned_url not yet implemented")
        return f"https://s3.amazonaws.com/bucket/{object_name}"

    def delete_object(self, object_name: str) -> bool:
        """Delete object from S3"""
        logger.warning("S3Provider.delete_object not yet implemented")
        return True
