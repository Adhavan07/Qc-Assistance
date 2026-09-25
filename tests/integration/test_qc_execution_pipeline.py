"""
Integration tests for QC Job Dispatch, Worker Processing, Finding Persistence, and SSE Streaming.
"""

import os
import tempfile
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.src.api.deps import get_db, get_queue
from backend.src.api.main import app
from backend.src.infrastructure.database import Base
from backend.src.infrastructure.models import Organization, QCRun
from backend.src.infrastructure.queue import AsyncInMemoryQueue
from backend.src.services.qc_worker import process_qc_job
from tests.unit.test_engine import create_sample_schematic_pdf


@pytest.fixture
async def qc_pipeline_env():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    test_queue = AsyncInMemoryQueue()

    async def override_get_db():
        async with session_factory() as session:
            yield session

    def override_get_queue():
        return test_queue

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_queue] = override_get_queue

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Register Org
        reg = await client.post(
            "/api/v1/auth/register",
            json={
                "organization_name": "Quality EMS Corp",
                "organization_slug": "quality-ems",
                "full_name": "Vikram Seth",
                "email": "vikram@qualityems.com",
                "password": "Password123!",
            },
        )
        token = reg.json()["access_token"]
        client.headers.update({"Authorization": f"Bearer {token}"})

        # Create Project
        proj = await client.post("/api/v1/projects", json={"name": "Harness QC Batch A"})
        project_id = proj.json()["id"]

        yield {
            "client": client,
            "queue": test_queue,
            "session_factory": session_factory,
            "project_id": project_id,
        }

    app.dependency_overrides.clear()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.mark.anyio
async def test_full_async_qc_pipeline_execution(qc_pipeline_env):
    client: AsyncClient = qc_pipeline_env["client"]
    queue: AsyncInMemoryQueue = qc_pipeline_env["queue"]
    session_factory = qc_pipeline_env["session_factory"]
    project_id = qc_pipeline_env["project_id"]

    with tempfile.TemporaryDirectory() as tmpdir:
        # 1. Create realistic PDF on disk
        test_pdf = os.path.join(tmpdir, "industrial_harness.pdf")
        create_sample_schematic_pdf(test_pdf)

        # 2. Confirm Document Upload
        doc_resp = await client.post(
            "/api/v1/documents/doc_test_101/confirm",
            json={
                "project_id": project_id,
                "filename": "industrial_harness.pdf",
                "storage_path": test_pdf,
                "file_size_bytes": os.path.getsize(test_pdf),
                "mime_type": "application/pdf",
                "sha256_checksum": "dummychecksum1234567890abcdef",
                "page_count": 1,
            },
        )
        assert doc_resp.status_code == 201

        # 3. Check credits before trigger (Initial: 3)
        org_resp = await client.get("/api/v1/organizations/me")
        assert org_resp.json()["credits_remaining"] == 3

        # 4. Trigger QC Run
        run_resp = await client.post(
            "/api/v1/qc-runs",
            json={"document_id": "doc_test_101", "standards": ["IPC-WHMA-A-620D", "UL 508A"]},
        )
        assert run_resp.status_code == 201
        run_data = run_resp.json()
        qc_run_id = run_data["id"]
        assert run_data["overall_status"] == "QUEUED"

        # 5. Verify credit deducted from 3 to 2
        org_resp_after = await client.get("/api/v1/organizations/me")
        assert org_resp_after.json()["credits_remaining"] == 2

        # 6. Dequeue and execute worker
        assert queue.queue_size() == 1
        job_payload = await queue.dequeue()
        assert job_payload.qc_run_id == qc_run_id

        await process_qc_job(job_payload, session_factory)

        # 7. Poll QC Run Status -> Should be completed with FAIL (due to missing gauge & color)
        status_resp = await client.get(f"/api/v1/qc-runs/{qc_run_id}")
        assert status_resp.status_code == 200
        completed_run = status_resp.json()
        assert completed_run["overall_status"] == "FAIL"
        assert completed_run["checks_failed"] >= 2
        assert completed_run["processing_time_ms"] >= 0

        # 8. Query Findings
        findings_resp = await client.get(f"/api/v1/qc-runs/{qc_run_id}/findings")
        assert findings_resp.status_code == 200
        findings = findings_resp.json()
        assert len(findings) >= 2

        # Check finding properties
        rule_ids = [f["rule_id"] for f in findings]
        assert "RULE-WG-001" in rule_ids
        assert "RULE-CC-003" in rule_ids

        # 9. Test Server-Sent Events (SSE) Stream
        sse_resp = await client.get(f"/api/v1/qc-runs/{qc_run_id}/stream")
        assert sse_resp.status_code == 200
        assert "text/event-stream" in sse_resp.headers["content-type"]
        assert "event: progress" in sse_resp.text
        assert "event: complete" in sse_resp.text


@pytest.mark.anyio
async def test_qc_credit_exhaustion_blocks_processing(qc_pipeline_env):
    client: AsyncClient = qc_pipeline_env["client"]
    project_id = qc_pipeline_env["project_id"]

    # Register document
    await client.post(
        "/api/v1/documents/doc_exhaust_test/confirm",
        json={
            "project_id": project_id,
            "filename": "spec.pdf",
            "storage_path": "/tmp/dummy.pdf",
            "file_size_bytes": 1000,
            "mime_type": "application/pdf",
            "sha256_checksum": "dummy123456",
            "page_count": 1,
        },
    )

    # Org starts with 3 credits. Consume all 3 credits.
    for i in range(3):
        res = await client.post("/api/v1/qc-runs", json={"document_id": "doc_exhaust_test"})
        assert res.status_code == 201

    # 4th attempt must fail with 402 Payment Required!
    fail_res = await client.post("/api/v1/qc-runs", json={"document_id": "doc_exhaust_test"})
    assert fail_res.status_code == 402
    assert "exhausted its available QC check credits" in fail_res.json()["detail"]
