"""
Deterministic QC Rules Engine & Versioned Rule Packs.
Evaluates explicit engineering and compliance constraints against the Intermediate Document Model (IDR).
Covers mandatory rule categories: wire, terminal, component, reference, documentation, consistency.
Implements versioned rule packs for IPC-WHMA-A-620D, UL 508A, ISO 7200, MIL-STD-681D, and Spandsons Internal standards.
"""

from abc import ABC, abstractmethod
import re
from typing import Any, Dict, List, Optional, Set
from .schemas import (
    Confidence,
    ConfidenceLevelEnum,
    IntermediateDocumentModel,
    QCFinding,
    SeverityEnum,
)


class BaseRule(ABC):
    """Abstract base class for all deterministic QC rules."""

    rule_id: str
    name: str
    category: str  # wire, terminal, component, reference, documentation, consistency
    severity: SeverityEnum
    standard: str
    standard_section: str
    version: str = "1.0.0"
    enabled: bool = True
    applicability: str = "All engineering wiring drawings"
    expected_condition: str = ""
    remediation_guidance: str = ""

    @abstractmethod
    def evaluate(self, doc: IntermediateDocumentModel) -> List[QCFinding]:
        """Evaluate rule against document and return any discovered findings."""
        pass

    def metadata(self) -> Dict[str, Any]:
        """Return rule metadata dictionary."""
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "category": self.category,
            "severity": self.severity.value,
            "version": self.version,
            "enabled": self.enabled,
            "standard": self.standard,
            "standard_section": self.standard_section,
            "applicability": self.applicability,
            "expected_condition": self.expected_condition,
            "remediation_guidance": self.remediation_guidance,
        }


# ============================================================================
# CATEGORY 1: WIRE
# ============================================================================


class MissingWireGaugeRule(BaseRule):
    """RULE-WG-001: Every electrical wire run must have an explicit gauge specification."""

    rule_id = "RULE-WG-001"
    name = "Missing Wire Gauge"
    category = "wire"
    severity = SeverityEnum.CRITICAL
    standard = "IPC-WHMA-A-620D"
    standard_section = "Section 4.1 (Wire Selection & Rating)"
    version = "1.0.0"
    applicability = "All point-to-point wiring runs and harness assemblies"
    expected_condition = "All wire callouts must specify nominal wire gauge in AWG or mm²."
    remediation_guidance = "Declare nominal AWG (e.g. 18 AWG, 22 AWG) or metric cross-section (e.g. 0.75 mm²)."

    def evaluate(self, doc: IntermediateDocumentModel) -> List[QCFinding]:
        if not self.enabled:
            return []
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
                            recommendation=self.remediation_guidance,
                        )
                    )
                    finding_seq += 1

        return findings


class ColorCodeMismatchRule(BaseRule):
    """RULE-CC-003: Wire color abbreviations must adhere to standard engineering color codes."""

    rule_id = "RULE-CC-003"
    name = "Color Code Ambiguity"
    category = "wire"
    severity = SeverityEnum.MAJOR
    standard = "UL 508A"
    standard_section = "Section 66.5 (Internal Wiring Color Codes)"
    version = "1.0.0"
    applicability = "All single-conductor and point-to-point leads"
    expected_condition = "Every lead must be marked or color-coded for functional identification."
    remediation_guidance = "Assign standard conductor insulation color (BLK, RED, BLU, WHT, etc.)."

    def evaluate(self, doc: IntermediateDocumentModel) -> List[QCFinding]:
        if not self.enabled:
            return []
        findings: List[QCFinding] = []
        finding_seq = 1

        for page in doc.pages:
            for wire in page.wire_callouts:
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
                            recommendation=self.remediation_guidance,
                        )
                    )
                    finding_seq += 1

        return findings


class GroundConductorColorRule(BaseRule):
    """RULE-WIRE-GND-001: Protective earth & ground conductors must be GREEN or GREEN/YELLOW."""

    rule_id = "RULE-WIRE-GND-001"
    name = "Protective Ground Conductor Color Compliance"
    category = "wire"
    severity = SeverityEnum.CRITICAL
    standard = "UL 508A / NFPA 79"
    standard_section = "UL 508A Section 15.2 / NFPA 79 Section 13.2"
    version = "1.0.0"
    applicability = "All protective earthing, equipment grounding, and chassis ground conductors"
    expected_condition = "Conductors designated as protective earth must be GREEN or GREEN/YELLOW."
    remediation_guidance = "Change conductor color to GREEN or GRN/YEL for all protective grounding runs."

    PERMITTED_GROUND_COLORS = {"GRN", "GREEN", "GRN/YEL", "GREEN/YELLOW", "GRN-YEL", "GREEN-YELLOW"}
    GROUND_TERMS = re.compile(r"(?:^|[_\W])(GND|PE|EARTH|GROUND|CHASSIS[_-]?GND|FRAME[_-]?GND)(?:[_\W\d]|$)", re.IGNORECASE)

    def evaluate(self, doc: IntermediateDocumentModel) -> List[QCFinding]:
        if not self.enabled:
            return []
        findings: List[QCFinding] = []
        finding_seq = 1

        for page in doc.pages:
            for wire in page.wire_callouts:
                is_ground_wire = False
                # Check wire ID, raw text, and endpoint connectors
                text_to_check = f"{wire.wire_number or ''} {wire.raw_text} {wire.from_connector or ''} {wire.to_connector or ''}"
                if self.GROUND_TERMS.search(text_to_check):
                    # Exclude signal/analog return labels if explicitly marked signal (e.g. AGND, SIG_GND)
                    if not re.search(r"\b(AGND|SIG_GND|DGND|ANALOG_GND)\b", text_to_check, re.IGNORECASE):
                        is_ground_wire = True

                if is_ground_wire and wire.color:
                    clean_color = wire.color.strip().upper()
                    if clean_color not in self.PERMITTED_GROUND_COLORS:
                        findings.append(
                            QCFinding(
                                id=f"D-GND-{doc.document_id[:4]}-{page.page_number}-{finding_seq:03d}",
                                rule_id=self.rule_id,
                                category=self.category,
                                description=(
                                    f"Protective ground wire '{wire.wire_number or wire.raw_text}' is assigned non-compliant "
                                    f"color '{wire.color}'. Protective earth must be GREEN or GREEN/YELLOW."
                                ),
                                severity=self.severity,
                                confidence=Confidence(level=ConfidenceLevelEnum.HIGH, score=0.96),
                                page=page.page_number,
                                location=wire.location,
                                evidence=f"Wire: '{wire.raw_text}', Color: '{wire.color}'",
                                requirement="Protective ground and equipment earthing conductors must have green or green with yellow stripe insulation.",
                                standard=self.standard,
                                standard_section=self.standard_section,
                                recommendation=self.remediation_guidance,
                            )
                        )
                        finding_seq += 1

        return findings


