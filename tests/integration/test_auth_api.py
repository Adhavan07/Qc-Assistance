"""
Integration tests for Authentication & RBAC API endpoints.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.src.api.deps import get_db
from backend.src.api.main import app
from backend.src.infrastructure.database import Base


@pytest.fixture
async def test_client():
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
async def test_organization_registration_and_login(test_client: AsyncClient):
    # 1. Register
    reg_payload = {
        "organization_name": "Spandsons Horizon",
        "organization_slug": "spandsons-horizon",
        "full_name": "Pravin Kumar",
        "email": "pravin@spandsons.com",
        "password": "SecurePassword123!",
    }
    reg_resp = await test_client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_resp.status_code == 201
    token_data = reg_resp.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"

    # 2. Reject duplicate registration with same slug
    dup_slug_resp = await test_client.post("/api/v1/auth/register", json=reg_payload)
    assert dup_slug_resp.status_code == 400
    assert "already taken" in dup_slug_resp.json()["detail"]

    # 3. Login with correct credentials
    login_resp = await test_client.post(
        "/api/v1/auth/login",
        json={"email": "pravin@spandsons.com", "password": "SecurePassword123!"},
    )
    assert login_resp.status_code == 200
    auth_token = login_resp.json()["access_token"]

    # 4. Login with wrong password
    bad_login = await test_client.post(
        "/api/v1/auth/login",
        json={"email": "pravin@spandsons.com", "password": "WrongPassword!"},
    )
    assert bad_login.status_code == 401

    # 5. Access /auth/me with bearer token
    me_resp = await test_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert me_resp.status_code == 200
    user_info = me_resp.json()
    assert user_info["email"] == "pravin@spandsons.com"
    assert user_info["role"] == "OWNER"


@pytest.mark.anyio
async def test_rbac_member_invitation_permissions(test_client: AsyncClient):
    # Register Owner
    await test_client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": "Apex Electronics",
            "organization_slug": "apex-elec",
            "full_name": "Ananya Roy",
            "email": "owner@apex.com",
            "password": "Password12345!",
        },
    )
    owner_login = await test_client.post(
        "/api/v1/auth/login",
        json={"email": "owner@apex.com", "password": "Password12345!"},
    )
    owner_token = owner_login.json()["access_token"]

    # Owner adds an INSPECTOR
    add_resp = await test_client.post(
        "/api/v1/organizations/members",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={
            "email": "inspector@apex.com",
            "full_name": "Inspector Bob",
            "role": "INSPECTOR",
            "password": "Password12345!",
        },
    )
    assert add_resp.status_code == 201

    # Inspector logs in
    insp_login = await test_client.post(
        "/api/v1/auth/login",
        json={"email": "inspector@apex.com", "password": "Password12345!"},
    )
    insp_token = insp_login.json()["access_token"]

    # Inspector attempts to invite another member (Should fail with 403 Forbidden)
    forbidden_resp = await test_client.post(
        "/api/v1/organizations/members",
        headers={"Authorization": f"Bearer {insp_token}"},
        json={
            "email": "hacker@apex.com",
            "full_name": "Hacker",
            "role": "ADMIN",
            "password": "Password12345!",
        },
    )
    assert forbidden_resp.status_code == 403
    assert "requires minimum role 'ADMIN'" in forbidden_resp.json()["detail"]
