"""
Unit tests for deterministic QC rules and versioned rule packs.
Verifies all 6 mandatory rule categories (wire, terminal, component, reference, documentation, consistency)
and validates rule pack management, toggling, and standards mapping.
"""

import pytest

from backend.src.ai.schemas import (
    BoundingBox,
    Connector,
    DocumentPage,
    GeneralNote,
    IntermediateDocumentModel,
    SeverityEnum,
    TitleBlock,
    WireCallout,
)
from backend.src.ai.rules import (
    ColorCodeMismatchRule,
    ComponentDesignatorSyntaxRule,
    CrossReferenceEndpointRule,
    DanglingWireReferenceRule,
    DrawingNumberSyntaxRule,
    DuplicateDesignatorRule,
    GeneralNotesContradictionRule,
    GroundConductorColorRule,
    MissingWireGaugeRule,
    OvercurrentDeviceRatingRule,
    RevisionSyntaxRule,
    RulePack,
    RuleRegistry,
    TerminalBlockDesignationRule,
    TerminalMissingPartNumberRule,
    TerminalOvercrowdingRule,
    TitleBlockIncompleteRule,
    WireAmpacitySizingRule,
    WireGaugeContactCompatibilityRule,
)


# ============================================================================
# CATEGORY 1: WIRE TESTS
# ============================================================================


def test_missing_wire_gauge_detection():
    doc = IntermediateDocumentModel(
        document_id="doc_wire_gauge",
        filename="schematic.pdf",
        page_count=1,
        pages=[
            DocumentPage(
                page_number=1,
                width=1000,
                height=800,
                wire_callouts=[
                    WireCallout(id="w1", wire_number="W101", gauge=None, color="RED", raw_text="W101 RED"),
                    WireCallout(id="w2", wire_number="W102", gauge="18 AWG", color="BLK", raw_text="W102 18AWG BLK"),
                ],
            )
        ],
    )
    rule = MissingWireGaugeRule()
    findings = rule.evaluate(doc)
    assert len(findings) == 1
    assert findings[0].rule_id == "RULE-WG-001"
    assert findings[0].severity == SeverityEnum.CRITICAL
    assert findings[0].category == "wire"
    assert "W101" in findings[0].description


def test_color_code_ambiguity_detection():
    doc = IntermediateDocumentModel(
        document_id="doc_color_code",
        filename="schematic.pdf",
        page_count=1,
        pages=[
            DocumentPage(
                page_number=1,
                width=1000,
                height=800,
                wire_callouts=[
                    WireCallout(id="w1", wire_number="W101", gauge="18 AWG", color=None, raw_text="W101 18AWG"),
                    WireCallout(id="w2", wire_number="W102", gauge="20 AWG", color="BLU", raw_text="W102 20AWG BLU"),
                ],
            )
        ],
    )
    rule = ColorCodeMismatchRule()
    findings = rule.evaluate(doc)
    assert len(findings) == 1
    assert findings[0].rule_id == "RULE-CC-003"
    assert findings[0].severity == SeverityEnum.MAJOR
    assert findings[0].category == "wire"


def test_ground_conductor_color_compliance():
    doc = IntermediateDocumentModel(
        document_id="doc_ground_color",
        filename="schematic.pdf",
        page_count=1,
        pages=[
            DocumentPage(
                page_number=1,
                width=1000,
                height=800,
                wire_callouts=[
                    # Violation: Ground conductor labeled RED
                    WireCallout(
                        id="w1",
                        wire_number="W_PE_01",
                        gauge="14 AWG",
                        color="RED",
                        from_connector="TB1-1",
                        to_connector="GND1",
                        raw_text="W_PE_01 14AWG RED (TB1-1 to GND1)",
                    ),
                    # Compliant: Ground conductor labeled GRN/YEL
                    WireCallout(
                        id="w2",
                        wire_number="W_PE_02",
                        gauge="14 AWG",
                        color="GRN/YEL",
                        from_connector="TB1-2",
                        to_connector="GND1",
                        raw_text="W_PE_02 14AWG GRN/YEL (TB1-2 to GND1)",
                    ),
                ],
            )
        ],
    )
    rule = GroundConductorColorRule()
    findings = rule.evaluate(doc)
    assert len(findings) == 1
    assert findings[0].rule_id == "RULE-WIRE-GND-001"
    assert findings[0].severity == SeverityEnum.CRITICAL
    assert findings[0].category == "wire"
    assert "W_PE_01" in findings[0].description


