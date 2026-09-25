# Engineering Changelog & Audit Log
**Project**: Wiring Diagram QC Assistant  
**Client / Product Owner**: Spandsons Horizon Engineering Pvt. Ltd. (Pravin, Gogulnath)  
**Maintained by**: Lead Software Architect, AI/ML Engineer, DevOps, Security, QA Team

All significant architectural decisions, codebase modifications, schema changes, and test verifications are recorded chronologically in this document.

---

## [Phase 2: AI Evaluation Framework & Gold Dataset] — 2026-09-25

### Added
- **AI Evaluation Metrics & Scoring Engine (`backend/src/ai/evaluation/metrics.py`)**:
  - Implemented exact mathematical calculations for Precision, Recall, $F_1$-score, and Critical-Error Recall.
  - Added zero-division resilience and Pydantic models: `GroundTruthFinding`, `EvaluationTestCase`, `CaseEvaluationResult`, and `BenchmarkReport`.
- **Curated Gold-Standard Dataset (`backend/src/ai/evaluation/gold_dataset.py`)**:
  - `GoldDatasetManager`: Programmatically generates 10 realistic PDF engineering drawing manuals covering:
    - TC-01: Fully compliant baseline harness (all gauges, colors, unique RefDes, complete title block -> PASS).
    - TC-02: Missing wire gauge callouts (2 Critical defects, IPC-620 § 4.1 -> FAIL).
    - TC-03: Color code ambiguity (2 Major defects, UL 508A § 66.5 -> FAIL).
    - TC-04: Duplicate connector reference designators (1 Critical defect, ANSI/IEEE 200 § 4.2 -> FAIL).
    - TC-05: Incomplete title block (1 Minor defect, ISO 7200 / ASME Y14.1 -> REVIEW_REQUIRED).
    - TC-06: Mixed multi-defect industrial panel (1 Critical, 1 Major, 1 Minor -> FAIL).
    - TC-07: Clean high-current 3-phase power distribution (4/0 AWG, 2 AWG -> PASS).
    - TC-08: Terminal strip harness with unrated jumper (1 Critical -> FAIL).
    - TC-09: Multi-page wiring package with distributed defects across pages 2 and 3 (1 Major, 1 Critical -> FAIL).
    - TC-10: Metric cross-section compliant harness (0.75 mm², 1.5 mm² -> PASS).
- **Benchmark Runner & Quality Gate (`backend/src/ai/evaluation/runner.py`)**:
  - `EvaluationRunner`: Executes `QCAnalysisEngine` across test cases, matches predicted findings against ground truth annotations (by rule ID, page, and evidence keywords), and enforces release quality gates.
  - Quality Gate: Critical Error Recall $\ge 98.0\%$, $F_1 \ge 85.0\%$.
- **Evaluation Command-Line Interface (`backend/src/evaluation_cli.py`)**:
  - CLI runner `python -m backend.src.evaluation_cli` displaying tabular case-by-case detection results, confusion counts (TP, FP, FN), aggregate metrics, and emitting structured benchmark JSON reports.
- **Unit & Regression Test Suites**:
  - `tests/unit/test_metrics.py`: Tests edge-case metric calculations and zero-division resilience.
  - `tests/evaluation/test_benchmark_regression.py`: Automated pytest regression suite enforcing zero false positives on compliant drawings and 100% Critical Error Recall.
  - Test result: **16/16 tests passed across unit and evaluation test suites**.

### Fixed / Enhanced
- **`backend/src/ai/extractor.py`**:
  - Resolved false positive defect detection where military standard specification numbers (e.g. `MIL-W-22759`) inside general notes were mistakenly parsed as unrated physical wire runs.
  - Added negative lookbehind in `WIRE_ID_PATTERN` and added explicit exclusion for notes, title blocks, and military/industry specification prefixes (`MIL-W-`, `MIL-DTL-`, `MIL-STD-`).

---

## [Phase 1: AI Engine Prototype (MVP-0)] — 2026-09-25

### Added
- **Pydantic Data Schemas (`backend/src/ai/schemas.py`)**:
  - `BoundingBox`: Coordinate modeling with non-negative validation (`x`, `y`, `width`, `height`).
  - `Confidence`: Strict bounds validation (`0.0 <= score <= 1.0`) with categorical levels (`HIGH`, `MEDIUM`, `LOW`).
  - `IntermediateDocumentModel`: Internal structural representation of multi-page engineering drawings, containing `TitleBlock`, `WireCallout`, `Connector`, `GeneralNote`, and raw page dimensions.
  - `QCFinding`: Strict schema for discrepancies with enforced `D-xxx` ID format, severity levels (`CRITICAL`, `MAJOR`, `MINOR`, `INFO`), standard citation, evidence snippet, and engineering recommendation.
  - `QCSummary` & `QCAnalysisResult`: Summary metrics and full report payload with model/prompt/ruleset version tracking.
