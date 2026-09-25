"""
Background QC Processing Worker Service.
Consumes queued jobs, orchestrates the AI QC Engine, persists findings,
and maintains transactional integrity with credit refunding on system failure.
"""

from datetime import datetime, timezone
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..ai.engine import QCAnalysisEngine
from ..core.logging import logger
from ..infrastructure.models import AuditLog, Organization, QCFinding, QCRun
from ..infrastructure.queue import QCJobPayload


async def process_qc_job(payload: QCJobPayload, session_factory: async_sessionmaker[AsyncSession]):
    """Execute background QC analysis job for a given payload."""
    log = logger.bind(
        qc_run_id=payload.qc_run_id,
        doc_id=payload.document_id,
        org_id=payload.organization_id,
    )
    log.info("qc_job_started", file_path=payload.file_path)

    async with session_factory() as session:
        try:
            # 1. Update status to PROCESSING
            stmt = select(QCRun).where(QCRun.id == payload.qc_run_id)
            qc_run = (await session.execute(stmt)).scalar_one_or_none()
            if not qc_run:
                log.error("qc_run_not_found_in_database")
                return

            qc_run.overall_status = "PROCESSING"
            await session.commit()

            # 2. Invoke the decoupled AI QC Engine
            engine = QCAnalysisEngine()
            analysis_result = engine.analyze(
                file_path=payload.file_path,
                standards=payload.standards,
                document_id=payload.document_id,
            )

            # 3. Persist Findings
            for f in analysis_result.findings:
                finding_entity = QCFinding(
                    id=str(uuid.uuid4()),
                    qc_run_id=payload.qc_run_id,
                    finding_code=f.id,
                    rule_id=f.rule_id,
                    category=f.category,
                    description=f.description,
                    severity=f.severity.value,
                    confidence_level=f.confidence.level.value,
                    confidence_score=f.confidence.score,
                    page_number=f.page,
                    location_bbox=f.location.model_dump() if f.location else None,
                    evidence_text=f.evidence,
                    requirement_text=f.requirement,
                    standard_citation=f"{f.standard} {f.standard_section}",
                    recommendation=f.recommendation,
                )
                session.add(finding_entity)

            # 4. Update QCRun record
            qc_run.overall_status = analysis_result.overall_status.value
            qc_run.checks_total = analysis_result.summary.checks_total
            qc_run.checks_passed = analysis_result.summary.passed
            qc_run.checks_failed = analysis_result.summary.failed
            qc_run.checks_review = analysis_result.summary.review
            qc_run.processing_time_ms = analysis_result.processing_time_ms
            qc_run.completed_at = datetime.now(timezone.utc)

            # 5. Audit Log
            audit = AuditLog(
                id=str(uuid.uuid4()),
                organization_id=payload.organization_id,
                action="QC_ANALYSIS_COMPLETED",
                resource_type="qc_run",
                resource_id=payload.qc_run_id,
                event_metadata={
                    "status": analysis_result.overall_status.value,
                    "findings_count": len(analysis_result.findings),
                    "processing_time_ms": analysis_result.processing_time_ms,
                },
            )
            session.add(audit)
            await session.commit()
            log.info("qc_job_completed", status=analysis_result.overall_status.value, findings=len(analysis_result.findings))

        except Exception as exc:
            log.error("qc_job_failed", error=str(exc))
            # Refund organization credit on fatal error
            org_stmt = select(Organization).where(Organization.id == payload.organization_id)
            org = (await session.execute(org_stmt)).scalar_one_or_none()
            if org:
                org.credits_remaining += 1

            if qc_run:
                qc_run.overall_status = "FAILED"
                qc_run.completed_at = datetime.now(timezone.utc)

            await session.commit()