def test_wire_ampacity_sizing_detection():
    doc = IntermediateDocumentModel(
        document_id="doc_ampacity",
        filename="schematic.pdf",
        page_count=1,
        pages=[
            DocumentPage(
                page_number=1,
                width=1000,
                height=800,
                wire_callouts=[
                    # Violation: 18 AWG wire on 20A circuit breaker (12 AWG minimum required by UL 508A Table 28.1)
                    WireCallout(
                        id="w1",
                        wire_number="W101",
                        gauge="18 AWG",
                        color="BLK",
                        raw_text="W101 18 AWG BLK (CB1 20A FEED)",
                    ),
                    # Compliant: 12 AWG wire on 20A circuit
                    WireCallout(
                        id="w2",
                        wire_number="W102",
                        gauge="12 AWG",
                        color="BLK",
                        raw_text="W102 12 AWG BLK (CB2 20A FEED)",
                    ),
                ],
            )
        ],
    )
    rule = WireAmpacitySizingRule()
    findings = rule.evaluate(doc)
    assert len(findings) == 1
    assert findings[0].rule_id == "RULE-WIRE-AMP-001"
    assert findings[0].severity == SeverityEnum.CRITICAL
    assert "undersized" in findings[0].description
    assert "20A" in findings[0].description


# ============================================================================
# CATEGORY 2: TERMINAL TESTS
# ============================================================================


def test_terminal_missing_part_number():
    doc = IntermediateDocumentModel(
        document_id="doc_trm_mpn",
        filename="schematic.pdf",
        page_count=1,
        pages=[
            DocumentPage(
                page_number=1,
                width=1000,
                height=800,
                connectors=[
                    Connector(id="c1", ref_des="TB1", part_number=None),  # Missing MPN!
                    Connector(id="c2", ref_des="J1", part_number="MS3106A-20-4P"),
                ],
            )
        ],
    )
    rule = TerminalMissingPartNumberRule()
    findings = rule.evaluate(doc)
    assert len(findings) == 1
    assert findings[0].rule_id == "RULE-TRM-MPN-001"
    assert findings[0].severity == SeverityEnum.MAJOR
    assert findings[0].category == "terminal"
    assert "TB1" in findings[0].description


def test_terminal_block_designation_completeness():
    doc = IntermediateDocumentModel(
        document_id="doc_trm_pin",
        filename="schematic.pdf",
        page_count=1,
        pages=[
            DocumentPage(
                page_number=1,
                width=1000,
                height=800,
                wire_callouts=[
                    # Bare TB1 used by multiple wires without position qualifiers
                    WireCallout(id="w1", wire_number="W101", from_connector="TB1", to_connector="P1-1", raw_text="W101 (TB1-P1-1)"),
                    WireCallout(id="w2", wire_number="W102", from_connector="TB1", to_connector="P1-2", raw_text="W102 (TB1-P1-2)"),
                ],
            )
        ],
    )
    rule = TerminalBlockDesignationRule()
    findings = rule.evaluate(doc)
    assert len(findings) == 1
    assert findings[0].rule_id == "RULE-TRM-PIN-001"
    assert findings[0].severity == SeverityEnum.MAJOR
    assert findings[0].category == "terminal"
    assert "TB1" in findings[0].description


