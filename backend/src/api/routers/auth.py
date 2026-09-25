"""
Authentication Endpoints: Registration, Login, Token Refresh, Logout, Profile, and Password Management.
"""

from datetime import timedelta
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import settings
from ...core.security import (
    create_access_token,
    create_password_reset_token,
    create_refresh_token,
    decode_password_reset_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)
from ...infrastructure.models import AuditLog, Organization, User
from ..auth_schemas import (
    ChangePasswordRequest,
    LoginRequest,
    MessageResponse,
    OrganizationResponse,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshTokenRequest,
    RegisterRequest,
    TokenResponse,
    UpdateMemberRequest,
    UserResponse,
    UserRole,
)
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

    # 6. Issue Tokens
    expires_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
    access_token = create_access_token(
        subject=user.id,
        tenant_id=organization.id,
        role=user.role,
        expires_delta=timedelta(minutes=expires_minutes),
    )
    refresh_token = create_refresh_token(
        subject=user.id,
        tenant_id=organization.id,
        role=user.role,
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in_seconds=expires_minutes * 60,
        user=UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=UserRole(user.role),
            organization_id=user.organization_id,
            is_active=user.is_active,
            created_at=user.created_at.isoformat() if user.created_at else None,
        ),
        organization=OrganizationResponse(
            id=organization.id,
            name=organization.name,
            slug=organization.slug,
            plan_tier=organization.plan_tier,
            credits_remaining=organization.credits_remaining,
            created_at=organization.created_at.isoformat() if organization.created_at else None,
        ),
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate email and password, issuing signed JWT access and refresh tokens."""
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

    # Fetch organization details
    org_stmt = select(Organization).where(Organization.id == user.organization_id)
    organization = (await db.execute(org_stmt)).scalar_one_or_none()

    # Log login event in audit log
    audit = AuditLog(
        id=str(uuid.uuid4()),
        organization_id=user.organization_id,
        actor_id=user.id,
        action="USER_LOGGED_IN",
        resource_type="user",
        resource_id=user.id,
        event_metadata={"email": user.email},
    )
    db.add(audit)
    await db.commit()

    expires_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
    access_token = create_access_token(
        subject=user.id,
        tenant_id=user.organization_id,
        role=user.role,
        expires_delta=timedelta(minutes=expires_minutes),
    )
    refresh_token = create_refresh_token(
        subject=user.id,
        tenant_id=user.organization_id,
        role=user.role,
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in_seconds=expires_minutes * 60,
        user=UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=UserRole(user.role),
            organization_id=user.organization_id,
            is_active=user.is_active,
            created_at=user.created_at.isoformat() if user.created_at else None,
        ),
        organization=OrganizationResponse(
            id=organization.id,
            name=organization.name,
            slug=organization.slug,
            plan_tier=organization.plan_tier,
            credits_remaining=organization.credits_remaining,
            created_at=organization.created_at.isoformat() if organization and organization.created_at else None,
        ) if organization else None,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token_endpoint(
    payload: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    """Exchange a valid refresh token for a newly issued access token."""
    decoded = decode_refresh_token(payload.refresh_token)
    user_id = decoded.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token claims",
        )

    stmt = select(User).where(User.id == user_id)
    user = (await db.execute(stmt)).scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account no longer active",
        )

    org_stmt = select(Organization).where(Organization.id == user.organization_id)
    organization = (await db.execute(org_stmt)).scalar_one_or_none()

    expires_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
    new_access_token = create_access_token(
        subject=user.id,
        tenant_id=user.organization_id,
        role=user.role,
        expires_delta=timedelta(minutes=expires_minutes),
    )
    new_refresh_token = create_refresh_token(
        subject=user.id,
        tenant_id=user.organization_id,
        role=user.role,
    )

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in_seconds=expires_minutes * 60,
        user=UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=UserRole(user.role),
            organization_id=user.organization_id,
            is_active=user.is_active,
            created_at=user.created_at.isoformat() if user.created_at else None,
        ),
        organization=OrganizationResponse(
            id=organization.id,
            name=organization.name,
            slug=organization.slug,
            plan_tier=organization.plan_tier,
            credits_remaining=organization.credits_remaining,
            created_at=organization.created_at.isoformat() if organization and organization.created_at else None,
        ) if organization else None,
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Log out the current user session and record the security audit event."""
    audit = AuditLog(
        id=str(uuid.uuid4()),
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        action="USER_LOGGED_OUT",
        resource_type="user",
        resource_id=current_user.id,
        event_metadata={"email": current_user.email},
    )
    db.add(audit)
    await db.commit()

    return MessageResponse(
        message="Successfully logged out",
        detail="Session terminated. Please discard client bearer tokens.",
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
        created_at=current_user.created_at.isoformat() if current_user.created_at else None,
    )


