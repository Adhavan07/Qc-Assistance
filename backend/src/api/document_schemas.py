"""
Pydantic Schemas for Projects, Documents, QC Runs, and Findings.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from ..ai.schemas import BoundingBox, ConfidenceLevelEnum, DocumentPage, SeverityEnum


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = None


class ProjectResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    description: Optional[str] = None
    created_at: datetime
    document_count: Optional[int] = 0


class UploadIntentRequest(BaseModel):
    project_id: str
    filename: str = Field(..., min_length=3)
    file_size_bytes: int = Field(..., gt=0, le=50 * 1024 * 1024, description="Max 50MB")
    mime_type: str = Field(..., pattern=r"^(application/pdf|image/png|image/jpeg)$")


class UploadIntentResponse(BaseModel):
    document_id: str
    storage_path: str
    upload_url: str
    upload_fields: Dict[str, Any]
    expires_in_seconds: int


class ConfirmUploadRequest(BaseModel):
    project_id: str
    filename: str
    storage_path: str
    file_size_bytes: int
    mime_type: str
    sha256_checksum: str
    page_count: int = 1
    allow_duplicate: bool = False


class DocumentResponse(BaseModel):
    id: str
    organization_id: str
    project_id: str
    filename: str
    file_size_bytes: int
    mime_type: str
    sha256_checksum: str
    page_count: int
    status: str
    created_at: datetime
    is_duplicate: Optional[bool] = False
    existing_document_id: Optional[str] = None


class DocumentDownloadResponse(BaseModel):
    document_id: str
    filename: str
    download_url: str
    expires_in_seconds: int



class CreateQCRunRequest(BaseModel):
    document_id: str
    standards: List[str] = Field(default_factory=lambda: ["IPC-WHMA-A-620D", "UL 508A"])


class QCFindingResponse(BaseModel):
    id: str
    finding_code: str
    rule_id: str
    category: str
    description: str
    severity: str
    confidence_level: str
    confidence_score: float
    page_number: int
    location_bbox: Optional[Dict[str, Any]] = None
    evidence_text: str
    requirement_text: str
    standard_citation: str
    recommendation: str
    created_at: datetime


class QCRunResponse(BaseModel):
    id: str
    organization_id: str
    document_id: str
    overall_status: str
    checks_total: int
    checks_passed: int
    checks_failed: int
    checks_review: int
    model_version: str
    prompt_version: str
    rules_version: str
    processing_time_ms: int
    created_at: datetime
    completed_at: Optional[datetime] = None


class ProcessDocumentRequest(BaseModel):
    async_mode: bool = False
    force_reprocess: bool = False


class ProcessingJobResponse(BaseModel):
    id: str
    organization_id: str
    document_id: str
    job_type: str
    status: str
    current_step: str
    progress_percent: int
    attempts: int
    max_attempts: int
    error_message: Optional[str] = None
    result_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class DocumentExtractedResponse(BaseModel):
    document_id: str
    filename: str
    page_count: int
    pages: List[DocumentPage]
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PageImageResponse(BaseModel):
    document_id: str
    page_number: int
    image_url: str
    thumbnail_url: str
    width: int
    height: int

