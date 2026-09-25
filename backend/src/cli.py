"""
Command-Line Interface for the AI QC Engine Prototype.
Usage:
    python -m backend.src.cli <path_to_wiring_diagram.pdf> [--pdf-out report.pdf] [--xlsx-out report.xlsx]
"""

import argparse
import json
import os
import sys

from .ai.engine import QCAnalysisEngine
from .reports.pdf_generator import PDFReportGenerator
from .reports.xlsx_generator import XLSXReportGenerator


def main():
    parser = argparse.ArgumentParser(
        description="Wiring Diagram QC Assistant — AI Engine Prototype (MVP-0)"
    )
    parser.add_argument("document", help="Path to wiring diagram manual (PDF, PNG, JPG)")
    parser.add_argument("--standards", nargs="+", default=["IPC-WHMA-A-620D", "UL 508A"], help="Standards to apply")
    parser.add_argument("--json-out", help="Path to write structured JSON output")
    parser.add_argument("--pdf-out", help="Path to write PDF audit report")
    parser.add_argument("--xlsx-out", help="Path to write XLSX audit spreadsheet")

    args = parser.parse_args()

    if not os.path.exists(args.document):
        print(f"Error: File not found: {args.document}", file=sys.stderr)
        sys.exit(1)

    print(f"\n=======================================================")
    print(f"  Wiring Diagram QC Assistant — AI Engine v1.0")
    print(f"=======================================================")
    print(f"Ingesting: {args.document}")
    print(f"Standards: {', '.join(args.standards)}")

    engine = QCAnalysisEngine()
    result = engine.analyze(args.document, standards=args.standards)

    print(f"\nAnalysis Completed in {result.processing_time_ms} ms")
    print(f"Overall Status: {result.overall_status.value}")
    print(f"Summary: Total Checks: {result.summary.checks_total} | Passed: {result.summary.passed} | Failed: {result.summary.failed} | Review: {result.summary.review}")
    print(f"Findings Breakdown: Critical: {result.summary.critical_count} | Major: {result.summary.major_count} | Minor: {result.summary.minor_count}")
    print(f"Discrepancies Detected: {len(result.findings)}")

    for f in result.findings:
        print(f"  [{f.id}] ({f.severity.value}) Pg {f.page}: {f.description}")
        print(f"       Standard: {f.standard} {f.standard_section}")
        print(f"       Rec: {f.recommendation}\n")

    if args.json_out:
        with open(args.json_out, "w") as f:
            f.write(result.model_dump_json(indent=2))
        print(f"JSON Output saved to: {args.json_out}")

    if args.pdf_out:
        pdf_gen = PDFReportGenerator()
        pdf_gen.generate(result, args.pdf_out)
        print(f"PDF Report generated: {args.pdf_out}")

    if args.xlsx_out:
        xlsx_gen = XLSXReportGenerator()
        xlsx_gen.generate(result, args.xlsx_out)
        print(f"XLSX Report generated: {args.xlsx_out}")


if __name__ == "__main__":
    main()
