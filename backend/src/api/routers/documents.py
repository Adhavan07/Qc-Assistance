"""
Projects & Document Management Router.
Handles project grouping, presigned upload URLs, document registration, and file retrieval.
"""

from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...infrastructure.models import AuditLog, Document, Organization, Project, User
from ...infrastructure.storage import StorageServiceInterface
from ..deps import get_db, get_storage
from ..deps_auth import get_current_user
from ..document_schemas import (
    ConfirmUploadRequest,
    DocumentResponse,
    ProjectCreate,
    ProjectResponse,
    UploadIntentRequest,
    UploadIntentResponse,
)

router = APIRouter(tags=["Documents & Projects"])


# --- Projects Endpoints ---

@router.post("/projects", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a project container within the caller's organization."""
    project_id = str(uuid.uuid4())
    project = Project(
        id=project_id,
        organization_id=current_user.organization_id,
        name=payload.name,
        description=payload.description,
    )
    db.add(project)
    await db.commit()

    return ProjectResponse(
        id=project.id,
        organization_id=project.organization_id,
        name=project.name,
        description=project.description,
        created_at=project.created_at,
    )


@router.get("/projects", response_model=List[ProjectResponse])
async def list_projects(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all projects belonging to the caller's organization."""
    stmt = select(Project).where(Project.organization_id == current_user.organization_id)
    projects = (await db.execute(stmt)).scalars().all()

    return [
        ProjectResponse(
            id=p.id,
            organization_id=p.organization_id,
            name=p.name,
            description=p.description,
            created_at=p.created_at,
        )
        for p in projects
    ]


# --- Document Upload Endpoints ---

@router.post("/documents/upload-intent", response_model=UploadIntentResponse)
async def request_upload_intent(
    payload: UploadIntentRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: StorageServiceInterface = Depends(get_storage),
):
    """
    Generate an S3 presigned POST URL for direct, secure browser-to-bucket upload.
    Enforces tenant path partitioning.
    """
    # Verify project exists and belongs to tenant
    proj_stmt = (
        select(Project)
        .where(Project.id == payload.project_id)
        .where(Project.organization_id == current_user.organization_id)
    )
    project = (await db.execute(proj_stmt)).scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found in your organization",
        )

    doc_id = str(uuid.uuid4())
    upload_info = storage.generate_upload_url(
        organization_id=current_user.organization_id,
        document_id=doc_id,
        filename=payload.filename,
    )

    return UploadIntentResponse(
        document_id=doc_id,
        storage_path=upload_info["storage_path"],
        upload_url=upload_info["upload_url"],
        upload_fields=upload_info.get("fields", {}),
        expires_in_seconds=upload_info["expires_in_seconds"],
    )


@router.post("/documents/{document_id}/confirm", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def confirm_document_upload(
    document_id: str,
    payload: ConfirmUploadRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Confirm that file upload completed to S3 and register document entity in database.
    """
    # Verify project belongs to tenant
    proj_stmt = (
        select(Project)
        .where(Project.id == payload.project_id)
        .where(Project.organization_id == current_user.organization_id)
    )
    if not (await db.execute(proj_stmt)).scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found in your organization",
        )

    doc = Document(
        id=document_id,
        organization_id=current_user.organization_id,
        project_id=payload.project_id,
        uploaded_by=current_user.id,
        filename=payload.filename,
        file_size_bytes=payload.file_size_bytes,
        mime_type=payload.mime_type,
        sha256_checksum=payload.sha256_checksum,
        storage_path=payload.storage_path,
        page_count=payload.page_count,
        status="UPLOADED",
    )
    db.add(doc)

    audit = AuditLog(
        id=str(uuid.uuid4()),
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        action="DOCUMENT_UPLOADED",
        resource_type="document",
        resource_id=document_id,
        event_metadata={"filename": payload.filename, "size_bytes": payload.file_size_bytes},
    )
    db.add(audit)
    await db.commit()

    return DocumentResponse(
        id=doc.id,
        organization_id=doc.organization_id,
        project_id=doc.project_id,
        filename=doc.filename,
        file_size_bytes=doc.file_size_bytes,
        mime_type=doc.mime_type,
        sha256_checksum=doc.sha256_checksum,
        page_count=doc.page_count,
        status=doc.status,
        created_at=doc.created_at,
    )


@router.get("/documents", response_model=List[DocumentResponse])
async def list_documents(
    project_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List documents belonging to the caller's organization."""
    stmt = select(Document).where(Document.organization_id == current_user.organization_id)
    if project_id:
        stmt = stmt.where(Document.project_id == project_id)

    documents = (await db.execute(stmt)).scalars().all()

    return [
        DocumentResponse(
            id=d.id,
            organization_id=d.organization_id,
            project_id=d.project_id,
            filename=d.filename,
            file_size_bytes=d.file_size_bytes,
            mime_type=d.mime_type,
            sha256_checksum=d.sha256_checksum,
            page_count=d.page_count,
            status=d.status,
            created_at=d.created_at,
        )
        for d in documents
    ]


@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve document details by ID with tenant isolation."""
    stmt = (
        select(Document)
        .where(Document.id == document_id)
        .where(Document.organization_id == current_user.organization_id)
    )
    doc = (await db.execute(stmt)).scalar_one_or_none()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found in your organization",
        )

    return DocumentResponse(
        id=doc.id,
        organization_id=doc.organization_id,
        project_id=doc.project_id,
        filename=doc.filename,
        file_size_bytes=doc.file_size_bytes,
        mime_type=doc.mime_type,
        sha256_checksum=doc.sha256_checksum,
        page_count=doc.page_count,
        status=doc.status,
        created_at=doc.created_at,
    )
