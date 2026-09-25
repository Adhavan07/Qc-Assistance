"""
Cross-Tenant Security & Isolation Verification Tests.
Simulates IDOR and cross-tenant access attempts to prove strict logical isolation.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.src.api.deps import get_db
from backend.src.api.main import app
from backend.src.infrastructure.database import Base


@pytest.fixture
async def multi_tenant_client():
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
        yield client

    app.dependency_overrides.clear()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.mark.anyio
async def test_cross_tenant_member_list_isolation(multi_tenant_client: AsyncClient):
    # 1. Register Company Alpha
    alpha_resp = await multi_tenant_client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": "Company Alpha",
            "organization_slug": "company-alpha",
            "full_name": "Alpha Owner",
            "email": "owner@alpha.com",
            "password": "Password123!",
        },
    )
    alpha_token = alpha_resp.json()["access_token"]

    # 2. Register Company Beta
    beta_resp = await multi_tenant_client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": "Company Beta",
            "organization_slug": "company-beta",
            "full_name": "Beta Owner",
            "email": "owner@beta.com",
            "password": "Password123!",
        },
    )
    beta_token = beta_resp.json()["access_token"]

    # 3. Alpha Owner adds an employee in Alpha
    await multi_tenant_client.post(
        "/api/v1/organizations/members",
        headers={"Authorization": f"Bearer {alpha_token}"},
        json={
            "email": "engineer@alpha.com",
            "full_name": "Alpha Engineer",
            "role": "ENGINEER",
            "password": "Password123!",
        },
    )

    # 4. Beta Owner lists members
    beta_members_resp = await multi_tenant_client.get(
        "/api/v1/organizations/members",
        headers={"Authorization": f"Bearer {beta_token}"},
    )
    assert beta_members_resp.status_code == 200
    beta_members = beta_members_resp.json()

    # CRITICAL CHECK: Beta must ONLY see Beta members, NEVER Alpha members!
    member_emails = [m["email"] for m in beta_members]
    assert "owner@beta.com" in member_emails
    assert "owner@alpha.com" not in member_emails
    assert "engineer@alpha.com" not in member_emails
    assert len(beta_members) == 1


@pytest.mark.anyio
async def test_organization_me_returns_isolated_tenant(multi_tenant_client: AsyncClient):
    # Register Org 1
    resp1 = await multi_tenant_client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": "Tenant One",
            "organization_slug": "tenant-one",
            "full_name": "User One",
            "email": "one@tenant.com",
            "password": "Password123!",
        },
    )
    token1 = resp1.json()["access_token"]

    # Register Org 2
    resp2 = await multi_tenant_client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": "Tenant Two",
            "organization_slug": "tenant-two",
            "full_name": "User Two",
            "email": "two@tenant.com",
            "password": "Password123!",
        },
    )
    token2 = resp2.json()["access_token"]

    # Query Org 1
    org1_resp = await multi_tenant_client.get(
        "/api/v1/organizations/me",
        headers={"Authorization": f"Bearer {token1}"},
    )
    assert org1_resp.json()["slug"] == "tenant-one"

    # Query Org 2
    org2_resp = await multi_tenant_client.get(
        "/api/v1/organizations/me",
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert org2_resp.json()["slug"] == "tenant-two"
