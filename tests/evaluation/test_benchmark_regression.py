"""
AI Evaluation Benchmark Regression Suite.
Runs the complete Gold-Standard dataset across 10 wiring manuals
and validates that precision, recall, and critical-error recall satisfy release criteria.
"""

import tempfile
import pytest

from backend.src.ai.evaluation.gold_dataset import GoldDatasetManager
from backend.src.ai.evaluation.runner import EvaluationRunner


@pytest.fixture(scope="module")
def gold_dataset_cases():
    with tempfile.TemporaryDirectory() as tmpdir:
        cases = GoldDatasetManager.setup_dataset(tmpdir)
        yield cases


def test_gold_dataset_benchmark_execution(gold_dataset_cases):
    """Executes the benchmark suite and enforces accuracy quality gates."""
    runner = EvaluationRunner()
    report = runner.run_benchmark(gold_dataset_cases)

    # 1. Verify case execution
    assert report.total_cases == 10
    assert report.total_expected_findings > 0

    # 2. Enforce Critical Error Recall Gate: No missed safety-critical defects!
    # In electrical engineering drawings, missing an unrated wire gauge or duplicate connector is catastrophic.
    assert report.critical_error_recall >= 0.98, (
        f"Critical error recall ({report.critical_error_recall}) fell below mandatory 98.0% threshold"
    )

    # 3. Enforce Overall Precision & Recall Quality Gates
    assert report.precision >= 0.80, f"Precision ({report.precision}) fell below 80.0%"
    assert report.recall >= 0.85, f"Recall ({report.recall}) fell below 85.0%"
    assert report.f1_score >= 0.85, f"F1 Score ({report.f1_score}) fell below 85.0%"

    # 4. Enforce Overall Quality Gate Flag
    assert report.passed_quality_gate is True


def test_clean_drawings_zero_false_positives(gold_dataset_cases):
    """Compliant drawings (TC-01, TC-07, TC-10) must produce 0 false positive defects."""
    clean_case_ids = {"TC-01", "TC-07", "TC-10"}
    clean_cases = [c for c in gold_dataset_cases if c.case_id in clean_case_ids]

    runner = EvaluationRunner()
    report = runner.run_benchmark(clean_cases)

    assert report.total_cases == 3
    assert report.total_expected_findings == 0
    assert report.total_false_positives == 0, (
        f"Compliant drawings produced {report.total_false_positives} false positives!"
    )
    assert report.cases_passed_status == 3
