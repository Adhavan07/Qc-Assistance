"""
Unit tests for Document Processing:
- PDF page rasterization and thumbnailing
- Decompression bomb defense
- Multimodal OCR and spatial bounding box extraction
- Title block parsing, wire callouts, connectors, and general notes
"""

import io
from PIL import Image
import pytest
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from backend.src.ai.extractor import DocumentExtractor
from backend.src.ai.schemas import IntermediateDocumentModel
from backend.src.services.image_processor import ImageProcessor


def create_sample_wiring_pdf() -> bytes:
    """Generate a realistic electrical wiring diagram PDF in memory."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)

    # Page 1: Schematic & Wire Run
    # Title Block (bottom-right standard location)
    c.drawString(100, 750, "TITLE: MAIN CONTROL HARNESS SCHEMATIC")
    c.drawString(100, 730, "DRAWING NO: DWG-ELEC-2026-001 REV: C")
    c.drawString(100, 710, "DRAWN BY: J. DOE")
    c.drawString(100, 690, "APPROVED BY: R. SMITH")
    c.drawString(100, 670, "DATE: 2026-09-25")
    c.drawString(100, 650, "COMPANY: SPANDSONS HORIZON ENGINEERING")

    # Wire Schedule / Callouts
    c.drawString(100, 580, "WIRE W101 18 AWG RED FROM J1 TO P2")
    c.drawString(100, 560, "WIRE W102 22 AWG BLK FROM TB1:1 TO J1:2")
    c.drawString(100, 540, "WIRE W103 16 AWG WHT/BLU FROM TB2:4 TO P1:1")
    c.drawString(100, 520, "W104 20 AWG GRN/YEL FROM J2 TO GND-1")

    # Connectors & Terminal Blocks
    c.drawString(100, 450, "CONNECTORS: J1: MS3106A-20-29P, P2: MS3102A-20-29S")
    c.drawString(100, 430, "TERMINAL BLOCKS: TB1: WEIDMULLER-WDU4, TB2: PHOENIX-UK5")

    # General Engineering Notes
    c.drawString(100, 350, "NOTES:")
    c.drawString(100, 330, "1. ALL WIRES SHALL BE TEFLON INSULATED MIL-W-22759/16.")
    c.drawString(100, 310, "2. MINIMUM BEND RADIUS SHALL BE 6X OUTSIDE WIRE DIAMETER.")
    c.drawString(100, 290, "3. CONTINUITY TEST REQUIRED PRIOR TO POTTING.")

    c.showPage()

    # Page 2: Secondary Interconnect
    c.drawString(100, 750, "TITLE: POWER DISTRIBUTION INTERCONNECT")
    c.drawString(100, 730, "DRAWING NO: DWG-ELEC-2026-002 REV: A")
    c.drawString(100, 600, "WIRE W201 12 AWG BLK FROM TB1:5 TO CON1")
    c.drawString(100, 580, "WIRE W202 12 AWG RED FROM TB1:6 TO CON1")
    c.showPage()

    c.save()
    return buf.getvalue()


def test_pdf_page_rasterization_and_thumbnails():
    """Verify high-fidelity multi-page PDF rendering to PNG bytes and thumbnails."""
    pdf_bytes = create_sample_wiring_pdf()
    pages = ImageProcessor.rasterize_document(pdf_bytes, filename="harness.pdf", dpi=150)

    assert len(pages) == 2

    for p in pages:
        assert p["page_number"] in [1, 2]
        assert p["width"] > 0
        assert p["height"] > 0
        # Check PNG magic bytes
        assert p["image_bytes"].startswith(b"\x89PNG")
        assert p["thumbnail_bytes"].startswith(b"\x89PNG")

        # Verify thumbnail width is constrained
        with Image.open(io.BytesIO(p["thumbnail_bytes"])) as thumb:
            assert thumb.size[0] <= 320


def test_raster_image_processing_and_decompression_defense():
    """Verify PNG/JPG schematic ingestion and dimension security protection."""
    # Create valid schematic image
    valid_img = Image.new("RGB", (1200, 800), color=(255, 255, 255))
    buf = io.BytesIO()
    valid_img.save(buf, format="PNG")
    raw_png = buf.getvalue()

    result = ImageProcessor.process_raster_image(raw_png)
    assert result["page_number"] == 1
    assert result["width"] == 1200
    assert result["height"] == 800
    assert result["image_bytes"].startswith(b"\x89PNG")
    assert result["thumbnail_bytes"].startswith(b"\x89PNG")

    # Decompression bomb defense test
    oversized_img = Image.new("RGB", (12000, 1000), color=(255, 255, 255))
    buf_bomb = io.BytesIO()
    oversized_img.save(buf_bomb, format="PNG")
    with pytest.raises(ValueError, match="exceeds maximum safety limit"):
        ImageProcessor.process_raster_image(buf_bomb.getvalue())


def test_document_extractor_spatial_boxes_and_idr():
    """Verify structured parsing of title block, wires, connectors, and spatial coordinates."""
    pdf_bytes = create_sample_wiring_pdf()
    extractor = DocumentExtractor()
    idr: IntermediateDocumentModel = extractor.extract(
        file_bytes=pdf_bytes,
        filename="harness.pdf",
        document_id="doc_test_100",
    )

    assert idr.document_id == "doc_test_100"
    assert idr.page_count == 2
    assert len(idr.pages) == 2

    page1 = idr.pages[0]
    assert page1.width > 0
    assert page1.height > 0

    # Title Block validation
    assert page1.title_block is not None
    assert page1.title_block.drawing_number == "DWG-ELEC-2026-001"
    assert page1.title_block.revision == "C"
    assert page1.title_block.drawn_by == "J. DOE"
    assert page1.title_block.approved_by == "R. SMITH"
    assert page1.title_block.date == "2026-09-25"

    # Wire Callouts validation
    wire_ids = [w.wire_number for w in page1.wire_callouts]
    assert "W101" in wire_ids
    assert "W102" in wire_ids
    assert "W103" in wire_ids

    w101 = next(w for w in page1.wire_callouts if w.wire_number == "W101")
    assert w101.gauge == "18 AWG"
    assert w101.color == "RED"
    assert w101.from_connector == "J1"
    assert w101.to_connector == "P2"
    assert w101.location is not None
    assert w101.location.width > 0
    assert w101.location.height > 0

    # Connectors & Terminal Blocks validation
    ref_des_set = {c.ref_des for c in page1.connectors}
    assert "J1" in ref_des_set
    assert "P2" in ref_des_set
    assert "TB1" in ref_des_set
    assert "TB2" in ref_des_set

    # General Notes validation
    assert len(page1.general_notes) >= 3
    notes_dict = {n.note_number: n.text for n in page1.general_notes}
    assert 1 in notes_dict
    assert "MIL-W-22759/16" in notes_dict[1]
    assert 2 in notes_dict
    assert "MINIMUM BEND RADIUS" in notes_dict[2]

    # Verify Page 2
    page2 = idr.pages[1]
    assert page2.title_block is not None
    assert page2.title_block.drawing_number == "DWG-ELEC-2026-002"
    p2_wires = [w.wire_number for w in page2.wire_callouts]
    assert "W201" in p2_wires


def test_file_size_limit_rejection():
    """Verify 50 MB denial-of-service defense."""
    extractor = DocumentExtractor()
    huge_bytes = b"0" * (51 * 1024 * 1024)
    with pytest.raises(ValueError, match="exceeds maximum limit"):
        extractor.extract(file_bytes=huge_bytes, filename="giant.pdf")
