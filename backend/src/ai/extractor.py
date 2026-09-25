"""
Document Extraction & Parsing Pipeline.
Converts raw PDF/image files into a normalized Intermediate Document Representation (IDR).
Extracts text with spatial coordinate bounding boxes, title block metadata,
wire callouts, connector & terminal block indices, and general engineering notes.
"""

from dataclasses import dataclass
import io
import os
import re
from typing import Any, List, Optional, Tuple, Union
import uuid
from PIL import Image
from pypdf import PdfReader

try:
    import pypdfium2 as pdfium
    HAS_PDFIUM = True
except ImportError:
    HAS_PDFIUM = False

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
WIRE_ID_PATTERN = re.compile(
    r"(?<![A-Za-z0-9\-_])(W\d+|WIRE[-_]?\d+|NET[-_]?\d+|HARN[-_]?\d+)\b", re.IGNORECASE
)

# Connector / Device / Terminal Block designators (e.g., "J1", "P2", "TB1", "TB2", "TERM1", "K1", "CON3")
CONNECTOR_PATTERN = re.compile(
    r"\b([JP]\d+|TB\d+|CON\d+|CN\d+|X\d+|PL\d+|TERM\d+)\b", re.IGNORECASE
)


@dataclass
class ExtractedTextLine:
    """Represents a text line with optional spatial bounding box."""
    text: str
    bbox: Optional[BoundingBox] = None


def _extract_text_and_bbox(
    item: Union[str, ExtractedTextLine, Tuple[str, Any]],
    default_bbox: Optional[BoundingBox] = None,
) -> Tuple[str, Optional[BoundingBox]]:
    if isinstance(item, ExtractedTextLine):
        return item.text, item.bbox or default_bbox
    elif isinstance(item, tuple) and len(item) == 2:
        return str(item[0]), item[1] or default_bbox
    return str(item), default_bbox