class WireAmpacitySizingRule(BaseRule):
    """RULE-WIRE-AMP-001: Conductor gauge must satisfy UL 508A Table 28.1 ampacity ratings."""

    rule_id = "RULE-WIRE-AMP-001"
    name = "Wire Ampacity Sizing vs Circuit Rating"
    category = "wire"
    severity = SeverityEnum.CRITICAL
    standard = "UL 508A"
    standard_section = "Table 28.1 (Ampacities of Insulated Conductors)"
    version = "1.0.0"
    applicability = "Power distribution circuits and branch circuits"
    expected_condition = "Conductor gauge must support the continuous rated current of the upstream circuit breaker/fuse."
    remediation_guidance = "Upsize wire gauge per UL 508A Table 28.1 (e.g. 14 AWG for 15A, 12 AWG for 20A, 10 AWG for 30A)."

    # Minimum AWG gauge for standard circuit breaker ratings (UL 508A Table 28.1)
    # Higher AWG number = thinner conductor
    RATING_MAX_AWG = [
        (15, 14),  # 15A requires at least 14 AWG (cannot use 16, 18, 20, 22)
        (20, 12),  # 20A requires at least 12 AWG
        (30, 10),  # 30A requires at least 10 AWG
        (50, 8),   # 50A requires at least 8 AWG
        (70, 6),   # 70A requires at least 6 AWG
    ]

    CURRENT_PATTERN = re.compile(r"\b(15|20|30|40|50|60|70)\s*(?:A|AMP|AMPS)\b", re.IGNORECASE)
    AWG_PATTERN = re.compile(r"\b(\d{1,2})\s*AWG\b", re.IGNORECASE)

    def evaluate(self, doc: IntermediateDocumentModel) -> List[QCFinding]:
        if not self.enabled:
            return []
        findings: List[QCFinding] = []
        finding_seq = 1

        for page in doc.pages:
            for wire in page.wire_callouts:
                if not wire.gauge:
                    continue

                awg_match = self.AWG_PATTERN.search(wire.gauge)
                if not awg_match:
                    continue
                wire_awg = int(awg_match.group(1))

                # Check if wire callout or line contains a current rating
                curr_match = self.CURRENT_PATTERN.search(wire.raw_text)
                if curr_match:
                    rated_amps = int(curr_match.group(1))
                    for threshold_amps, max_allowed_awg in self.RATING_MAX_AWG:
                        if rated_amps >= threshold_amps and wire_awg > max_allowed_awg:
                            findings.append(
                                QCFinding(
                                    id=f"D-AMP-{doc.document_id[:4]}-{page.page_number}-{finding_seq:03d}",
                                    rule_id=self.rule_id,
                                    category=self.category,
                                    description=(
                                        f"Conductor '{wire.wire_number or wire.raw_text}' gauge {wire.gauge} is undersized "
                                        f"for {rated_amps}A circuit protection (minimum required: {max_allowed_awg} AWG per UL 508A Table 28.1)."
                                    ),
                                    severity=self.severity,
                                    confidence=Confidence(level=ConfidenceLevelEnum.HIGH, score=0.97),
                                    page=page.page_number,
                                    location=wire.location,
                                    evidence=f"Callout: '{wire.raw_text}', Gauge: {wire.gauge}, Rating: {rated_amps}A",
                                    requirement=f"Conductor must have sufficient ampacity to safely carry {rated_amps}A without thermal damage.",
                                    standard=self.standard,
                                    standard_section=self.standard_section,
                                    recommendation=f"Upsize wire to at least {max_allowed_awg} AWG or reduce circuit breaker rating.",
                                )
                            )
                            finding_seq += 1
                            break

        return findings


# ============================================================================
# CATEGORY 2: TERMINAL
# ============================================================================


class TerminalMissingPartNumberRule(BaseRule):
    """RULE-TRM-MPN-001: Terminal blocks & connectors must declare an approved manufacturer part number."""

    rule_id = "RULE-TRM-MPN-001"
    name = "Terminal & Connector Part Number Missing"
    category = "terminal"
    severity = SeverityEnum.MAJOR
    standard = "IPC-WHMA-A-620D"
    standard_section = "Section 9.1 (Connector Hardware Requirements)"
    version = "1.0.0"
    applicability = "All connectors and terminal blocks"
    expected_condition = "All connectors and terminal blocks must have defined manufacturer part numbers."
    remediation_guidance = "Add manufacturer part number (e.g. MS3106A-20-4P, WAGO-2002-1201) to drawing BOM."

    def evaluate(self, doc: IntermediateDocumentModel) -> List[QCFinding]:
        if not self.enabled:
            return []
        findings: List[QCFinding] = []
        finding_seq = 1

        for page in doc.pages:
            for conn in page.connectors:
                # Terminal blocks and connectors must have part numbers
                if not conn.part_number:
                    findings.append(
                        QCFinding(
                            id=f"D-TRM-MPN-{doc.document_id[:4]}-{page.page_number}-{finding_seq:03d}",
                            rule_id=self.rule_id,
                            category=self.category,
                            description=f"Component '{conn.ref_des}' lacks a manufacturer part number specification in the BOM schedule.",
                            severity=self.severity,
                            confidence=Confidence(level=ConfidenceLevelEnum.HIGH, score=0.91),
                            page=page.page_number,
                            location=conn.location,
                            evidence=f"RefDes: '{conn.ref_des}', Part Number: None",
                            requirement="Connectors and terminal blocks must specify manufacturer part numbers for procurement and crimp tool verification.",
                            standard=self.standard,
                            standard_section=self.standard_section,
                            recommendation=self.remediation_guidance,
                        )
                    )
                    finding_seq += 1

        return findings


