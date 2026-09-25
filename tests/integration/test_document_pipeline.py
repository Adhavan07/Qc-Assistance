"""
Integration tests for Project Creation and Document Upload Pipeline.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.src.api.deps import get_db
from backend.src.api.main import app
from backend.src.infrastructure.database import Base


@pytest.fixture
async def authenticated_client():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Register and get token
        reg_resp = await client.post(
            "/api/v1/auth/register",
            json={
                "organization_name": "Loom Tech Inc",
                "organization_slug": "loom-tech",
                "full_name": "Sarah Connor",
                "email": "sarah@loomtech.com",
                "password": "Password123!",
            },
        )
        token = reg_resp.json()["access_token"]
        client.headers.update({"Authorization": f"Bearer {token}"})
        yield client

    app.dependency_overrides.clear()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.mark.anyio
async def test_project_and_document_upload_flow(authenticated_client: AsyncClient):
    # 1. Create a Project
    proj_resp = await authenticated_client.post(
        "/api/v1/projects",
        json={"name": "Aerospace Harness Batch #1", "description": "MIL-SPEC test project"},
    )
    assert proj_resp.status_code == 201
    project = proj_resp.json()
    project_id = project["id"]
    assert project["name"] == "Aerospace Harness Batch #1"

    # 2. Request Upload Intent
    intent_resp = await authenticated_client.post(
        "/api/v1/documents/upload-intent",
        json={
            "project_id": project_id,
            "filename": "radar_harness_drawing.pdf",
            "file_size_bytes": 1024 * 350,
            "mime_type": "application/pdf",
        },
    )
    assert intent_resp.status_code == 200
    intent = intent_resp.json()
    document_id = intent["document_id"]
    storage_path = intent["storage_path"]
    assert "tenants/" in storage_path
    assert "upload_url" in intent

    # 3. Confirm Document Upload
    confirm_resp = await authenticated_client.post(
        f"/api/v1/documents/{document_id}/confirm",
        json={
            "project_id": project_id,
            "filename": "radar_harness_drawing.pdf",
            "storage_path": storage_path,
            "file_size_bytes": 1024 * 350,
            "mime_type": "application/pdf",
            "sha256_checksum": "a1b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef0",
            "page_count": 2,
        },
    )
    assert confirm_resp.status_code == 201
    doc = confirm_resp.json()
    assert doc["id"] == document_id
    assert doc["filename"] == "radar_harness_drawing.pdf"
    assert doc["status"] == "UPLOADED"

    # 4. List Documents
    list_resp = await authenticated_client.get(f"/api/v1/documents?project_id={project_id}")
    assert list_resp.status_code == 200
    docs = list_resp.json()
    assert len(docs) == 1
    assert docs[0]["id"] == document_id

    # 5. Get Document Details
    detail_resp = await authenticated_client.get(f"/api/v1/documents/{document_id}")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["id"] == document_id


@pytest.mark.anyio
async def test_project_crud_lifecycle(authenticated_client: AsyncClient):
    # 1. Create Project
    create_resp = await authenticated_client.post(
        "/api/v1/projects",
        json={"name": "Avionics Cabinet Beta", "description": "High-density harnesses"},
    )
    assert create_resp.status_code == 201
    proj_id = create_resp.json()["id"]

    # 2. Get Project
    get_resp = await authenticated_client.get(f"/api/v1/projects/{proj_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["name"] == "Avionics Cabinet Beta"
    assert get_resp.json()["document_count"] == 0

    # 3. Update Project
    patch_resp = await authenticated_client.patch(
        f"/api/v1/projects/{proj_id}",
        json={"name": "Avionics Cabinet Beta Rev 2", "description": "Updated specs"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["name"] == "Avionics Cabinet Beta Rev 2"

    # 4. Delete Project
    del_resp = await authenticated_client.delete(f"/api/v1/projects/{proj_id}")
    assert del_resp.status_code == 200
    assert "successfully deleted" in del_resp.json()["message"]

    # 5. Confirm Gone
    gone_resp = await authenticated_client.get(f"/api/v1/projects/{proj_id}")
    assert gone_resp.status_code == 404


@pytest.mark.anyio
async def test_sha256_deduplication_detection(authenticated_client: AsyncClient):
    # Setup project
    proj_resp = await authenticated_client.post(
        "/api/v1/projects",
        json={"name": "Dedup Test Project"},
    )
    project_id = proj_resp.json()["id"]

    checksum = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

    # Upload Doc 1
    doc1_id = "doc-dedup-01"
    doc1_resp = await authenticated_client.post(
        f"/api/v1/documents/{doc1_id}/confirm",
        json={
            "project_id": project_id,
            "filename": "harness_spec.pdf",
            "storage_path": f"tenants/test/documents/{doc1_id}/original/harness_spec.pdf",
            "file_size_bytes": 1024,
            "mime_type": "application/pdf",
            "sha256_checksum": checksum,
            "page_count": 1,
        },
    )
    assert doc1_resp.status_code == 201

    # Upload Doc 2 with same checksum (Must be rejected with 409 Conflict)
    doc2_id = "doc-dedup-02"
    dup_resp = await authenticated_client.post(
        f"/api/v1/documents/{doc2_id}/confirm",
        json={
            "project_id": project_id,
            "filename": "harness_spec_copy.pdf",
            "storage_path": f"tenants/test/documents/{doc2_id}/original/harness_spec_copy.pdf",
            "file_size_bytes": 1024,
            "mime_type": "application/pdf",
            "sha256_checksum": checksum,
            "page_count": 1,
            "allow_duplicate": False,
        },
    )
    assert dup_resp.status_code == 409
    assert "Duplicate diagram detected" in dup_resp.json()["detail"]

    # Upload Doc 2 with allow_duplicate=True (Succeeds)
    force_resp = await authenticated_client.post(
        f"/api/v1/documents/{doc2_id}/confirm",
        json={
            "project_id": project_id,
            "filename": "harness_spec_copy.pdf",
            "storage_path": f"tenants/test/documents/{doc2_id}/original/harness_spec_copy.pdf",
            "file_size_bytes": 1024,
            "mime_type": "application/pdf",
            "sha256_checksum": checksum,
            "page_count": 1,
            "allow_duplicate": True,
        },
    )
    assert force_resp.status_code == 201
    assert force_resp.json()["is_duplicate"] is True


@pytest.mark.anyio
async def test_direct_multipart_upload_and_download_url(authenticated_client: AsyncClient):
    # Setup project
    proj_resp = await authenticated_client.post(
        "/api/v1/projects",
        json={"name": "Direct Upload Project"},
    )
    project_id = proj_resp.json()["id"]

    # Simple valid PDF binary header
    pdf_bytes = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Count 1\n/Kids [3 0 R]\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n168\n%%EOF"

    files = {"file": ("direct_schematic.pdf", pdf_bytes, "application/pdf")}
    data = {"project_id": project_id, "allow_duplicate": "true"}

    upload_resp = await authenticated_client.post(
        "/api/v1/documents/upload",
        files=files,
        data=data,
    )
    assert upload_resp.status_code == 201
    doc_data = upload_resp.json()
    assert doc_data["filename"] == "direct_schematic.pdf"
    assert doc_data["status"] == "UPLOADED"
    doc_id = doc_data["id"]

    # Request presigned download URL
    dl_resp = await authenticated_client.get(f"/api/v1/documents/{doc_id}/download-url")
    assert dl_resp.status_code == 200
    assert "download_url" in dl_resp.json()
    assert dl_resp.json()["expires_in_seconds"] == 900

    # Delete Document
    del_resp = await authenticated_client.delete(f"/api/v1/documents/{doc_id}")
    assert del_resp.status_code == 200

    # Verify 404 after deletion
    after_del = await authenticated_client.get(f"/api/v1/documents/{doc_id}")
    assert after_del.status_code == 404


@pytest.mark.anyio
async def test_cross_tenant_project_and_document_idor(authenticated_client: AsyncClient):
    # Client 1 creates project & document
    p1_resp = await authenticated_client.post(
        "/api/v1/projects",
        json={"name": "Org 1 Secret Diagrams"},
    )
    p1_id = p1_resp.json()["id"]

    doc1_resp = await authenticated_client.post(
        "/api/v1/documents/doc-secret-1/confirm",
        json={
            "project_id": p1_id,
            "filename": "secret_schematic.pdf",
            "storage_path": "tenants/org1/documents/doc-secret-1/original/secret_schematic.pdf",
            "file_size_bytes": 500,
            "mime_type": "application/pdf",
            "sha256_checksum": "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
            "page_count": 1,
        },
    )
    assert doc1_resp.status_code == 201
    doc1_id = doc1_resp.json()["id"]

    # Register Org 2 (Attacker)
    reg2 = await authenticated_client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": "Org Two Competitor",
            "organization_slug": "org-two-comp",
            "full_name": "Eve Attacker",
            "email": "eve@competitor.com",
            "password": "Password123!",
        },
    )
    token2 = reg2.json()["access_token"]
    headers2 = {"Authorization": f"Bearer {token2}"}

    # Org 2 attempts to GET Org 1 Project (Must return 404)
    assert (await authenticated_client.get(f"/api/v1/projects/{p1_id}", headers=headers2)).status_code == 404

    # Org 2 attempts to UPDATE Org 1 Project (Must return 404)
    assert (
        await authenticated_client.patch(
            f"/api/v1/projects/{p1_id}",
            headers=headers2,
            json={"name": "Hacked Project"},
        )
    ).status_code == 404

    # Org 2 attempts to DELETE Org 1 Project (Must return 404)
    assert (await authenticated_client.delete(f"/api/v1/projects/{p1_id}", headers=headers2)).status_code == 404

    # Org 2 attempts to upload into Org 1 Project (Must return 404)
    assert (
        await authenticated_client.post(
            "/api/v1/documents/upload-intent",
            headers=headers2,
            json={
                "project_id": p1_id,
                "filename": "trojan.pdf",
                "file_size_bytes": 100,
                "mime_type": "application/pdf",
            },
        )
    ).status_code == 404

    # Org 2 attempts to GET Org 1 Document (Must return 404)
    assert (await authenticated_client.get(f"/api/v1/documents/{doc1_id}", headers=headers2)).status_code == 404

    # Org 2 attempts to DOWNLOAD Org 1 Document (Must return 404)
    assert (await authenticated_client.get(f"/api/v1/documents/{doc1_id}/download-url", headers=headers2)).status_code == 404

    # Org 2 attempts to DELETE Org 1 Document (Must return 404)
    assert (await authenticated_client.delete(f"/api/v1/documents/{doc1_id}", headers=headers2)).status_code == 404

