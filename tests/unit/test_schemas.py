"""
Unit tests for AI Engine Pydantic schemas.
Verifies schema constraints, validation rules, and error handling.
"""

import pytest
from pydantic import ValidationError
from backend.src.ai.schemas import (
    BoundingBox,
    Confidence,
    ConfidenceLevelEnum,
    OverallStatusEnum,
    QCAnalysisResult,
    QCFinding,
    QCSummary,
    SeverityEnum,
)


def test_valid_qc_finding():
    finding = QCFinding(
        id="D-001",
        rule_id="RULE-WG-001",
        category="WIRE_SPEC",
        description="Wire W101 missing gauge",
        severity=SeverityEnum.CRITICAL,
        confidence=Confidence(level=ConfidenceLevelEnum.HIGH, score=0.98),
        page=1,
        location=BoundingBox(x=10, y=20, width=100, height=30),
        evidence="Observed text: W101 RED",
        requirement="All wires must declare nominal AWG gauge",
        standard="IPC-WHMA-A-620D",
        standard_section="Section 4.1",
        recommendation="Declare nominal gauge, e.g. 18 AWG",
    )
    assert finding.id == "D-001"
    assert finding.severity == SeverityEnum.CRITICAL
    assert finding.confidence.score == 0.98


def test_finding_id_prefix_validation():
    """Finding ID must start with 'D-' prefix."""
    with pytest.raises(ValidationError):
        QCFinding(
            id="INVALID-123",  # Must start with D-
            rule_id="RULE-WG-001",
            category="WIRE_SPEC",
            description="Wire W101 missing gauge",
            severity=SeverityEnum.CRITICAL,
            confidence=Confidence(level=ConfidenceLevelEnum.HIGH, score=0.98),
            page=1,
            evidence="Evidence",
            requirement="Requirement",
            standard="IPC-620",
            standard_section="4.1",
            recommendation="Recommendation",
        )


def test_bounding_box_validation():
    """Negative coordinates or non-positive width/height must be rejected."""
    with pytest.raises(ValidationError):
        BoundingBox(x=-5, y=10, width=50, height=50)

    with pytest.raises(ValidationError):
        BoundingBox(x=10, y=10, width=0, height=50)


def test_confidence_score_range():
    """Confidence score must be strictly between 0.0 and 1.0."""
    with pytest.raises(ValidationError):
        Confidence(level=ConfidenceLevelEnum.HIGH, score=1.5)

    with pytest.raises(ValidationError):
        Confidence(level=ConfidenceLevelEnum.LOW, score=-0.1)


def test_qc_analysis_result_serialization():
    summary = QCSummary(
        checks_total=10,
        passed=8,
        failed=1,
        review=1,
        critical_count=1,
        major_count=0,
        minor_count=1,
        info_count=0,
    )
    result = QCAnalysisResult(
        document_id="doc_test_01",
        filename="test_manual.pdf",
        standards_applied=["IPC-620"],
        overall_status=OverallStatusEnum.FAIL,
        summary=summary,
        findings=[],
        model_version="test-model",
        prompt_version="test-prompt",
        rules_version="test-rules",
        processing_time_ms=120,
    )
    json_str = result.model_dump_json()
    assert "doc_test_01" in json_str
    assert "FAIL" in json_str