class TerminalBlockDesignationRule(BaseRule):
    """RULE-TRM-PIN-001: Terminal block terminations must specify explicit terminal position / pin designators."""

    rule_id = "RULE-TRM-PIN-001"
    name = "Terminal Block Position & Pin Numbering Completeness"
    category = "terminal"
    severity = SeverityEnum.MAJOR
    standard = "IPC-WHMA-A-620D"
    standard_section = "Section 13.5 (Terminal Block Markings)"
    version = "1.0.0"
    applicability = "All terminal block wiring terminations"
    expected_condition = "Terminal block connection endpoints must declare position or pole numbers (e.g. TB1-1, TB1-2)."
    remediation_guidance = "Specify terminal position (e.g. TB1-3) rather than bare block designator."

    TB_PATTERN = re.compile(r"^TB\d+$", re.IGNORECASE)

    def evaluate(self, doc: IntermediateDocumentModel) -> List[QCFinding]:
        if not self.enabled:
            return []
        findings: List[QCFinding] = []
        finding_seq = 1

        # Count references to bare TB endpoints (without pin suffix like TB1-1 or TB1:2)
        for page in doc.pages:
            tb_references: Dict[str, List[str]] = {}
            for wire in page.wire_callouts:
                for ep in [wire.from_connector, wire.to_connector]:
                    if ep and self.TB_PATTERN.match(ep.strip()):
                        tb_id = ep.strip().upper()
                        tb_references.setdefault(tb_id, []).append(wire.wire_number or wire.raw_text)

            for tb_id, wires in tb_references.items():
                if len(wires) > 1:
                    findings.append(
                        QCFinding(
                            id=f"D-TRM-PIN-{doc.document_id[:4]}-{page.page_number}-{finding_seq:03d}",
                            rule_id=self.rule_id,
                            category=self.category,
                            description=(
                                f"Terminal block '{tb_id}' has {len(wires)} wire connections ({', '.join(wires[:3])}) "
                                f"without explicit pole/position numbers (e.g. {tb_id}-1, {tb_id}-2)."
                            ),
                            severity=self.severity,
                            confidence=Confidence(level=ConfidenceLevelEnum.HIGH, score=0.90),
                            page=page.page_number,
                            location=None,
                            evidence=f"Bare terminal block '{tb_id}' referenced by wires: {', '.join(wires)}",
                            requirement="Multi-point terminal block connections must declare terminal pole or position numbers for assembly routing.",
                            standard=self.standard,
                            standard_section=self.standard_section,
                            recommendation=self.remediation_guidance,
                        )
                    )
                    finding_seq += 1

        return findings


class TerminalOvercrowdingRule(BaseRule):
    """RULE-TRM-CRW-001: Maximum 2 conductors terminated under a single terminal clamp position."""

    rule_id = "RULE-TRM-CRW-001"
    name = "Terminal Screw Clamp Conductor Overcrowding"
    category = "terminal"
    severity = SeverityEnum.MAJOR
    standard = "UL 508A"
    standard_section = "Section 28.3.2 (Conductors per Terminal)"
    version = "1.0.0"
    applicability = "All screw and spring clamp terminal connections"
    expected_condition = "No more than 2 conductors per individual terminal clamp position."
    remediation_guidance = "Use jumper bars or additional terminal positions to distribute conductors."

    def evaluate(self, doc: IntermediateDocumentModel) -> List[QCFinding]:
        if not self.enabled:
            return []
        findings: List[QCFinding] = []
        finding_seq = 1

        for page in doc.pages:
            pin_wire_count: Dict[str, List[str]] = {}
            for wire in page.wire_callouts:
                for ep in [wire.from_connector, wire.to_connector]:
                    if ep and ("-" in ep or ":" in ep):
                        pin_id = ep.strip().upper()
                        pin_wire_count.setdefault(pin_id, []).append(wire.wire_number or wire.raw_text)

            for pin_id, wires in pin_wire_count.items():
                if len(wires) > 2:
                    findings.append(
                        QCFinding(
                            id=f"D-TRM-CRW-{doc.document_id[:4]}-{page.page_number}-{finding_seq:03d}",
                            rule_id=self.rule_id,
                            category=self.category,
                            description=(
                                f"Terminal position '{pin_id}' terminates {len(wires)} conductors ({', '.join(wires)}). "
                                f"UL 508A limits terminal clamp connections to a maximum of 2 conductors."
                            ),
                            severity=self.severity,
                            confidence=Confidence(level=ConfidenceLevelEnum.HIGH, score=0.94),
                            page=page.page_number,
                            location=None,
                            evidence=f"Terminal '{pin_id}' shared by {len(wires)} wires: {', '.join(wires)}",
                            requirement="No more than 2 conductors shall be connected to a single terminal clamp unless listed for multiple conductors.",
                            standard=self.standard,
                            standard_section=self.standard_section,
                            recommendation=self.remediation_guidance,
                        )
                    )
                    finding_seq += 1

        return findings


# ============================================================================
# CATEGORY 3: COMPONENT
# ============================================================================


class ComponentDesignatorSyntaxRule(BaseRule):
    """RULE-CMP-SYN-001: Component reference designators must follow ANSI/IEEE 315 class prefixes."""

    rule_id = "RULE-CMP-SYN-001"
    name = "Standard Component Reference Designator Class Lettering"
    category = "component"
    severity = SeverityEnum.MAJOR
    standard = "ANSI/IEEE 315 / IEEE 200"
    standard_section = "Section 4 (Reference Designation System)"
    version = "1.0.0"
    applicability = "All electrical schematic components and connectors"
    expected_condition = "Reference designators must begin with recognized IEEE 315 class prefix letters."
    remediation_guidance = "Rename component designator to conform to IEEE 315 class lettering conventions."

    # Standard IEEE 315 reference designator class letters
    VALID_PREFIXES = {
        "J", "P", "TB", "TERM", "K", "CB", "F", "SW", "S", "R", "C", "D", "CR",
        "M", "PS", "X", "CON", "CN", "PL", "U", "Q", "T", "L", "VR", "DS", "LS"
    }

    PREFIX_REGEX = re.compile(r"^([A-Z]+)(\d+.*)$", re.IGNORECASE)

    def evaluate(self, doc: IntermediateDocumentModel) -> List[QCFinding]:
        if not self.enabled:
            return []
        findings: List[QCFinding] = []
        finding_seq = 1

        for page in doc.pages:
            for conn in page.connectors:
                ref = conn.ref_des.strip().upper()
                match = self.PREFIX_REGEX.match(ref)
                if match:
                    prefix = match.group(1)
                    if prefix not in self.VALID_PREFIXES:
                        findings.append(
                            QCFinding(
                                id=f"D-CMP-SYN-{doc.document_id[:4]}-{page.page_number}-{finding_seq:03d}",
                                rule_id=self.rule_id,
                                category=self.category,
                                description=(
                                    f"Component reference designator '{ref}' uses unrecognized class prefix '{prefix}'. "
                                    f"Standard prefixes per IEEE 315 include J, P, TB, K, CB, F, SW, R, C, D."
                                ),
                                severity=self.severity,
                                confidence=Confidence(level=ConfidenceLevelEnum.HIGH, score=0.93),
                                page=page.page_number,
                                location=conn.location,
                                evidence=f"Observed RefDes: '{conn.ref_des}'",
                                requirement="Component reference designators must adhere to standard IEEE 315 electrical class letter prefixes.",
                                standard=self.standard,
                                standard_section=self.standard_section,
                                recommendation=self.remediation_guidance,
                            )
                        )
                        finding_seq += 1

        return findings