def test_terminal_overcrowding_detection():
    doc = IntermediateDocumentModel(
        document_id="doc_trm_crw",
        filename="schematic.pdf",
        page_count=1,
        pages=[
            DocumentPage(
                page_number=1,
                width=1000,
                height=800,
                wire_callouts=[
                    # 3 wires terminating under identical screw terminal TB1-1 (UL 508A limits to 2 max)
                    WireCallout(id="w1", wire_number="W101", from_connector="TB1-1", to_connector="J1-1", raw_text="W101"),
                    WireCallout(id="w2", wire_number="W102", from_connector="TB1-1", to_connector="J1-2", raw_text="W102"),
                    WireCallout(id="w3", wire_number="W103", from_connector="TB1-1", to_connector="J1-3", raw_text="W103"),
                ],
            )
        ],
    )
    rule = TerminalOvercrowdingRule()
    findings = rule.evaluate(doc)
    assert len(findings) == 1
    assert findings[0].rule_id == "RULE-TRM-CRW-001"
    assert findings[0].severity == SeverityEnum.MAJOR
    assert "TB1-1" in findings[0].description
    assert "3 conductors" in findings[0].description


# ============================================================================
# CATEGORY 3: COMPONENT TESTS
# ============================================================================


def test_component_designator_syntax():
    doc = IntermediateDocumentModel(
        document_id="doc_cmp_syn",
        filename="schematic.pdf",
        page_count=1,
        pages=[
            DocumentPage(
                page_number=1,
                width=1000,
                height=800,
                connectors=[
                    Connector(id="c1", ref_des="DEV99", part_number="ACME-100"),  # Non-standard prefix "DEV"
                    Connector(id="c2", ref_des="J1", part_number="MS3106A"),       # Standard IEEE "J"
                    Connector(id="c3", ref_des="TB1", part_number="WAGO-2002"),    # Standard IEEE "TB"
                ],
            )
        ],
    )
    rule = ComponentDesignatorSyntaxRule()
    findings = rule.evaluate(doc)
    assert len(findings) == 1
    assert findings[0].rule_id == "RULE-CMP-SYN-001"
    assert findings[0].severity == SeverityEnum.MAJOR
    assert findings[0].category == "component"
    assert "DEV99" in findings[0].description


def test_overcurrent_device_rating_detection():
    doc = IntermediateDocumentModel(
        document_id="doc_cmp_ocp",
        filename="schematic.pdf",
        page_count=1,
        pages=[
            DocumentPage(
                page_number=1,
                width=1000,
                height=800,
                raw_text_blocks=[
                    "MAIN POWER FEED: 3-PHASE 480VAC",
                    "CB1 BRANCH BREAKER",  # Missing rating like 15A or 20A!
                    "F1 CONTROL FUSE 2A 250V",  # Compliant: 2A declared
                ],
            )
        ],
    )
    rule = OvercurrentDeviceRatingRule()
    findings = rule.evaluate(doc)
    assert len(findings) == 1
    assert findings[0].rule_id == "RULE-CMP-OCP-001"
    assert findings[0].severity == SeverityEnum.CRITICAL
    assert findings[0].category == "component"
    assert "CB1" in findings[0].description


# ============================================================================
# CATEGORY 4: REFERENCE TESTS
# ============================================================================


def test_duplicate_reference_designator_detection():
    doc = IntermediateDocumentModel(
        document_id="doc_rd",
        filename="schematic.pdf",
        page_count=2,
        pages=[
            DocumentPage(
                page_number=1,
                width=1000,
                height=800,
                connectors=[Connector(id="c1", ref_des="J1", part_number="MS3106")],
            ),
            DocumentPage(
                page_number=2,
                width=1000,
                height=800,
                connectors=[Connector(id="c2", ref_des="J1", part_number="AMP-1234")],  # Duplicate J1!
            ),
        ],
    )
    rule = DuplicateDesignatorRule()
    findings = rule.evaluate(doc)
    assert len(findings) == 1
    assert findings[0].rule_id == "RULE-RD-004"
    assert findings[0].severity == SeverityEnum.CRITICAL
    assert findings[0].category == "reference"
    assert "Duplicate reference designator 'J1'" in findings[0].description


