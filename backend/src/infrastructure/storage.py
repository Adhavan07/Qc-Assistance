"""
S3-Compatible Object Storage Service.
Implements tenant-partitioned storage paths and short-lived presigned URLs.
Includes a local filesystem fallback for offline development and testing.
"""

import os
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import boto3
from botocore.config import Config

from ..core.config import settings


class StorageServiceInterface(ABC):
    @abstractmethod
    def generate_upload_url(
        self, organization_id: str, document_id: str, filename: str
    ) -> Dict[str, Any]:
        """Generate presigned upload URL and path."""
        pass

    @abstractmethod
    def generate_download_url(self, storage_path: str, expire_seconds: int = 900) -> str:
        """Generate presigned download URL."""
        pass


class S3StorageService(StorageServiceInterface):
    def __init__(self):
        client_kwargs = {
            "service_name": "s3",
            "region_name": settings.S3_REGION,
            "config": Config(signature_version="s3v4"),
        }
        if settings.S3_ENDPOINT_URL:
            client_kwargs["endpoint_url"] = settings.S3_ENDPOINT_URL
        if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
            client_kwargs["aws_access_key_id"] = settings.AWS_ACCESS_KEY_ID
            client_kwargs["aws_secret_access_key"] = settings.AWS_SECRET_ACCESS_KEY

        self.s3_client = boto3.client(**client_kwargs)
        self.bucket = settings.S3_BUCKET_NAME

    def get_tenant_storage_path(self, organization_id: str, document_id: str, filename: str) -> str:
        safe_name = os.path.basename(filename)
        return f"tenants/{organization_id}/documents/{document_id}/original/{safe_name}"

    def generate_upload_url(
        self, organization_id: str, document_id: str, filename: str
    ) -> Dict[str, Any]:
        storage_path = self.get_tenant_storage_path(organization_id, document_id, filename)
        presigned_post = self.s3_client.generate_presigned_post(
            Bucket=self.bucket,
            Key=storage_path,
            ExpiresIn=settings.PRESIGNED_URL_EXPIRE_SECONDS,
            Conditions=[
                ["content-length-range", 100, 50 * 1024 * 1024],  # Max 50 MB
            ],
        )
        return {
            "storage_path": storage_path,
            "upload_url": presigned_post["url"],
            "fields": presigned_post["fields"],
            "expires_in_seconds": settings.PRESIGNED_URL_EXPIRE_SECONDS,
        }

    def generate_download_url(self, storage_path: str, expire_seconds: int = 900) -> str:
        return self.s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": storage_path},
            ExpiresIn=expire_seconds,
        )


class LocalMockStorageService(StorageServiceInterface):
    """Local storage fallback for unit testing and offline development."""

    def __init__(self, base_dir: str = "/tmp/qc_storage"):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    def generate_upload_url(
        self, organization_id: str, document_id: str, filename: str
    ) -> Dict[str, Any]:
        safe_name = os.path.basename(filename)
        storage_path = f"tenants/{organization_id}/documents/{document_id}/original/{safe_name}"
        return {
            "storage_path": storage_path,
            "upload_url": f"http://localhost:8000/api/v1/mock-upload/{storage_path}",
            "fields": {"key": storage_path},
            "expires_in_seconds": 900,
        }

    def generate_download_url(self, storage_path: str, expire_seconds: int = 900) -> str:
        return f"http://localhost:8000/api/v1/mock-download/{storage_path}?expires={expire_seconds}"


def get_storage_service() -> StorageServiceInterface:
    """Factory returning S3 storage or LocalMock based on credentials."""
    if settings.AWS_ACCESS_KEY_ID or settings.S3_ENDPOINT_URL:
        try:
            return S3StorageService()
        except Exception:
            return LocalMockStorageService()
    return LocalMockStorageService()