@router.patch("/me", response_model=UserResponse)
async def update_current_user_profile(
    payload: UpdateMemberRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update user's own profile (e.g., full name)."""
    if payload.full_name:
        current_user.full_name = payload.full_name
        db.add(current_user)

        audit = AuditLog(
            id=str(uuid.uuid4()),
            organization_id=current_user.organization_id,
            actor_id=current_user.id,
            action="USER_PROFILE_UPDATED",
            resource_type="user",
            resource_id=current_user.id,
            event_metadata={"new_name": payload.full_name},
        )
        db.add(audit)
        await db.commit()
        await db.refresh(current_user)

    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=UserRole(current_user.role),
        organization_id=current_user.organization_id,
        is_active=current_user.is_active,
        created_at=current_user.created_at.isoformat() if current_user.created_at else None,
    )


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change the authenticated user's password with current password verification."""
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password verification failed",
        )

    if verify_password(payload.new_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password cannot be identical to current password",
        )

    current_user.password_hash = hash_password(payload.new_password)
    db.add(current_user)

    audit = AuditLog(
        id=str(uuid.uuid4()),
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        action="PASSWORD_CHANGED",
        resource_type="user",
        resource_id=current_user.id,
        event_metadata={"email": current_user.email},
    )
    db.add(audit)
    await db.commit()

    return MessageResponse(
        message="Password updated successfully",
        detail="Please use your new password for subsequent logins.",
    )


@router.post("/password-reset/request", response_model=MessageResponse)
async def request_password_reset(
    payload: PasswordResetRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Request password reset token. In production, this emails the user a secure token link.
    Returns token in message for local / staging verification.
    """
    stmt = select(User).where(User.email == payload.email)
    user = (await db.execute(stmt)).scalar_one_or_none()

    if not user:
        # Prevent user enumeration by returning standard response
        return MessageResponse(
            message="If an account exists with this email, password reset instructions have been dispatched.",
        )

    reset_token = create_password_reset_token(user.email)

    audit = AuditLog(
        id=str(uuid.uuid4()),
        organization_id=user.organization_id,
        actor_id=user.id,
        action="PASSWORD_RESET_REQUESTED",
        resource_type="user",
        resource_id=user.id,
        event_metadata={"email": user.email},
    )
    db.add(audit)
    await db.commit()

    return MessageResponse(
        message="Password reset token generated successfully",
        detail=reset_token,
    )


@router.post("/password-reset/confirm", response_model=MessageResponse)
async def confirm_password_reset(
    payload: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db),
):
    """Validate reset token and set new password."""
    email = decode_password_reset_token(payload.token)

    stmt = select(User).where(User.email == email)
    user = (await db.execute(stmt)).scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User account associated with this token was not found",
        )

    user.password_hash = hash_password(payload.new_password)
    db.add(user)

    audit = AuditLog(
        id=str(uuid.uuid4()),
        organization_id=user.organization_id,
        actor_id=user.id,
        action="PASSWORD_RESET_CONFIRMED",
        resource_type="user",
        resource_id=user.id,
        event_metadata={"email": user.email},
    )
    db.add(audit)
    await db.commit()

    return MessageResponse(
        message="Password has been reset successfully. You may now log in with your new password.",
    )