class OvercurrentDeviceRatingRule(BaseRule):
    """RULE-CMP-OCP-001: Overcurrent protective devices (CB, F) must declare rated current."""

    rule_id = "RULE-CMP-OCP-001"
    name = "Overcurrent Protective Device Rating Declaration"
    category = "component"
    severity = SeverityEnum.CRITICAL
    standard = "UL 508A"
    standard_section = "Section 29.1 (Branch Circuit Overcurrent Protection)"
    version = "1.0.0"
    applicability = "All circuit breakers, fuses, and supplementary protectors"
    expected_condition = "Protective devices must display continuous current rating on the schematic."
    remediation_guidance = "Add trip / ampere rating (e.g. CB1: 15A, F1: 5A) to schematic symbol."

    OCP_PATTERN = re.compile(r"\b(CB\d+|F\d+)\b", re.IGNORECASE)
    RATING_PATTERN = re.compile(r"\b\d+(?:\.\d+)?\s*(?:A|AMP|AMPS|mA)\b", re.IGNORECASE)

    def evaluate(self, doc: IntermediateDocumentModel) -> List[QCFinding]:
        if not self.enabled:
            return []
        findings: List[QCFinding] = []
        finding_seq = 1

        for page in doc.pages:
            for text in page.raw_text_blocks:
                ocp_match = self.OCP_PATTERN.search(text)
                if ocp_match:
                    device_tag = ocp_match.group(1).upper()
                    has_rating = self.RATING_PATTERN.search(text)
                    if not has_rating:
                        findings.append(
                            QCFinding(
                                id=f"D-CMP-OCP-{doc.document_id[:4]}-{page.page_number}-{finding_seq:03d}",
                                rule_id=self.rule_id,
                                category=self.category,
                                description=(
                                    f"Overcurrent protection device '{device_tag}' lacks a continuous current rating specification."
                                ),
                                severity=self.severity,
                                confidence=Confidence(level=ConfidenceLevelEnum.HIGH, score=0.92),
                                page=page.page_number,
                                location=None,
                                evidence=f"Text block: '{text}'",
                                requirement="Circuit breakers and fuses must display continuous current and voltage ratings on the schematic.",
                                standard=self.standard,
                                standard_section=self.standard_section,
                                recommendation=self.remediation_guidance,
                            )
                        )
                        finding_seq += 1

        return findings


# ============================================================================
# CATEGORY 4: REFERENCE
# ============================================================================


class DuplicateDesignatorRule(BaseRule):
    """RULE-RD-004: Component reference designators (J1, P2, TB1) must be unique across the assembly."""

    rule_id = "RULE-RD-004"
    name = "Duplicate Reference Designator"
    category = "reference"
    severity = SeverityEnum.CRITICAL
    standard = "ANSI/IEEE 200"
    standard_section = "Section 4.2 (Reference Designator Rules)"
    version = "1.0.0"
    applicability = "All schematic components and connectors across all pages"
    expected_condition = "Reference designators must be unique across the entire drawing package."
    remediation_guidance = "Re-designate duplicate component to a unique identifier (e.g. J1A, J1B, or J2)."

    def evaluate(self, doc: IntermediateDocumentModel) -> List[QCFinding]:
        if not self.enabled:
            return []
        findings: List[QCFinding] = []
        seen_refs: Dict[str, int] = {}
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
                            recommendation=self.remediation_guidance,
                        )
                    )
                    finding_seq += 1
                else:
                    seen_refs[ref] = page.page_number

        return findings


class DanglingWireReferenceRule(BaseRule):
    """RULE-REF-DNG-001: Wire callout specifies source connector but lacks destination termination."""

    rule_id = "RULE-REF-DNG-001"
    name = "Dangling Un-terminated Conductor Run"
    category = "reference"
    severity = SeverityEnum.MAJOR
    standard = "IPC-WHMA-A-620D"
    standard_section = "Section 13.4 (Conductor Termination & End Routing)"
    version = "1.0.0"
    applicability = "All point-to-point conductor callouts"
    expected_condition = "Wire runs must specify both origin and destination termination points, or designate spare status."
    remediation_guidance = "Specify destination connector endpoint or mark conductor as 'SPARE (CAPPED)'."

    SPARE_TERMS = re.compile(r"\b(SPARE|NC|CAPPED|OPEN|STUB|SHRINK)\b", re.IGNORECASE)

    def evaluate(self, doc: IntermediateDocumentModel) -> List[QCFinding]:
        if not self.enabled:
            return []
        findings: List[QCFinding] = []
        finding_seq = 1

        for page in doc.pages:
            for wire in page.wire_callouts:
                # Wire has from_connector but missing to_connector without being a marked spare
                if wire.from_connector and not wire.to_connector:
                    if not self.SPARE_TERMS.search(wire.raw_text):
                        findings.append(
                            QCFinding(
                                id=f"D-REF-DNG-{doc.document_id[:4]}-{page.page_number}-{finding_seq:03d}",
                                rule_id=self.rule_id,
                                category=self.category,
                                description=(
                                    f"Conductor '{wire.wire_number or wire.raw_text}' originates from '{wire.from_connector}' "
                                    f"but lacks a destination termination endpoint or spare designation."
                                ),
                                severity=self.severity,
                                confidence=Confidence(level=ConfidenceLevelEnum.HIGH, score=0.91),
                                page=page.page_number,
                                location=wire.location,
                                evidence=f"Wire: '{wire.raw_text}', From: '{wire.from_connector}', To: None",
                                requirement="Point-to-point conductor runs must define both termination endpoints or declare stub/spare treatment.",
                                standard=self.standard,
                                standard_section=self.standard_section,
                                recommendation=self.remediation_guidance,
                            )
                        )
                        finding_seq += 1

        return findings