def test_dangling_wire_reference_detection():
    doc = IntermediateDocumentModel(
        document_id="doc_dangling",
        filename="schematic.pdf",
        page_count=1,
        pages=[
            DocumentPage(
                page_number=1,
                width=1000,
                height=800,
                wire_callouts=[
                    # Dangling: has from_connector but missing to_connector and not marked spare
                    WireCallout(
                        id="w1",
                        wire_number="W101",
                        from_connector="J1-1",
                        to_connector=None,
                        raw_text="W101 20 AWG RED (FROM J1-1)",
                    ),
                    # Compliant: un-terminated wire explicitly marked as SPARE CAPPED
                    WireCallout(
                        id="w2",
                        wire_number="W102",
                        from_connector="J1-2",
                        to_connector=None,
                        raw_text="W102 20 AWG BLK (FROM J1-2 SPARE CAPPED)",
                    ),
                ],
            )
        ],
    )
    rule = DanglingWireReferenceRule()
    findings = rule.evaluate(doc)
    assert len(findings) == 1
    assert findings[0].rule_id == "RULE-REF-DNG-001"
    assert findings[0].severity == SeverityEnum.MAJOR
    assert findings[0].category == "reference"
    assert "W101" in findings[0].description


def test_cross_reference_endpoint_resolution():
    doc = IntermediateDocumentModel(
        document_id="doc_xrf",
        filename="schematic.pdf",
        page_count=1,
        pages=[
            DocumentPage(
                page_number=1,
                width=1000,
                height=800,
                connectors=[
                    Connector(id="c1", ref_des="J1", part_number="MS3106A"),
                    Connector(id="c2", ref_des="P1", part_number="MS3102A"),
                ],
                wire_callouts=[
                    # Endpoint J99 does not exist in declared connectors
                    WireCallout(
                        id="w1",
                        wire_number="W101",
                        from_connector="J1-1",
                        to_connector="J99-1",
                        raw_text="W101 20 AWG RED (J1-1 to J99-1)",
                    ),
                    # Endpoint P1-1 exists
                    WireCallout(
                        id="w2",
                        wire_number="W102",
                        from_connector="J1-2",
                        to_connector="P1-1",
                        raw_text="W102 20 AWG BLK (J1-2 to P1-1)",
                    ),
                ],
            )
        ],
    )
    rule = CrossReferenceEndpointRule()
    findings = rule.evaluate(doc)
    assert len(findings) == 1
    assert findings[0].rule_id == "RULE-REF-XRF-001"
    assert findings[0].severity == SeverityEnum.CRITICAL
    assert findings[0].category == "reference"
    assert "J99" in findings[0].description


# ============================================================================
# CATEGORY 5: DOCUMENTATION TESTS
# ============================================================================


def test_title_block_incomplete_detection():
    doc = IntermediateDocumentModel(
        document_id="doc_tb",
        filename="schematic.pdf",
        page_count=1,
        pages=[
            DocumentPage(
                page_number=1,
                width=1000,
                height=800,
                title_block=TitleBlock(
                    drawing_number=None,  # Missing drawing number!
                    revision="A",
                    drawn_by="Engineer A",
                    date="2026-08-01",
                ),
            )
        ],
    )
    rule = TitleBlockIncompleteRule()
    findings = rule.evaluate(doc)
    assert len(findings) == 1
    assert findings[0].rule_id == "RULE-TB-005"
    assert findings[0].category == "documentation"
    assert "Drawing Number" in findings[0].description


