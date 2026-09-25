"""
Unit tests for the unified QC Pipeline, State Machine, Finding Arbitration, and Event Hub.
Validates the complete 8-stage pipeline, 7-state state machine, finding fusion,
and real-time SSE progress streaming.
"""

import os
import tempfile
import pytest

from backend.src.ai.schemas import (
    AIFindingPayload,
    Confidence,
    ConfidenceLevelEnum,
    DocumentPage,
    IntermediateDocumentModel,
    OverallStatusEnum,
    QCFinding,
    SeverityEnum,
    WireCallout,
)
from backend.src.services.qc_pipeline import (
    FindingArbiter,
    QCPipelineEventHub,
    QCPipelineOrchestrator,
    QCPipelineStatus,
    QCPipelineStep,
)
from tests.unit.test_engine import create_sample_schematic_pdf


def test_finding_arbiter_deterministic_and_ai_fusion():
    """Verify that when AI and Deterministic rules agree on a defect, confidence is reinforced."""
    doc = IntermediateDocumentModel(
        document_id="doc_fusion",
        filename="test.pdf",
        page_count=1,
        pages=[
            DocumentPage(
                page_number=1,
                width=1000,
                height=800,
                wire_callouts=[
                    WireCallout(id="w1", wire_number="W102", gauge=None, color="RED", raw_text="W102 RED")
                ],
            )
        ],
    )

    deterministic_findings = [
        QCFinding(
            id="D-WG-doc_-1-001",
            rule_id="RULE-WG-001",
            category="wire",
            description="Wire 'W102' lacks an explicit wire gauge specification.",
            severity=SeverityEnum.CRITICAL,
            confidence=Confidence(level=ConfidenceLevelEnum.HIGH, score=0.98),
            page=1,
            location=None,
            evidence="Callout: 'W102 RED'",
            requirement="All wiring runs must declare gauge.",
            standard="IPC-WHMA-A-620D",
            standard_section="Section 4.1",
            recommendation="Declare nominal AWG.",
        )
    ]

    ai_findings = [
        AIFindingPayload(
            finding_code="D-001",
            rule_id="RULE-WG-001",
            category="WIRE_SPEC",
            description="Conductor W102 lacks gauge specification for current draw.",
            severity=SeverityEnum.CRITICAL,
            confidence_score=0.96,
            confidence_level=ConfidenceLevelEnum.HIGH,
            page_number=1,
            location_bbox=None,
            evidence_text="W102 RED",
            requirement_text="Conductor must be sized per IPC-620.",
            standard_citation="IPC-WHMA-A-620D Section 4.1",
            recommendation="Specify 18 AWG.",
        )
    ]

    merged = FindingArbiter.arbitrate_and_merge(
        deterministic_findings=deterministic_findings,
        ai_findings=ai_findings,
        doc=doc,
    )

    assert len(merged) == 1
    fused = merged[0]
    # Finding ID must be renumbered sequentially
    assert fused.id == "D-001"
    assert fused.rule_id == "RULE-WG-001"
    # Confidence reinforced above both individual scores (0.98 + 0.01 = 0.99)
    assert fused.confidence.score == 0.99
    assert fused.confidence.level == ConfidenceLevelEnum.HIGH
    assert fused.severity == SeverityEnum.CRITICAL
    assert "W102" in fused.evidence


def test_finding_arbiter_standalone_deterministic_findings():
    """Verify that deterministic findings without AI corroboration remain authoritative with 100% precision."""
    deterministic_findings = [
        QCFinding(
            id="D-TB-doc_-1-001",
            rule_id="RULE-TB-005",
            category="documentation",
            description="Page 1 title block is missing revision.",
            severity=SeverityEnum.MINOR,
            confidence=Confidence(level=ConfidenceLevelEnum.HIGH, score=0.96),
            page=1,
            location=None,
            evidence="Revision: None",
            requirement="Title block must declare revision.",
            standard="ISO 7200",
            standard_section="Section 5",
            recommendation="Add revision.",
        )
    ]

    merged = FindingArbiter.arbitrate_and_merge(
        deterministic_findings=deterministic_findings,
        ai_findings=[],
    )

    assert len(merged) == 1
    assert merged[0].id == "D-001"
    assert merged[0].rule_id == "RULE-TB-005"
    assert merged[0].confidence.score == 0.96


def test_finding_arbiter_standalone_ai_findings_confidence_threshold():
    """Verify that novel AI findings must meet >= 0.70 confidence threshold to be included."""
    ai_findings = [
        # High confidence novel AI finding (>= 0.70) -> Accepted
        AIFindingPayload(
            finding_code="D-AI-01",
            rule_id="RULE-CON-NOT-001",
            category="CONSISTENCY",
            description="Drawing note 3 references unshielded cable but pinout indicates high-speed differential signal.",
            severity=SeverityEnum.MAJOR,
            confidence_score=0.88,
            confidence_level=ConfidenceLevelEnum.HIGH,
            page_number=1,
            evidence_text="Note 3: UNSHIELDED TWISTED PAIR",
            requirement_text="High-speed RS-485 lines must use foil shielding per engineering SOP.",
            standard_citation="IPC-WHMA-A-620D Section 1.5",
            recommendation="Change cable specification to shielded twisted pair.",
        ),
        # Low confidence hallucination (< 0.70) -> Rejected
        AIFindingPayload(
            finding_code="D-AI-02",
            rule_id="RULE-WG-001",
            category="WIRE_SPEC",
            description="Possible missing label on wire bundle.",
            severity=SeverityEnum.INFO,
            confidence_score=0.55,
            confidence_level=ConfidenceLevelEnum.LOW,
            page_number=1,
            evidence_text="Bundle 4",
            requirement_text="General labeling recommendation.",
            standard_citation="Best Practice",
            recommendation="Review bundle label.",
        ),
    ]

    merged = FindingArbiter.arbitrate_and_merge(
        deterministic_findings=[],
        ai_findings=ai_findings,
    )

    assert len(merged) == 1
    assert merged[0].id == "D-001"
    assert merged[0].rule_id == "RULE-CON-NOT-001"
    assert merged[0].severity == SeverityEnum.MAJOR
    assert merged[0].confidence.score == 0.88


