"""
Organization & Member Management Endpoints.
Enforces multi-tenant scoping and RBAC authorization.
"""

from typing import List
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.security import hash_password
from ...infrastructure.models import AuditLog, Organization, User
from ..auth_schemas import (
    InviteMemberRequest,
    MessageResponse,
    OrganizationResponse,
    UpdateMemberRequest,
    UpdateOrganizationRequest,
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
        created_at=org.created_at.isoformat() if org.created_at else None,
    )


@router.patch("/me", response_model=OrganizationResponse)
async def update_current_organization(
    payload: UpdateOrganizationRequest,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Update organization settings (e.g., name). Requires ADMIN or OWNER role."""
    stmt = select(Organization).where(Organization.id == current_user.organization_id)
    org = (await db.execute(stmt)).scalar_one_or_none()

    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    if payload.name:
        org.name = payload.name
        db.add(org)

        audit = AuditLog(
            id=str(uuid.uuid4()),
            organization_id=current_user.organization_id,
            actor_id=current_user.id,
            action="ORGANIZATION_UPDATED",
            resource_type="organization",
            resource_id=org.id,
            event_metadata={"new_name": payload.name},
        )
        db.add(audit)
        await db.commit()
        await db.refresh(org)

    return OrganizationResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        plan_tier=org.plan_tier,
        credits_remaining=org.credits_remaining,
        created_at=org.created_at.isoformat() if org.created_at else None,
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
            created_at=m.created_at.isoformat() if m.created_at else None,
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

    if payload.role == UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot provision a SUPER_ADMIN through organization member invitation",
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
        created_at=new_user.created_at.isoformat() if new_user.created_at else None,
    )


@router.patch("/members/{member_id}", response_model=UserResponse)
async def update_organization_member(
    member_id: str,
    payload: UpdateMemberRequest,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """
    Update member role, full name, or active status.
    Requires ADMIN or OWNER role. Enforces tenant boundary and privilege escalation guards.
    """
    # 1. Tenant boundary check: member must belong to the caller's organization
    stmt = (
        select(User)
        .where(User.id == member_id)
        .where(User.organization_id == current_user.organization_id)
    )
    member = (await db.execute(stmt)).scalar_one_or_none()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found in your organization",
        )

    # 2. Privilege Escalation Guards
    if payload.role == UserRole.OWNER and current_user.role != UserRole.OWNER.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only an OWNER can promote a member to OWNER",
        )

    if member.role == UserRole.OWNER.value and current_user.role != UserRole.OWNER.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only an OWNER can modify an OWNER account",
        )

    if payload.role == UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot assign SUPER_ADMIN role at tenant level",
        )

    # 3. Sole Owner Protection Guard: Cannot demote or deactivate the last remaining active OWNER
    if member.role == UserRole.OWNER.value:
        demoting = payload.role is not None and payload.role != UserRole.OWNER
        deactivating = payload.is_active is False
        if demoting or deactivating:
            owner_count_stmt = (
                select(func.count(User.id))
                .where(User.organization_id == current_user.organization_id)
                .where(User.role == UserRole.OWNER.value)
                .where(User.is_active == True)
            )
            owner_count = (await db.execute(owner_count_stmt)).scalar() or 0
            if owner_count <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot demote or deactivate the sole owner of the organization",
                )

    # 4. Apply updates
    if payload.full_name is not None:
        member.full_name = payload.full_name
    if payload.role is not None:
        member.role = payload.role.value
    if payload.is_active is not None:
        member.is_active = payload.is_active

    db.add(member)

    # 5. Audit Log
    audit = AuditLog(
        id=str(uuid.uuid4()),
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        action="MEMBER_UPDATED",
        resource_type="user",
        resource_id=member.id,
        event_metadata={
            "updated_fields": {k: str(v) for k, v in payload.model_dump(exclude_unset=True).items()}
        },
    )
    db.add(audit)
    await db.commit()
    await db.refresh(member)

    return UserResponse(
        id=member.id,
        email=member.email,
        full_name=member.full_name,
        role=UserRole(member.role),
        organization_id=member.organization_id,
        is_active=member.is_active,
        created_at=member.created_at.isoformat() if member.created_at else None,
    )


@router.delete("/members/{member_id}", response_model=MessageResponse)
async def delete_organization_member(
    member_id: str,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """
    Remove a member from the organization.
    Requires ADMIN or OWNER role. Enforces tenant boundary and sole-owner protection.
    """
    # 1. Tenant boundary check
    stmt = (
        select(User)
        .where(User.id == member_id)
        .where(User.organization_id == current_user.organization_id)
    )
    member = (await db.execute(stmt)).scalar_one_or_none()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found in your organization",
        )

    # 2. Cannot delete self
    if member.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account. Use account closure or have another administrator remove you.",
        )

    # 3. Privilege Guard: Only OWNER can delete an OWNER
    if member.role == UserRole.OWNER.value and current_user.role != UserRole.OWNER.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only an OWNER can remove an OWNER account",
        )

    # 4. Sole Owner Protection Guard
    if member.role == UserRole.OWNER.value:
        owner_count_stmt = (
            select(func.count(User.id))
            .where(User.organization_id == current_user.organization_id)
            .where(User.role == UserRole.OWNER.value)
            .where(User.is_active == True)
        )
        owner_count = (await db.execute(owner_count_stmt)).scalar() or 0
        if owner_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete the sole owner of the organization",
            )

    member_email = member.email
    await db.delete(member)

    # 5. Audit Log
    audit = AuditLog(
        id=str(uuid.uuid4()),
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        action="MEMBER_REMOVED",
        resource_type="user",
        resource_id=member_id,
        event_metadata={"deleted_email": member_email},
    )
    db.add(audit)
    await db.commit()

    return MessageResponse(
        message=f"Member '{member_email}' was successfully removed from the organization",
    )

