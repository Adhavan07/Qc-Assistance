"""
Curated Gold-Standard Evaluation Dataset for Wiring Diagram QC.
Generates 10 standardized synthetic engineering drawings with ground-truth labels.
"""

import os
from typing import List
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from ..schemas import SeverityEnum
from .metrics import EvaluationTestCase, GroundTruthFinding


class GoldDatasetManager:
    """Manages creation and loading of the Gold Standard Benchmark Dataset."""

    @staticmethod
    def setup_dataset(directory: str) -> List[EvaluationTestCase]:
        """Generate PDF files on disk and return test case definitions."""
        os.makedirs(directory, exist_ok=True)
        test_cases: List[EvaluationTestCase] = []

        # Case 1: Fully Compliant Baseline Harness
        c1_path = os.path.join(directory, "case_01_compliant_baseline.pdf")
        GoldDatasetManager._create_case_01(c1_path)
        test_cases.append(
            EvaluationTestCase(
                case_id="TC-01",
                name="Fully Compliant Baseline Harness",
                description="Drawing with all wire gauges, valid color codes, unique connectors, and complete title block.",
                file_path=c1_path,
                expected_findings=[],
                expected_overall_status="PASS",
            )
        )

        # Case 2: Missing Wire Gauge Callouts
        c2_path = os.path.join(directory, "case_02_missing_wire_gauges.pdf")
        GoldDatasetManager._create_case_02(c2_path)
        test_cases.append(
            EvaluationTestCase(
                case_id="TC-02",
                name="Missing Wire Gauge Callouts",
                description="Diagram with two conductors missing AWG rating (Critical IPC-620 violation).",
                file_path=c2_path,
                expected_findings=[
                    GroundTruthFinding(
                        rule_id="RULE-WG-001",
                        page=1,
                        severity=SeverityEnum.CRITICAL,
                        evidence_keyword="W202",
                        description="Missing wire gauge on W202",
                    ),
                    GroundTruthFinding(
                        rule_id="RULE-WG-001",
                        page=1,
                        severity=SeverityEnum.CRITICAL,
                        evidence_keyword="W203",
                        description="Missing wire gauge on W203",
                    ),
                ],
                expected_overall_status="FAIL",
            )
        )

        # Case 3: Color Code Ambiguity
        c3_path = os.path.join(directory, "case_03_missing_color_codes.pdf")
        GoldDatasetManager._create_case_03(c3_path)
        test_cases.append(
            EvaluationTestCase(
                case_id="TC-03",
                name="Color Code Ambiguity",
                description="Diagram with two conductors lacking insulation color callouts (UL 508A violation).",
                file_path=c3_path,
                expected_findings=[
                    GroundTruthFinding(
                        rule_id="RULE-CC-003",
                        page=1,
                        severity=SeverityEnum.MAJOR,
                        evidence_keyword="W301",
                        description="Missing color on W301",
                    ),
                    GroundTruthFinding(
                        rule_id="RULE-CC-003",
                        page=1,
                        severity=SeverityEnum.MAJOR,
                        evidence_keyword="W302",
                        description="Missing color on W302",
                    ),
                ],
                expected_overall_status="FAIL",
            )
        )

        # Case 4: Duplicate Reference Designator
        c4_path = os.path.join(directory, "case_04_duplicate_refdes.pdf")
        GoldDatasetManager._create_case_04(c4_path)
        test_cases.append(
            EvaluationTestCase(
                case_id="TC-04",
                name="Duplicate Reference Designator",
                description="Multi-page schematic where connector J1 is defined twice (Critical IEEE-200 violation).",
                file_path=c4_path,
                expected_findings=[
                    GroundTruthFinding(
                        rule_id="RULE-RD-004",
                        page=2,
                        severity=SeverityEnum.CRITICAL,
                        evidence_keyword="J1",
                        description="Duplicate connector J1 on Page 2",
                    )
                ],
                expected_overall_status="FAIL",
            )
        )

        # Case 5: Incomplete Title Block
        c5_path = os.path.join(directory, "case_05_incomplete_title_block.pdf")
        GoldDatasetManager._create_case_05(c5_path)
        test_cases.append(
            EvaluationTestCase(
                case_id="TC-05",
                name="Incomplete Title Block",
                description="Drawing missing revision and engineering approval/date fields.",
                file_path=c5_path,
                expected_findings=[
                    GroundTruthFinding(
                        rule_id="RULE-TB-005",
                        page=1,
                        severity=SeverityEnum.MINOR,
                        evidence_keyword="Title Block",
                        description="Incomplete title block control fields",
                    )
                ],
                expected_overall_status="REVIEW_REQUIRED",
            )
        )

        # Case 6: Mixed Multi-Defect Industrial Panel
        c6_path = os.path.join(directory, "case_06_mixed_industrial_panel.pdf")
        GoldDatasetManager._create_case_06(c6_path)
        test_cases.append(
            EvaluationTestCase(
                case_id="TC-06",
                name="Mixed Multi-Defect Industrial Panel",
                description="Industrial panel schematic with 1 missing gauge, 1 missing color, and incomplete title block.",
                file_path=c6_path,
                expected_findings=[
                    GroundTruthFinding(
                        rule_id="RULE-WG-001",
                        page=1,
                        severity=SeverityEnum.CRITICAL,
                        evidence_keyword="W602",
                        description="Missing gauge on W602",
                    ),
                    GroundTruthFinding(
                        rule_id="RULE-CC-003",
                        page=1,
                        severity=SeverityEnum.MAJOR,
                        evidence_keyword="W603",
                        description="Missing color on W603",
                    ),
                    GroundTruthFinding(
                        rule_id="RULE-TB-005",
                        page=1,
                        severity=SeverityEnum.MINOR,
                        evidence_keyword="Title Block",
                        description="Missing title block date",
                    ),
                ],
                expected_overall_status="FAIL",
            )
        )

        # Case 7: Clean Power Distribution Assembly
        c7_path = os.path.join(directory, "case_07_clean_power_dist.pdf")
        GoldDatasetManager._create_case_07(c7_path)
        test_cases.append(
            EvaluationTestCase(
                case_id="TC-07",
                name="Clean Power Distribution Assembly",
                description="High-current 3-phase wiring drawing with heavy gauge conductors (4/0 AWG, 2 AWG).",
                file_path=c7_path,
                expected_findings=[],
                expected_overall_status="PASS",
            )
        )

        # Case 8: Terminal Strip Assembly with Single Unspecified Wire
        c8_path = os.path.join(directory, "case_08_terminal_strip.pdf")
        GoldDatasetManager._create_case_08(c8_path)
        test_cases.append(
            EvaluationTestCase(
                case_id="TC-08",
                name="Terminal Strip Harness",
                description="Terminal block harness with one unrated jumper wire.",
                file_path=c8_path,
                expected_findings=[
                    GroundTruthFinding(
                        rule_id="RULE-WG-001",
                        page=1,
                        severity=SeverityEnum.CRITICAL,
                        evidence_keyword="W804",
                        description="Missing gauge on jumper W804",
                    )
                ],
                expected_overall_status="FAIL",
            )
        )

        # Case 9: Multi-Page Wiring Package
        c9_path = os.path.join(directory, "case_09_multipage_package.pdf")
        GoldDatasetManager._create_case_09(c9_path)
        test_cases.append(
            EvaluationTestCase(
                case_id="TC-09",
                name="Multi-Page Wiring Package",
                description="3-page drawing package with defects distributed on page 2 and page 3.",
                file_path=c9_path,
                expected_findings=[
                    GroundTruthFinding(
                        rule_id="RULE-CC-003",
                        page=2,
                        severity=SeverityEnum.MAJOR,
                        evidence_keyword="W902",
                        description="Missing color on page 2",
                    ),
                    GroundTruthFinding(
                        rule_id="RULE-WG-001",
                        page=3,
                        severity=SeverityEnum.CRITICAL,
                        evidence_keyword="W903",
                        description="Missing gauge on page 3",
                    ),
                ],
                expected_overall_status="FAIL",
            )
        )

        # Case 10: Fully Annotated Clean Harness with Metric Gauges
        c10_path = os.path.join(directory, "case_10_metric_gauges.pdf")
        GoldDatasetManager._create_case_10(c10_path)
        test_cases.append(
            EvaluationTestCase(
                case_id="TC-10",
                name="Metric Gauge Compliant Harness",
                description="Automotive wiring schematic utilizing metric mm2 cross-sections (0.75 mm2, 1.5 mm2).",
                file_path=c10_path,
                expected_findings=[],
                expected_overall_status="PASS",
            )
        )

        return test_cases

    # --- PDF Creation Helpers ---

    @staticmethod
    def _create_case_01(path: str):
        c = canvas.Canvas(path, pagesize=letter)
        c.drawString(400, 50, "TITLE: MAIN ENGINE HARNESS")
        c.drawString(400, 35, "DWG NO: WD-1001-A")
        c.drawString(400, 20, "REV: B")
        c.drawString(400, 5, "DRAWN BY: J. Smith")
        c.drawString(250, 5, "DATE: 2026-01-15")
        c.drawString(72, 700, "W101 18 AWG RED (J1-P1)")
        c.drawString(72, 680, "W102 20 AWG BLK (J1-P2)")
        c.drawString(72, 660, "W103 22 AWG WHT/BLU (TB1-P3)")
        c.drawString(72, 550, "CONNECTORS: J1 (MS3106A), P1, P2, P3, TB1")
        c.drawString(72, 450, "NOTES: 1. ALL WIRES PER MIL-W-22759.")
        c.save()

    @staticmethod
    def _create_case_02(path: str):
        c = canvas.Canvas(path, pagesize=letter)
        c.drawString(400, 50, "TITLE: SENSOR INTERFACE HARNESS")
        c.drawString(400, 35, "DWG NO: WD-2002-B")
        c.drawString(400, 20, "REV: A")
        c.drawString(400, 5, "DRAWN BY: A. Patel")
        c.drawString(250, 5, "DATE: 2026-02-10")
        c.drawString(72, 700, "W201 18 AWG RED (J1-P1)")
        c.drawString(72, 680, "W202 BLK (J1-P2)")  # Missing gauge
        c.drawString(72, 660, "W203 BLU (TB1-P3)")  # Missing gauge
        c.drawString(72, 550, "CONNECTORS: J1, P1, P2, P3, TB1")
        c.save()

    @staticmethod
    def _create_case_03(path: str):
        c = canvas.Canvas(path, pagesize=letter)
        c.drawString(400, 50, "TITLE: POWER SUPPLY LOOM")
        c.drawString(400, 35, "DWG NO: WD-3003-C")
        c.drawString(400, 20, "REV: C")
        c.drawString(400, 5, "DRAWN BY: C. Davis")
        c.drawString(250, 5, "DATE: 2026-03-01")
        c.drawString(72, 700, "W301 16 AWG (J1-P1)")  # Missing color
        c.drawString(72, 680, "W302 18 AWG (J1-P2)")  # Missing color
        c.drawString(72, 660, "W303 22 AWG BLK (TB1-P3)")
        c.drawString(72, 550, "CONNECTORS: J1, P1, P2, P3, TB1")
        c.save()

    @staticmethod
    def _create_case_04(path: str):
        c = canvas.Canvas(path, pagesize=letter)
        # Page 1
        c.drawString(400, 50, "TITLE: RELAY DISTRIBUTION UNIT (SHEET 1)")
        c.drawString(400, 35, "DWG NO: WD-4004-D")
        c.drawString(400, 20, "REV: A")
        c.drawString(400, 5, "DRAWN BY: R. Ray")
        c.drawString(250, 5, "DATE: 2026-04-01")
        c.drawString(72, 700, "W401 18 AWG RED (J1-P1)")
        c.drawString(72, 550, "CONNECTORS: J1 (MIL-SPEC-20), P1")
        c.showPage()
        # Page 2
        c.drawString(400, 50, "TITLE: RELAY DISTRIBUTION UNIT (SHEET 2)")
        c.drawString(400, 35, "DWG NO: WD-4004-D")
        c.drawString(400, 20, "REV: A")
        c.drawString(400, 5, "DRAWN BY: R. Ray")
        c.drawString(250, 5, "DATE: 2026-04-01")
        c.drawString(72, 700, "W402 18 AWG BLK (J1-P2)")
        c.drawString(72, 550, "CONNECTORS: J1 (SUB-D-9), P2")  # Duplicate J1!
        c.save()

    @staticmethod
    def _create_case_05(path: str):
        c = canvas.Canvas(path, pagesize=letter)
        # Missing REV and DATE intentionally
        c.drawString(400, 50, "TITLE: CABLING SYSTEM")
        c.drawString(400, 35, "DWG NO: WD-5005-E")
        c.drawString(400, 5, "DRAWN BY: E. Zhang")
        c.drawString(72, 700, "W501 18 AWG RED (J1-P1)")
        c.drawString(72, 550, "CONNECTORS: J1, P1")
        c.save()

    @staticmethod
    def _create_case_06(path: str):
        c = canvas.Canvas(path, pagesize=letter)
        # Incomplete title block (missing Date)
        c.drawString(400, 50, "TITLE: INDUSTRIAL CONTROL CABINET")
        c.drawString(400, 35, "DWG NO: WD-6006-F")
        c.drawString(400, 20, "REV: B")
        c.drawString(400, 5, "DRAWN BY: F. Gomez")
        # Wires with defects
        c.drawString(72, 700, "W601 14 AWG RED (TB1-P1)")
        c.drawString(72, 680, "W602 BLK (TB1-P2)")  # Missing gauge
        c.drawString(72, 660, "W603 18 AWG (TB1-P3)")  # Missing color
        c.drawString(72, 550, "CONNECTORS: TB1, P1, P2, P3")
        c.save()

    @staticmethod
    def _create_case_07(path: str):
        c = canvas.Canvas(path, pagesize=letter)
        c.drawString(400, 50, "TITLE: 3-PHASE POWER FEEDER")
        c.drawString(400, 35, "DWG NO: WD-7007-G")
        c.drawString(400, 20, "REV: 1")
        c.drawString(400, 5, "DRAWN BY: G. Lee")
        c.drawString(250, 5, "DATE: 2026-05-15")
        c.drawString(72, 700, "W701 4/0 AWG RED (SW1-TB1)")
        c.drawString(72, 680, "W702 4/0 AWG BLK (SW1-TB1)")
        c.drawString(72, 660, "W703 4/0 AWG BLU (SW1-TB1)")
        c.drawString(72, 640, "W704 2 AWG GRN/YEL (SW1-GND1)")
        c.drawString(72, 550, "CONNECTORS: SW1, TB1")
        c.save()

    @staticmethod
    def _create_case_08(path: str):
        c = canvas.Canvas(path, pagesize=letter)
        c.drawString(400, 50, "TITLE: AUTOMATION JUNCTION BOX")
        c.drawString(400, 35, "DWG NO: WD-8008-H")
        c.drawString(400, 20, "REV: A")
        c.drawString(400, 5, "DRAWN BY: H. White")
        c.drawString(250, 5, "DATE: 2026-06-01")
        c.drawString(72, 700, "W801 18 AWG RED (TB1-TB2)")
        c.drawString(72, 680, "W802 18 AWG BLK (TB1-TB2)")
        c.drawString(72, 660, "W803 18 AWG BLU (TB1-TB2)")
        c.drawString(72, 640, "W804 ORN (TB1-TB2)")  # Missing gauge
        c.drawString(72, 550, "CONNECTORS: TB1, TB2")
        c.save()

    @staticmethod
    def _create_case_09(path: str):
        c = canvas.Canvas(path, pagesize=letter)
        # Page 1 - Clean
        c.drawString(400, 50, "TITLE: RADAR HARNESS (SHEET 1)")
        c.drawString(400, 35, "DWG NO: WD-9009-I")
        c.drawString(400, 20, "REV: D")
        c.drawString(400, 5, "DRAWN BY: I. Novak")
        c.drawString(250, 5, "DATE: 2026-07-04")
        c.drawString(72, 700, "W901 20 AWG RED (J1-P1)")
        c.drawString(72, 550, "CONNECTORS: J1, P1")
        c.showPage()
        # Page 2 - Missing color
        c.drawString(400, 50, "TITLE: RADAR HARNESS (SHEET 2)")
        c.drawString(400, 35, "DWG NO: WD-9009-I")
        c.drawString(400, 20, "REV: D")
        c.drawString(400, 5, "DRAWN BY: I. Novak")
        c.drawString(250, 5, "DATE: 2026-07-04")
        c.drawString(72, 700, "W902 22 AWG (J2-P2)")  # Missing color
        c.drawString(72, 550, "CONNECTORS: J2, P2")
        c.showPage()
        # Page 3 - Missing gauge
        c.drawString(400, 50, "TITLE: RADAR HARNESS (SHEET 3)")
        c.drawString(400, 35, "DWG NO: WD-9009-I")
        c.drawString(400, 20, "REV: D")
        c.drawString(400, 5, "DRAWN BY: I. Novak")
        c.drawString(250, 5, "DATE: 2026-07-04")
        c.drawString(72, 700, "W903 BLK (J3-P3)")  # Missing gauge
        c.drawString(72, 550, "CONNECTORS: J3, P3")
        c.save()

    @staticmethod
    def _create_case_10(path: str):
        c = canvas.Canvas(path, pagesize=letter)
        c.drawString(400, 50, "TITLE: METRIC CHASSIS HARNESS")
        c.drawString(400, 35, "DWG NO: WD-1010-J")
        c.drawString(400, 20, "REV: 2")
        c.drawString(400, 5, "DRAWN BY: J. Tanaka")
        c.drawString(250, 5, "DATE: 2026-08-12")
        c.drawString(72, 700, "W1001 0.75 mm2 RED (J1-P1)")
        c.drawString(72, 680, "W1002 1.5 mm2 BLK (J1-P2)")
        c.drawString(72, 660, "W1003 2.5 mm2 GRN/YEL (J1-GND1)")
        c.drawString(72, 550, "CONNECTORS: J1, P1, P2")
        c.save()