class CrossReferenceEndpointRule(BaseRule):
    """RULE-REF-XRF-001: Wire callout endpoint references a connector ID not declared in the schematic."""

    rule_id = "RULE-REF-XRF-001"
    name = "Unresolved Connector Cross-Reference Endpoint"
    category = "reference"
    severity = SeverityEnum.CRITICAL
    standard = "IPC-WHMA-A-620D"
    standard_section = "Section 13.4 (Wire Routing & Cross-References)"
    version = "1.0.0"
    applicability = "All point-to-point wire routing callouts"
    expected_condition = "All wire endpoint connector identifiers must exist in the connector schedule or drawing sheets."
    remediation_guidance = "Correct connector reference designator to match a declared component in the BOM."

    CONNECTOR_BASE_REGEX = re.compile(r"^([A-Z0-9]+)(?:[-:\/].*)?$", re.IGNORECASE)

    def evaluate(self, doc: IntermediateDocumentModel) -> List[QCFinding]:
        if not self.enabled:
            return []
        findings: List[QCFinding] = []
        finding_seq = 1

        # Collect all valid declared connector reference designators across all pages
        declared_connectors: Set[str] = set()
        for page in doc.pages:
            for conn in page.connectors:
                declared_connectors.add(conn.ref_des.strip().upper())
            for block in page.raw_text_blocks:
                # Also capture CONNECTORS: header declarations if present in text
                conn_line_match = re.search(r"CONNECTORS?:\s*(.*)", block, re.IGNORECASE)
                if conn_line_match:
                    tokens = re.findall(r"\b([A-Z0-9]+)\b", conn_line_match.group(1).upper())
                    for t in tokens:
                        if len(t) >= 2 and not t.isdigit():
                            declared_connectors.add(t)

        # Skip check if no connectors were declared in the entire document
        if not declared_connectors:
            return []

        for page in doc.pages:
            for wire in page.wire_callouts:
                for ep in [wire.from_connector, wire.to_connector]:
                    if not ep:
                        continue
                    clean_ep = ep.strip().upper()
                    match = self.CONNECTOR_BASE_REGEX.match(clean_ep)
                    if not match:
                        continue
                    base_ref = match.group(1)
                    # Exclude generic ground references
                    if base_ref in {"GND", "PE", "EARTH", "CHASSIS", "FRAME"}:
                        continue

                    if base_ref not in declared_connectors:
                        findings.append(
                            QCFinding(
                                id=f"D-REF-XRF-{doc.document_id[:4]}-{page.page_number}-{finding_seq:03d}",
                                rule_id=self.rule_id,
                                category=self.category,
                                description=(
                                    f"Wire '{wire.wire_number or wire.raw_text}' references endpoint '{ep}', "
                                    f"but connector '{base_ref}' is not declared anywhere in the connector BOM schedule."
                                ),
                                severity=self.severity,
                                confidence=Confidence(level=ConfidenceLevelEnum.HIGH, score=0.95),
                                page=page.page_number,
                                location=wire.location,
                                evidence=f"Wire endpoint '{ep}' not in declared components: {sorted(list(declared_connectors))[:8]}",
                                requirement="Every wire termination endpoint must resolve to an authorized component in the drawing schedule.",
                                standard=self.standard,
                                standard_section=self.standard_section,
                                recommendation=self.remediation_guidance,
                            )
                        )
                        finding_seq += 1

        return findings


# ============================================================================
# CATEGORY 5: DOCUMENTATION
# ============================================================================


class TitleBlockIncompleteRule(BaseRule):
    """RULE-TB-005: Mandatory title block fields (Drawing No, Revision, Drawn By, Date) must be present."""

    rule_id = "RULE-TB-005"
    name = "Incomplete Title Block"
    category = "documentation"
    severity = SeverityEnum.MINOR
    standard = "ISO 7200 / ASME Y14.1"
    standard_section = "Section 5 (Title Block Data Fields)"
    version = "1.0.0"
    applicability = "All drawing sheet title blocks"
    expected_condition = "Mandatory title block control fields must be fully populated."
    remediation_guidance = "Complete title block metadata before releasing drawing for production build."

    def evaluate(self, doc: IntermediateDocumentModel) -> List[QCFinding]:
        if not self.enabled:
            return []
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
                        recommendation=f"Complete title block metadata before releasing drawing: fill in {', '.join(missing_fields)}.",
                    )
                )
                finding_seq += 1

        return findings


class DrawingNumberSyntaxRule(BaseRule):
    """RULE-DOC-NUM-001: Drawing number must not contain placeholder strings (DRAFT, TBD, XXXX)."""

    rule_id = "RULE-DOC-NUM-001"
    name = "Drawing Number Syntax & Placeholder Validation"
    category = "documentation"
    severity = SeverityEnum.MINOR
    standard = "ISO 7200"
    standard_section = "Section 5.1 (Identification of Drawing)"
    version = "1.0.0"
    applicability = "All engineering drawing title blocks"
    expected_condition = "Drawing number must be a formal identifier and cannot contain placeholder strings."
    remediation_guidance = "Assign official drawing number from PLM/ERP."

    PLACEHOLDERS = {"DRAFT", "TBD", "XXXX", "TEMP", "UNASSIGNED", "000000", "TEST", "SAMPLE", "NONE"}

    def evaluate(self, doc: IntermediateDocumentModel) -> List[QCFinding]:
        if not self.enabled:
            return []
        findings: List[QCFinding] = []
        finding_seq = 1

        for page in doc.pages:
            tb = page.title_block
            if tb and tb.drawing_number:
                dwg = tb.drawing_number.strip().upper()
                if dwg in self.PLACEHOLDERS or len(dwg) < 3 or re.match(r"^X+$", dwg):
                    findings.append(
                        QCFinding(
                            id=f"D-DOC-NUM-{doc.document_id[:4]}-{page.page_number}-{finding_seq:03d}",
                            rule_id=self.rule_id,
                            category=self.category,
                            description=f"Drawing number '{tb.drawing_number}' contains placeholder or invalid syntax.",
                            severity=self.severity,
                            confidence=Confidence(level=ConfidenceLevelEnum.HIGH, score=0.95),
                            page=page.page_number,
                            location=None,
                            evidence=f"Drawing Number: '{tb.drawing_number}'",
                            requirement="Drawing number must be an authentic engineering document number prior to production release.",
                            standard=self.standard,
                            standard_section=self.standard_section,
                            recommendation=self.remediation_guidance,
                        )
                    )
                    finding_seq += 1

        return findings