class DocumentExtractor:
    """Extracts structured engineering data from drawing documents."""

    MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB
    DEFAULT_DPI = 150

    def __init__(self):
        pass

    def extract(
        self,
        file_path: Optional[str] = None,
        document_id: Optional[str] = None,
        file_bytes: Optional[bytes] = None,
        filename: Optional[str] = None,
    ) -> IntermediateDocumentModel:
        """
        Extract structured IDR from a file path or in-memory byte buffer.
        """
        if file_bytes is not None:
            content = file_bytes
            fname = filename or "document.pdf"
        elif file_path is not None:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")
            file_size = os.path.getsize(file_path)
            if file_size > self.MAX_FILE_SIZE_BYTES:
                raise ValueError(f"File size {file_size} exceeds maximum limit of 50 MB")
            with open(file_path, "rb") as f:
                content = f.read()
            fname = filename or os.path.basename(file_path)
        else:
            raise ValueError("Either file_path or file_bytes must be provided")

        if len(content) > self.MAX_FILE_SIZE_BYTES:
            raise ValueError(f"Content size exceeds maximum limit of 50 MB")

        doc_id = document_id or f"doc_{uuid.uuid4().hex[:12]}"
        ext = os.path.splitext(fname)[1].lower()

        if ext == ".pdf" or content.startswith(b"%PDF"):
            return self._extract_pdf(content, doc_id, fname)
        elif ext in [".png", ".jpg", ".jpeg"] or content.startswith(b"\x89PNG") or content.startswith(b"\xff\xd8"):
            return self._extract_image(content, doc_id, fname)
        else:
            raise ValueError(f"Unsupported file format: {ext}. Permitted: .pdf, .png, .jpg, .jpeg")

    def _extract_pdf(self, content: bytes, doc_id: str, filename: str) -> IntermediateDocumentModel:
        if HAS_PDFIUM:
            try:
                return self._extract_pdf_pdfium(content, doc_id, filename)
            except Exception:
                pass
        return self._extract_pdf_pypdf(content, doc_id, filename)

    def _extract_pdf_pdfium(self, content: bytes, doc_id: str, filename: str) -> IntermediateDocumentModel:
        doc = pdfium.PdfDocument(content)
        try:
            page_count = len(doc)
            pages: List[DocumentPage] = []
            scale = self.DEFAULT_DPI / 72.0

            for idx in range(page_count):
                page = doc.get_page(idx)
                try:
                    w_pts, h_pts = page.get_size()
                    width_px = int(w_pts * scale)
                    height_px = int(h_pts * scale)

                    textpage = page.get_textpage()
                    try:
                        num_rects = textpage.count_rects()
                        bounded_lines: List[ExtractedTextLine] = []
                        raw_text_blocks: List[str] = []

                        for r_idx in range(num_rects):
                            l, b, r, t = textpage.get_rect(r_idx)
                            line_str = textpage.get_text_bounded(l, b, r, t).strip()
                            if not line_str:
                                continue
                            raw_text_blocks.append(line_str)
                            bx = max(0, int(l * scale))
                            by = max(0, int((h_pts - t) * scale))
                            bw = max(1, int((r - l) * scale))
                            bh = max(1, int((t - b) * scale))
                            bounded_lines.append(
                                ExtractedTextLine(
                                    text=line_str,
                                    bbox=BoundingBox(x=bx, y=by, width=bw, height=bh),
                                )
                            )
                    finally:
                        textpage.close()

                    # Fallback to PyPDF text if vector rects were empty (scanned PDF or special fonts)
                    if not bounded_lines:
                        return self._extract_pdf_pypdf(content, doc_id, filename)

                    title_block = self._parse_title_block(bounded_lines)
                    wire_callouts = self._parse_wire_callouts(bounded_lines, idx + 1)
                    connectors = self._parse_connectors(bounded_lines, idx + 1)
                    notes = self._parse_notes(bounded_lines, idx + 1)

                    pages.append(
                        DocumentPage(
                            page_number=idx + 1,
                            width=width_px,
                            height=height_px,
                            title_block=title_block,
                            wire_callouts=wire_callouts,
                            connectors=connectors,
                            general_notes=notes,
                            raw_text_blocks=raw_text_blocks,
                        )
                    )
                finally:
                    page.close()

            return IntermediateDocumentModel(
                document_id=doc_id,
                filename=filename,
                page_count=page_count,
                pages=pages,
                metadata={"format": "pdf", "engine": "pdfium2_spatial", "dpi": str(self.DEFAULT_DPI)},
            )
        finally:
            doc.close()

    def _extract_pdf_pypdf(self, content: bytes, doc_id: str, filename: str) -> IntermediateDocumentModel:
        reader = PdfReader(io.BytesIO(content))
        page_count = max(1, len(reader.pages))
        pages: List[DocumentPage] = []

        for idx, page in enumerate(reader.pages, start=1):
            width = int(page.mediabox.width) if page.mediabox else 1000
            height = int(page.mediabox.height) if page.mediabox else 800
            text = page.extract_text() or ""
            text_lines = [line.strip() for line in text.splitlines() if line.strip()]

            # Wrap in line objects
            bounded_lines = [
                ExtractedTextLine(
                    text=line,
                    bbox=BoundingBox(x=50, y=50 + (l_idx * 25), width=max(50, len(line) * 8), height=20),
                )
                for l_idx, line in enumerate(text_lines)
            ]

            title_block = self._parse_title_block(bounded_lines)
            wire_callouts = self._parse_wire_callouts(bounded_lines, idx)
            connectors = self._parse_connectors(bounded_lines, idx)
            notes = self._parse_notes(bounded_lines, idx)

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
            metadata={"format": "pdf", "engine": "pypdf_fallback"},
        )

    def _extract_image(self, content: bytes, doc_id: str, filename: str) -> IntermediateDocumentModel:
        with Image.open(io.BytesIO(content)) as img:
            width, height = img.size
            if width > 10000 or height > 10000:
                raise ValueError("Image dimension exceeds 10,000 px limit (decompression defense)")

        # Create structured single-page container with bounding box grids for standard drawing zones
        tb_box = BoundingBox(
            x=int(width * 0.65),
            y=int(height * 0.82),
            width=int(width * 0.32),
            height=int(height * 0.15),
        )
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

    def _parse_title_block(self, lines: Union[List[str], List[ExtractedTextLine]]) -> TitleBlock:
        tb = TitleBlock()
        for item in lines:
            line, _ = _extract_text_and_bbox(item)
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
            if "COMPANY:" in line_upper or "CLIENT:" in line_upper:
                match = re.search(r"(?:COMPANY|CLIENT):[ \t]*(.*)", line, re.IGNORECASE)
                if match:
                    tb.company_name = match.group(1).strip()
        return tb

    def _parse_wire_callouts(
        self,
        lines: Union[List[str], List[ExtractedTextLine]],
        page_num: int,
    ) -> List[WireCallout]:
        callouts: List[WireCallout] = []
        counter = 1

        for idx, item in enumerate(lines):
            line, item_bbox = _extract_text_and_bbox(item)
            line_upper = line.upper().strip()

            # Exclude title blocks, notes, connectors header, and spec references
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

            has_wire_id = WIRE_ID_PATTERN.search(line)
            has_gauge = WIRE_GAUGE_PATTERN.search(line)
            has_color = COLOR_PATTERN.search(line)

            if has_wire_id or has_gauge or (has_color and ("TO" in line_upper or "-" in line)):
                wire_id = has_wire_id.group(1) if has_wire_id else f"W{counter}"
                gauge = has_gauge.group(1) if has_gauge else None
                color = has_color.group(1) if has_color else None

                conn_match = re.findall(CONNECTOR_PATTERN, line)
                from_c = conn_match[0] if len(conn_match) > 0 else None
                to_c = conn_match[1] if len(conn_match) > 1 else None

                loc_bbox = item_bbox or BoundingBox(x=100, y=100 + (idx * 20), width=300, height=20)

                callouts.append(
                    WireCallout(
                        id=f"wire_p{page_num}_{counter}",
                        wire_number=wire_id,
                        gauge=gauge,
                        color=color,
                        from_connector=from_c,
                        to_connector=to_c,
                        raw_text=line,
                        location=loc_bbox,
                    )
                )
                counter += 1

        return callouts

    def _parse_connectors(
        self,
        lines: Union[List[str], List[ExtractedTextLine]],
        page_num: int,
    ) -> List[Connector]:
        connectors: List[Connector] = []
        seen = set()

        for idx, item in enumerate(lines):
            line, item_bbox = _extract_text_and_bbox(item)
            matches = re.finditer(CONNECTOR_PATTERN, line)
            for m in matches:
                ref = m.group(1).upper()
                if ref not in seen:
                    seen.add(ref)
                    pn_match = re.search(r"[A-Z0-9]{3,}-[A-Z0-9\-]+", line)
                    part_no = pn_match.group(0) if pn_match else None

                    loc_bbox = item_bbox or BoundingBox(x=200, y=150 + (idx * 25), width=150, height=30)

                    connectors.append(
                        Connector(
                            id=f"conn_p{page_num}_{ref}",
                            ref_des=ref,
                            part_number=part_no,
                            location=loc_bbox,
                        )
                    )
        return connectors

    def _parse_notes(
        self,
        lines: Union[List[str], List[ExtractedTextLine]],
        page_num: int,
    ) -> List[GeneralNote]:
        notes: List[GeneralNote] = []
        in_notes_section = False
        note_counter = 1

        for idx, item in enumerate(lines):
            line, item_bbox = _extract_text_and_bbox(item)
            line_upper = line.upper()

            if "NOTE" in line_upper:
                in_notes_section = True
                continue

            if in_notes_section:
                match = re.match(r"^(\d+)[.)\s]+(.*)", line)
                if match:
                    num = int(match.group(1))
                    loc_bbox = item_bbox or BoundingBox(x=50, y=500 + (num * 25), width=400, height=25)
                    notes.append(
                        GeneralNote(
                            note_number=num,
                            text=match.group(2).strip(),
                            location=loc_bbox,
                        )
                    )
                    note_counter = num + 1
                elif line.strip() and not line.startswith("---"):
                    loc_bbox = item_bbox or BoundingBox(x=50, y=500 + (note_counter * 25), width=400, height=25)
                    notes.append(
                        GeneralNote(
                            note_number=note_counter,
                            text=line.strip(),
                            location=loc_bbox,
                        )
                    )
                    note_counter += 1

        return notes
