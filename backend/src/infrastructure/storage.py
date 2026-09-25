"""
S3-Compatible Object Storage Service.
Implements tenant-partitioned storage paths and short-lived presigned URLs.
Includes a local filesystem fallback for offline development and testing.
"""

import hashlib
import io
import os
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import boto3
from botocore.config import Config
import pypdf

from ..core.config import settings


def compute_sha256(content: bytes) -> str:
    """Compute hex SHA-256 digest of binary content."""
    return hashlib.sha256(content).hexdigest()


def count_pdf_pages(content: bytes) -> int:
    """Accurately count pages in PDF drawing manuals using pypdf."""
    try:
        reader = pypdf.PdfReader(io.BytesIO(content))
        return max(1, len(reader.pages))
    except Exception:
        return 1


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

    @abstractmethod
    def save_file(self, storage_path: str, content: bytes) -> str:
        """Directly persist binary content to storage backend."""
        pass

    @abstractmethod
    def read_file(self, storage_path: str) -> bytes:
        """Retrieve binary content from storage backend."""
        pass

    @abstractmethod
    def delete_file(self, storage_path: str) -> bool:
        """Delete file from storage backend."""
        pass

    @abstractmethod
    def file_exists(self, storage_path: str) -> bool:
        """Check if file exists in storage backend."""
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
                ["content-length-range", 10, 50 * 1024 * 1024],  # Max 50 MB
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

    def save_file(self, storage_path: str, content: bytes) -> str:
        self.s3_client.put_object(
            Bucket=self.bucket,
            Key=storage_path,
            Body=content,
        )
        return storage_path

    def read_file(self, storage_path: str) -> bytes:
        response = self.s3_client.get_object(Bucket=self.bucket, Key=storage_path)
        return response["Body"].read()

    def delete_file(self, storage_path: str) -> bool:
        try:
            self.s3_client.delete_object(Bucket=self.bucket, Key=storage_path)
            return True
        except Exception:
            return False

    def file_exists(self, storage_path: str) -> bool:
        try:
            self.s3_client.head_object(Bucket=self.bucket, Key=storage_path)
            return True
        except Exception:
            return False


class LocalMockStorageService(StorageServiceInterface):
    """Local filesystem storage for offline development and test execution."""

    def __init__(self, base_dir: str = "/tmp/qc_storage"):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    def _full_path(self, storage_path: str) -> str:
        # Prevent path traversal attacks
        clean_path = storage_path.lstrip("/").replace("..", "_")
        return os.path.join(self.base_dir, clean_path)

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

    def save_file(self, storage_path: str, content: bytes) -> str:
        full_path = self._full_path(storage_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "wb") as f:
            f.write(content)
        return storage_path

    def read_file(self, storage_path: str) -> bytes:
        full_path = self._full_path(storage_path)
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"Storage object not found: {storage_path}")
        with open(full_path, "rb") as f:
            return f.read()

    def delete_file(self, storage_path: str) -> bool:
        full_path = self._full_path(storage_path)
        if os.path.exists(full_path):
            try:
                os.remove(full_path)
                return True
            except OSError:
                return False
        return False

    def file_exists(self, storage_path: str) -> bool:
        return os.path.exists(self._full_path(storage_path))


def get_storage_service() -> StorageServiceInterface:
    """Factory returning S3 storage or LocalMock based on credentials."""
    if settings.AWS_ACCESS_KEY_ID or settings.S3_ENDPOINT_URL:
        try:
            return S3StorageService()
        except Exception:
            return LocalMockStorageService()
    return LocalMockStorageService()