class RevisionSyntaxRule(BaseRule):
    """RULE-DOC-REV-001: Revision identifiers must avoid prohibited letters (I, O, Q, S, X, Z) per ASME Y14.35M."""

    rule_id = "RULE-DOC-REV-001"
    name = "Drawing Revision Standard Lettering Sequence"
    category = "documentation"
    severity = SeverityEnum.MINOR
    standard = "ASME Y14.35M"
    standard_section = "Section 5.1 (Revision Letters)"
    version = "1.0.0"
    applicability = "All engineering drawing title blocks"
    expected_condition = "Drawing revision must follow ASME Y14.35M permissible lettering sequence."
    remediation_guidance = "Update revision to next permissible ASME letter (skip I, O, Q, S, X, Z)."

    PROHIBITED_LETTERS = {"I", "O", "Q", "S", "X", "Z"}

    def evaluate(self, doc: IntermediateDocumentModel) -> List[QCFinding]:
        if not self.enabled:
            return []
        findings: List[QCFinding] = []
        finding_seq = 1

        for page in doc.pages:
            tb = page.title_block
            if tb and tb.revision:
                rev = tb.revision.strip().upper()
                if len(rev) == 1 and rev in self.PROHIBITED_LETTERS:
                    findings.append(
                        QCFinding(
                            id=f"D-DOC-REV-{doc.document_id[:4]}-{page.page_number}-{finding_seq:03d}",
                            rule_id=self.rule_id,
                            category=self.category,
                            description=(
                                f"Revision letter '{rev}' is prohibited under ASME Y14.35M (letters I, O, Q, S, X, Z "
                                f"are forbidden to avoid visual confusion with digits 1, 0, 8, 2)."
                            ),
                            severity=self.severity,
                            confidence=Confidence(level=ConfidenceLevelEnum.HIGH, score=0.98),
                            page=page.page_number,
                            location=None,
                            evidence=f"Revision: '{tb.revision}'",
                            requirement="Revision sequences must comply with ASME Y14.35M standard letter designations.",
                            standard=self.standard,
                            standard_section=self.standard_section,
                            recommendation=self.remediation_guidance,
                        )
                    )
                    finding_seq += 1

        return findings


# ============================================================================
# CATEGORY 6: CONSISTENCY
# ============================================================================


class GeneralNotesContradictionRule(BaseRule):
    """RULE-CON-NOT-001: Wire callouts must not contradict minimum gauge constraints in General Notes."""

    rule_id = "RULE-CON-NOT-001"
    name = "General Drawing Notes vs Wire Schedule Contradiction"
    category = "consistency"
    severity = SeverityEnum.MAJOR
    standard = "IPC-WHMA-A-620D"
    standard_section = "Section 1.5 (Order of Precedence & Conflicting Requirements)"
    version = "1.0.0"
    applicability = "Schematics containing General Notes and wire schedules"
    expected_condition = "Wire runs must satisfy or exceed minimum constraints declared in General Notes."
    remediation_guidance = "Harmonize wire callout gauge/insulation with General Drawing Note requirements."

    MIN_GAUGE_NOTE_REGEX = re.compile(
        r"(?:MINIMUM\s+WIRE\s+GAUGE|MIN\s+GAUGE|ALL\s+WIRES\s+SHALL\s+BE)\s*:?\s*(\d{1,2})\s*AWG",
        re.IGNORECASE,
    )
    AWG_REGEX = re.compile(r"\b(\d{1,2})\s*AWG\b", re.IGNORECASE)

    def evaluate(self, doc: IntermediateDocumentModel) -> List[QCFinding]:
        if not self.enabled:
            return []
        findings: List[QCFinding] = []
        finding_seq = 1

        for page in doc.pages:
            # Check general notes for minimum wire gauge specification
            min_awg_required: Optional[int] = None
            note_evidence: str = ""

            for note in page.general_notes:
                match = self.MIN_GAUGE_NOTE_REGEX.search(note.text)
                if match:
                    min_awg_required = int(match.group(1))
                    note_evidence = f"Note {note.note_number}: '{note.text}'"
                    break

            if min_awg_required is None:
                continue

            # Verify that no wire is thinner (higher AWG) than the required minimum
            for wire in page.wire_callouts:
                if not wire.gauge:
                    continue
                w_match = self.AWG_REGEX.search(wire.gauge)
                if w_match:
                    wire_awg = int(w_match.group(1))
                    if wire_awg > min_awg_required:
                        findings.append(
                            QCFinding(
                                id=f"D-CON-NOT-{doc.document_id[:4]}-{page.page_number}-{finding_seq:03d}",
                                rule_id=self.rule_id,
                                category=self.category,
                                description=(
                                    f"Wire '{wire.wire_number or wire.raw_text}' gauge {wire.gauge} contradicts General Note "
                                    f"specifying a minimum wire size of {min_awg_required} AWG."
                                ),
                                severity=self.severity,
                                confidence=Confidence(level=ConfidenceLevelEnum.HIGH, score=0.96),
                                page=page.page_number,
                                location=wire.location,
                                evidence=f"Wire: '{wire.raw_text}' vs {note_evidence}",
                                requirement="Wire schedule callouts must conform to drawing general notes or include an explicit exception flag.",
                                standard=self.standard,
                                standard_section=self.standard_section,
                                recommendation=f"Upsize wire to {min_awg_required} AWG or heavier to satisfy General Note specification.",
                            )
                        )
                        finding_seq += 1

        return findings