def test_drawing_number_syntax_validation():
    doc = IntermediateDocumentModel(
        document_id="doc_dwg_num",
        filename="schematic.pdf",
        page_count=1,
        pages=[
            DocumentPage(
                page_number=1,
                width=1000,
                height=800,
                title_block=TitleBlock(
                    drawing_number="DRAFT",  # Placeholder!
                    revision="A",
                    drawn_by="Engineer A",
                    date="2026-08-01",
                ),
            )
        ],
    )
    rule = DrawingNumberSyntaxRule()
    findings = rule.evaluate(doc)
    assert len(findings) == 1
    assert findings[0].rule_id == "RULE-DOC-NUM-001"
    assert findings[0].severity == SeverityEnum.MINOR
    assert findings[0].category == "documentation"
    assert "placeholder" in findings[0].description


def test_revision_syntax_asme_prohibited_letters():
    doc = IntermediateDocumentModel(
        document_id="doc_rev_syntax",
        filename="schematic.pdf",
        page_count=1,
        pages=[
            DocumentPage(
                page_number=1,
                width=1000,
                height=800,
                title_block=TitleBlock(
                    drawing_number="WD-1001-A",
                    revision="I",  # Prohibited letter 'I' per ASME Y14.35M
                    drawn_by="Engineer A",
                    date="2026-08-01",
                ),
            )
        ],
    )
    rule = RevisionSyntaxRule()
    findings = rule.evaluate(doc)
    assert len(findings) == 1
    assert findings[0].rule_id == "RULE-DOC-REV-001"
    assert findings[0].severity == SeverityEnum.MINOR
    assert findings[0].category == "documentation"
    assert "ASME Y14.35M" in findings[0].description


# ============================================================================
# CATEGORY 6: CONSISTENCY TESTS
# ============================================================================


def test_general_notes_contradiction_detection():
    doc = IntermediateDocumentModel(
        document_id="doc_notes_con",
        filename="schematic.pdf",
        page_count=1,
        pages=[
            DocumentPage(
                page_number=1,
                width=1000,
                height=800,
                general_notes=[
                    GeneralNote(note_number=1, text="MINIMUM WIRE GAUGE: 18 AWG."),
                    GeneralNote(note_number=2, text="ALL HARNESS BUNDLES TO BE LACED."),
                ],
                wire_callouts=[
                    # Violation: 24 AWG is thinner than required 18 AWG
                    WireCallout(id="w1", wire_number="W101", gauge="24 AWG", color="RED", raw_text="W101 24 AWG RED"),
                    # Compliant: 16 AWG is heavier than 18 AWG
                    WireCallout(id="w2", wire_number="W102", gauge="16 AWG", color="BLK", raw_text="W102 16 AWG BLK"),
                ],
            )
        ],
    )
    rule = GeneralNotesContradictionRule()
    findings = rule.evaluate(doc)
    assert len(findings) == 1
    assert findings[0].rule_id == "RULE-CON-NOT-001"
    assert findings[0].severity == SeverityEnum.MAJOR
    assert findings[0].category == "consistency"
    assert "contradicts General Note" in findings[0].description


def test_wire_gauge_contact_compatibility():
    doc = IntermediateDocumentModel(
        document_id="doc_gauge_compat",
        filename="schematic.pdf",
        page_count=1,
        pages=[
            DocumentPage(
                page_number=1,
                width=1000,
                height=800,
                wire_callouts=[
                    # Violation: Heavy power 4/0 AWG conductor attempting to terminate into DB9 signal connector
                    WireCallout(
                        id="w1",
                        wire_number="W101",
                        gauge="4/0 AWG",
                        color="RED",
                        from_connector="CB1",
                        to_connector="DB9-1",
                        raw_text="W101 4/0 AWG RED (CB1 to DB9-1)",
                    ),
                    # Compliant: 22 AWG into DB9
                    WireCallout(
                        id="w2",
                        wire_number="W102",
                        gauge="22 AWG",
                        color="BLU",
                        from_connector="J1-1",
                        to_connector="DB9-2",
                        raw_text="W102 22 AWG BLU (J1-1 to DB9-2)",
                    ),
                ],
            )
        ],
    )
    rule = WireGaugeContactCompatibilityRule()
    findings = rule.evaluate(doc)
    assert len(findings) == 1
    assert findings[0].rule_id == "RULE-CON-CNT-001"
    assert findings[0].severity == SeverityEnum.CRITICAL
    assert findings[0].category == "consistency"
    assert "DB9-1" in findings[0].description


