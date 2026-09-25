"""
Organization & Member Management Endpoints.
Enforces multi-tenant scoping and RBAC authorization.
"""

from typing import List
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.security import hash_password
from ...infrastructure.models import AuditLog, Organization, User
from ..auth_schemas import (
    InviteMemberRequest,
    OrganizationResponse,
    UserResponse,
    UserRole,
)
from ..deps import get_db
from ..deps_auth import get_current_user, require_role

router = APIRouter(prefix="/organizations", tags=["Organizations"])


@router.get("/me", response_model=OrganizationResponse)
async def get_current_organization(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve details and available QC credits for the current user's organization."""
    stmt = select(Organization).where(Organization.id == current_user.organization_id)
    org = (await db.execute(stmt)).scalar_one_or_none()

    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    return OrganizationResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        plan_tier=org.plan_tier,
        credits_remaining=org.credits_remaining,
    )


@router.get("/members", response_model=List[UserResponse])
async def list_organization_members(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all user accounts belonging exclusively to the caller's organization."""
    stmt = select(User).where(User.organization_id == current_user.organization_id)
    members = (await db.execute(stmt)).scalars().all()

    return [
        UserResponse(
            id=m.id,
            email=m.email,
            full_name=m.full_name,
            role=UserRole(m.role),
            organization_id=m.organization_id,
            is_active=m.is_active,
        )
        for m in members
    ]


@router.post("/members", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def add_organization_member(
    payload: InviteMemberRequest,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """
    Invite / add a new user to the organization.
    Requires ADMIN or OWNER role.
    """
    # 1. Check if email already exists anywhere
    email_stmt = select(User).where(User.email == payload.email)
    if (await db.execute(email_stmt)).scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with email '{payload.email}' already exists",
        )

    # 2. Cannot invite a user with higher or equal privilege unless OWNER
    if payload.role == UserRole.OWNER and current_user.role != UserRole.OWNER.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only an OWNER can provision another OWNER",
        )

    # 3. Create user in current tenant organization
    new_user_id = str(uuid.uuid4())
    new_user = User(
        id=new_user_id,
        email=payload.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role.value,
        organization_id=current_user.organization_id,
        is_active=True,
    )
    db.add(new_user)

    # 4. Log security audit event
    audit = AuditLog(
        id=str(uuid.uuid4()),
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        action="MEMBER_ADDED",
        resource_type="user",
        resource_id=new_user_id,
        event_metadata={"invited_email": payload.email, "assigned_role": payload.role.value},
    )
    db.add(audit)
    await db.commit()

    return UserResponse(
        id=new_user.id,
        email=new_user.email,
        full_name=new_user.full_name,
        role=UserRole(new_user.role),
        organization_id=new_user.organization_id,
        is_active=new_user.is_active,
    )
