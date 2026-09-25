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


@pytest.mark.anyio
async def test_refresh_token_lifecycle(test_client: AsyncClient):
    # 1. Register
    reg_resp = await test_client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": "Refresh Org",
            "organization_slug": "refresh-org",
            "full_name": "Refresh User",
            "email": "refresh@org.com",
            "password": "Password12345!",
        },
    )
    assert reg_resp.status_code == 201
    reg_data = reg_resp.json()
    refresh_token = reg_data["refresh_token"]
    assert refresh_token is not None

    # 2. Exchange refresh token for new access token
    refresh_resp = await test_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_resp.status_code == 200
    new_data = refresh_resp.json()
    new_access_token = new_data["access_token"]
    assert new_access_token is not None

    # 3. Test new access token against /auth/me
    me_resp = await test_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {new_access_token}"},
    )
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "refresh@org.com"

    # 4. Bogus refresh token returns 401
    bad_resp = await test_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "invalid.refresh.token"},
    )
    assert bad_resp.status_code == 401


@pytest.mark.anyio
async def test_logout_and_profile_update(test_client: AsyncClient):
    # 1. Register
    reg_resp = await test_client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": "Profile Org",
            "organization_slug": "profile-org",
            "full_name": "Original Name",
            "email": "profile@org.com",
            "password": "Password12345!",
        },
    )
    token = reg_resp.json()["access_token"]

    # 2. Update profile name
    patch_resp = await test_client.patch(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
        json={"full_name": "Updated Name"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["full_name"] == "Updated Name"

    # 3. Logout
    logout_resp = await test_client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert logout_resp.status_code == 200
    assert "Successfully logged out" in logout_resp.json()["message"]


@pytest.mark.anyio
async def test_password_change_and_reset_flows(test_client: AsyncClient):
    # 1. Register
    reg_resp = await test_client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": "Password Flow Org",
            "organization_slug": "pwd-flow-org",
            "full_name": "Pwd User",
            "email": "pwd@flow.com",
            "password": "OldPassword123!",
        },
    )
    token = reg_resp.json()["access_token"]

    # 2. Change password with wrong current password (Fails)
    bad_change = await test_client.post(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={"current_password": "WrongPassword!", "new_password": "NewPassword123!"},
    )
    assert bad_change.status_code == 400

    # 3. Change password successfully
    good_change = await test_client.post(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={"current_password": "OldPassword123!", "new_password": "NewPassword123!"},
    )
    assert good_change.status_code == 200

    # 4. Old password fails login
    fail_login = await test_client.post(
        "/api/v1/auth/login",
        json={"email": "pwd@flow.com", "password": "OldPassword123!"},
    )
    assert fail_login.status_code == 401

    # 5. New password succeeds login
    ok_login = await test_client.post(
        "/api/v1/auth/login",
        json={"email": "pwd@flow.com", "password": "NewPassword123!"},
    )
    assert ok_login.status_code == 200

    # 6. Request password reset
    reset_req = await test_client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": "pwd@flow.com"},
    )
    assert reset_req.status_code == 200
    reset_token = reset_req.json()["detail"]
    assert reset_token is not None

    # 7. Confirm password reset
    reset_confirm = await test_client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": reset_token, "new_password": "ResetPassword999!"},
    )
    assert reset_confirm.status_code == 200

    # 8. Login with reset password
    reset_login = await test_client.post(
        "/api/v1/auth/login",
        json={"email": "pwd@flow.com", "password": "ResetPassword999!"},
    )
    assert reset_login.status_code == 200

