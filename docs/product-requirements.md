# Product Requirements Document (PRD)

**Project Name**: Wiring Diagram QC Assistant  
**Client**: Spandsons Horizon Engineering Pvt. Ltd. (Pravin, Team & Gogulnath)  
**Product Type**: B2B Multi-Tenant SaaS Platform  
**Document Version**: 2.0.0 (Phase 0 Architecture Release)  
**Date**: 2026-09-25  
**Author**: Principal Software Architect & Technical Project Team  

---

## 1. Executive Summary & Problem Statement

Quality Control (QC) inspection of electrical wiring diagram manuals, harness drawings, and industrial control schematics is currently a manual, expert-dependent, and time-intensive process. A single aerospace or industrial control manual can span dozens of sheets containing thousands of connection nets, terminal points, conductor callouts, and component references.

Manual review suffers from significant operational friction:
1. **Prolonged Turnaround Times**: Manual inspections require hours to days per revision, creating engineering and production bottlenecks in Electronic Manufacturing Services (EMS), wire harness assembly, and panel manufacturing.
2. **Downstream Production Scrap**: Human error in drawing review results in severe defects reaching the shop floor (e.g., undersized conductors leading to thermal hazards, mismatched mating contact sizes, missing torque specifications, or violation of bend radius minimums).
3. **Audit & Compliance Overhead**: Contract manufacturers must verify compliance against stringent standards (IPC-WHMA-A-620 Class 3, UL 508A, MIL-STD-681D) with verifiable proof for client audits.

The **Wiring Diagram QC Assistant** transforms an existing validated AI prompt asset into a defensible, multi-tenant commercial SaaS platform. The system combines deterministic rule-based engineering checks with multi-modal AI reasoning to produce instant, verifiable, and auditable QC reports with exact drawing evidence and coordinates.

---

## 2. Product Vision & Positioning

> **"An Engineering Document Quality Assurance Platform starting with electrical wiring diagrams and manuals."**

### Core Positioning
- **Not an unrestricted generic AI chatbot**: The platform does not allow hallucinated or unstructured responses. Every finding is anchored in deterministic rules, standard clauses, page numbers, and exact bounding-box coordinates.
- **Auditable Quality System**: Designed for manufacturing engineers, quality inspectors, and compliance officers who require verifiable evidence (`Expected` vs. `Actual`), confidence ratings, and exportable artifacts (formal PDF and structured Excel).
- **Industrial Enterprise Look & Feel**: Modern, high-contrast, professional white enterprise aesthetic with clean typography, responsive layout, and dedicated engineering schematic canvas.

---

## 3. Scope & Requirement Classification

Based on detailed analysis of the **Spandsons Horizon Engineering Project Charter (v1.0)**, system requirements are categorized into strict priority tiers:

### 3.1 MUST HAVE (Phase 0 – MVP-1 Scope)
- **Multi-Tenant Authentication & RBAC**: Self-service organization onboarding, strict role hierarchy (`PLATFORM_ADMIN`, `TENANT_ADMIN`, `ENGINEER`, `REVIEWER`, `CUSTOMER_USER`, `READ_ONLY`), session management, bcrypt password hashing, and zero cross-tenant data leakage.
- **Secure Document Ingestion**: Drag-and-drop file upload supporting PDF, PNG, JPG, and JPEG with magic-byte/MIME validation, SHA-256 checksums, encrypted S3/MinIO storage, and presigned browser-to-bucket transfers.
- **Document Processing Pipeline**: Page extraction, high-resolution rendering, text vector extraction for CAD PDFs, and OCR fallback for raster scans, producing an Intermediate Document Representation (IDR) with coordinate provenance.
- **Deterministic QC Rules Engine**: Automated verification of mandatory engineering rules across:
  - Wire gauge callout & circuit breaker overcurrent rating (`RULE-WIRE-001`)
  - Connector contact pin gauge and current matching (`RULE-CONN-002`)
  - Minimum harness bend radius calculation (`RULE-BEND-001`)
  - AC/DC conductor insulation color coding (`RULE-COLOR-003`)
  - Terminal block torque markings (`RULE-TERM-004`)
  - Reference designator standard prefixes (`RULE-REV-005`)
- **AI Provider Abstraction & Schema Validation**: Decoupled interface (`AIProviderInterface`) supporting OpenAI, Anthropic, Google Gemini, and local mock providers with strict Pydantic JSON schema enforcement, prompt versioning, and zero prompt leakage.
- **Flagship Split-Screen Interactive QC Viewer**:
  - *Left Pane (60%)*: High-resolution zoomable and pannable schematic canvas with SVG overlays of discrepancy bounding boxes color-coded by severity.
  - *Right Pane (40%)*: Filterable discrepancy drawer with standard citations, evidence excerpts, recommendations, and confidence ratings.
  - *Synchronized Selection*: Clicking a bounding box scrolls to and selects the card; hovering a card pulses the box.
