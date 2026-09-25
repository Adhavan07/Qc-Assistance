"""
Document Extraction & Parsing Pipeline.
Converts raw PDF/image files into a normalized Intermediate Document Representation (IDR).
"""

import os
import re
import uuid
from typing import List, Optional
from pypdf import PdfReader
from PIL import Image

from .schemas import (
    BoundingBox,
    Connector,
    DocumentPage,
    GeneralNote,
    IntermediateDocumentModel,
    TitleBlock,
    WireCallout,
)

# Standard wire gauge pattern (e.g., "18 AWG", "22AWG", "0.75 mm2", "0.75mm²")
WIRE_GAUGE_PATTERN = re.compile(
    r"\b(\d{1,2}\s*AWG|\d+(?:\.\d+)?\s*(?:mm[2²]|sq\s*mm))\b", re.IGNORECASE
)

# Wire color abbreviations per industry standards (IPC-620, UL 508A, IEC 60757)
COLOR_PATTERN = re.compile(
    r"\b(BLK|BLACK|RED|BLU|BLUE|WHT|WHITE|GRN|GREEN|YEL|YELLOW|BRN|BROWN|ORN|ORANGE|GRY|GRAY|VIO|VIOLET|WHT/BLU|WHT/RED|GRN/YEL)\b",
    re.IGNORECASE,
)

# Wire identifier pattern (e.g., "W101", "WIRE-12", "NET_204")
# Negative lookbehind prevents matching standard specifications like "MIL-W-22759"
WIRE_ID_PATTERN = re.compile(
    r"(?<![A-Za-z0-9\-_])(W\d+|WIRE[-_]?\d+|NET[-_]?\d+|HARN[-_]?\d+)\b", re.IGNORECASE
)

# Connector / Device designators (e.g., "J1", "P2", "TB1", "K1", "SW1", "CON3")
CONNECTOR_PATTERN = re.compile(
    r"\b([JP]\d+|TB\d+|CON\d+|CN\d+|X\d+|PL\d+)\b", re.IGNORECASE
)


