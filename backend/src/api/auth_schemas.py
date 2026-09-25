"""
Pydantic Schemas for Authentication, Organization Provisioning, and RBAC.
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UserRole(str, Enum):
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    ENGINEER = "ENGINEER"
    INSPECTOR = "INSPECTOR"
    VIEWER = "VIEWER"
    SUPER_ADMIN = "SUPER_ADMIN"


ROLE_HIERARCHY = {
    UserRole.VIEWER: 1,
    UserRole.INSPECTOR: 2,
    UserRole.ENGINEER: 3,
    UserRole.ADMIN: 4,
    UserRole.OWNER: 5,
    UserRole.SUPER_ADMIN: 99,
}


class RegisterRequest(BaseModel):
    organization_name: str = Field(..., min_length=2, max_length=255)
    organization_slug: str = Field(..., min_length=2, max_length=100, pattern=r"^[a-z0-9-]+$")
    full_name: str = Field(..., min_length=2, max_length=255)
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=8, description="Minimum 8 characters")


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=5)
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_seconds: int


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: UserRole
    organization_id: str
    is_active: bool


class OrganizationResponse(BaseModel):
    id: str
    name: str
    slug: str
    plan_tier: str
    credits_remaining: int


class InviteMemberRequest(BaseModel):
    email: str = Field(..., min_length=5)
    full_name: str = Field(..., min_length=2)
    role: UserRole = UserRole.INSPECTOR
    password: str = Field(..., min_length=8)