class WireGaugeContactCompatibilityRule(BaseRule):
    """RULE-CON-CNT-001: Heavy power wire gauges cannot physically fit into miniature signal connectors."""

    rule_id = "RULE-CON-CNT-001"
    name = "Wire Gauge Physical Fit vs Contact Pin Capacity"
    category = "consistency"
    severity = SeverityEnum.CRITICAL
    standard = "IPC-WHMA-A-620D"
    standard_section = "Section 19.5 (Crimp Contact Size Compatibility)"
    version = "1.0.0"
    applicability = "All crimp contact and connector terminations"
    expected_condition = "Conductor wire gauge must be physically compatible with connector contact size."
    remediation_guidance = "Route heavy power conductors through an appropriately sized power connector."

    # Heavy power gauges that cannot physically terminate into miniature signal connectors
    HEAVY_GAUGES = {"4/0 AWG", "3/0 AWG", "2/0 AWG", "1/0 AWG", "2 AWG", "4 AWG", "6 AWG", "8 AWG"}
    # Connectors that only support fine signal wiring (typically 20 AWG to 28 AWG)
    MINIATURE_CONNECTORS = re.compile(
        r"\b(SUB[-_]?D|DB9|DB15|DB25|DB37|RJ45|RJ11|MICRO[-_]?D|HEADER|PICO)\b", re.IGNORECASE
    )

    def evaluate(self, doc: IntermediateDocumentModel) -> List[QCFinding]:
        if not self.enabled:
            return []
        findings: List[QCFinding] = []
        finding_seq = 1

        for page in doc.pages:
            for wire in page.wire_callouts:
                if not wire.gauge:
                    continue
                clean_gauge = wire.gauge.strip().upper()
                if clean_gauge in self.HEAVY_GAUGES:
                    # Check if either endpoint terminates in a miniature connector
                    for ep in [wire.from_connector, wire.to_connector]:
                        if ep and self.MINIATURE_CONNECTORS.search(ep):
                            findings.append(
                                QCFinding(
                                    id=f"D-CON-CNT-{doc.document_id[:4]}-{page.page_number}-{finding_seq:03d}",
                                    rule_id=self.rule_id,
                                    category=self.category,
                                    description=(
                                        f"Heavy power conductor '{wire.wire_number or wire.raw_text}' ({wire.gauge}) "
                                        f"cannot physically terminate into miniature connector '{ep}' (contact crimp barrel limit exceeded)."
                                    ),
                                    severity=self.severity,
                                    confidence=Confidence(level=ConfidenceLevelEnum.HIGH, score=0.99),
                                    page=page.page_number,
                                    location=wire.location,
                                    evidence=f"Gauge: {wire.gauge}, Endpoint: '{ep}'",
                                    requirement="Wire conductor cross-section must physically fit within the connector contact crimp barrel size.",
                                    standard=self.standard,
                                    standard_section=self.standard_section,
                                    recommendation=self.remediation_guidance,
                                )
                            )
                            finding_seq += 1

        return findings


# ============================================================================
# VERSIONED RULE PACKS
# ============================================================================


class RulePack:
    """Container grouping deterministic QC rules under a versioned engineering standard."""

    def __init__(
        self,
        pack_id: str,
        name: str,
        version: str,
        standard: str,
        description: str,
        rules: Optional[List[BaseRule]] = None,
        enabled: bool = True,
    ):
        self.pack_id = pack_id
        self.name = name
        self.version = version
        self.standard = standard
        self.description = description
        self.rules: List[BaseRule] = rules or []
        self.enabled = enabled

    def get_rule_ids(self) -> List[str]:
        return [r.rule_id for r in self.rules]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pack_id": self.pack_id,
            "name": self.name,
            "version": self.version,
            "standard": self.standard,
            "description": self.description,
            "rule_count": len(self.rules),
            "enabled": self.enabled,
            "rules": [r.metadata() for r in self.rules],
        }


def build_default_rule_packs() -> Dict[str, RulePack]:
    """Instantiate and return the suite of standard versioned rule packs."""

    # 1. Core Baseline Pack (Runs by default for regression stability)
    core_pack = RulePack(
        pack_id="PACK-CORE-BASELINE-V1.0",
        name="Core Baseline Engineering QC Ruleset",
        version="1.0.0",
        standard="Multi-Standard Baseline",
        description="Essential baseline checks: missing wire gauge, color ambiguity, duplicate designators, and incomplete title blocks.",
        rules=[
            MissingWireGaugeRule(),
            ColorCodeMismatchRule(),
            DuplicateDesignatorRule(),
            TitleBlockIncompleteRule(),
        ],
    )

    # 2. IPC-WHMA-A-620D Class 3 Pack
    ipc_pack = RulePack(
        pack_id="PACK-IPC-620-V1.0",
        name="IPC-WHMA-A-620D Class 3 Aerospace & High-Reliability Ruleset",
        version="1.0.0",
        standard="IPC-WHMA-A-620D",
        description="Requirements and acceptance for cable and wire harness assemblies (wire rating, terminal completeness, part numbers, dangling references, contact fit).",
        rules=[
            MissingWireGaugeRule(),
            TerminalMissingPartNumberRule(),
            TerminalBlockDesignationRule(),
            DanglingWireReferenceRule(),
            CrossReferenceEndpointRule(),
            GeneralNotesContradictionRule(),
            WireGaugeContactCompatibilityRule(),
        ],
    )

    # 3. UL 508A Industrial Control Panels Pack
    ul_pack = RulePack(
        pack_id="PACK-UL-508A-V1.0",
        name="UL 508A Industrial Control Panel Standards Ruleset",
        version="1.0.0",
        standard="UL 508A",
        description="Safety standard for industrial control panels (wire color coding, protective grounding, conductor ampacity sizing vs circuit breaker rating, terminal clamp capacity, overcurrent protection ratings).",
        rules=[
            ColorCodeMismatchRule(),
            GroundConductorColorRule(),
            WireAmpacitySizingRule(),
            TerminalOvercrowdingRule(),
            OvercurrentDeviceRatingRule(),
        ],
    )

    # 4. ISO 7200 / ASME Y14 Documentation Pack
    iso_pack = RulePack(
        pack_id="PACK-ISO-7200-V1.0",
        name="ISO 7200 / ASME Y14 Engineering Documentation Ruleset",
        version="1.0.0",
        standard="ISO 7200 / ASME Y14",
        description="Technical product documentation title blocks, drawing numbering syntax, and ASME Y14.35M revision lettering control.",
        rules=[
            TitleBlockIncompleteRule(),
            DrawingNumberSyntaxRule(),
            RevisionSyntaxRule(),
        ],
    )

    # 5. MIL-STD-681D Aerospace Wire Identification Pack
    mil_pack = RulePack(
        pack_id="PACK-MIL-STD-681-V1.0",
        name="MIL-STD-681D Aerospace Wire & Cable Identification Ruleset",
        version="1.0.0",
        standard="MIL-STD-681D",
        description="Identification coding and color marking standards for hookup wire and cable assemblies in defense systems.",
        rules=[
            MissingWireGaugeRule(),
            ColorCodeMismatchRule(),
            GroundConductorColorRule(),
        ],
    )

    # 6. Spandsons Horizon Internal Engineering Standard Pack
    spandsons_pack = RulePack(
        pack_id="PACK-SPANDSONS-V1.0",
        name="Spandsons Horizon Engineering Internal QC SOP Ruleset",
        version="1.0.0",
        standard="Spandsons Horizon Internal Engineering Standard",
        description="Internal corporate quality control standard: component designator verification, title block compliance, notes consistency, and drawing integrity.",
        rules=[
            MissingWireGaugeRule(),
            ColorCodeMismatchRule(),
            DuplicateDesignatorRule(),
            TitleBlockIncompleteRule(),
            ComponentDesignatorSyntaxRule(),
            GeneralNotesContradictionRule(),
        ],
    )

    return {
        core_pack.pack_id: core_pack,
        ipc_pack.pack_id: ipc_pack,
        ul_pack.pack_id: ul_pack,
        iso_pack.pack_id: iso_pack,
        mil_pack.pack_id: mil_pack,
        spandsons_pack.pack_id: spandsons_pack,
    }