def test_finding_arbiter_sequential_renumbering_and_severity_sort():
    """Verify that merged findings are sorted by page and severity (CRITICAL before MINOR), then renumbered D-001, D-002..."""
    deterministic_findings = [
        # Minor finding on Page 1
        QCFinding(
            id="D-TB-001",
            rule_id="RULE-TB-005",
            category="documentation",
            description="Missing date.",
            severity=SeverityEnum.MINOR,
            confidence=Confidence(level=ConfidenceLevelEnum.HIGH, score=0.96),
            page=1,
            evidence="Date: None",
            requirement="Date required.",
            standard="ISO 7200",
            standard_section="Sec 5",
            recommendation="Add date.",
        ),
        # Critical finding on Page 1
        QCFinding(
            id="D-WG-001",
            rule_id="RULE-WG-001",
            category="wire",
            description="Missing gauge.",
            severity=SeverityEnum.CRITICAL,
            confidence=Confidence(level=ConfidenceLevelEnum.HIGH, score=0.98),
            page=1,
            evidence="W101 (No Gauge)",
            requirement="Gauge required.",
            standard="IPC-620",
            standard_section="Sec 4",
            recommendation="Add gauge.",
        ),
    ]

    merged = FindingArbiter.arbitrate_and_merge(
        deterministic_findings=deterministic_findings,
        ai_findings=[],
    )

    assert len(merged) == 2
    # Critical should be sorted first (D-001)
    assert merged[0].id == "D-001"
    assert merged[0].severity == SeverityEnum.CRITICAL
    assert merged[0].rule_id == "RULE-WG-001"
    # Minor should be sorted second (D-002)
    assert merged[1].id == "D-002"
    assert merged[1].severity == SeverityEnum.MINOR
    assert merged[1].rule_id == "RULE-TB-005"


@pytest.mark.anyio
async def test_qc_pipeline_event_hub_pub_sub():
    """Verify real-time SSE progress event publishing and subscribing."""
    test_run_id = "test_run_event_hub"

    # Define subscriber coroutine
    received_events = []

    async def subscriber():
        async for event in QCPipelineEventHub.subscribe(test_run_id):
            received_events.append(event)
            if "event: complete" in event:
                break

    import asyncio
    sub_task = asyncio.create_task(subscriber())
    await asyncio.sleep(0.01)

    # Publish progress updates through the state machine
    await QCPipelineEventHub.publish(test_run_id, QCPipelineStatus.PROCESSING, QCPipelineStep.RASTERIZING_PAGES.value, 20)
    await QCPipelineEventHub.publish(test_run_id, QCPipelineStatus.ANALYZING, QCPipelineStep.AI_REASONING.value, 50)
    await QCPipelineEventHub.publish(test_run_id, QCPipelineStatus.RUNNING_RULES, QCPipelineStep.EVALUATING_DETERMINISTIC_RULES.value, 75)
    await QCPipelineEventHub.publish_complete(test_run_id, "FAIL", {"total_checks": 15, "failed": 2})

    await sub_task

    assert len(received_events) == 4
    assert "event: progress" in received_events[0]
    assert "PROCESSING" in received_events[0]
    assert "event: complete" in received_events[-1]
    assert "FAIL" in received_events[-1]


@pytest.mark.anyio
async def test_qc_pipeline_orchestrator_full_execution():
    """Verify the complete 8-stage pipeline orchestrator on a synthetic PDF."""
    with tempfile.TemporaryDirectory() as tmpdir:
        sample_pdf = os.path.join(tmpdir, "pipeline_harness.pdf")
        create_sample_schematic_pdf(sample_pdf)

        orchestrator = QCPipelineOrchestrator()
        result = await orchestrator.execute_pipeline(
            qc_run_id="run_pipeline_test",
            document_id="doc_pipeline_test",
            file_path=sample_pdf,
            organization_id="org_pipeline_test",
            standards=["IPC-WHMA-A-620D", "UL 508A"],
            enable_ai=True,
            session_factory=None,  # Offline execution
        )

        assert result.document_id == "doc_pipeline_test"
        assert result.overall_status == OverallStatusEnum.FAIL
        assert result.summary.failed >= 2
        assert len(result.findings) >= 2

        rule_ids = {f.rule_id for f in result.findings}
        assert "RULE-WG-001" in rule_ids
        assert "RULE-CC-003" in rule_ids

        # Sequential finding IDs check
        for idx, f in enumerate(result.findings, start=1):
            assert f.id == f"D-{idx:03d}"