# ============================================================================
# RULE PACKS & REGISTRY SYSTEM TESTS
# ============================================================================


def test_rule_registry_packs_and_categories():
    registry = RuleRegistry()

    # Verify rule packs availability
    packs = registry.list_packs()
    pack_ids = {p.pack_id for p in packs}
    expected_packs = {
        "PACK-CORE-BASELINE-V1.0",
        "PACK-IPC-620-V1.0",
        "PACK-UL-508A-V1.0",
        "PACK-ISO-7200-V1.0",
        "PACK-MIL-STD-681-V1.0",
        "PACK-SPANDSONS-V1.0",
    }
    assert expected_packs.issubset(pack_ids)

    # Verify all 6 mandatory categories have registered rules
    categories = ["wire", "terminal", "component", "reference", "documentation", "consistency"]
    for cat in categories:
        rules_in_cat = registry.get_rules_by_category(cat)
        assert len(rules_in_cat) > 0, f"Category '{cat}' has no registered rules!"

    # Verify total unique registered rules
    assert len(registry.rules) >= 15


def test_rule_pack_execution_and_filtering():
    doc = IntermediateDocumentModel(
        document_id="doc_pack_run",
        filename="test.pdf",
        page_count=1,
        pages=[
            DocumentPage(
                page_number=1,
                width=1000,
                height=800,
                title_block=TitleBlock(drawing_number="DRAFT", revision="X", drawn_by=None, date=None),
            )
        ],
    )
    registry = RuleRegistry()

    # Run only ISO 7200 pack
    iso_findings = registry.run_pack("PACK-ISO-7200-V1.0", doc)
    rule_ids = {f.rule_id for f in iso_findings}

    # Should find missing fields, DRAFT placeholder, and prohibited revision letter X
    assert "RULE-TB-005" in rule_ids
    assert "RULE-DOC-NUM-001" in rule_ids
    assert "RULE-DOC-REV-001" in rule_ids


def test_rule_toggling_enable_disable():
    registry = RuleRegistry()
    rule_id = "RULE-WG-001"

    # Disable rule
    assert registry.disable_rule(rule_id) is True
    rule = registry.get_rule(rule_id)
    assert rule.enabled is False

    doc = IntermediateDocumentModel(
        document_id="doc_disabled",
        filename="test.pdf",
        page_count=1,
        pages=[
            DocumentPage(
                page_number=1,
                width=1000,
                height=800,
                title_block=TitleBlock(drawing_number="WD-100", revision="A", drawn_by="Eng", date="2026-01-01"),
                wire_callouts=[WireCallout(id="w1", wire_number="W1", gauge=None, color="RED", raw_text="W1 RED")],
            )
        ],
    )
    # With rule disabled, it should return 0 findings
    findings = registry.run_all(doc)
    assert len(findings) == 0

    # Re-enable rule
    assert registry.enable_rule(rule_id) is True
    assert rule.enabled is True
    findings = registry.run_all(doc)
    assert len(findings) == 1


def test_rule_metadata_completeness():
    registry = RuleRegistry()
    for rule in registry.rules:
        meta = rule.metadata()
        assert meta["rule_id"]
        assert meta["name"]
        assert meta["category"] in {"wire", "terminal", "component", "reference", "documentation", "consistency"}
        assert meta["severity"] in {"CRITICAL", "MAJOR", "MINOR", "INFO"}
        assert meta["standard"]
        assert meta["standard_section"]
        assert meta["applicability"]
        assert meta["expected_condition"]
        assert meta["remediation_guidance"]