- **Document Extractor (`backend/src/ai/extractor.py`)**:
  - Secure file ingestion with 50 MB file size limit and 10,000 px dimension defense against decompression bombs.
  - PDF text extraction and geometry parsing using `pypdf`.
  - Regex-based heuristics for wire identification, AWG / metric gauge parsing, color code matching, connector designators (`J1`, `P2`, `TB1`), and title block extraction.
  - Image handling with PIL for raster schematics.
- **Deterministic Rules Engine (`backend/src/ai/rules.py`)**:
  - `BaseRule`: Abstract rule base class.
  - `MissingWireGaugeRule` (`RULE-WG-001`): Flags missing wire gauges as `CRITICAL` per IPC-WHMA-A-620D § 4.1.
  - `ColorCodeMismatchRule` (`RULE-CC-003`): Flags missing/ambiguous conductor colors as `MAJOR` per UL 508A § 66.5.
  - `DuplicateDesignatorRule` (`RULE-RD-004`): Flags duplicate connector reference designators as `CRITICAL` per ANSI/IEEE 200 § 4.2.
  - `TitleBlockIncompleteRule` (`RULE-TB-005`): Flags missing title block control fields (Revision, Date, Drawing No) as `MINOR` per ISO 7200 / ASME Y14.1.
  - `RuleRegistry`: Central evaluator orchestrating all deterministic checks.
- **LLM Provider Abstraction (`backend/src/ai/llm_adapter.py`)**:
  - `LLMProviderInterface`: Abstract base class with `generate_structured` method.
  - `MockLLMProvider`: Deterministic offline provider for unit tests, CI pipelines, and offline evaluation.
  - `LLMProviderFactory`: Factory pattern for swappable cloud providers.
- **Central QC Analysis Engine (`backend/src/ai/engine.py`)**:
  - Orchestrates extraction -> deterministic rules -> LLM reasoning -> finding arbitration & deduplication -> summary computation -> Pydantic validation.
- **Report Generation Engines**:
  - `PDFReportGenerator` (`backend/src/reports/pdf_generator.py`): ReportLab-based audit-ready PDF report generator with executive summary, pass/fail status banner, and discrepancy catalog.
  - `XLSXReportGenerator` (`backend/src/reports/xlsx_generator.py`): OpenPyXL-based two-sheet Excel workbook generator (`QC Summary` and `Discrepancy Details`) for ERP/PLM integration.
- **Command-Line Interface (`backend/src/cli.py`)**:
  - CLI runner allowing execution on any PDF/image manual with `--json-out`, `--pdf-out`, and `--xlsx-out` flags.
- **Unit Test Suite (`tests/unit/`)**:
  - `test_schemas.py`: Tests boundary validation, regex formatting, and error handling.
  - `test_rules.py`: Tests deterministic rule evaluation on compliant and non-compliant models.
  - `test_engine.py`: Generates synthetic PDF drawing and validates full pipeline output.
  - Test result: **11/11 tests passed in 0.28s**.
- **Configuration & Tooling**:
  - `pyproject.toml`: Configured `pythonpath = ["."]`.
  - `backend/requirements.txt`: Pinned dependencies (`pydantic`, `pypdf`, `reportlab`, `openpyxl`, `pillow`, `pytest`).
  - `.gitignore`: Configured to exclude virtual environments, cache, secrets, and test artifacts.
  - Git repository initialized on branch `main`.

---

## [Phase 0: Project Discovery & Technical Design] — 2026-09-25

### Added
- Created complete Technical Design Specification v1.0 covering all 31 mandatory sections in [`docs/PROJECT_DISCOVERY_AND_TECHNICAL_DESIGN.md`](file:///data/projects/QC-Assistance/docs/PROJECT_DISCOVERY_AND_TECHNICAL_DESIGN.md).
- Authored modular technical documents:
  - [`docs/product-requirements.md`](file:///data/projects/QC-Assistance/docs/product-requirements.md)
  - [`docs/system-requirements.md`](file:///data/projects/QC-Assistance/docs/system-requirements.md)
  - [`docs/architecture.md`](file:///data/projects/QC-Assistance/docs/architecture.md)
  - [`docs/threat-model.md`](file:///data/projects/QC-Assistance/docs/threat-model.md)
  - [`docs/ai-requirements.md`](file:///data/projects/QC-Assistance/docs/ai-requirements.md)
  - [`docs/data-model.md`](file:///data/projects/QC-Assistance/docs/data-model.md)
  - [`docs/api-specification.md`](file:///data/projects/QC-Assistance/docs/api-specification.md)
  - [`docs/deployment-architecture.md`](file:///data/projects/QC-Assistance/docs/deployment-architecture.md)
  - [`docs/testing-strategy.md`](file:///data/projects/QC-Assistance/docs/testing-strategy.md)
  - [`docs/decision-log.md`](file:///data/projects/QC-Assistance/docs/decision-log.md)
