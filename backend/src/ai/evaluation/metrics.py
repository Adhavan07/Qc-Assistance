"""
AI Evaluation Metrics & Scoring Models.
Implements precision, recall, F1, and critical-error recall calculations
for engineering quality control benchmarks.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from ..schemas import SeverityEnum


class GroundTruthFinding(BaseModel):
    """Expected discrepancy in a benchmark test case."""
    rule_id: str
    page: int
    severity: SeverityEnum
    evidence_keyword: str
    description: Optional[str] = None


class EvaluationTestCase(BaseModel):
    """Test case containing document metadata, file path, and expected findings."""
    case_id: str
    name: str
    description: str
    file_path: str
    expected_findings: List[GroundTruthFinding] = Field(default_factory=list)
    expected_overall_status: str = "PASS"


class CaseEvaluationResult(BaseModel):
    """Result of running evaluation on a single test case."""
    case_id: str
    case_name: str
    true_positives: int
    false_positives: int
    false_negatives: int
    critical_expected: int
    critical_detected: int
    predicted_findings_count: int
    expected_findings_count: int
    passed_overall_status_match: bool


class BenchmarkReport(BaseModel):
    """Aggregate benchmark report across all gold-standard test cases."""
    total_cases: int
    cases_passed_status: int
    total_expected_findings: int
    total_predicted_findings: int
    total_true_positives: int
    total_false_positives: int
    total_false_negatives: int
    precision: float = Field(..., ge=0.0, le=1.0)
    recall: float = Field(..., ge=0.0, le=1.0)
    f1_score: float = Field(..., ge=0.0, le=1.0)
    critical_error_recall: float = Field(..., ge=0.0, le=1.0)
    case_results: List[CaseEvaluationResult] = Field(default_factory=list)
    passed_quality_gate: bool


def calculate_metrics(
    tp: int,
    fp: int,
    fn: int,
    critical_expected: int = 0,
    critical_detected: int = 0,
) -> Dict[str, float]:
    """Calculate precision, recall, F1, and critical error recall with zero-division handling."""
    precision = tp / (tp + fp) if (tp + fp) > 0 else (1.0 if fn == 0 else 0.0)
    recall = tp / (tp + fn) if (tp + fn) > 0 else (1.0 if fp == 0 else 0.0)
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    critical_recall = (
        critical_detected / critical_expected if critical_expected > 0 else 1.0
    )

    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "critical_error_recall": round(critical_recall, 4),
    }
