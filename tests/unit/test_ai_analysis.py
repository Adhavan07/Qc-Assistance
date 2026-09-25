"""
AI Analysis & LLM Provider Abstraction Fixture Tests:
- Mock AI Provider deterministic reasoning
- Structured Pydantic JSON output validation and markdown fence extraction
- Client validated prompt asset v1.0 governance and trade secret concealment
- Prompt injection defense delimiters
- Database AI request logging (tokens, latency, cost accounting)
- Timeout detection and exponential backoff retry recovery
- Provider cost calculation for GPT-4o and Claude 3.5 Sonnet
"""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.src.ai.llm_adapter import (
    AIProviderFactory,
    AIRequest,
    AIResponse,
    AIServiceError,
    AITimeoutError,
    AIValidationError,
    AnthropicProvider,
    MockAIProvider,
    OpenAIProvider,
    extract_json_from_llm_text,
    parse_and_validate_ai_json,
)
from backend.src.ai.prompt_manager import PromptManager
from backend.src.ai.schemas import (
    AIAnalysisPayload,
    AIFindingPayload,
    ConfidenceLevelEnum,
    DocumentPage,
    IntermediateDocumentModel,
    SeverityEnum,
    TitleBlock,
    WireCallout,
)
from backend.src.ai.service import AIAnalysisService
from backend.src.infrastructure.database import Base
from backend.src.infrastructure.models import AIRequestLog, Organization


@pytest.fixture
def sample_idr() -> IntermediateDocumentModel:
    """Fixture providing a structured IDR with a missing wire gauge discrepancy."""
    page = DocumentPage(
        page_number=1,
        width=1200,
        height=850,
        title_block=TitleBlock(
            drawing_number="DWG-AI-TEST-001",
            revision="B",
            drawn_by="J. Doe",
            approved_by="R. Smith",
            date="2026-09-25",
        ),
        wire_callouts=[
            WireCallout(
                id="w1",
                wire_number="W101",
                gauge="18 AWG",
                color="RED",
                from_connector="CB-101",
                to_connector="J1",
                raw_text="W101 18 AWG RED FROM CB-101 TO J1",
            ),
            WireCallout(
                id="w2",
                wire_number="W102",
                gauge=None,  # Missing gauge violation
                color="BLK",
                from_connector="CB-102",
                to_connector="J2",
                raw_text="W102 BLK FROM CB-102 (20A) TO J2",
            ),
        ],
    )
    return IntermediateDocumentModel(
        document_id="doc_ai_test",
        filename="test_drawing.pdf",
        page_count=1,
        pages=[page],
    )


@pytest.fixture
async def db_session():
    """In-memory SQLite session for database logging verification."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        # Create test organization
        org = Organization(
            id="org_ai_test_01",
            name="AI Test Aerospace",
            slug="ai-test-aero",
            plan_tier="ENTERPRISE",
            credits_remaining=50,
        )
        session.add(org)
        await session.commit()
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.mark.anyio
async def test_mock_ai_provider_structured_output():
    """Verify MockAIProvider generates valid structured JSON conforming to AIAnalysisPayload."""
    provider = MockAIProvider()
    request = AIRequest(
        system_prompt=PromptManager.get_system_prompt(),
        user_prompt="Inspect drawing with W102 MISSING GAUGE connected to CB-101 (20A)",
        response_schema=PromptManager.get_json_schema(),
    )

    response = await provider.generate_analysis(request)
    assert response.provider == "mock-local"
    assert response.total_tokens > 0
    assert response.latency_ms >= 0

    payload: AIAnalysisPayload = response.structured_payload
    assert payload.prompt_version == "wiring-qc-prompt-v1.0"
    assert len(payload.findings) >= 1

    # Verify structured fields
    finding = payload.findings[0]
    assert finding.finding_code.startswith("D-")
    assert finding.rule_id == "RULE-WG-001"
    assert finding.severity == SeverityEnum.CRITICAL
    assert finding.confidence_score >= 0.9
    assert finding.confidence_level == ConfidenceLevelEnum.HIGH
    assert "W102" in finding.description
    assert "IPC-WHMA-A-620D" in finding.standard_citation
    assert len(finding.recommendation) > 10


def test_ai_json_extraction_from_markdown_fences():
    """Verify robust JSON extraction from markdown code blocks or wrapper text."""
    raw_markdown = """
