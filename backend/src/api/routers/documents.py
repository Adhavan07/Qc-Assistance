"""
Projects & Document Management Router.
Handles project lifecycle, presigned upload URLs, direct multipart ingestion,
SHA-256 deduplication, file retrieval, and tenant-scoped deletion.
"""

import os
from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...infrastructure.models import AuditLog, Document, Organization, Project, User
from ...infrastructure.storage import StorageServiceInterface, compute_sha256, count_pdf_pages
from ..auth_schemas import MessageResponse, UserRole
from ..deps import get_db, get_storage
from ..deps_auth import get_current_user, require_role
from ..document_schemas import (
    ConfirmUploadRequest,
    DocumentDownloadResponse,
    DocumentResponse,
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
    UploadIntentRequest,
    UploadIntentResponse,
)

router = APIRouter(tags=["Documents & Projects"])


# --- Projects Endpoints ---

@router.post("/projects", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate,
    current_user: User = Depends(require_role(UserRole.ENGINEER)),
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

    audit = AuditLog(
        id=str(uuid.uuid4()),
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        action="PROJECT_CREATED",
        resource_type="project",
        resource_id=project_id,
        event_metadata={"name": payload.name},
    )
    db.add(audit)
    await db.commit()

    return ProjectResponse(
        id=project.id,
        organization_id=project.organization_id,
        name=project.name,
        description=project.description,
        created_at=project.created_at,
        document_count=0,
    )


@router.get("/projects", response_model=List[ProjectResponse])
async def list_projects(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all projects belonging to caller's organization, including document counts."""
    # Query projects with document counts
    stmt = (
        select(Project, func.count(Document.id).label("doc_count"))
        .outerjoin(Document, Document.project_id == Project.id)
        .where(Project.organization_id == current_user.organization_id)
        .group_by(Project.id)
        .order_by(Project.created_at.desc())
    )
    results = (await db.execute(stmt)).all()

    return [
        ProjectResponse(
            id=p.id,
            organization_id=p.organization_id,
            name=p.name,
            description=p.description,
            created_at=p.created_at,
            document_count=count,
        )
        for p, count in results
    ]


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve details for a single project container with tenant isolation."""
    stmt = (
        select(Project, func.count(Document.id).label("doc_count"))
        .outerjoin(Document, Document.project_id == Project.id)
        .where(Project.id == project_id)
        .where(Project.organization_id == current_user.organization_id)
        .group_by(Project.id)
    )
    row = (await db.execute(stmt)).first()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found in your organization",
        )

    project, doc_count = row
    return ProjectResponse(
        id=project.id,
        organization_id=project.organization_id,
        name=project.name,
        description=project.description,
        created_at=project.created_at,
        document_count=doc_count,
    )


@router.patch("/projects/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    payload: ProjectUpdate,
    current_user: User = Depends(require_role(UserRole.ENGINEER)),
    db: AsyncSession = Depends(get_db),
):
    """Update project name or description."""
    stmt = (
        select(Project)
        .where(Project.id == project_id)
        .where(Project.organization_id == current_user.organization_id)
    )
    project = (await db.execute(stmt)).scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found in your organization",
        )

    if payload.name is not None:
        project.name = payload.name
    if payload.description is not None:
        project.description = payload.description

    db.add(project)

    audit = AuditLog(
        id=str(uuid.uuid4()),
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        action="PROJECT_UPDATED",
        resource_type="project",
        resource_id=project.id,
        event_metadata={"name": project.name},
    )
    db.add(audit)
    await db.commit()
    await db.refresh(project)

    # Count docs
    count_stmt = select(func.count(Document.id)).where(Document.project_id == project.id)
    doc_count = (await db.execute(count_stmt)).scalar() or 0

    return ProjectResponse(
        id=project.id,
        organization_id=project.organization_id,
        name=project.name,
        description=project.description,
        created_at=project.created_at,
        document_count=doc_count,
    )


@router.delete("/projects/{project_id}", response_model=MessageResponse)
async def delete_project(
    project_id: str,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Delete a project container and all nested documents and QC runs."""
    stmt = (
        select(Project)
        .where(Project.id == project_id)
        .where(Project.organization_id == current_user.organization_id)
    )
    project = (await db.execute(stmt)).scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found in your organization",
        )

    project_name = project.name
    await db.delete(project)

    audit = AuditLog(
        id=str(uuid.uuid4()),
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        action="PROJECT_DELETED",
        resource_type="project",
        resource_id=project_id,
        event_metadata={"deleted_project_name": project_name},
    )
    db.add(audit)
    await db.commit()

    return MessageResponse(
        message=f"Project '{project_name}' and all associated documents were successfully deleted",
    )


# --- Document Upload Endpoints ---

@router.post("/documents/upload-intent", response_model=UploadIntentResponse)
async def request_upload_intent(
    payload: UploadIntentRequest,
    current_user: User = Depends(require_role(UserRole.ENGINEER)),
    db: AsyncSession = Depends(get_db),
    storage: StorageServiceInterface = Depends(get_storage),
):
    """
    Generate an S3/MinIO presigned POST URL for direct, secure browser-to-bucket upload.
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
    current_user: User = Depends(require_role(UserRole.ENGINEER)),
    db: AsyncSession = Depends(get_db),
):
    """
    Confirm that file upload completed to S3/storage and register document entity in database.
    Performs SHA-256 deduplication check against caller's organization.
    """
    # 1. Verify project belongs to tenant
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

    # 2. SHA-256 Deduplication check
    existing_stmt = (
        select(Document)
        .where(Document.organization_id == current_user.organization_id)
        .where(Document.sha256_checksum == payload.sha256_checksum)
    )
    existing_doc = (await db.execute(existing_stmt)).scalar_one_or_none()

    if existing_doc and not payload.allow_duplicate:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Duplicate diagram detected: Exact SHA-256 matches existing document "
                f"'{existing_doc.filename}' (ID: {existing_doc.id}). Set allow_duplicate=true to force ingestion."
            ),
        )

    # 3. Create document record
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
        event_metadata={
            "filename": payload.filename,
            "size_bytes": payload.file_size_bytes,
            "sha256": payload.sha256_checksum,
            "page_count": payload.page_count,
        },
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
        is_duplicate=existing_doc is not None,
        existing_document_id=existing_doc.id if existing_doc else None,
    )


@router.post("/documents/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document_direct(
    file: UploadFile = File(...),
    project_id: str = Form(...),
    allow_duplicate: bool = Form(False),
    current_user: User = Depends(require_role(UserRole.ENGINEER)),
    db: AsyncSession = Depends(get_db),
    storage: StorageServiceInterface = Depends(get_storage),
):
    """
    Direct multipart/form-data upload for local development, testing, and direct clients.
    Computes SHA-256, validates file, counts PDF pages, and saves to storage backend.
    """
    # 1. Verify project belongs to tenant
    proj_stmt = (
        select(Project)
        .where(Project.id == project_id)
        .where(Project.organization_id == current_user.organization_id)
    )
    if not (await db.execute(proj_stmt)).scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found in your organization",
        )

    # 2. Read content
    content = await file.read()
    file_size = len(content)

    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty",
        )

    if file_size > 50 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds maximum allowed 50MB",
        )

    # 3. Compute checksum & page count
    checksum = compute_sha256(content)
    page_count = count_pdf_pages(content)

    # 4. Deduplication Check
    existing_stmt = (
        select(Document)
        .where(Document.organization_id == current_user.organization_id)
        .where(Document.sha256_checksum == checksum)
    )
    existing_doc = (await db.execute(existing_stmt)).scalar_one_or_none()

    if existing_doc and not allow_duplicate:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Duplicate diagram detected: Exact SHA-256 matches existing document "
                f"'{existing_doc.filename}' (ID: {existing_doc.id})."
            ),
        )

    # 5. Persist to storage backend
    doc_id = str(uuid.uuid4())
    safe_name = os.path.basename(file.filename or "diagram.pdf")
    storage_path = f"tenants/{current_user.organization_id}/documents/{doc_id}/original/{safe_name}"
    storage.save_file(storage_path, content)

    # 6. Create Document record
    doc = Document(
        id=doc_id,
        organization_id=current_user.organization_id,
        project_id=project_id,
        uploaded_by=current_user.id,
        filename=safe_name,
        file_size_bytes=file_size,
        mime_type=file.content_type or "application/pdf",
        sha256_checksum=checksum,
        storage_path=storage_path,
        page_count=page_count,
        status="UPLOADED",
    )
    db.add(doc)

    audit = AuditLog(
        id=str(uuid.uuid4()),
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        action="DOCUMENT_UPLOADED",
        resource_type="document",
        resource_id=doc_id,
        event_metadata={
            "filename": safe_name,
            "size_bytes": file_size,
            "sha256": checksum,
            "page_count": page_count,
            "mode": "direct_multipart",
        },
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
        is_duplicate=existing_doc is not None,
        existing_document_id=existing_doc.id if existing_doc else None,
    )


# --- Document Retrieval & Management Endpoints ---

@router.get("/documents", response_model=List[DocumentResponse])
async def list_documents(
    project_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List documents belonging to the caller's organization."""
    stmt = select(Document).where(Document.organization_id == current_user.organization_id)
    if project_id:
        stmt = stmt.where(Document.project_id == project_id)
    if status:
        stmt = stmt.where(Document.status == status)

    stmt = stmt.order_by(Document.created_at.desc())
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


@router.get("/documents/{document_id}/download-url", response_model=DocumentDownloadResponse)
async def get_document_download_url(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: StorageServiceInterface = Depends(get_storage),
):
    """Generate a presigned download URL for viewing or rendering the drawing."""
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

    download_url = storage.generate_download_url(doc.storage_path, expire_seconds=900)

    return DocumentDownloadResponse(
        document_id=doc.id,
        filename=doc.filename,
        download_url=download_url,
        expires_in_seconds=900,
    )


@router.delete("/documents/{document_id}", response_model=MessageResponse)
async def delete_document(
    document_id: str,
    current_user: User = Depends(require_role(UserRole.ENGINEER)),
    db: AsyncSession = Depends(get_db),
    storage: StorageServiceInterface = Depends(get_storage),
):
    """Delete a document, clean up storage backend, and remove all associated QC runs."""
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

    # Clean up storage backend
    storage.delete_file(doc.storage_path)

    doc_name = doc.filename
    await db.delete(doc)

    audit = AuditLog(
        id=str(uuid.uuid4()),
        organization_id=current_user.organization_id,
        actor_id=current_user.id,
        action="DOCUMENT_DELETED",
        resource_type="document",
        resource_id=document_id,
        event_metadata={"deleted_filename": doc_name},
    )
    db.add(audit)
    await db.commit()

    return MessageResponse(
        message=f"Document '{doc_name}' was successfully deleted",
    )

