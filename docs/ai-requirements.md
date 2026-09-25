# AI & Document Intelligence Requirements
**Project**: Wiring Diagram QC Assistant  
**Client / Product Owner**: Spandsons Horizon Engineering Pvt. Ltd.  
**Version**: 1.0.0 | **Date**: 2026-09-25

---

## 1. Document Extraction & OCR Strategy
Engineering drawings exhibit high visual density, rotated text, schematic symbols, and fine lines.

### Ingestion Flow:
1. **Resolution Standardization**: All input documents are rendered to 300 DPI images (`pypdfium2`).
2. **Text Layer Extraction**:
   - If the PDF has an embedded digital text layer with character coordinates, PyMuPDF extracts text spans directly with bounding boxes.
   - If the PDF is scanned or raster-based, Tesseract OCR v5 / PaddleOCR processes the image with page segmentation mode (`PSM 11` for sparse text with irregular orientations).
3. **Symbol & Region Detection**:
   - Title Block Extraction: Bottom-right quadrant localized and parsed into structured drawing metadata.
   - Notes Column Extraction: General notes column parsed into indexed clauses.
   - Wire Net & Pin Table Extraction: BOM tables and terminal strip tables extracted into tabular data.

## 2. Structured Pydantic Output Schema

```python
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

class SeverityEnum(str, Enum):
    CRITICAL = "CRITICAL"
    MAJOR = "MAJOR"
    MINOR = "MINOR"
    INFO = "INFO"

class ConfidenceLevelEnum(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class BoundingBox(BaseModel):
    x: int = Field(..., description="Top-left X coordinate in pixels")
    y: int = Field(..., description="Top-left Y coordinate in pixels")
    width: int = Field(..., description="Bounding box width in pixels")
    height: int = Field(..., description="Bounding box height in pixels")

class Confidence(BaseModel):
    level: ConfidenceLevelEnum
    score: float = Field(..., ge=0.0, le=1.0)

class QC Finding(BaseModel):
    id: str = Field(..., description="Unique finding ID, e.g. D-001")
    rule_id: str = Field(..., description="Associated rule code, e.g. RULE-WG-001")
    category: str = Field(..., description="Category, e.g. WIRE_GAUGE, TERMINAL, PINOUT")
    description: str = Field(..., description="Plain-language description of defect")
    severity: SeverityEnum
    confidence: Confidence
    page: int = Field(..., ge=1)
    location: Optional[BoundingBox] = None
    evidence: str = Field(..., description="Direct text or visual observation from document")
    requirement: str = Field(..., description="Mandate from standard or drawing note")
    standard: str = Field(..., description="e.g. IPC-WHMA-A-620D")
    standard_section: str = Field(..., description="e.g. Section 4.1.2")
    recommendation: str = Field(..., description="Actionable remediation advice")

class QCSummary(BaseModel):
    checks_total: int
    passed: int
    failed: int
    review: int

class QCAnalysisResult(BaseModel):
    document_id: str
    overall_status: str = Field(..., pattern="^(PASS|FAIL|REVIEW_REQUIRED)$")
    summary: QCSummary
    findings: List[QCFinding]
```

## 3. Human-in-the-Loop & Uncertainty Handling
When visual ambiguity or incomplete drawing data arises:
- If `confidence.score < 0.70`, the finding severity is flagged for human review (`REVIEW_REQUIRED`) rather than asserting a false certainty.
- The inspector's feedback (`CORRECT`, `INCORRECT`, `NEEDS_REVIEW`) is recorded in the evaluation database to prevent recurring false positives.
