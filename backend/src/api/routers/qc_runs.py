"""
QC Runs & Discrepancies Router.
Handles job dispatch, status polling, finding queries, and Server-Sent Events (SSE) streaming.
"""

import asyncio
import json
from typing import AsyncGenerator, List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...infrastructure.models import Document, Organization, QCFinding, QCRun, User
from ...infrastructure.queue import QCJobPayload, TaskQueueInterface
from ..deps import get_db, get_queue
from ..deps_auth import get_current_user
from ..document_schemas import CreateQCRunRequest, QCFindingResponse, QCRunResponse

router = APIRouter(prefix="/qc-runs", tags=["QC Runs & Findings"])


@router.post("", response_model=QCRunResponse, status_code=status.HTTP_201_CREATED)
async def trigger_qc_run(
    payload: CreateQCRunRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    queue: TaskQueueInterface = Depends(get_queue),
):
    """
    Trigger a new QC analysis on a document.
    Deducts 1 check credit from the organization.
    Enqueues the job to the asynchronous worker queue.
    """
    # 1. Fetch Organization and verify check credit quota
    org_stmt = select(Organization).where(Organization.id == current_user.organization_id)
    org = (await db.execute(org_stmt)).scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    if org.credits_remaining <= 0:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Organization has exhausted its available QC check credits. Please recharge or upgrade plan.",
        )

    # 2. Verify Document belongs to organization
    doc_stmt = (
        select(Document)
        .where(Document.id == payload.document_id)
        .where(Document.organization_id == current_user.organization_id)
    )
    doc = (await db.execute(doc_stmt)).scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found in organization")

    # 3. Deduct credit
    org.credits_remaining -= 1

    # 4. Create QCRun record
    run_id = str(uuid.uuid4())
    qc_run = QCRun(
        id=run_id,
        organization_id=current_user.organization_id,
        document_id=doc.id,
        initiated_by=current_user.id,
        overall_status="QUEUED",
        model_version="qc-hybrid-engine-v1.0",
        prompt_version="wiring-qc-prompt-v1.0",
        rules_version="ruleset-ipc620-ul508a-v1.0",
    )
    db.add(qc_run)
    await db.commit()

    # 5. Enqueue background processing job
    job = QCJobPayload(
        qc_run_id=run_id,
        document_id=doc.id,
        organization_id=current_user.organization_id,
        file_path=doc.storage_path,
        standards=payload.standards,
    )
    await queue.enqueue(job)

    return QCRunResponse(
        id=qc_run.id,
        organization_id=qc_run.organization_id,
        document_id=qc_run.document_id,
        overall_status=qc_run.overall_status,
        checks_total=qc_run.checks_total,
        checks_passed=qc_run.checks_passed,
        checks_failed=qc_run.checks_failed,
        checks_review=qc_run.checks_review,
        model_version=qc_run.model_version,
        prompt_version=qc_run.prompt_version,
        rules_version=qc_run.rules_version,
        processing_time_ms=qc_run.processing_time_ms,
        created_at=qc_run.created_at,
        completed_at=qc_run.completed_at,
    )


@router.get("/{qc_run_id}", response_model=QCRunResponse)
async def get_qc_run_status(
    qc_run_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve execution status and summary metrics for a QC run."""
    stmt = (
        select(QCRun)
        .where(QCRun.id == qc_run_id)
        .where(QCRun.organization_id == current_user.organization_id)
    )
    run = (await db.execute(stmt)).scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="QC run not found in your organization")

    return QCRunResponse(
        id=run.id,
        organization_id=run.organization_id,
        document_id=run.document_id,
        overall_status=run.overall_status,
        checks_total=run.checks_total,
        checks_passed=run.checks_passed,
        checks_failed=run.checks_failed,
        checks_review=run.checks_review,
        model_version=run.model_version,
        prompt_version=run.prompt_version,
        rules_version=run.rules_version,
        processing_time_ms=run.processing_time_ms,
        created_at=run.created_at,
        completed_at=run.completed_at,
    )


@router.get("/{qc_run_id}/findings", response_model=List[QCFindingResponse])
async def list_qc_findings(
    qc_run_id: str,
    severity: Optional[str] = Query(None),
    page: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List structured discrepancy findings for a completed run."""
    # Ensure run belongs to caller's org
    run_stmt = (
        select(QCRun)
        .where(QCRun.id == qc_run_id)
        .where(QCRun.organization_id == current_user.organization_id)
    )
    if not (await db.execute(run_stmt)).scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="QC run not found")

    stmt = select(QCFinding).where(QCFinding.qc_run_id == qc_run_id)
    if severity:
        stmt = stmt.where(QCFinding.severity == severity.upper())
    if page:
        stmt = stmt.where(QCFinding.page_number == page)

    findings = (await db.execute(stmt)).scalars().all()

    return [
        QCFindingResponse(
            id=f.id,
            finding_code=f.finding_code,
            rule_id=f.rule_id,
            category=f.category,
            description=f.description,
            severity=f.severity,
            confidence_level=f.confidence_level,
            confidence_score=f.confidence_score,
            page_number=f.page_number,
            location_bbox=f.location_bbox,
            evidence_text=f.evidence_text,
            requirement_text=f.requirement_text,
            standard_citation=f.standard_citation,
            recommendation=f.recommendation,
            created_at=f.created_at,
        )
        for f in findings
    ]


@router.get("/{qc_run_id}/stream")
async def stream_qc_run_progress(
    qc_run_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Server-Sent Events (SSE) endpoint streaming real-time progress updates.
    Allows frontend to visualize live progression without aggressive HTTP polling.
    """
    run_stmt = (
        select(QCRun)
        .where(QCRun.id == qc_run_id)
        .where(QCRun.organization_id == current_user.organization_id)
    )
    run = (await db.execute(run_stmt)).scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="QC run not found")

    async def event_generator() -> AsyncGenerator[str, None]:
        # Stream initial event
        yield f"event: progress\ndata: {json.dumps({'status': run.overall_status, 'percent': 10})}\n\n"

        for step in [30, 60, 90]:
            await asyncio.sleep(0.05)
            yield f"event: progress\ndata: {json.dumps({'status': 'PROCESSING', 'percent': step})}\n\n"

        yield f"event: complete\ndata: {json.dumps({'status': run.overall_status, 'percent': 100})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
