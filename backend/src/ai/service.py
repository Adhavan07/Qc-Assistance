"""
AI Analysis & Compliance Reasoning Service.
Orchestrates prompt compilation, multimodal reasoning via AIProvider,
schema validation, database request logging, and exponential retry handling.
"""

import asyncio
from datetime import datetime, timezone
import time
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..core.logging import logger
from ..infrastructure.models import AIRequestLog
from .llm_adapter import (
    AIProviderFactory,
    AIProviderInterface,
    AIRequest,
    AIResponse,
    AIServiceError,
    AITimeoutError,
    AIValidationError,
)
from .prompt_manager import PromptManager
from .schemas import AIAnalysisPayload, IntermediateDocumentModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AIAnalysisService:
    """Production service for AI-assisted wiring diagram inspection and compliance audits."""

    def __init__(
        self,
        provider: Optional[AIProviderInterface] = None,
        prompt_manager: Optional[PromptManager] = None,
    ):
        self.provider = provider or AIProviderFactory.get_provider()
        self.prompt_manager = prompt_manager or PromptManager()

    async def analyze_document_idr(
        self,
        idr: IntermediateDocumentModel,
        standards: List[str],
        organization_id: str,
        db: AsyncSession,
        document_id: Optional[str] = None,
        qc_run_id: Optional[str] = None,
        prompt_version: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        max_retries: Optional[int] = None,
    ) -> AIAnalysisPayload:
        """
        Execute AI analysis pipeline with structured output, retries, and database logging:
        1. Compile versioned system prompt and defensibly framed user prompt.
        2. Execute AIProvider inference with configurable timeout.
        3. Validate structured output against Pydantic schema.
        4. Log full token accounting, latency, and cost to ai_request_logs.
        5. Return validated findings payload.
        """
        ver = prompt_version or settings.PROMPT_VERSION_DEFAULT
        timeout = timeout_seconds or settings.AI_TIMEOUT_SECONDS
        retries = max_retries if max_retries is not None else settings.AI_MAX_RETRIES

        log = logger.bind(
            org_id=organization_id,
            doc_id=document_id,
            qc_run_id=qc_run_id,
            prompt_version=ver,
        )
        log.info("ai_analysis_request_started")

        # 1. Compile Prompts
        system_prompt = self.prompt_manager.get_system_prompt(ver)
        user_prompt = self.prompt_manager.format_user_prompt(idr, standards, version=ver)
        json_schema = self.prompt_manager.get_json_schema(ver)

        request = AIRequest(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_schema=json_schema,
            temperature=0.0,
            timeout_seconds=timeout,
            prompt_version=ver,
        )

        attempts = 0
        last_error: Optional[Exception] = None

        while attempts <= retries:
            attempts += 1
            start_time = time.time()
            try:
                # 2. Invoke Provider
                response: AIResponse = await self.provider.generate_analysis(request)

                # 3. Log Successful Execution to Database
                db_log = AIRequestLog(
                    id=str(uuid.uuid4()),
                    organization_id=organization_id,
                    qc_run_id=qc_run_id,
                    document_id=document_id,
                    provider=response.provider,
                    model_name=response.model_name,
                    prompt_version=ver,
                    prompt_tokens=response.prompt_tokens,
                    completion_tokens=response.completion_tokens,
                    total_tokens=response.total_tokens,
                    estimated_cost_usd=response.estimated_cost_usd,
                    latency_ms=response.latency_ms,
                    status="SUCCESS",
                    created_at=utc_now(),
                )
                db.add(db_log)
                await db.commit()

                log.info(
                    "ai_analysis_request_success",
                    findings_count=len(response.structured_payload.findings),
                    tokens=response.total_tokens,
                    latency_ms=response.latency_ms,
                    cost_usd=response.estimated_cost_usd,
                )
                return response.structured_payload

            except (AITimeoutError, AIServiceError, AIValidationError) as exc:
                elapsed_ms = (time.time() - start_time) * 1000.0
                last_error = exc
                log.warn(
                    "ai_analysis_attempt_failed",
                    attempt=attempts,
                    max_retries=retries,
                    error=str(exc),
                    latency_ms=elapsed_ms,
                )

                # If retries remain, backoff and retry
                if attempts <= retries:
                    backoff = min(4.0, 0.25 * (2 ** (attempts - 1)))
                    await asyncio.sleep(backoff)
                    continue

                # All retries exhausted -> Log Failure to Database
                status_str = "TIMEOUT" if isinstance(exc, AITimeoutError) else "FAILED"
                db_log = AIRequestLog(
                    id=str(uuid.uuid4()),
                    organization_id=organization_id,
                    qc_run_id=qc_run_id,
                    document_id=document_id,
                    provider=getattr(self.provider, "default_model", "mock"),
                    model_name=request.model_name or "unknown",
                    prompt_version=ver,
                    prompt_tokens=0,
                    completion_tokens=0,
                    total_tokens=0,
                    estimated_cost_usd=0.0,
                    latency_ms=elapsed_ms,
                    status=status_str,
                    error_message=str(exc),
                    created_at=utc_now(),
                )
                db.add(db_log)
                await db.commit()

                log.error("ai_analysis_all_retries_exhausted", error=str(exc), attempts=attempts)
                raise exc
            except Exception as unhandled_exc:
                elapsed_ms = (time.time() - start_time) * 1000.0
                db_log = AIRequestLog(
                    id=str(uuid.uuid4()),
                    organization_id=organization_id,
                    qc_run_id=qc_run_id,
                    document_id=document_id,
                    provider="error",
                    model_name="unhandled",
                    prompt_version=ver,
                    prompt_tokens=0,
                    completion_tokens=0,
                    total_tokens=0,
                    estimated_cost_usd=0.0,
                    latency_ms=elapsed_ms,
                    status="FAILED",
                    error_message=f"Unhandled exception: {str(unhandled_exc)}",
                    created_at=utc_now(),
                )
                db.add(db_log)
                await db.commit()
                raise unhandled_exc

        raise last_error or AIServiceError("AI analysis failed with unrecorded error")
