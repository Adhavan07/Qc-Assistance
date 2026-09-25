"""
Pydantic schemas for the AI QC Engine.
Defines the Intermediate Document Representation (IDR), Rule Definitions,
Structured QC Findings, and overall Analysis Results.
"""

from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class SeverityEnum(str, Enum):
    CRITICAL = "CRITICAL"
    MAJOR = "MAJOR"
    MINOR = "MINOR"
    INFO = "INFO"


class ConfidenceLevelEnum(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class OverallStatusEnum(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


class BoundingBox(BaseModel):
    """Spatial bounding box in pixels on the rendered 300 DPI page."""
    x: int = Field(..., ge=0, description="Top-left X coordinate")
    y: int = Field(..., ge=0, description="Top-left Y coordinate")
    width: int = Field(..., gt=0, description="Box width in pixels")
    height: int = Field(..., gt=0, description="Box height in pixels")


class Confidence(BaseModel):
    level: ConfidenceLevelEnum
    score: float = Field(..., ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")


class TitleBlock(BaseModel):
    drawing_number: Optional[str] = None
    title: Optional[str] = None
    revision: Optional[str] = None
    drawn_by: Optional[str] = None
    approved_by: Optional[str] = None
    date: Optional[str] = None
    company_name: Optional[str] = None


class WireCallout(BaseModel):
    id: str
    wire_number: Optional[str] = None
    gauge: Optional[str] = None  # e.g., "18 AWG", "0.75 mm²"
    color: Optional[str] = None  # e.g., "RED", "BLK", "WHT/BLU"
    from_connector: Optional[str] = None
    to_connector: Optional[str] = None
    raw_text: str
    location: Optional[BoundingBox] = None


class Connector(BaseModel):
    id: str
    ref_des: str  # e.g., "J1", "P2", "TB1"
    part_number: Optional[str] = None
    pin_count: Optional[int] = None
    location: Optional[BoundingBox] = None


class GeneralNote(BaseModel):
    note_number: int
    text: str
    location: Optional[BoundingBox] = None


class DocumentPage(BaseModel):
    page_number: int = Field(..., ge=1)
    width: int = Field(..., gt=0)
    height: int = Field(..., gt=0)
    title_block: Optional[TitleBlock] = None
    wire_callouts: List[WireCallout] = Field(default_factory=list)
    connectors: List[Connector] = Field(default_factory=list)
    general_notes: List[GeneralNote] = Field(default_factory=list)
    raw_text_blocks: List[str] = Field(default_factory=list)


class IntermediateDocumentModel(BaseModel):
    """Normalized structured representation of an engineering wiring manual."""
    document_id: str
    filename: str
    page_count: int = Field(..., ge=1)
    pages: List[DocumentPage] = Field(default_factory=list)
    metadata: Dict[str, str] = Field(default_factory=dict)


class QCFinding(BaseModel):
    """Standardized finding schema for all detected discrepancies."""
    id: str = Field(..., description="Unique finding ID, e.g. D-001")
    rule_id: str = Field(..., description="Associated rule ID, e.g. RULE-WG-001")
    category: str = Field(..., description="Defect category: WIRE_SPEC, TERMINAL, COLOR_CODE, etc.")
    description: str = Field(..., min_length=5, description="Clear description of the discrepancy")
    severity: SeverityEnum
    confidence: Confidence
    page: int = Field(..., ge=1, description="1-indexed page number")
    location: Optional[BoundingBox] = None
    evidence: str = Field(..., min_length=3, description="Observed text or graphical evidence")
    requirement: str = Field(..., min_length=5, description="The engineering or standard requirement")
    standard: str = Field(..., description="Standard code, e.g. IPC-WHMA-A-620D or UL 508A")
    standard_section: str = Field(..., description="Specific clause or section reference")
    recommendation: str = Field(..., min_length=5, description="Actionable engineering correction")

    @field_validator("id")
    @classmethod
    def validate_finding_id(cls, v: str) -> str:
        if not v.startswith("D-"):
            raise ValueError("Finding ID must begin with 'D-' prefix (e.g. D-001)")
        return v


class QCSummary(BaseModel):
    checks_total: int = Field(..., ge=0)
    passed: int = Field(..., ge=0)
    failed: int = Field(..., ge=0)
    review: int = Field(..., ge=0)
    critical_count: int = Field(0, ge=0)
    major_count: int = Field(0, ge=0)
    minor_count: int = Field(0, ge=0)
    info_count: int = Field(0, ge=0)


class QCAnalysisResult(BaseModel):
    """Complete, validated QC report payload."""
    document_id: str
    filename: str
    standards_applied: List[str]
    overall_status: OverallStatusEnum
    summary: QCSummary
    findings: List[QCFinding]
    model_version: str
    prompt_version: str
    rules_version: str
    processing_time_ms: int = Field(..., ge=0)


class AIFindingPayload(BaseModel):
    """Raw structured finding emitted by an LLM before arbitration."""
    finding_code: str = Field(..., description="Unique finding identifier, e.g. D-001")
    rule_id: str = Field(..., description="Associated standard rule code, e.g. RULE-WG-001")
    category: str = Field(..., description="Defect category: WIRE_SPEC, TERMINAL, COLOR_CODE, etc.")
    description: str = Field(..., min_length=5, description="Clear description of the discrepancy")
    severity: SeverityEnum
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    confidence_level: ConfidenceLevelEnum
    page_number: int = Field(..., ge=1)
    location_bbox: Optional[BoundingBox] = None
    evidence_text: str = Field(..., min_length=2, description="Observed text or graphical evidence")
    requirement_text: str = Field(..., min_length=5, description="Engineering standard requirement")
    standard_citation: str = Field(..., min_length=3, description="Specific clause or standard citation")
    recommendation: str = Field(..., min_length=5, description="Actionable engineering correction")

    @field_validator("finding_code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        if not v.startswith("D-"):
            return f"D-{v}"
        return v


class AIAnalysisPayload(BaseModel):
    """Complete structured response emitted by an AI Provider."""
    prompt_version: str
    findings: List[AIFindingPayload] = Field(default_factory=list)
    summary_notes: Optional[str] = None