- **Human Review & Feedback Loop**: Ability for engineers to mark findings as `CORRECT`, `FALSE_POSITIVE`, or `NEEDS_REVIEW` with reviewer comments, feeding evaluation benchmarks without altering production prompts.
- **Dual Formal Export**:
  - *PDF Report*: Audit-grade report including title cover, overall verdict, checks summary, severity breakdown, findings with evidence, and compliance sign-off.
  - *Excel XLSX Matrix*: Multi-sheet workbook (`Summary`, `Findings`, `Checks`, `Evidence`, `Audit Trail`) for engineering workflow integration.
- **Dashboard & History**: Summary cards (Drawings Checked, Pass Rate, Open Findings, Latency), recent inspections table, and search/filter.
- **Tenant Usage & Metering**: Tracking checks performed and remaining credits across Pay-Per-Check and Subscription tiers.
- **Compliance Audit Logging**: Append-only activity stream recording all uploads, QC runs, reviews, and downloads.

### 3.2 SHOULD HAVE (Post-MVP Enhancements)
- **Server-Sent Events (SSE) Streaming**: Real-time progress bar updates (`S3 Staging` -> `OCR` -> `Rule Engine` -> `AI Synthesis`) eliminating polling.
- **Project Containers**: Grouping related documents under named projects (e.g., "Boeing 777X Avionics Harness Rev D").
- **Rule Pack Manager UI**: Tenant admin interface to enable/disable rules and adjust tolerance parameters.
- **Deduplication Cache**: SHA-256 hash matching to prevent redundant AI re-analysis on identical document pages.

### 3.3 FUTURE (Phase 3+ Long-Term Vision)
- **AI Revision Diffing**: Automated side-by-side comparison between Revision A and Revision B highlighting modified wire tags, changed pinouts, and newly introduced defects.
- **Extended Formats**: Direct vector ingestion of AutoCAD DXF/DWG and high-bitdepth multi-layer TIFF.
- **Public Developer REST API**: Webhooks and API tokens for automated CAD/CAM pipeline integration.
- **On-Premise Air-Gapped Deployment**: Packaged containerized deployment for defense and secure aerospace facilities.

---

## 4. User Personas & Permissions

| Role | Target Persona | Primary Responsibilities | Permissions |
| :--- | :--- | :--- | :--- |
| **PLATFORM_ADMIN** | Spandsons SaaS Operations | System health, tenant management, global rule packs, global billing oversight | Full global access across tenants |
| **TENANT_ADMIN** | Engineering Director / QC Lead | Organization settings, user management, billing, project creation, rule configuration | Full administrative access within tenant |
| **ENGINEER** | Harness Design / Manufacturing Eng. | Upload schematics, initiate QC runs, inspect findings, export reports | Read/Write within assigned projects |
| **REVIEWER / INSPECTOR**| Quality Inspector / QA Specialist | Review discrepancies, mark false alarms, add audit comments, approve reports | Read & Review/Feedback permissions |
| **CUSTOMER_USER** | External Client / Subcontractor | View approved QC reports and download compliance certificates | Read-only access to published reports |
| **READ_ONLY** | Compliance Auditor / Executive | View dashboard metrics, audit logs, and read reports | Read-only access |

---

## 5. End-to-End User Experience & Flagship Workflow

```
Customer Sign In
       │
       ▼
Upload Manual (Drag & Drop PDF/Image, select Standards: IPC-620 / UL 508A)
       │
       ▼
Asynchronous Processing Pipeline
├── 1. S3 Staging & SHA-256 Checksum Validation
├── 2. Vector Extraction + OCR Rasterization (IDR Model)
├── 3. Deterministic Rules Engine Execution (48+ Checks)
└── 4. Multimodal AI Verification & Evidence Extraction
       │
       ▼
Interactive Split-Screen Inspector
├── Left: Pan/Zoom Schematic Canvas with Bounding Box Overlays
└── Right: Discrepancy Drawer with Standard Citations & Actions
       │
       ▼
Inspector Feedback & Sign-Off ([✓ Correct] / [✗ False Positive])
       │
       ▼
Export Audit Artifacts (Formal PDF Report & Multi-Sheet Excel XLSX)
```

---

## 6. Non-Functional Requirements (NFRs)

- **Performance**: Document processing turnaround under 5 seconds per sheet for standard vector drawings; under 15 seconds for multi-page scanned drawings.
- **Availability**: 99.9% uptime SLA for multi-tenant production API.
- **Security & Confidentiality**: Customer engineering drawings treated as strictly confidential trade secrets. Encrypted at rest (AES-256) and in transit (TLS 1.3). No customer data utilized for public foundation model training.
- **Reliability & Idempotency**: All background jobs idempotent and resilient to worker termination with automatic credit refunding on unrecoverable failures.
- **Accessibility**: Compliance with WCAG 2.2 Level AA guidelines.
