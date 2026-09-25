"""
Integration tests for SQLAlchemy 2.0 ORM models and relationships.
"""

import uuid
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.src.infrastructure.database import Base
from backend.src.infrastructure.models import (
    AuditLog,
    Document,
    FindingFeedback,
    Organization,
    Project,
    QCFinding,
    QCRun,
    User,
)


@pytest.fixture
async def async_db():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.mark.anyio
async def test_organization_and_user_creation(async_db: AsyncSession):
    org = Organization(
        id=str(uuid.uuid4()),
        name="Acme Harness Ltd",
        slug="acme-harness",
        plan_tier="SUBSCRIPTION",
        credits_remaining=50,
    )
    async_db.add(org)
    await async_db.flush()

    user = User(
        id=str(uuid.uuid4()),
        email="inspector@acme.com",
        password_hash="argon2_hashed_secret",
        full_name="Rajesh Sharma",
        role="INSPECTOR",
        organization_id=org.id,
    )
    async_db.add(user)
    await async_db.commit()

    # Query back
    stmt = select(Organization).where(Organization.slug == "acme-harness")
    result = await async_db.execute(stmt)
    saved_org = result.scalar_one()

    assert saved_org.name == "Acme Harness Ltd"
    assert saved_org.credits_remaining == 50


@pytest.mark.anyio
async def test_full_qc_run_lifecycle_in_database(async_db: AsyncSession):
    org_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    project_id = str(uuid.uuid4())
    doc_id = str(uuid.uuid4())
    run_id = str(uuid.uuid4())
    finding_id = str(uuid.uuid4())

    # 1. Create Tenant & User
    org = Organization(id=org_id, name="Spandsons Horizon", slug="spandsons")
    user = User(id=user_id, email="eng@spandsons.com", password_hash="hash", full_name="Gogulnath", organization_id=org_id)
    project = Project(id=project_id, organization_id=org_id, name="Automotive Loom Batch A")
    async_db.add_all([org, user, project])
    await async_db.flush()

    # 2. Ingest Document Record
    doc = Document(
        id=doc_id,
        organization_id=org_id,
        project_id=project_id,
        uploaded_by=user_id,
        filename="chassis_manual.pdf",
        file_size_bytes=1024 * 500,
        mime_type="application/pdf",
        sha256_checksum="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        storage_path=f"tenants/{org_id}/documents/{doc_id}/chassis_manual.pdf",
        page_count=3,
        status="COMPLETED",
    )
    async_db.add(doc)
    await async_db.flush()

    # 3. Create QC Run
    qc_run = QCRun(
        id=run_id,
        organization_id=org_id,
        document_id=doc_id,
        initiated_by=user_id,
        overall_status="FAIL",
        checks_total=12,
        checks_passed=10,
        checks_failed=2,
        model_version="qc-hybrid-v1",
        prompt_version="prompt-v1",
        rules_version="ruleset-v1",
        processing_time_ms=350,
    )
    async_db.add(qc_run)
    await async_db.flush()

    # 4. Create Finding
    finding = QCFinding(
        id=finding_id,
        qc_run_id=run_id,
        finding_code="D-001",
        rule_id="RULE-WG-001",
        category="WIRE_SPEC",
        description="Missing wire gauge on W102",
        severity="CRITICAL",
        confidence_level="HIGH",
        confidence_score=0.98,
        page_number=1,
        location_bbox={"x": 100, "y": 200, "width": 150, "height": 30},
        evidence_text="W102 BLU",
        requirement_text="Must declare AWG",
        standard_citation="IPC-620 Section 4.1",
        recommendation="Declare nominal gauge",
    )
    async_db.add(finding)

    # 5. Create Audit Log
    audit = AuditLog(
        id=str(uuid.uuid4()),
        organization_id=org_id,
        actor_id=user_id,
        action="QC_RUN_COMPLETED",
        resource_type="qc_run",
        resource_id=run_id,
        event_metadata={"status": "FAIL", "findings_count": 1},
    )
    async_db.add(audit)
    await async_db.commit()

    # Verify query by tenant
    stmt = select(QCFinding).join(QCRun).where(QCRun.organization_id == org_id)
    findings = (await async_db.execute(stmt)).scalars().all()
    assert len(findings) == 1
    assert findings[0].finding_code == "D-001"
    assert findings[0].severity == "CRITICAL"


@pytest.mark.anyio
async def test_cascading_delete_organization(async_db: AsyncSession):
    org_id = str(uuid.uuid4())
    org = Organization(id=org_id, name="Test Delete Org", slug="test-delete")
    user = User(id=str(uuid.uuid4()), email="temp@test.com", password_hash="h", full_name="T", organization_id=org_id)
    async_db.add_all([org, user])
    await async_db.commit()

    # Delete organization
    await async_db.delete(org)
    await async_db.commit()

    # User should also be gone
    res = await async_db.execute(select(User).where(User.organization_id == org_id))
    assert res.scalars().all() == []
