"""
Deterministic QC Rules Engine.
Evaluates explicit engineering and compliance constraints against the Intermediate Document Model.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from .schemas import (
    Confidence,
    ConfidenceLevelEnum,
    IntermediateDocumentModel,
    QCFinding,
    SeverityEnum,
)


class BaseRule(ABC):
    rule_id: str
    name: str
    category: str
    severity: SeverityEnum
    standard: str
    standard_section: str

    @abstractmethod
    def evaluate(self, doc: IntermediateDocumentModel) -> List[QCFinding]:
        """Evaluate rule against document and return any discovered findings."""
        pass


class MissingWireGaugeRule(BaseRule):
    """RULE-WG-001: Every electrical wire run must have an explicit gauge specification."""

    rule_id = "RULE-WG-001"
    name = "Missing Wire Gauge"
    category = "WIRE_SPEC"
    severity = SeverityEnum.CRITICAL
    standard = "IPC-WHMA-A-620D"
    standard_section = "Section 4.1 (Wire Selection & Rating)"

    def evaluate(self, doc: IntermediateDocumentModel) -> List[QCFinding]:
        findings: List[QCFinding] = []
        finding_seq = 1

        for page in doc.pages:
            for wire in page.wire_callouts:
                if not wire.gauge:
                    findings.append(
                        QCFinding(
                            id=f"D-WG-{doc.document_id[:4]}-{page.page_number}-{finding_seq:03d}",
                            rule_id=self.rule_id,
                            category=self.category,
                            description=f"Wire '{wire.wire_number or wire.raw_text}' lacks an explicit wire gauge specification.",
                            severity=self.severity,
                            confidence=Confidence(level=ConfidenceLevelEnum.HIGH, score=0.98),
                            page=page.page_number,
                            location=wire.location,
                            evidence=f"Callout: '{wire.raw_text}'",
                            requirement="All wiring runs must specify nominal wire gauge (AWG or mm²) to satisfy ampacity and crimp tooling requirements.",
                            standard=self.standard,
                            standard_section=self.standard_section,
                            recommendation="Update schematic to declare nominal AWG (e.g. 18 AWG, 22 AWG) or metric cross-section.",
                        )
                    )
                    finding_seq += 1

        return findings


class ColorCodeMismatchRule(BaseRule):
    """RULE-CC-003: Wire color abbreviations must adhere to standard engineering color codes."""

    rule_id = "RULE-CC-003"
    name = "Color Code Ambiguity"
    category = "COLOR_CODE"
    severity = SeverityEnum.MAJOR
    standard = "UL 508A"
    standard_section = "Section 66.5 (Internal Wiring Color Codes)"

    def evaluate(self, doc: IntermediateDocumentModel) -> List[QCFinding]:
        findings: List[QCFinding] = []
        finding_seq = 1

        for page in doc.pages:
            for wire in page.wire_callouts:
                # If wire is designated as a power/earth or specific function without standard color
                if not wire.color:
                    findings.append(
                        QCFinding(
                            id=f"D-CC-{doc.document_id[:4]}-{page.page_number}-{finding_seq:03d}",
                            rule_id=self.rule_id,
                            category=self.category,
                            description=f"Wire '{wire.wire_number or wire.raw_text}' is missing a color code identification.",
                            severity=self.severity,
                            confidence=Confidence(level=ConfidenceLevelEnum.HIGH, score=0.92),
                            page=page.page_number,
                            location=wire.location,
                            evidence=f"Callout text: '{wire.raw_text}'",
                            requirement="Conductors must be clearly color-coded or marked for phase, neutral, DC polarity, or grounding identification.",
                            standard=self.standard,
                            standard_section=self.standard_section,
                            recommendation="Assign standard conductor insulation color (e.g. BLK, RED, BLU, WHT, or GRN/YEL for earth ground).",
                        )
                    )
                    finding_seq += 1

        return findings


class TitleBlockIncompleteRule(BaseRule):
    """RULE-TB-005: Mandatory title block fields (Drawing No, Revision, Drawn By, Date) must be present."""

    rule_id = "RULE-TB-005"
    name = "Incomplete Title Block"
    category = "DOCUMENTATION"
    severity = SeverityEnum.MINOR
    standard = "ISO 7200 / ASME Y14.1"
    standard_section = "Section 5 (Title Block Data Fields)"

    def evaluate(self, doc: IntermediateDocumentModel) -> List[QCFinding]:
        findings: List[QCFinding] = []
        finding_seq = 1

        for page in doc.pages:
            tb = page.title_block
            missing_fields: List[str] = []

            if not tb:
                missing_fields = ["Drawing Number", "Revision", "Drawn By", "Date"]
            else:
                if not tb.drawing_number:
                    missing_fields.append("Drawing Number")
                if not tb.revision:
                    missing_fields.append("Revision")
                if not tb.drawn_by:
                    missing_fields.append("Drawn By")
                if not tb.date:
                    missing_fields.append("Date")

            if missing_fields:
                findings.append(
                    QCFinding(
                        id=f"D-TB-{doc.document_id[:4]}-{page.page_number}-{finding_seq:03d}",
                        rule_id=self.rule_id,
                        category=self.category,
                        description=f"Page {page.page_number} title block is missing required control fields: {', '.join(missing_fields)}.",
                        severity=self.severity,
                        confidence=Confidence(level=ConfidenceLevelEnum.HIGH, score=0.96),
                        page=page.page_number,
                        location=None,
                        evidence=f"Observed Title Block: {tb.model_dump() if tb else 'None'}",
                        requirement="Production engineering schematics must maintain revision control and engineering sign-off fields.",
                        standard=self.standard,
                        standard_section=self.standard_section,
                        recommendation=f"Complete title block metadata before releasing drawing for production build: fill in {', '.join(missing_fields)}.",
                    )
                )
                finding_seq += 1

        return findings


class DuplicateDesignatorRule(BaseRule):
    """RULE-RD-004: Component reference designators (J1, P2, TB1) must be unique and defined."""

    rule_id = "RULE-RD-004"
    name = "Duplicate Reference Designator"
    category = "DESIGNATOR"
    severity = SeverityEnum.CRITICAL
    standard = "ANSI/IEEE 200"
    standard_section = "Section 4.2 (Reference Designator Rules)"

    def evaluate(self, doc: IntermediateDocumentModel) -> List[QCFinding]:
        findings: List[QCFinding] = []
        seen_refs = {}
        finding_seq = 1

        for page in doc.pages:
            for conn in page.connectors:
                ref = conn.ref_des.upper()
                if ref in seen_refs:
                    prev_page = seen_refs[ref]
                    findings.append(
                        QCFinding(
                            id=f"D-RD-{doc.document_id[:4]}-{page.page_number}-{finding_seq:03d}",
                            rule_id=self.rule_id,
                            category=self.category,
                            description=f"Duplicate reference designator '{ref}' found on page {page.page_number} (previously declared on page {prev_page}).",
                            severity=self.severity,
                            confidence=Confidence(level=ConfidenceLevelEnum.HIGH, score=0.95),
                            page=page.page_number,
                            location=conn.location,
                            evidence=f"RefDes: {ref} on Page {page.page_number} collisions with Page {prev_page}",
                            requirement="Reference designators must be strictly unique across the assembly schematic to avoid assembly miswiring.",
                            standard=self.standard,
                            standard_section=self.standard_section,
                            recommendation=f"Re-designate duplicate component '{ref}' to a unique identifier (e.g. {ref}A, {ref}B, or next sequential number).",
                        )
                    )
                    finding_seq += 1
                else:
                    seen_refs[ref] = page.page_number

        return findings


class RuleRegistry:
    """Central registry and execution manager for deterministic QC rules."""

    def __init__(self):
        self.rules: List[BaseRule] = [
            MissingWireGaugeRule(),
            ColorCodeMismatchRule(),
            TitleBlockIncompleteRule(),
            DuplicateDesignatorRule(),
        ]

    def run_all(self, doc: IntermediateDocumentModel) -> List[QCFinding]:
        all_findings: List[QCFinding] = []
        for rule in self.rules:
            findings = rule.evaluate(doc)
            all_findings.extend(findings)
        return all_findings