Here is the analyzed quality control findings report:
```json
{
  "prompt_version": "wiring-qc-prompt-v1.0",
  "findings": [
    {
      "finding_code": "D-001",
      "rule_id": "RULE-WG-001",
      "category": "WIRE_SPEC",
      "description": "Conductor W102 is missing gauge spec",
      "severity": "CRITICAL",
      "confidence_score": 0.98,
      "confidence_level": "HIGH",
      "page_number": 1,
      "evidence_text": "W102 BLK",
      "requirement_text": "Conductors must have gauge callouts",
      "standard_citation": "IPC-WHMA-A-620D §13.4",
      "recommendation": "Specify minimum 14 AWG wire"
    }
  ],
  "summary_notes": "1 critical discrepancy detected"
}
```
Thank you for using the QC engine.
"""
    parsed = parse_and_validate_ai_json(raw_markdown, AIAnalysisPayload)
    assert isinstance(parsed, AIAnalysisPayload)
    assert len(parsed.findings) == 1
    assert parsed.findings[0].finding_code == "D-001"

    # Verify non-JSON error handling
    with pytest.raises(AIValidationError, match="Model output is not valid JSON"):
        parse_and_validate_ai_json("Error: The model was unable to complete the request.")


def test_prompt_manager_versioning_and_delimiters(sample_idr: IntermediateDocumentModel):
    """Verify client validated prompt asset v1.0 governance and defensive data framing."""
    # 1. System prompt contains all required international standards
    sys_prompt = PromptManager.get_system_prompt("wiring-qc-prompt-v1.0")
    assert "IPC/WHMA-A-620D" in sys_prompt
    assert "UL 508A" in sys_prompt
    assert "MIL-STD-681D" in sys_prompt
    assert "ISO 7200" in sys_prompt
    assert "DEFENSIVE DATA FRAMING & PROMPT INJECTION DEFENSE" in sys_prompt

    # 2. User prompt frames drawing data defensively
    user_prompt = PromptManager.format_user_prompt(
        idr=sample_idr,
        standards=["IPC-WHMA-A-620D", "UL 508A"],
        version="wiring-qc-prompt-v1.0",
    )
    assert "<drawing_data>" in user_prompt
    assert "</drawing_data>" in user_prompt
    assert "DWG-AI-TEST-001" in user_prompt
    assert "W101" in user_prompt
    assert "W102" in user_prompt

    # 3. Invalid version throws error
    with pytest.raises(ValueError, match="Unknown prompt version"):
        PromptManager.get_prompt_asset("invalid-prompt-version-99")


@pytest.mark.anyio
async def test_ai_analysis_service_successful_execution(sample_idr: IntermediateDocumentModel, db_session: AsyncSession):
    """Verify full AIAnalysisService pipeline execution and database request logging."""
    service = AIAnalysisService()
    payload = await service.analyze_document_idr(
        idr=sample_idr,
        standards=["IPC-WHMA-A-620D"],
        organization_id="org_ai_test_01",
        db=db_session,
        document_id="doc_ai_test",
    )

    assert isinstance(payload, AIAnalysisPayload)
    assert len(payload.findings) >= 1

    # Verify immutable database log
    stmt = select(AIRequestLog).where(AIRequestLog.organization_id == "org_ai_test_01")
    logs = (await db_session.execute(stmt)).scalars().all()
    assert len(logs) == 1
    ai_log = logs[0]
    assert ai_log.status == "SUCCESS"
    assert ai_log.provider == "mock-local"
    assert ai_log.prompt_version == "wiring-qc-prompt-v1.0"
    assert ai_log.total_tokens > 0
    assert ai_log.latency_ms >= 0


@pytest.mark.anyio
async def test_ai_analysis_service_timeout_handling(sample_idr: IntermediateDocumentModel, db_session: AsyncSession):
    """Verify timeout defense and failed execution audit logging."""
    timeout_provider = MockAIProvider(simulate_timeout=True)
    service = AIAnalysisService(provider=timeout_provider)

    with pytest.raises(AITimeoutError, match="timed out"):
        await service.analyze_document_idr(
            idr=sample_idr,
            standards=["IPC-WHMA-A-620D"],
            organization_id="org_ai_test_01",
            db=db_session,
            document_id="doc_ai_test",
            max_retries=1,
        )

    # Verify failure logged to database
    stmt = (
        select(AIRequestLog)
        .where(AIRequestLog.organization_id == "org_ai_test_01")
        .where(AIRequestLog.status == "TIMEOUT")
    )
    timeout_log = (await db_session.execute(stmt)).scalar_one_or_none()
    assert timeout_log is not None
    assert "timed out" in timeout_log.error_message.lower()


@pytest.mark.anyio
async def test_ai_analysis_service_retry_and_recovery(sample_idr: IntermediateDocumentModel, db_session: AsyncSession):
    """Verify that transient failures recover seamlessly via exponential backoff."""
    class FlakyProvider(MockAIProvider):
        def __init__(self):
            super().__init__()
            self.call_count = 0

        async def generate_analysis(self, request: AIRequest) -> AIResponse:
            self.call_count += 1
            if self.call_count == 1:
                # Fail on first attempt
                raise AIServiceError("Transient 503 upstream connection timeout")
            # Succeed on second attempt
            return await super().generate_analysis(request)

    flaky = FlakyProvider()
    service = AIAnalysisService(provider=flaky)

    payload = await service.analyze_document_idr(
        idr=sample_idr,
        standards=["IPC-WHMA-A-620D"],
        organization_id="org_ai_test_01",
        db=db_session,
        max_retries=2,
    )

    assert isinstance(payload, AIAnalysisPayload)
    assert flaky.call_count == 2  # Recovered on attempt 2


def test_cloud_provider_cost_calculations():
    """Verify token pricing formulas for OpenAI GPT-4o and Anthropic Claude 3.5."""
    # OpenAI GPT-4o
    openai = OpenAIProvider(api_key="sk-mock")
    cost_gpt4o = openai.calculate_cost(prompt_tokens=1_000_000, completion_tokens=1_000_000, model="gpt-4o")
    assert cost_gpt4o == pytest.approx(12.50)  # $2.50 + $10.00

    # Anthropic Claude 3.5 Sonnet
    anthropic = AnthropicProvider(api_key="sk-ant-mock")
    cost_claude = anthropic.calculate_cost(
        prompt_tokens=1_000_000, completion_tokens=1_000_000, model="claude-3-5-sonnet-20241022"
    )
    assert cost_claude == pytest.approx(18.00)  # $3.00 + $15.00
