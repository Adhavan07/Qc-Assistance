"""
Deterministic Audit-Grade PDF Report Generator.
Utilizes ReportLab to generate standardized engineering compliance reports from QCAnalysisResult.
"""

import io
from typing import Union
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from ..ai.schemas import OverallStatusEnum, QCAnalysisResult, SeverityEnum


class PDFReportGenerator:
    """Generates immutable, audit-ready PDF reports from validated QC findings."""

    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        self.title_style = ParagraphStyle(
            "DocTitle",
            parent=self.styles["Heading1"],
            fontSize=20,
            leading=24,
            textColor=colors.HexColor("#0f172a"),
            fontName="Helvetica-Bold",
        )
        self.subtitle_style = ParagraphStyle(
            "DocSubtitle",
            parent=self.styles["Normal"],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#64748b"),
        )
        self.section_heading = ParagraphStyle(
            "SectionHeading",
            parent=self.styles["Heading2"],
            fontSize=13,
            leading=17,
            textColor=colors.HexColor("#1e293b"),
            fontName="Helvetica-Bold",
            spaceBefore=10,
            spaceAfter=6,
        )
        self.body_style = ParagraphStyle(
            "Body",
            parent=self.styles["Normal"],
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#334155"),
        )
        self.table_header_style = ParagraphStyle(
            "TableHeader",
            parent=self.styles["Normal"],
            fontSize=8,
            leading=10,
            fontName="Helvetica-Bold",
            textColor=colors.white,
        )

    def generate(self, result: QCAnalysisResult, output_destination: Union[str, io.BytesIO]):
        """Compile result into PDF document."""
        doc = SimpleDocTemplate(
            output_destination,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36,
        )
        story = []

        # 1. Header Banner
        header_table = Table(
            [
                [
                    Paragraph("WIRING DIAGRAM QC ASSISTANT", self.title_style),
                    Paragraph(f"<b>STATUS:</b> {result.overall_status.value}", self._get_status_style(result.overall_status)),
                ],
                [
                    Paragraph("Engineering Quality Control & Compliance Report", self.subtitle_style),
                    Paragraph(f"Doc ID: {result.document_id}", self.subtitle_style),
                ],
            ],
            colWidths=[380, 160],
        )
        header_table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ]
            )
        )
        story.append(header_table)
        story.append(Spacer(1, 8))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cbd5e1"), spaceAfter=12))

        # 2. Executive Metadata Box
        meta_data = [
            [
                Paragraph("<b>Filename:</b>", self.body_style),
                Paragraph(result.filename, self.body_style),
                Paragraph("<b>Applied Standards:</b>", self.body_style),
                Paragraph(", ".join(result.standards_applied), self.body_style),
            ],
            [
                Paragraph("<b>Ruleset Version:</b>", self.body_style),
                Paragraph(result.rules_version, self.body_style),
                Paragraph("<b>Processing Duration:</b>", self.body_style),
                Paragraph(f"{result.processing_time_ms} ms", self.body_style),
            ],
        ]
        meta_table = Table(meta_data, colWidths=[90, 180, 110, 160])
        meta_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                    ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#e2e8f0")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#f1f5f9")),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(meta_table)
        story.append(Spacer(1, 14))

        # 3. Summary Metrics Table
        story.append(Paragraph("1. Executive Summary & Defect Metrics", self.section_heading))
        summary_rows = [
            [
                Paragraph("Total Checks", self.table_header_style),
                Paragraph("Passed", self.table_header_style),
                Paragraph("Failed", self.table_header_style),
                Paragraph("Critical", self.table_header_style),
                Paragraph("Major", self.table_header_style),
                Paragraph("Minor", self.table_header_style),
            ],
            [
                Paragraph(str(result.summary.checks_total), self.body_style),
                Paragraph(str(result.summary.passed), self.body_style),
                Paragraph(str(result.summary.failed), self.body_style),
                Paragraph(str(result.summary.critical_count), self.body_style),
                Paragraph(str(result.summary.major_count), self.body_style),
                Paragraph(str(result.summary.minor_count), self.body_style),
            ],
        ]
        summary_table = Table(summary_rows, colWidths=[90, 90, 90, 90, 90, 90])
        summary_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(summary_table)
        story.append(Spacer(1, 14))

        # 4. Detailed Findings Table
        story.append(Paragraph(f"2. Discrepancy Findings Catalog ({len(result.findings)} Detected)", self.section_heading))
        if not result.findings:
            story.append(Paragraph("✓ No discrepancies detected. Document satisfies all checked rules.", self.body_style))
        else:
            findings_data = [
                [
                    Paragraph("ID", self.table_header_style),
                    Paragraph("Pg", self.table_header_style),
                    Paragraph("Severity", self.table_header_style),
                    Paragraph("Category", self.table_header_style),
                    Paragraph("Description & Evidence", self.table_header_style),
                    Paragraph("Standard & Recommendation", self.table_header_style),
                ]
            ]

            for f in result.findings:
                sev_color = self._get_severity_hex(f.severity)
                findings_data.append(
                    [
                        Paragraph(f"<b>{f.id}</b>", self.body_style),
                        Paragraph(str(f.page), self.body_style),
                        Paragraph(f"<font color='{sev_color}'><b>{f.severity.value}</b></font>", self.body_style),
                        Paragraph(f.category, self.body_style),
                        Paragraph(f"<b>{f.description}</b><br/><font color='#64748b'>Evidence: {f.evidence}</font>", self.body_style),
                        Paragraph(f"<b>{f.standard} {f.standard_section}</b><br/><i>Rec: {f.recommendation}</i>", self.body_style),
                    ]
                )

            findings_table = Table(findings_data, colWidths=[45, 25, 55, 75, 175, 165])
            findings_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#94a3b8")),
                        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ]
                )
            )
            story.append(findings_table)

        # 5. Build Document
        doc.build(story)

    def _get_status_style(self, status: OverallStatusEnum) -> ParagraphStyle:
        bg = "#ef4444" if status == OverallStatusEnum.FAIL else ("#f59e0b" if status == OverallStatusEnum.REVIEW_REQUIRED else "#10b981")
        return ParagraphStyle(
            "StatusStyle",
            parent=self.styles["Heading2"],
            fontSize=13,
            leading=16,
            textColor=colors.HexColor(bg),
            alignment=2,  # Right aligned
            fontName="Helvetica-Bold",
        )

    def _get_severity_hex(self, severity: SeverityEnum) -> str:
        if severity == SeverityEnum.CRITICAL:
            return "#dc2626"
        elif severity == SeverityEnum.MAJOR:
            return "#ea580c"
        elif severity == SeverityEnum.MINOR:
            return "#d97706"
        return "#2563eb"
