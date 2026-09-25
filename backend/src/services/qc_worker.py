"""
Background QC Processing Worker Service.
Consumes queued jobs and orchestrates the unified 8-stage QC Pipeline & State Machine.
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..core.logging import logger
from ..infrastructure.queue import QCJobPayload
from .qc_pipeline import QCPipelineOrchestrator


async def process_qc_job(payload: QCJobPayload, session_factory: async_sessionmaker[AsyncSession]):
    """Execute background QC analysis job using the unified QCPipelineOrchestrator."""
    log = logger.bind(
        qc_run_id=payload.qc_run_id,
        doc_id=payload.document_id,
        org_id=payload.organization_id,
    )
    log.info("qc_worker_dispatching_pipeline", file_path=payload.file_path)

    orchestrator = QCPipelineOrchestrator()
    return await orchestrator.execute_pipeline(
        qc_run_id=payload.qc_run_id,
        document_id=payload.document_id,
        file_path=payload.file_path,
        organization_id=payload.organization_id,
        standards=payload.standards,
        rule_pack_ids=payload.rule_pack_ids,
        enable_ai=payload.enable_ai,
        session_factory=session_factory,
    )
