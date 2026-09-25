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
