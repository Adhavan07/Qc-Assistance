"""
Integration tests for Document Processing API Pipeline:
- Trigger document processing job (synchronous and asynchronous)
- Real-time job status tracking and step progression
- Multimodal spatial IDR retrieval (title block, wire callouts, connectors, notes)
- Rasterized page image rendering and thumbnail retrieval
- Processing job manual retry lifecycle
- Cross-tenant IDOR defense on all processing endpoints
"""

import io
import pytest
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.src.api.deps import get_db, get_storage
from backend.src.api.main import app
from backend.src.infrastructure.database import Base
from backend.src.infrastructure.storage import LocalMockStorageService


def generate_test_wiring_pdf() -> bytes:
    """Generate sample PDF with real wire callouts and title block."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.drawString(100, 750, "TITLE: AVIONICS POWER HARNESS")
    c.drawString(100, 730, "DRAWING NO: DWG-AVION-2026 REV: D")
    c.drawString(100, 710, "DRAWN BY: J. DOE")
    c.drawString(100, 690, "APPROVED BY: E. MUSK")
    c.drawString(100, 670, "DATE: 2026-09-25")
    c.drawString(100, 600, "WIRE W101 18 AWG RED FROM J1 TO P2")
    c.drawString(100, 580, "WIRE W102 22 AWG BLK FROM TB1:1 TO J1:2")
    c.drawString(100, 560, "WIRE W103 20 AWG WHT/BLU FROM TB2:3 TO P2:4")
    c.drawString(100, 480, "CONNECTORS: J1: MS3106A-20-29P, P2: MS3102A-20-29S, TB1: WDU-4")
    c.drawString(100, 380, "NOTES:")
    c.drawString(100, 360, "1. ALL WIRES SHALL BE TEFLON INSULATED.")
    c.drawString(100, 340, "2. TEST FOR CONTINUITY BEFORE DELIVERY.")
    c.showPage()
    c.save()
    return buf.getvalue()


@pytest.fixture
async def setup_env(tmp_path):
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    storage_mock = LocalMockStorageService(base_dir=str(tmp_path / "test_storage"))

    async def override_get_db():
        async with session_factory() as session:
            yield session

    def override_get_storage():
        return storage_mock

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_storage] = override_get_storage

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Register Org A User
        reg_a = await client.post(
            "/api/v1/auth/register",
            json={
                "organization_name": "Apex Avionics",
                "organization_slug": "apex-avionics",
                "full_name": "Alice Lead",
                "email": "alice@apexavionics.com",
                "password": "Password123!",
            },
        )
        token_a = reg_a.json()["access_token"]

        # Register Org B User
        reg_b = await client.post(
            "/api/v1/auth/register",
            json={
                "organization_name": "Rival Aerospace",
                "organization_slug": "rival-aero",
                "full_name": "Bob Spy",
                "email": "bob@rivalaero.com",
                "password": "Password123!",
            },
        )
        token_b = reg_b.json()["access_token"]

        yield {
            "client": client,
            "token_a": token_a,
            "token_b": token_b,
        }

    app.dependency_overrides.clear()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.mark.anyio
async def test_full_document_processing_lifecycle(setup_env):
    """Test full document upload, processing, extracted IDR, and page rendering."""
    client: AsyncClient = setup_env["client"]
    token_a = setup_env["token_a"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # 1. Create project
    proj_resp = await client.post(
        "/api/v1/projects",
        json={"name": "Avionics Harness Program", "description": "Phase 4 verification"},
        headers=headers_a,
    )
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]

    # 2. Upload PDF diagram via direct multipart endpoint
    pdf_bytes = generate_test_wiring_pdf()
    files = {"file": ("avionics_schematic.pdf", pdf_bytes, "application/pdf")}
    upload_resp = await client.post(
        "/api/v1/documents/upload",
        data={"project_id": project_id, "allow_duplicate": "true"},
        files=files,
        headers=headers_a,
    )
    assert upload_resp.status_code == 201
    doc_data = upload_resp.json()
    doc_id = doc_data["id"]
    assert doc_data["status"] == "UPLOADED"

    # 3. Verify extracted IDR endpoint is blocked before processing
    pre_extracted = await client.get(
        f"/api/v1/documents/{doc_id}/extracted",
        headers=headers_a,
    )
    assert pre_extracted.status_code == 400
    assert "has not been processed yet" in pre_extracted.json()["detail"]

    # 4. Trigger synchronous Document Processing
    process_resp = await client.post(
        f"/api/v1/documents/{doc_id}/process",
        json={"async_mode": False, "force_reprocess": False},
        headers=headers_a,
    )
    assert process_resp.status_code == 200
    job_data = process_resp.json()
    assert job_data["document_id"] == doc_id
    assert job_data["status"] == "COMPLETED"
    assert job_data["progress_percent"] == 100
    assert job_data["current_step"] == "COMPLETED"
    assert job_data["result_metadata"] is not None
    assert job_data["result_metadata"]["page_count"] == 1
    assert job_data["result_metadata"]["wire_callouts_extracted"] >= 3

    # 5. Verify Document entity status transitioned to PROCESSED
    doc_check = await client.get(f"/api/v1/documents/{doc_id}", headers=headers_a)
    assert doc_check.status_code == 200
    assert doc_check.json()["status"] == "PROCESSED"

    # 6. Retrieve Extracted IDR
    extracted_resp = await client.get(
        f"/api/v1/documents/{doc_id}/extracted",
        headers=headers_a,
    )
    assert extracted_resp.status_code == 200
    idr_data = extracted_resp.json()
    assert idr_data["document_id"] == doc_id
    assert idr_data["page_count"] == 1
    page1 = idr_data["pages"][0]

    # Verify Title Block
    assert page1["title_block"] is not None
    assert page1["title_block"]["drawing_number"] == "DWG-AVION-2026"
    assert page1["title_block"]["revision"] == "D"

    # Verify Wire Callouts
    wire_numbers = [w["wire_number"] for w in page1["wire_callouts"]]
    assert "W101" in wire_numbers
    assert "W102" in wire_numbers
    assert "W103" in wire_numbers

    # Verify Connectors
    connector_refs = [c["ref_des"] for c in page1["connectors"]]
    assert "J1" in connector_refs
    assert "P2" in connector_refs
    assert "TB1" in connector_refs

    # Verify General Notes
    assert len(page1["general_notes"]) >= 2

    # 7. Test Page Image URL retrieval
    page_img_resp = await client.get(
        f"/api/v1/documents/{doc_id}/pages/1/image",
        headers=headers_a,
    )
    assert page_img_resp.status_code == 200
    img_info = page_img_resp.json()
    assert img_info["document_id"] == doc_id
    assert img_info["page_number"] == 1
    assert "download_url" in img_info["image_url"] or "mock-download" in img_info["image_url"]

    # 8. Test raw page image binary stream
    raw_img_resp = await client.get(
        f"/api/v1/documents/{doc_id}/pages/1/raw-image",
        headers=headers_a,
    )
    assert raw_img_resp.status_code == 200
    assert raw_img_resp.headers["content-type"] == "image/png"
    assert raw_img_resp.content.startswith(b"\x89PNG")

    # 9. Test raw thumbnail binary stream
    raw_thumb_resp = await client.get(
        f"/api/v1/documents/{doc_id}/pages/1/raw-thumbnail",
        headers=headers_a,
    )
    assert raw_thumb_resp.status_code == 200
    assert raw_thumb_resp.headers["content-type"] == "image/png"
    assert raw_thumb_resp.content.startswith(b"\x89PNG")

    # 10. List Processing Jobs
    jobs_resp = await client.get(
        f"/api/v1/documents/{doc_id}/processing-jobs",
        headers=headers_a,
    )
    assert jobs_resp.status_code == 200
    jobs_list = jobs_resp.json()
    assert len(jobs_list) >= 1
    assert jobs_list[0]["status"] == "COMPLETED"

    # 11. Test Manual Job Retry Endpoint
    retry_resp = await client.post(
        f"/api/v1/documents/{doc_id}/processing-jobs/{job_data['id']}/retry",
        headers=headers_a,
    )
    assert retry_resp.status_code == 200
    retried_job = retry_resp.json()
    assert retried_job["status"] == "COMPLETED"
    assert retried_job["attempts"] >= 2


@pytest.mark.anyio
async def test_cross_tenant_idor_document_processing(setup_env):
    """Verify tenant isolation: Org B cannot process, view IDR, or download Org A images."""
    client: AsyncClient = setup_env["client"]
    token_a = setup_env["token_a"]
    token_b = setup_env["token_b"]
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Org A creates project and uploads document
    proj_resp = await client.post(
        "/api/v1/projects",
        json={"name": "Org A Confidential Project"},
        headers=headers_a,
    )
    project_id = proj_resp.json()["id"]

    pdf_bytes = generate_test_wiring_pdf()
    files = {"file": ("classified_diagram.pdf", pdf_bytes, "application/pdf")}
    upload_resp = await client.post(
        "/api/v1/documents/upload",
        data={"project_id": project_id, "allow_duplicate": "true"},
        files=files,
        headers=headers_a,
    )
    doc_id = upload_resp.json()["id"]

    # Org A processes document
    proc_resp = await client.post(
        f"/api/v1/documents/{doc_id}/process",
        headers=headers_a,
    )
    assert proc_resp.status_code == 200
    job_id = proc_resp.json()["id"]

    # Org B attempts to trigger process on Org A document -> 404
    b_process = await client.post(
        f"/api/v1/documents/{doc_id}/process",
        headers=headers_b,
    )
    assert b_process.status_code == 404

    # Org B attempts to retrieve extracted IDR -> 404
    b_extracted = await client.get(
        f"/api/v1/documents/{doc_id}/extracted",
        headers=headers_b,
    )
    assert b_extracted.status_code == 404

    # Org B attempts to access page image -> 404
    b_img = await client.get(
        f"/api/v1/documents/{doc_id}/pages/1/image",
        headers=headers_b,
    )
    assert b_img.status_code == 404

    # Org B attempts to access raw page image stream -> 404
    b_raw = await client.get(
        f"/api/v1/documents/{doc_id}/pages/1/raw-image",
        headers=headers_b,
    )
    assert b_raw.status_code == 404

    # Org B attempts to view processing jobs -> 404
    b_jobs = await client.get(
        f"/api/v1/documents/{doc_id}/processing-jobs",
        headers=headers_b,
    )
    assert b_jobs.status_code == 404

    # Org B attempts to retry Org A job -> 404
    b_retry = await client.post(
        f"/api/v1/documents/{doc_id}/processing-jobs/{job_id}/retry",
        headers=headers_b,
    )
    assert b_retry.status_code == 404
