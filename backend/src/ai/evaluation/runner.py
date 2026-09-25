"""
AI Evaluation Benchmark Runner.
Executes the QC Analysis Engine against the Gold-Standard dataset,
matches findings against ground truth, and calculates precision/recall metrics.
"""

from typing import List, Optional
from ..engine import QCAnalysisEngine
from ..schemas import QCFinding, SeverityEnum
from .gold_dataset import GoldDatasetManager
from .metrics import (
    BenchmarkReport,
    CaseEvaluationResult,
    EvaluationTestCase,
    GroundTruthFinding,
    calculate_metrics,
)


class EvaluationRunner:
    """Executes evaluation benchmarks and enforces quality gates."""

    MIN_CRITICAL_RECALL = 0.98  # Quality Gate: 98% Critical Error Recall
    MIN_F1_SCORE = 0.85         # Quality Gate: 85% F1 Score

    def __init__(self, engine: Optional[QCAnalysisEngine] = None):
        self.engine = engine or QCAnalysisEngine()

    def run_benchmark(self, test_cases: List[EvaluationTestCase]) -> BenchmarkReport:
        case_results: List[CaseEvaluationResult] = []
        total_tp = 0
        total_fp = 0
        total_fn = 0
        total_critical_expected = 0
        total_critical_detected = 0
        total_expected = 0
        total_predicted = 0
        cases_passed_status = 0

        for case in test_cases:
            # Execute analysis
            qc_result = self.engine.analyze(case.file_path)
            predicted_findings = qc_result.findings

            total_expected += len(case.expected_findings)
            total_predicted += len(predicted_findings)

            # Match findings
            matched_gt_indices = set()
            case_tp = 0
            case_fp = 0

            for pred in predicted_findings:
                match_found = False
                for idx, gt in enumerate(case.expected_findings):
                    if idx in matched_gt_indices:
                        continue
                    if self._matches(pred, gt):
                        match_found = True
                        matched_gt_indices.add(idx)
                        case_tp += 1
                        break
                if not match_found:
                    case_fp += 1

            case_fn = len(case.expected_findings) - len(matched_gt_indices)

            # Critical error metrics
            crit_expected = sum(
                1 for gt in case.expected_findings if gt.severity == SeverityEnum.CRITICAL
            )
            crit_detected = sum(
                1
                for idx in matched_gt_indices
                if case.expected_findings[idx].severity == SeverityEnum.CRITICAL
            )

            total_tp += case_tp
            total_fp += case_fp
            total_fn += case_fn
            total_critical_expected += crit_expected
            total_critical_detected += crit_detected

            status_matched = (
                qc_result.overall_status.value == case.expected_overall_status
                or (case.expected_overall_status == "REVIEW_REQUIRED" and qc_result.overall_status.value in ["REVIEW_REQUIRED", "FAIL"])
            )
            if status_matched:
                cases_passed_status += 1

            case_results.append(
                CaseEvaluationResult(
                    case_id=case.case_id,
                    case_name=case.name,
                    true_positives=case_tp,
                    false_positives=case_fp,
                    false_negatives=case_fn,
                    critical_expected=crit_expected,
                    critical_detected=crit_detected,
                    predicted_findings_count=len(predicted_findings),
                    expected_findings_count=len(case.expected_findings),
                    passed_overall_status_match=status_matched,
                )
            )

        metrics = calculate_metrics(
            tp=total_tp,
            fp=total_fp,
            fn=total_fn,
            critical_expected=total_critical_expected,
            critical_detected=total_critical_detected,
        )

        passed_gate = (
            metrics["critical_error_recall"] >= self.MIN_CRITICAL_RECALL
            and metrics["f1_score"] >= self.MIN_F1_SCORE
        )

        return BenchmarkReport(
            total_cases=len(test_cases),
            cases_passed_status=cases_passed_status,
            total_expected_findings=total_expected,
            total_predicted_findings=total_predicted,
            total_true_positives=total_tp,
            total_false_positives=total_fp,
            total_false_negatives=total_fn,
            precision=metrics["precision"],
            recall=metrics["recall"],
            f1_score=metrics["f1_score"],
            critical_error_recall=metrics["critical_error_recall"],
            case_results=case_results,
            passed_quality_gate=passed_gate,
        )

    def _matches(self, pred: QCFinding, gt: GroundTruthFinding) -> bool:
        """Determines if a predicted finding corresponds to an expected ground truth finding."""
        if pred.rule_id != gt.rule_id:
            return False
        if pred.page != gt.page:
            return False
        if gt.evidence_keyword.lower() not in pred.evidence.lower() and gt.evidence_keyword.lower() not in pred.description.lower():
            return False
        return True
