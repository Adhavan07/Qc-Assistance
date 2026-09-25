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


@pytest.mark.anyio
async def test_cross_tenant_idor_member_mutation(multi_tenant_client: AsyncClient):
    # 1. Register Org Red
    red_resp = await multi_tenant_client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": "Red Corp",
            "organization_slug": "red-corp",
            "full_name": "Red Owner",
            "email": "owner@red.com",
            "password": "Password123!",
        },
    )
    red_token = red_resp.json()["access_token"]

    # Red adds a member
    red_member_resp = await multi_tenant_client.post(
        "/api/v1/organizations/members",
        headers={"Authorization": f"Bearer {red_token}"},
        json={
            "email": "engineer@red.com",
            "full_name": "Red Engineer",
            "role": "ENGINEER",
            "password": "Password123!",
        },
    )
    assert red_member_resp.status_code == 201
    red_member_id = red_member_resp.json()["id"]

    # 2. Register Org Blue
    blue_resp = await multi_tenant_client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": "Blue Corp",
            "organization_slug": "blue-corp",
            "full_name": "Blue Owner",
            "email": "owner@blue.com",
            "password": "Password123!",
        },
    )
    blue_token = blue_resp.json()["access_token"]

    # 3. IDOR Attack: Blue attempts to PATCH Red's member (MUST return 404, never 200 or 500)
    idor_patch = await multi_tenant_client.patch(
        f"/api/v1/organizations/members/{red_member_id}",
        headers={"Authorization": f"Bearer {blue_token}"},
        json={"full_name": "Compromised Name"},
    )
    assert idor_patch.status_code == 404
    assert "Member not found in your organization" in idor_patch.json()["detail"]

    # 4. IDOR Attack: Blue attempts to DELETE Red's member (MUST return 404)
    idor_delete = await multi_tenant_client.delete(
        f"/api/v1/organizations/members/{red_member_id}",
        headers={"Authorization": f"Bearer {blue_token}"},
    )
    assert idor_delete.status_code == 404
    assert "Member not found in your organization" in idor_delete.json()["detail"]

    # 5. Verify Red member was completely untouched
    red_members_resp = await multi_tenant_client.get(
        "/api/v1/organizations/members",
        headers={"Authorization": f"Bearer {red_token}"},
    )
    red_members = red_members_resp.json()
    engineer = next(m for m in red_members if m["id"] == red_member_id)
    assert engineer["full_name"] == "Red Engineer"


@pytest.mark.anyio
async def test_member_lifecycle_and_sole_owner_guards(multi_tenant_client: AsyncClient):
    # 1. Register Acme Corp
    acme_resp = await multi_tenant_client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": "Acme Systems",
            "organization_slug": "acme-sys",
            "full_name": "Acme Owner",
            "email": "owner@acme.com",
            "password": "Password123!",
        },
    )
    owner_token = acme_resp.json()["access_token"]
    owner_id = acme_resp.json()["user"]["id"]

    # 2. Owner updates Organization Name
    org_patch = await multi_tenant_client.patch(
        "/api/v1/organizations/me",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"name": "Acme Advanced Systems"},
    )
    assert org_patch.status_code == 200
    assert org_patch.json()["name"] == "Acme Advanced Systems"

    # 3. Owner adds an ADMIN and an ENGINEER
    admin_add = await multi_tenant_client.post(
        "/api/v1/organizations/members",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={
            "email": "admin@acme.com",
            "full_name": "Acme Admin",
            "role": "ADMIN",
            "password": "Password123!",
        },
    )
    assert admin_add.status_code == 201
    admin_id = admin_add.json()["id"]

    eng_add = await multi_tenant_client.post(
        "/api/v1/organizations/members",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={
            "email": "engineer@acme.com",
            "full_name": "Acme Engineer",
            "role": "ENGINEER",
            "password": "Password123!",
        },
    )
    assert eng_add.status_code == 201
    eng_id = eng_add.json()["id"]

    # Login as Admin
    admin_login = await multi_tenant_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@acme.com", "password": "Password123!"},
    )
    admin_token = admin_login.json()["access_token"]

    # 4. Privilege Escalation: Admin tries to promote Engineer to OWNER (MUST fail 403)
    escalate_resp = await multi_tenant_client.patch(
        f"/api/v1/organizations/members/{eng_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"role": "OWNER"},
    )
    assert escalate_resp.status_code == 403
    assert "Only an OWNER can promote a member to OWNER" in escalate_resp.json()["detail"]

    # 5. Admin tries to demote or alter the OWNER (MUST fail 403)
    admin_attack_owner = await multi_tenant_client.patch(
        f"/api/v1/organizations/members/{owner_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"role": "VIEWER"},
    )
    assert admin_attack_owner.status_code == 403
    assert "Only an OWNER can modify an OWNER account" in admin_attack_owner.json()["detail"]

    # 6. Admin tries to delete the OWNER (MUST fail 403)
    admin_delete_owner = await multi_tenant_client.delete(
        f"/api/v1/organizations/members/{owner_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert admin_delete_owner.status_code == 403
    assert "Only an OWNER can remove an OWNER account" in admin_delete_owner.json()["detail"]

    # 7. Self-Deletion Prevention: Owner tries to delete themselves (MUST fail 400)
    self_delete = await multi_tenant_client.delete(
        f"/api/v1/organizations/members/{owner_id}",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert self_delete.status_code == 400
    assert "Cannot delete your own account" in self_delete.json()["detail"]

    # 8. Sole Owner Protection: Owner tries to demote themselves to VIEWER (MUST fail 400)
    demote_sole_owner = await multi_tenant_client.patch(
        f"/api/v1/organizations/members/{owner_id}",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"role": "VIEWER"},
    )
    assert demote_sole_owner.status_code == 400
    assert "Cannot demote or deactivate the sole owner" in demote_sole_owner.json()["detail"]

    # 9. Clean deletion: Owner removes Engineer (Succeeds 200)
    del_eng = await multi_tenant_client.delete(
        f"/api/v1/organizations/members/{eng_id}",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert del_eng.status_code == 200
    assert "successfully removed" in del_eng.json()["message"]

