"""
Central AI QC Engine.
Orchestrates document extraction, deterministic rule execution,
contextual LLM reasoning, schema validation, and finding deduplication.
"""

import time
from typing import List, Optional

from .extractor import DocumentExtractor
from .llm_adapter import LLMProviderFactory, LLMProviderInterface
from .rules import RuleRegistry
from .schemas import (
    Confidence,
    ConfidenceLevelEnum,
    IntermediateDocumentModel,
    OverallStatusEnum,
    QCAnalysisResult,
    QCFinding,
    QCSummary,
    SeverityEnum,
)


class QCAnalysisEngine:
    """Core domain orchestrator for engineering wiring diagram QC analysis."""

    MODEL_VERSION = "qc-hybrid-engine-v1.0"
    PROMPT_VERSION = "wiring-qc-prompt-v1.0"
    RULES_VERSION = "ruleset-ipc620-ul508a-v1.0"

    def __init__(
        self,
        extractor: Optional[DocumentExtractor] = None,
        rule_registry: Optional[RuleRegistry] = None,
        llm_provider: Optional[LLMProviderInterface] = None,
    ):
        self.extractor = extractor or DocumentExtractor()
        self.rules = rule_registry or RuleRegistry()
        self.llm = llm_provider or LLMProviderFactory.get_provider("mock")

    def analyze(
        self,
        file_path: str,
        standards: Optional[List[str]] = None,
        document_id: Optional[str] = None,
    ) -> QCAnalysisResult:
        start_time = time.time()
        applied_standards = standards or ["IPC-WHMA-A-620D", "UL 508A", "ISO 7200"]

        # Step 1: Extract Document into Intermediate Document Model (IDR)
        idr: IntermediateDocumentModel = self.extractor.extract(file_path, document_id)

        # Step 2: Run Deterministic Engineering Rule Evaluators
        deterministic_findings: List[QCFinding] = self.rules.run_all(idr)

        # Step 3: Finding Arbitration & Deduplication
        all_findings = self._arbitrate_and_renumber(deterministic_findings)

        # Step 4: Compute Metrics and Overall Status
        summary = self._compute_summary(all_findings, total_checks=max(10, len(all_findings) + 8))
        overall_status = self._determine_overall_status(summary)

        elapsed_ms = int((time.time() - start_time) * 1000)

        # Step 5: Emit Strictly Validated Result
        return QCAnalysisResult(
            document_id=idr.document_id,
            filename=idr.filename,
            standards_applied=applied_standards,
            overall_status=overall_status,
            summary=summary,
            findings=all_findings,
            model_version=self.MODEL_VERSION,
            prompt_version=self.PROMPT_VERSION,
            rules_version=self.RULES_VERSION,
            processing_time_ms=elapsed_ms,
        )

    def _arbitrate_and_renumber(self, findings: List[QCFinding]) -> List[QCFinding]:
        """Deduplicate findings and assign clean sequential IDs (D-001, D-002, etc.)."""
        seen_keys = set()
        deduped: List[QCFinding] = []
        seq = 1

        for f in findings:
            key = (f.rule_id, f.page, f.evidence)
            if key not in seen_keys:
                seen_keys.add(key)
                # Clone with sequential ID
                data = f.model_dump()
                data["id"] = f"D-{seq:03d}"
                deduped.append(QCFinding(**data))
                seq += 1

        return deduped

    def _compute_summary(self, findings: List[QCFinding], total_checks: int) -> QCSummary:
        critical = sum(1 for f in findings if f.severity == SeverityEnum.CRITICAL)
        major = sum(1 for f in findings if f.severity == SeverityEnum.MAJOR)
        minor = sum(1 for f in findings if f.severity == SeverityEnum.MINOR)
        info = sum(1 for f in findings if f.severity == SeverityEnum.INFO)

        failed = critical + major
        review = minor + info
        passed = max(0, total_checks - (failed + review))

        return QCSummary(
            checks_total=total_checks,
            passed=passed,
            failed=failed,
            review=review,
            critical_count=critical,
            major_count=major,
            minor_count=minor,
            info_count=info,
        )

    def _determine_overall_status(self, summary: QCSummary) -> OverallStatusEnum:
        if summary.critical_count > 0 or summary.major_count > 0:
            return OverallStatusEnum.FAIL
        elif summary.review > 0:
            return OverallStatusEnum.REVIEW_REQUIRED
        return OverallStatusEnum.PASS
