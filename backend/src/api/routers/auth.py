"""
Authentication Endpoints: Registration, Login, Profile.
"""

from datetime import timedelta
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import settings
from ...core.security import create_access_token, hash_password, verify_password
from ...infrastructure.models import AuditLog, Organization, User
from ..auth_schemas import LoginRequest, RegisterRequest, TokenResponse, UserResponse, UserRole
from ..deps import get_db
from ..deps_auth import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register_organization(
    payload: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Self-service registration: Provisions a new Organization and its initial OWNER user atomically.
    """
    # 1. Check for duplicate slug
    slug_stmt = select(Organization).where(Organization.slug == payload.organization_slug)
    if (await db.execute(slug_stmt)).scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Organization URL slug '{payload.organization_slug}' is already taken",
        )

    # 2. Check for duplicate email
    email_stmt = select(User).where(User.email == payload.email)
    if (await db.execute(email_stmt)).scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"An account with email '{payload.email}' already exists",
        )

    # 3. Create Organization
    org_id = str(uuid.uuid4())
    organization = Organization(
        id=org_id,
        name=payload.organization_name,
        slug=payload.organization_slug,
        plan_tier="PAY_PER_CHECK",
        credits_remaining=3,  # Free initial trial credits
    )
    db.add(organization)
    await db.flush()

    # 4. Create Initial User with OWNER role
    user_id = str(uuid.uuid4())
    user = User(
        id=user_id,
        email=payload.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        role=UserRole.OWNER.value,
        organization_id=org_id,
        is_active=True,
    )
    db.add(user)

    # 5. Audit Log Entry
    audit = AuditLog(
        id=str(uuid.uuid4()),
        organization_id=org_id,
        actor_id=user_id,
        action="ORGANIZATION_REGISTERED",
        resource_type="organization",
        resource_id=org_id,
        event_metadata={"org_slug": payload.organization_slug, "owner_email": payload.email},
    )
    db.add(audit)
    await db.commit()

    # 6. Issue Token
    expires_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
    token = create_access_token(
        subject=user.id,
        tenant_id=organization.id,
        role=user.role,
        expires_delta=timedelta(minutes=expires_minutes),
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in_seconds=expires_minutes * 60,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate email and password, issuing a signed JWT."""
    stmt = select(User).where(User.email == payload.email)
    user = (await db.execute(stmt)).scalar_one_or_none()

    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been deactivated. Please contact your organization administrator.",
        )

    expires_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
    token = create_access_token(
        subject=user.id,
        tenant_id=user.organization_id,
        role=user.role,
        expires_delta=timedelta(minutes=expires_minutes),
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in_seconds=expires_minutes * 60,
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
):
    """Return the currently authenticated user's profile and active organization ID."""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=UserRole(current_user.role),
        organization_id=current_user.organization_id,
        is_active=current_user.is_active,
    )
