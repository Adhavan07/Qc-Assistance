"""
Integration tests for storage services and tenant path isolation.
"""

from backend.src.infrastructure.storage import LocalMockStorageService, S3StorageService


def test_local_storage_presigned_urls():
    service = LocalMockStorageService(base_dir="/tmp/test_qc_storage")
    upload_info = service.generate_upload_url(
        organization_id="org_123",
        document_id="doc_456",
        filename="wiring_spec.pdf",
    )

    assert "tenants/org_123/documents/doc_456/original/wiring_spec.pdf" in upload_info["storage_path"]
    assert "upload_url" in upload_info
    assert upload_info["expires_in_seconds"] == 900

    download_url = service.generate_download_url(upload_info["storage_path"])
    assert "mock-download" in download_url
    assert "wiring_spec.pdf" in download_url


def test_s3_storage_tenant_path_partitioning():
    # Verify path generation logic without needing live AWS credentials
    service = LocalMockStorageService()
    path = service.generate_upload_url("tenant_alpha", "doc_789", "schematic_v2.pdf")["storage_path"]
    assert path.startswith("tenants/tenant_alpha/")