class DocumentExtractor:
    """Extracts structured engineering data from drawing documents."""

    MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB

    def __init__(self):
        pass

    def extract(self, file_path: str, document_id: Optional[str] = None) -> IntermediateDocumentModel:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        file_size = os.path.getsize(file_path)
        if file_size > self.MAX_FILE_SIZE_BYTES:
            raise ValueError(f"File size {file_size} exceeds maximum limit of 50 MB")

        doc_id = document_id or f"doc_{uuid.uuid4().hex[:12]}"
        filename = os.path.basename(file_path)
        ext = os.path.splitext(filename)[1].lower()

        if ext == ".pdf":
            return self._extract_pdf(file_path, doc_id, filename)
        elif ext in [".png", ".jpg", ".jpeg"]:
            return self._extract_image(file_path, doc_id, filename)
        else:
            raise ValueError(f"Unsupported file format: {ext}. Permitted: .pdf, .png, .jpg, .jpeg")

    def _extract_pdf(self, file_path: str, doc_id: str, filename: str) -> IntermediateDocumentModel:
        reader = PdfReader(file_path)
        page_count = len(reader.pages)
        pages: List[DocumentPage] = []

        for idx, page in enumerate(reader.pages, start=1):
            width = int(page.mediabox.width) if page.mediabox else 1000
            height = int(page.mediabox.height) if page.mediabox else 800
            text = page.extract_text() or ""
            text_lines = [line.strip() for line in text.splitlines() if line.strip()]

            # Parse elements from text lines
            title_block = self._parse_title_block(text_lines)
            wire_callouts = self._parse_wire_callouts(text_lines, idx)
            connectors = self._parse_connectors(text_lines, idx)
            notes = self._parse_notes(text_lines, idx)

            pages.append(
                DocumentPage(
                    page_number=idx,
                    width=width,
                    height=height,
                    title_block=title_block,
                    wire_callouts=wire_callouts,
                    connectors=connectors,
                    general_notes=notes,
                    raw_text_blocks=text_lines,
                )
            )

        return IntermediateDocumentModel(
            document_id=doc_id,
            filename=filename,
            page_count=page_count,
            pages=pages,
            metadata={"format": "pdf", "reader": "pypdf"},
        )

    def _extract_image(self, file_path: str, doc_id: str, filename: str) -> IntermediateDocumentModel:
        with Image.open(file_path) as img:
            width, height = img.size
            if width > 10000 or height > 10000:
                raise ValueError("Image dimension exceeds 10,000 px limit (decompression defense)")

        # In standalone mode without external OCR daemon, create a standard page container
        page = DocumentPage(
            page_number=1,
            width=width,
            height=height,
            title_block=TitleBlock(title=filename),
            raw_text_blocks=[f"Raster schematic: {filename}"],
        )

        return IntermediateDocumentModel(
            document_id=doc_id,
            filename=filename,
            page_count=1,
            pages=[page],
            metadata={"format": "raster_image", "dimensions": f"{width}x{height}"},
        )

    def _parse_title_block(self, lines: List[str]) -> TitleBlock:
        tb = TitleBlock()
        for line in lines:
            line_upper = line.upper()
            if "DWG" in line_upper or "DRAWING NO" in line_upper or "DOC NO" in line_upper:
                match = re.search(r"(?:DWG|DRAWING NO|DOC NO)[.:\s]+([A-Z0-9\-_]+)", line, re.IGNORECASE)
                if match:
                    tb.drawing_number = match.group(1).strip()
            if "TITLE:" in line_upper or "DESCRIPTION:" in line_upper:
                match = re.search(r"(?:TITLE|DESCRIPTION):[ \t]*(.*)", line, re.IGNORECASE)
                if match:
                    tb.title = match.group(1).strip()
            if "REV:" in line_upper or "REVISION:" in line_upper:
                match = re.search(r"(?:REV|REVISION):[ \t]*([A-Z0-9]+)", line, re.IGNORECASE)
                if match:
                    tb.revision = match.group(1).strip()
            if "DRAWN BY:" in line_upper:
                match = re.search(r"DRAWN BY:[ \t]*(.*)", line, re.IGNORECASE)
                if match:
                    tb.drawn_by = match.group(1).strip()
            if "APPROVED BY:" in line_upper:
                match = re.search(r"APPROVED BY:[ \t]*(.*)", line, re.IGNORECASE)
                if match:
                    tb.approved_by = match.group(1).strip()
            if "DATE:" in line_upper:
                match = re.search(r"DATE:[ \t]*([0-9\-\/A-Za-z]+)", line, re.IGNORECASE)
                if match:
                    tb.date = match.group(1).strip()
        return tb

    def _parse_wire_callouts(self, lines: List[str], page_num: int) -> List[WireCallout]:
        callouts: List[WireCallout] = []
        counter = 1

        for idx, line in enumerate(lines):
            line_upper = line.upper().strip()
            # Exclude title blocks, notes, connectors list, and specification references
            if (
                line_upper.startswith("NOTE")
                or line_upper.startswith("TITLE:")
                or line_upper.startswith("DWG")
                or line_upper.startswith("DRAWN BY:")
                or line_upper.startswith("APPROVED BY:")
                or line_upper.startswith("CONNECTORS:")
                or "MIL-W-" in line_upper
                or "MIL-DTL-" in line_upper
                or "MIL-STD-" in line_upper
            ):
                continue

            # Check if line indicates a wire or contains wire-like attributes
            has_wire_id = WIRE_ID_PATTERN.search(line)
            has_gauge = WIRE_GAUGE_PATTERN.search(line)
            has_color = COLOR_PATTERN.search(line)

            if has_wire_id or has_gauge or (has_color and ("TO" in line.upper() or "-" in line)):
                wire_id = has_wire_id.group(1) if has_wire_id else f"W{counter}"
                gauge = has_gauge.group(1) if has_gauge else None
                color = has_color.group(1) if has_color else None

                # Extract from/to connector hints if present (e.g. J1-P1 or J1:1 TO P2:4)
                conn_match = re.findall(CONNECTOR_PATTERN, line)
                from_c = conn_match[0] if len(conn_match) > 0 else None
                to_c = conn_match[1] if len(conn_match) > 1 else None

                callouts.append(
                    WireCallout(
                        id=f"wire_p{page_num}_{counter}",
                        wire_number=wire_id,
                        gauge=gauge,
                        color=color,
                        from_connector=from_c,
                        to_connector=to_c,
                        raw_text=line,
                        location=BoundingBox(x=100, y=100 + (idx * 20), width=300, height=20),
                    )
                )
                counter += 1

        return callouts

    def _parse_connectors(self, lines: List[str], page_num: int) -> List[Connector]:
        connectors: List[Connector] = []
        seen = set()

        for idx, line in enumerate(lines):
            matches = re.finditer(CONNECTOR_PATTERN, line)
            for m in matches:
                ref = m.group(1).upper()
                if ref not in seen:
                    seen.add(ref)
                    # Check if line also provides part number (e.g., "J1: MS3106A-20-29P")
                    pn_match = re.search(r"[A-Z0-9]{3,}-[A-Z0-9\-]+", line)
                    part_no = pn_match.group(0) if pn_match else None

                    connectors.append(
                        Connector(
                            id=f"conn_p{page_num}_{ref}",
                            ref_des=ref,
                            part_number=part_no,
                            location=BoundingBox(x=200, y=150 + (idx * 25), width=150, height=30),
                        )
                    )
        return connectors

    def _parse_notes(self, lines: List[str], page_num: int) -> List[GeneralNote]:
        notes: List[GeneralNote] = []
        in_notes_section = False
        note_counter = 1

        for line in lines:
            line_upper = line.upper()
            if "NOTE" in line_upper:
                in_notes_section = True
                continue

            if in_notes_section:
                # Check for numbered note (e.g., "1. All wires to be teflon insulated")
                match = re.match(r"^(\d+)[.)\s]+(.*)", line)
                if match:
                    num = int(match.group(1))
                    notes.append(
                        GeneralNote(
                            note_number=num,
                            text=match.group(2).strip(),
                            location=BoundingBox(x=50, y=500 + (num * 25), width=400, height=25),
                        )
                    )
                    note_counter = num + 1
                elif line.strip() and not line.startswith("---"):
                    # Continuation or unnumbered note
                    notes.append(
                        GeneralNote(
                            note_number=note_counter,
                            text=line.strip(),
                            location=BoundingBox(x=50, y=500 + (note_counter * 25), width=400, height=25),
                        )
                    )
                    note_counter += 1

        return notes
