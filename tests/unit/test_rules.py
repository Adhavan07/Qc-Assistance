"""
Unit tests for deterministic QC rules.
Verifies that rules trigger correctly on compliance violations and pass on compliant designs.
"""

from backend.src.ai.schemas import (
    BoundingBox,
    Connector,
    DocumentPage,
    IntermediateDocumentModel,
    SeverityEnum,
    TitleBlock,
    WireCallout,
)
from backend.src.ai.rules import (
    ColorCodeMismatchRule,
    DuplicateDesignatorRule,
    MissingWireGaugeRule,
    RuleRegistry,
    TitleBlockIncompleteRule,
)


def test_missing_wire_gauge_detection():
    doc = IntermediateDocumentModel(
        document_id="test_doc",
        filename="schematic.pdf",
        page_count=1,
        pages=[
            DocumentPage(
                page_number=1,
                width=1000,
                height=800,
                wire_callouts=[
                    WireCallout(
                        id="w1",
                        wire_number="W101",
                        gauge=None,  # Missing gauge!
                        color="RED",
                        raw_text="W101 RED",
                    ),
                    WireCallout(
                        id="w2",
                        wire_number="W102",
                        gauge="18 AWG",  # Valid gauge
                        color="BLK",
                        raw_text="W102 18AWG BLK",
                    ),
                ],
            )
        ],
    )
    rule = MissingWireGaugeRule()
    findings = rule.evaluate(doc)
    assert len(findings) == 1
    assert findings[0].rule_id == "RULE-WG-001"
    assert findings[0].severity == SeverityEnum.CRITICAL
    assert "W101" in findings[0].description


def test_color_code_ambiguity_detection():
    doc = IntermediateDocumentModel(
        document_id="test_doc",
        filename="schematic.pdf",
        page_count=1,
        pages=[
            DocumentPage(
                page_number=1,
                width=1000,
                height=800,
                wire_callouts=[
                    WireCallout(
                        id="w1",
                        wire_number="W101",
                        gauge="18 AWG",
                        color=None,  # Missing color!
                        raw_text="W101 18AWG",
                    )
                ],
            )
        ],
    )
    rule = ColorCodeMismatchRule()
    findings = rule.evaluate(doc)
    assert len(findings) == 1
    assert findings[0].rule_id == "RULE-CC-003"
    assert findings[0].severity == SeverityEnum.MAJOR


def test_duplicate_reference_designator_detection():
    doc = IntermediateDocumentModel(
        document_id="test_doc",
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
    assert "Duplicate reference designator 'J1'" in findings[0].description


def test_title_block_incomplete_detection():
    doc = IntermediateDocumentModel(
        document_id="test_doc",
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
                    date="2025-08-01",
                ),
            )
        ],
    )
    rule = TitleBlockIncompleteRule()
    findings = rule.evaluate(doc)
    assert len(findings) == 1
    assert findings[0].rule_id == "RULE-TB-005"
    assert "Drawing Number" in findings[0].description


def test_rule_registry_aggregation():
    registry = RuleRegistry()
    assert len(registry.rules) >= 4
