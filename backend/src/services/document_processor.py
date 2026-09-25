"""
Document Processing & Ingestion Pipeline Service.
Orchestrates PDF rasterization, spatial OCR extraction, IDR structuring,
and job lifecycle state transitions with automatic retries and tenant isolation.
"""

import asyncio
from datetime import datetime, timezone
import json
import time
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..ai.extractor import DocumentExtractor
from ..ai.schemas import IntermediateDocumentModel
from ..core.logging import logger
from ..infrastructure.models import AuditLog, Document, ProcessingJob
from ..infrastructure.storage import StorageServiceInterface
from .image_processor import ImageProcessor


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class DocumentProcessor:
    """Production service for document rasterization, spatial extraction, and IDR generation."""

    def __init__(
        self,
        db: AsyncSession,
        storage: StorageServiceInterface,
        extractor: Optional[DocumentExtractor] = None,
    ):
        self.db = db
        self.storage = storage
        self.extractor = extractor or DocumentExtractor()

    async def get_or_create_job(
        self,
        document_id: str,
        organization_id: str,
        job_type: str = "DOCUMENT_PROCESSING",
    ) -> ProcessingJob:
        """Find pending/retrying job or create a new processing job."""
        stmt = (
            select(ProcessingJob)
            .where(ProcessingJob.document_id == document_id)
            .where(ProcessingJob.organization_id == organization_id)
            .where(ProcessingJob.status.in_(["PENDING", "RETRYING", "PROCESSING"]))
            .order_by(ProcessingJob.created_at.desc())
        )
        existing_job = (await self.db.execute(stmt)).scalar_one_or_none()
        if existing_job:
            return existing_job

        new_job = ProcessingJob(
            id=str(uuid.uuid4()),
            organization_id=organization_id,
            document_id=document_id,
            job_type=job_type,
            status="PENDING",
            current_step="QUEUED",
            progress_percent=0,
            attempts=0,
            max_attempts=3,
        )
        self.db.add(new_job)
        await self.db.commit()
        await self.db.refresh(new_job)
        return new_job

    async def process_document(
        self,
        document_id: str,
        organization_id: str,
        job_id: Optional[str] = None,
        force_reprocess: bool = False,
    ) -> ProcessingJob:
        """
        Execute full document ingestion pipeline:
        1. Fetch document and validate tenant ownership.
        2. Rasterize pages into high-res PNG viewports and thumbnails.
        3. Extract spatial text, title blocks, wire callouts, connectors, and notes.
        4. Construct and persist Intermediate Document Representation (IDR).
        5. Update job and document states transactionally with retry defense.
        """
        start_time = time.time()
        log = logger.bind(document_id=document_id, organization_id=organization_id, job_id=job_id)
        log.info("document_processing_pipeline_started")

        # 1. Fetch document
        doc_stmt = (
            select(Document)
            .where(Document.id == document_id)
            .where(Document.organization_id == organization_id)
        )
        doc = (await self.db.execute(doc_stmt)).scalar_one_or_none()
        if not doc:
            log.error("document_not_found_for_tenant")
            raise ValueError(f"Document '{document_id}' not found in organization '{organization_id}'")

        # 2. Fetch or create Job
        if job_id:
            job_stmt = (
                select(ProcessingJob)
                .where(ProcessingJob.id == job_id)
                .where(ProcessingJob.organization_id == organization_id)
            )
            job = (await self.db.execute(job_stmt)).scalar_one_or_none()
            if not job:
                raise ValueError(f"Processing job '{job_id}' not found")
        else:
            job = await self.get_or_create_job(document_id, organization_id)

        # Increment attempt counter
        job.attempts += 1
        job.status = "PROCESSING"
        job.started_at = utc_now()
        job.current_step = "INITIALIZING"
        job.progress_percent = 10
        doc.status = "PROCESSING"
        await self.db.commit()

        try:
            # 3. Read raw document content from storage backend
            log.info("reading_document_from_storage", storage_path=doc.storage_path)
            if not self.storage.file_exists(doc.storage_path):
                raise FileNotFoundError(f"Document binary not found at storage path: {doc.storage_path}")

            content = self.storage.read_file(doc.storage_path)
            if not content:
                raise ValueError("Retrieved empty file content from storage")

            # 4. Phase 1: High-fidelity Page Rasterization
            job.current_step = "RASTERIZING_PAGES"
            job.progress_percent = 25
            await self.db.commit()

            log.info("rasterizing_pages", filename=doc.filename, size_bytes=len(content))
            rendered_pages = ImageProcessor.rasterize_document(
                content=content,
                filename=doc.filename,
                mime_type=doc.mime_type,
            )

            # Persist page viewports to storage under tenant directory
            for p in rendered_pages:
                page_num = p["page_number"]
                page_img_path = f"tenants/{organization_id}/documents/{document_id}/pages/page_{page_num}.png"
                thumb_img_path = f"tenants/{organization_id}/documents/{document_id}/pages/thumb_{page_num}.png"

                self.storage.save_file(page_img_path, p["image_bytes"])
                self.storage.save_file(thumb_img_path, p["thumbnail_bytes"])

            job.progress_percent = 50
            await self.db.commit()

            # 5. Phase 2: Spatial & Semantic Extraction (IDR Parsing)
            job.current_step = "EXTRACTING_STRUCTURED_DATA"
            job.progress_percent = 65
            await self.db.commit()

            log.info("extracting_structured_idr")
            idr: IntermediateDocumentModel = self.extractor.extract(
                file_bytes=content,
                filename=doc.filename,
                document_id=doc.id,
            )

            # 6. Phase 3: Persist Intermediate Document Representation (IDR)
            job.current_step = "PERSISTING_IDR"
            job.progress_percent = 85
            await self.db.commit()

            idr_json = idr.model_dump_json(indent=2)
            idr_storage_path = f"tenants/{organization_id}/documents/{document_id}/extracted/idr.json"
            self.storage.save_file(idr_storage_path, idr_json.encode("utf-8"))

            # 7. Phase 4: Job Completion & Metric Recording
            elapsed_ms = int((time.time() - start_time) * 1000)
            total_wires = sum(len(page.wire_callouts) for page in idr.pages)
            total_connectors = sum(len(page.connectors) for page in idr.pages)
            total_notes = sum(len(page.general_notes) for page in idr.pages)

            job.status = "COMPLETED"
            job.current_step = "COMPLETED"
            job.progress_percent = 100
            job.completed_at = utc_now()
            job.error_message = None
            job.result_metadata = {
                "page_count": idr.page_count,
                "pages_rasterized": len(rendered_pages),
                "wire_callouts_extracted": total_wires,
                "connectors_extracted": total_connectors,
                "general_notes_extracted": total_notes,
                "title_block_found": idr.pages[0].title_block is not None if idr.pages else False,
                "processing_time_ms": elapsed_ms,
                "format": idr.metadata.get("format", "unknown"),
                "engine": idr.metadata.get("engine", "default"),
            }

            doc.status = "PROCESSED"
            doc.page_count = idr.page_count

            audit = AuditLog(
                id=str(uuid.uuid4()),
                organization_id=organization_id,
                action="DOCUMENT_PROCESSED",
                resource_type="document",
                resource_id=document_id,
                event_metadata={
                    "job_id": job.id,
                    "pages": idr.page_count,
                    "wires": total_wires,
                    "connectors": total_connectors,
                    "duration_ms": elapsed_ms,
                    "attempts": job.attempts,
                },
            )
            self.db.add(audit)
            await self.db.commit()
            await self.db.refresh(job)

            log.info(
                "document_processing_pipeline_completed",
                pages=idr.page_count,
                wires=total_wires,
                duration_ms=elapsed_ms,
            )
            return job

        except Exception as exc:
            log.error("document_processing_failed", error=str(exc), attempt=job.attempts)
            if job.attempts < job.max_attempts:
                job.status = "RETRYING"
                job.current_step = f"RETRY_PENDING_ATTEMPT_{job.attempts + 1}"
                job.error_message = f"Attempt {job.attempts} encountered error: {str(exc)}"
            else:
                job.status = "FAILED"
                job.current_step = "FAILED"
                job.completed_at = utc_now()
                job.error_message = f"Failed after {job.attempts} attempts: {str(exc)}"
                doc.status = "FAILED"

                audit = AuditLog(
                    id=str(uuid.uuid4()),
                    organization_id=organization_id,
                    action="DOCUMENT_PROCESSING_FAILED",
                    resource_type="document",
                    resource_id=document_id,
                    event_metadata={
                        "job_id": job.id,
                        "error": str(exc),
                        "attempts": job.attempts,
                    },
                )
                self.db.add(audit)

            await self.db.commit()
            await self.db.refresh(job)
            raise exc

    async def retry_job(
        self,
        job_id: str,
        organization_id: str,
    ) -> ProcessingJob:
        """Manually trigger retry on a failed or stalled processing job."""
        stmt = (
            select(ProcessingJob)
            .where(ProcessingJob.id == job_id)
            .where(ProcessingJob.organization_id == organization_id)
        )
        job = (await self.db.execute(stmt)).scalar_one_or_none()
        if not job:
            raise ValueError(f"Processing job '{job_id}' not found")

        # Allow resetting attempt count if explicitly commanded
        if job.status == "FAILED":
            job.max_attempts += 2

        job.status = "PENDING"
        job.current_step = "QUEUED"
        job.progress_percent = 0
        job.error_message = None
        await self.db.commit()

        return await self.process_document(
            document_id=job.document_id,
            organization_id=organization_id,
            job_id=job.id,
            force_reprocess=True,
        )


async def execute_background_processing(
    document_id: str,
    organization_id: str,
    job_id: str,
    session_factory: async_sessionmaker[AsyncSession],
    storage: StorageServiceInterface,
):
    """Async background worker task entry point."""
    async with session_factory() as session:
        processor = DocumentProcessor(db=session, storage=storage)
        try:
            await processor.process_document(
                document_id=document_id,
                organization_id=organization_id,
                job_id=job_id,
            )
        except Exception as exc:
            logger.error("background_processing_task_failed", job_id=job_id, error=str(exc))