# ============================================================================
# CENTRAL RULE REGISTRY
# ============================================================================


class RuleRegistry:
    """
    Central registry and execution manager for deterministic QC rules and versioned rule packs.
    Supports granular pack activation, category filtering, standards mapping, and rule toggling.
    """

    def __init__(self, default_active_packs: Optional[List[str]] = None):
        self._packs: Dict[str, RulePack] = build_default_rule_packs()
        self._active_pack_ids: List[str] = default_active_packs or ["PACK-CORE-BASELINE-V1.0"]

        # Cache of all unique rules indexed by rule_id
        self._rules_by_id: Dict[str, BaseRule] = {}
        for pack in self._packs.values():
            for rule in pack.rules:
                if rule.rule_id not in self._rules_by_id:
                    self._rules_by_id[rule.rule_id] = rule

    @property
    def rules(self) -> List[BaseRule]:
        """Return list of all registered rules (maintains backwards compatibility)."""
        return list(self._rules_by_id.values())

    def list_packs(self) -> List[RulePack]:
        """Return all available rule packs."""
        return list(self._packs.values())

    def get_pack(self, pack_id: str) -> Optional[RulePack]:
        """Retrieve a rule pack by its identifier."""
        return self._packs.get(pack_id)

    def register_pack(self, pack: RulePack) -> None:
        """Register a new or custom rule pack."""
        self._packs[pack.pack_id] = pack
        for rule in pack.rules:
            self._rules_by_id[rule.rule_id] = rule

    def set_active_packs(self, pack_ids: List[str]) -> None:
        """Configure which rule packs are active for analysis."""
        self._active_pack_ids = [pid for pid in pack_ids if pid in self._packs]

    def get_active_packs(self) -> List[str]:
        """Return the active rule pack identifiers."""
        return list(self._active_pack_ids)

    def get_rule(self, rule_id: str) -> Optional[BaseRule]:
        """Retrieve a specific rule by ID."""
        return self._rules_by_id.get(rule_id)

    def enable_rule(self, rule_id: str) -> bool:
        """Enable a rule across all registered packs."""
        rule = self._rules_by_id.get(rule_id)
        if rule:
            rule.enabled = True
            return True
        return False

    def disable_rule(self, rule_id: str) -> bool:
        """Disable a rule across all registered packs."""
        rule = self._rules_by_id.get(rule_id)
        if rule:
            rule.enabled = False
            return True
        return False

    def get_rules_by_category(self, category: str) -> List[BaseRule]:
        """Filter registered rules by category (wire, terminal, component, reference, documentation, consistency)."""
        cat_lower = category.lower()
        return [r for r in self._rules_by_id.values() if r.category.lower() == cat_lower]

    def get_rules_by_standard(self, standard_query: str) -> List[BaseRule]:
        """Filter registered rules matching a standard name or keyword."""
        q = standard_query.lower()
        return [r for r in self._rules_by_id.values() if q in r.standard.lower()]

    def run_pack(self, pack_id: str, doc: IntermediateDocumentModel) -> List[QCFinding]:
        """Execute a single specific rule pack against a document."""
        return self.run_all(doc, active_pack_ids=[pack_id])

    def run_packs(self, pack_ids: List[str], doc: IntermediateDocumentModel) -> List[QCFinding]:
        """Execute specific rule packs against a document."""
        return self.run_all(doc, active_pack_ids=pack_ids)

    def run_all(
        self,
        doc: IntermediateDocumentModel,
        active_pack_ids: Optional[List[str]] = None,
        standards: Optional[List[str]] = None,
    ) -> List[QCFinding]:
        """
        Execute deterministic rules against an IDR document.
        Deduplicates rules so that shared rules across packs run only once per document.
        """
        all_findings: List[QCFinding] = []
        rules_to_run: List[BaseRule] = []
        seen_rule_ids: Set[str] = set()

        # Determine target packs
        target_pids = active_pack_ids or self._active_pack_ids

        # If specific pack IDs requested
        if target_pids:
            for pid in target_pids:
                pack = self._packs.get(pid)
                if pack and pack.enabled:
                    for rule in pack.rules:
                        if rule.rule_id not in seen_rule_ids and rule.enabled:
                            rules_to_run.append(rule)
                            seen_rule_ids.add(rule.rule_id)

        # If standards filter specified in addition to or instead of packs
        if standards:
            for std in standards:
                matching_rules = self.get_rules_by_standard(std)
                for rule in matching_rules:
                    if rule.rule_id not in seen_rule_ids and rule.enabled:
                        rules_to_run.append(rule)
                        seen_rule_ids.add(rule.rule_id)

        # Fallback to active packs if no rules matched
        if not rules_to_run:
            for pid in self._active_pack_ids:
                pack = self._packs.get(pid)
                if pack and pack.enabled:
                    for rule in pack.rules:
                        if rule.rule_id not in seen_rule_ids and rule.enabled:
                            rules_to_run.append(rule)
                            seen_rule_ids.add(rule.rule_id)

        for rule in rules_to_run:
            findings = rule.evaluate(doc)
            all_findings.extend(findings)

        return all_findings
