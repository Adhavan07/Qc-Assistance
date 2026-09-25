# Engineering Changelog & Audit Log
**Project**: Wiring Diagram QC Assistant  
**Client / Product Owner**: Spandsons Horizon Engineering Pvt. Ltd. (Pravin, Gogulnath)  
**Maintained by**: Lead Software Architect, AI/ML Engineer, DevOps, Security, QA Team

All significant architectural decisions, codebase modifications, schema changes, and test verifications are recorded chronologically in this document.

---

## [Phase 6: QC Rule Engine] — 2026-09-25

### Added
- **Deterministic QC Rules Engine Across 6 Mandatory Categories (`backend/src/ai/rules.py`)**:
  - `BaseRule`: Abstract base class enforcing metadata integrity (`rule_id`, `name`, `category`, `severity`, `version`, `enabled`, `standard`, `standard_section`, `applicability`, `expected_condition`, `remediation_guidance`).
  - **Category: Wire (`wire`)**:
    - `MissingWireGaugeRule` (`RULE-WG-001`, IPC-WHMA-A-620D §4.1): Validates explicit wire gauge declarations on all conductors.
    - `ColorCodeMismatchRule` (`RULE-CC-003`, UL 508A §66.5): Enforces unambiguous standard insulation color codes.
    - `GroundConductorColorRule` (`RULE-WIRE-GND-001`, UL 508A §15.2 / NFPA 79 §13.2): Validates that protective ground and earth conductors are insulated GREEN or GREEN/YELLOW.
    - `WireAmpacitySizingRule` (`RULE-WIRE-AMP-001`, UL 508A Table 28.1): Flags undersized conductors vs declared circuit breaker and fuse current ratings.
  - **Category: Terminal (`terminal`)**:
    - `TerminalMissingPartNumberRule` (`RULE-TRM-MPN-001`, IPC-WHMA-A-620D §9.1): Validates manufacturer part numbers on all terminal blocks and connectors.
    - `TerminalBlockDesignationRule` (`RULE-TRM-PIN-001`, IPC-WHMA-A-620D §13.5): Enforces explicit terminal position/pin numbering (e.g. `TB1-1`, `TB1-2`) for multi-conductor connections.
    - `TerminalOvercrowdingRule` (`RULE-TRM-CRW-001`, UL 508A §28.3.2): Flags terminal screw clamps terminating more than the standard maximum of 2 conductors.
  - **Category: Component (`component`)**:
    - `ComponentDesignatorSyntaxRule` (`RULE-CMP-SYN-001`, ANSI/IEEE 315 / IEEE 200 §4): Validates standard class prefix letters (J, P, TB, K, CB, F, SW, R, C, D).
    - `OvercurrentDeviceRatingRule` (`RULE-CMP-OCP-001`, UL 508A §29.1): Verifies that circuit breakers and fuses declare continuous current ratings.
  - **Category: Reference (`reference`)**:
    - `DuplicateDesignatorRule` (`RULE-RD-004`, ANSI/IEEE 200 §4.2): Enforces global uniqueness of component reference designators across multi-sheet schematics.
    - `DanglingWireReferenceRule` (`RULE-REF-DNG-001`, IPC-WHMA-A-620D §13.4): Identifies un-terminated conductors without destination endpoints or spare/stub markings.
    - `CrossReferenceEndpointRule` (`RULE-REF-XRF-001`, IPC-WHMA-A-620D §13.4): Flags wire endpoints referencing non-existent connector designators not declared in the drawing BOM.
  - **Category: Documentation (`documentation`)**:
    - `TitleBlockIncompleteRule` (`RULE-TB-005`, ISO 7200 / ASME Y14.1 §5): Verifies Drawing Number, Revision, Drawn By, and Date in drawing title blocks.
    - `DrawingNumberSyntaxRule` (`RULE-DOC-NUM-001`, ISO 7200 §5.1): Rejects unreleased placeholder strings (DRAFT, TBD, XXXX, TEMP, UNASSIGNED).
    - `RevisionSyntaxRule` (`RULE-DOC-REV-001`, ASME Y14.35M §5.1): Prohibits confusing revision letters (I, O, Q, S, X, Z) per standard engineering practice.
  - **Category: Consistency (`consistency`)**:
    - `GeneralNotesContradictionRule` (`RULE-CON-NOT-001`, IPC-WHMA-A-620D §1.5): Flags contradictions between General Drawing Notes (e.g. minimum wire gauge) and wire schedules.
    - `WireGaugeContactCompatibilityRule` (`RULE-CON-CNT-001`, IPC-WHMA-A-620D §19.5): Detects physical incompatibilities between heavy power conductors (4/0 to 8 AWG) and miniature signal connectors (DB9, SUB-D, RJ45).
- **Versioned Rule Pack Architecture (`backend/src/ai/rules.py`)**:
  - `RulePack`: Standard container supporting pack ID, version, description, standard citation, and rule composition.
  - Implemented 6 versioned packs:
    - `PACK-CORE-BASELINE-V1.0`: Core benchmark rules for regression stability.
    - `PACK-IPC-620-V1.0`: IPC-WHMA-A-620D Class 3 Aerospace & High-Reliability Ruleset.
    - `PACK-UL-508A-V1.0`: UL 508A Industrial Control Panel Standards Ruleset.
    - `PACK-ISO-7200-V1.0`: ISO 7200 / ASME Y14 Engineering Documentation Ruleset.
    - `PACK-MIL-STD-681-V1.0`: MIL-STD-681D Aerospace Wire Identification Ruleset.
    - `PACK-SPANDSONS-V1.0`: Spandsons Horizon Internal Engineering QC Standard Ruleset.
- **Rule Registry & Engine Integration (`backend/src/ai/rules.py`, `backend/src/ai/engine.py`)**:
  - `RuleRegistry`: Implements pack registration, category querying, standard querying, rule enable/disable toggling, and multi-pack execution with deduplication.
  - `QCAnalysisEngine.analyze`: Added `rule_pack_ids` parameter for dynamic rule pack dispatch.
- **Unit & Regression Verification (`tests/unit/test_rules.py`)**:
  - Added 16 new test fixtures (21 total in `test_rules.py`) covering all 17 rules, rule packs, toggling, standards mapping, and metadata completeness.
  - Test suite expanded from 57 to **73 tests passing (100%)**.

---

## [Phase 5: AI Analysis] — 2026-09-25

### Added
- **AI Provider Abstraction Layer (`backend/src/ai/llm_adapter.py`)**:
  - `AIProviderInterface`: Decoupled contract standardizing multimodal structured analysis, latency tracking, and token pricing across foundation model providers.
  - `MockAIProvider`: High-speed, deterministic offline provider with contextual finding generation, configurable synthetic injection, simulated latency, timeout simulation, and failure simulation.
  - `OpenAIProvider`: Production async adapter for GPT-4o and GPT-4o-mini with native JSON mode (`response_format={"type": "json_object"}`), automatic retry with exponential backoff, and token pricing computation.
  - `AnthropicProvider`: Production async adapter for Claude 3.5 Sonnet and Haiku with JSON extraction and token cost accounting.
  - `AIProviderFactory`: Dynamic provider resolution configured via environment (`AI_PROVIDER="mock"` default).
- **Client Validated Prompt Asset (`backend/src/ai/prompts/wiring_qc_v1_0.py`)**:
  - Encapsulated Spandsons Horizon Engineering's proprietary inspection directives as a versioned asset (`wiring-qc-prompt-v1.0`).
  - Covers international standards: IPC/WHMA-A-620D, UL 508A, MIL-STD-681D, and ISO 7200 across 5 mandatory categories: Wire Sizing, Color Coding Ambiguity, Terminal/Connector Designators, Title Block ISO Data Fields, and General Notes Consistency.
  - Anti-indirect prompt injection defense: Drawing text is framed strictly as passive data inside `<drawing_data>` delimiters.
  - Proprietary trade secret concealment: System instructions are maintained strictly server-side and never returned in customer API responses.
- **Prompt Manager & Governance (`backend/src/ai/prompt_manager.py`)**:
  - `PromptManager`: Registry managing prompt compilation, JSON output schemas, and safe XML data serialization of IDR representations.
- **Pydantic Schema Validation & JSON Repair (`backend/src/ai/schemas.py`, `backend/src/ai/llm_adapter.py`)**:
  - Added `AIFindingPayload` and `AIAnalysisPayload` with strict field validation (`finding_code`, `rule_id`, `severity`, `confidence_score`, `location_bbox`, `evidence_text`, `recommendation`).
  - Implemented `parse_and_validate_ai_json` and `extract_json_from_llm_text` with automatic markdown code fence stripping and format recovery.
- **AI Analysis Service & Database Observability (`backend/src/ai/service.py`)**:
  - `AIAnalysisService`: Coordinates prompt compilation, provider execution, schema validation, and exponential backoff retry recovery.
  - Implemented database logging via `AIRequestLog` recording `provider`, `model_name`, `prompt_version`, `prompt_tokens`, `completion_tokens`, `total_tokens`, `estimated_cost_usd`, `latency_ms`, and `status`.
- **Database Model & Composite Indexes (`backend/src/infrastructure/models.py`)**:
  - Added `AIRequestLog` entity with foreign keys to `organizations`, `documents`, and `qc_runs`.
  - Added composite indexes: `idx_ai_log_org_created` and `idx_ai_log_provider_model`.
- **AI Fixture Test Suite (`tests/unit/test_ai_analysis.py`)**:
  - Added 7 comprehensive test fixtures validating mock output, JSON fence extraction, prompt asset v1.0 governance, database logging, timeout detection, retry recovery, and cloud pricing formulas.
  - Test suite expanded from 50 to **57 tests passing (100%)**.

---

## [Phase 4: Document Processing] — 2026-09-25

### Added
- **Asynchronous & Synchronous Document Processing Pipeline (`backend/src/services/document_processor.py`)**:
  - `DocumentProcessor` orchestrating PDF rasterization, spatial OCR extraction, IDR structuring, and job lifecycle state transitions.
  - Stateful tracking: `PENDING` -> `PROCESSING` (`INITIALIZING`, `RASTERIZING_PAGES`, `EXTRACTING_STRUCTURED_DATA`, `PERSISTING_IDR`) -> `COMPLETED` / `RETRYING` / `FAILED`.
  - Transactional retry mechanism with exponential backoff support (`attempts` vs `max_attempts` tracking).
  - Background worker dispatch capability (`execute_background_processing`).
  - Immutable audit logging for `DOCUMENT_PROCESSING_STARTED`, `DOCUMENT_PROCESSED`, and `DOCUMENT_PROCESSING_FAILED`.
- **Database Model & Migrations (`backend/src/infrastructure/models.py`)**:
  - `ProcessingJob` model with tenant and document foreign keys, cascade deletion, status, step progression, attempt counter, error message, and JSON execution metrics.
  - Multi-tenant composite indexes: `idx_proc_job_org_status` and `idx_proc_job_doc_status`.
- **High-Fidelity PDF Rasterization & Image Processing Service (`backend/src/services/image_processor.py`)**:
  - Vector PDF rendering via Google Chrome's PDFium engine (`pypdfium2`) generating crisp 150-300 DPI viewports.
  - Dual output generation: high-resolution viewport PNGs (`page_{num}.png`) and aspect-ratio constrained navigation thumbnails (`thumb_{num}.png`, max 320px).
  - Decompression bomb protection: 10,000 px dimension limits and 100 Megapixel safety boundary.
  - Image preprocessing for OCR: grayscale normalization, auto-contrast enhancement, and unsharp masking.
- **Multimodal Text Extraction & Spatial Coordinate Bounding Boxes (`backend/src/ai/extractor.py`)**:
  - Dual extraction engine: high-precision vector text extraction via `pypdfium2` with exact spatial bounding boxes, falling back to `pypdf`.
  - True spatial coordinate calculation mapping PDF vector space to rendered raster pixel coordinates (`BoundingBox(x, y, width, height)`).
  - Domain-specific entity parsing with bound locations:
    - Title block metadata: `DWG NO`, `REV`, `TITLE`, `DRAWN BY`, `APPROVED BY`, `DATE`, `COMPANY`.
    - Wire callouts: wire ID (`W101`), gauge (`18 AWG`, `0.75 mm²`), color codes (`RED`, `BLK`, `WHT/BLU`, `GRN/YEL`), from/to connector hints.
    - Connectors & Terminal Blocks: `J1`, `P2`, `TB1`, `TB2`, `TERM1`, `CON1` with part number extraction.
    - Numbered engineering general notes parsing.
- **Document Processing REST API Endpoints (`backend/src/api/routers/documents.py`)**:
  - `POST /api/v1/documents/{id}/process`: Triggers ingestion pipeline with synchronous or background execution modes (`async_mode` flag).
  - `GET /api/v1/documents/{id}/processing-jobs`: Returns historical processing runs and attempts.
  - `GET /api/v1/documents/{id}/processing-jobs/{job_id}`: Returns real-time step and percent completion.
  - `POST /api/v1/documents/{id}/processing-jobs/{job_id}/retry`: Manually re-attempts failed or stalled jobs.
  - `GET /api/v1/documents/{id}/extracted`: Retrieves structured Intermediate Document Representation (IDR).
  - `GET /api/v1/documents/{id}/pages/{page_number}/image`: Generates presigned URLs for rendered page viewports.
  - `GET /api/v1/documents/{id}/pages/{page_number}/raw-image`: Direct binary streaming of rasterized PNG page.
  - `GET /api/v1/documents/{id}/pages/{page_number}/raw-thumbnail`: Direct binary streaming of page thumbnail PNG.
- **Frontend SaaS Ingestion & Viewer Enhancements**:
  - Extended API client (`frontend/src/lib/api.ts`) with typed methods for processing triggers, status polling, IDR retrieval, and raw image streaming.
  - Added TypeScript definitions in `frontend/src/types/index.ts` for `ProcessingJob`, `TitleBlock`, `WireCallout`, `Connector`, `GeneralNote`, `DocumentPage`, and `IntermediateDocumentModel`.
  - Connected `UploadView.tsx` directly into the document processing pipeline on upload completion.
- **Test Suite Expansion**:
  - Created unit tests in `tests/unit/test_document_processing.py` covering PDF rasterization, decompression defense, spatial bounding boxes, and 50MB file size limits.
  - Created integration tests in `tests/integration/test_document_processing_api.py` validating full processing lifecycle, IDR retrieval, raw image streaming, job retry, and cross-tenant IDOR isolation.
  - Test suite expanded from 44 to **50 tests passing (100%)**.

---

## [Phase 3: Projects + Document Upload] — 2026-09-25

### Added
- **Project Lifecycle Management (`backend/src/api/routers/documents.py`)**:
  - Project creation endpoint (`POST /api/v1/projects`) requiring `ENGINEER` role or higher, tenant-scoped.
  - Project listing endpoint (`GET /api/v1/projects`) returning active projects aggregated with document counts.
  - Project retrieval by ID (`GET /api/v1/projects/{id}`) with strict tenant isolation.
  - Project update endpoint (`PATCH /api/v1/projects/{id}`) for name and description edits.
  - Project deletion endpoint (`DELETE /api/v1/projects/{id}`) with cascading document/QC removal and audit logging.
- **Two-Phase Direct-to-Storage Presigned Upload**:
  - `POST /api/v1/documents/upload-intent`: Generates S3/MinIO presigned POST upload URLs partitioned by tenant path (`tenants/{org_id}/documents/{doc_id}/original/{filename}`).
  - `POST /api/v1/documents/{id}/confirm`: Verifies project membership, performs SHA-256 deduplication, and transitions document status to `UPLOADED`.
- **Direct Multipart File Ingestion**:
  - `POST /api/v1/documents/upload`: Direct `multipart/form-data` upload endpoint supporting local development, CI/CD, and offline testing without cloud S3 dependencies.
  - Automatic binary SHA-256 checksum calculation and page count extraction using `pypdf`.
- **SHA-256 Checksum Deduplication & Conflict Prevention**:
  - Automatic detection of identical diagrams previously uploaded within the organization.
  - Returns `409 Conflict` with existing document reference to protect clients against redundant storage and inspection credit expenditure.
  - Optional `allow_duplicate` override parameter to allow re-ingestion when explicitly commanded.
- **Storage Backend Enhancements (`backend/src/infrastructure/storage.py`)**:
  - Standardized interface for `save_file`, `read_file`, `delete_file`, and `file_exists`.
  - Implemented both for local filesystem storage (`LocalMockStorageService`) and S3-compatible cloud storage (`S3StorageService`).
  - Added presigned download URL generation endpoint (`GET /api/v1/documents/{id}/download-url`).
  - Added tenant-isolated document deletion (`DELETE /api/v1/documents/{id}`) with object storage cleanup.
- **Frontend SaaS Ingestion Workflow (`frontend/src/components/UploadView.tsx`)**:
  - Target project selection card with inline "+ New Project" creation form.
  - Client-side SHA-256 checksum computation via Web Crypto API.
  - Duplicate diagram detection warning banner with 1-click override checkbox.
  - Real-time pipeline staging progress indicators matching the white professional enterprise theme.
- **Verification**:
  - Test suite expanded from 40 to **44 tests** covering project CRUD, SHA-256 deduplication, direct multipart ingestion, and cross-tenant IDOR defense.
  - All **44/44 tests passing** in 15.93s.
  - `npm run build` / Next.js production compilation passing with **0 errors**.

---

## [Phase 2: Authentication + Multi-Tenancy] — 2026-09-25

### Added
- **Tenant Self-Service Provisioning & Identity Management (`backend/src/api/routers/auth.py`)**:
  - Atomic organization provisioning + initial `OWNER` account creation (`POST /api/v1/auth/register`).
  - Cryptographically signed JWT tokens with claims: `sub` (user_id), `org_id` (tenant_id), `role`, `type` ("access" vs "refresh" vs "password_reset").
  - Refresh token exchange flow (`POST /api/v1/auth/refresh`) generating new access and refresh tokens.
  - User logout endpoint (`POST /api/v1/auth/logout`) logging immutable `USER_LOGGED_OUT` audit trails.
  - User profile management (`GET /api/v1/auth/me`, `PATCH /api/v1/auth/me`).
  - Secure password management: salted bcrypt hashing, password change (`POST /api/v1/auth/change-password`), password reset token generation and confirmation (`POST /api/v1/auth/password-reset/request`, `POST /api/v1/auth/password-reset/confirm`).
- **Strict Multi-Tenancy & Logical Partitioning (`backend/src/api/routers/organizations.py`)**:
  - Hard security rule enforced across all endpoints: `organization_id` is derived exclusively from authenticated JWT claims, never from client request parameters.
  - Multi-tenant data isolation verified: cross-tenant access attempts return 404 Not Found to prevent data exposure and resource existence leakage.
  - Sole-Owner Protection: Prevents an organization from accidentally demoting or deleting its last remaining active OWNER account.
  - Privilege Escalation Guards: Prevents lower-tier roles (ENGINEER, INSPECTOR, VIEWER) from managing members, and prevents ADMINs from creating, elevating, modifying, or deleting OWNER accounts.
- **Organization & Member Management (`backend/src/api/routers/organizations.py`)**:
  - Tenant profile retrieval and name updates (`GET /api/v1/organizations/me`, `PATCH /api/v1/organizations/me`).
  - Tenant-scoped member listing (`GET /api/v1/organizations/members`).
  - Team member invitations with role assignments (`POST /api/v1/organizations/members`).
  - Member role and status updates (`PATCH /api/v1/organizations/members/{id}`).
  - Member deletion (`DELETE /api/v1/organizations/members/{id}`).
- **Immutable Security Audit Logging**:
  - Every auth and tenancy event generates an immutable `AuditLog` entry: `ORGANIZATION_REGISTERED`, `USER_LOGGED_IN`, `USER_LOGGED_OUT`, `USER_PROFILE_UPDATED`, `PASSWORD_CHANGED`, `PASSWORD_RESET_REQUESTED`, `PASSWORD_RESET_CONFIRMED`, `ORGANIZATION_UPDATED`, `MEMBER_ADDED`, `MEMBER_UPDATED`, `MEMBER_REMOVED`.
- **Frontend SaaS Integration (`frontend/src/`)**:
  - `AuthModal.tsx`: High-contrast, clean white enterprise sign-in and tenant registration modal with demo shortcuts.
  - `TeamModal.tsx`: Organization and team member management modal allowing owners/admins to view members, invite engineers/inspectors, update roles, and inspect QC credit balances.
  - `Navbar.tsx`: Integrated user menu with Organization & Team modal launcher, Tenant switcher, and secure session logout.
  - `auth-context.tsx`: Full session persistence with `localStorage`, real API client calls, and automatic profile re-hydration.
- **Verification**:
  - Test suite expanded from 35 to **40 tests** covering refresh tokens, password resets, IDOR attacks, and privilege escalation guards.
  - All **40/40 tests passing** in 15.49s.
  - `npm run build` / Next.js production compilation passing with **0 errors**.

---

## [Phase 1: Project Foundation & Containerized Monorepo] — 2026-09-25

### Added
- **Multi-Service Containerization (`docker-compose.yml`)**:
  - Full local development stack orchestrating all 7 services:
    - `web`: Next.js 16 frontend on port 3000
    - `api`: FastAPI REST API on port 8000 with healthcheck probes
    - `worker`: Background QC worker processing asynchronous task queues
    - `postgres`: PostgreSQL 16 on port 5432 with healthchecks
    - `redis`: Redis 7 on port 6379 for task queueing and SSE pub/sub
    - `minio`: MinIO S3-compatible object storage on ports 9000 & 9001
    - `mailpit`: Mailpit local SMTP & webmail testing on ports 1025 & 8025
- **Production & Development Dockerfiles**:
  - `backend/Dockerfile`: Multi-stage build, unprivileged `appuser` (UID 1001), pinned dependencies, healthcheck probe.
  - `backend/Dockerfile.dev`: Live reloading uvicorn development container.
  - `frontend/Dockerfile`: Multi-stage build, unprivileged `nextjs` user (UID 1001), standalone Next.js production runner.
  - `frontend/Dockerfile.dev`: Next.js Turbopack development container.
- **Developer Experience & Tooling**:
  - Root `Makefile`: Targets for `setup`, `dev`, `dev-docker`, `test`, `lint`, `format`, `build`, `migrate`, `seed`, and `clean`.
  - `.env.example`: Centralized template documenting all environment variables across backend, frontend, database, redis, S3, and AI models.
  - `.pre-commit-config.yaml`: Pre-commit hooks for trailing whitespace, YAML/JSON validation, private key detection, and Ruff formatting.
  - `.github/workflows/ci.yml`: GitHub Actions automated CI pipeline executing pytest with code coverage and Next.js production builds.
- **Database Seeding (`backend/src/infrastructure/seed.py`)**:
  - Idempotent database seeder provisioning demo organization (`Spandsons Horizon Engineering Pvt. Ltd.`), initial users (`pravin@spandsons.com`, `gogulnath@spandsons.com`, `inspector@spandsons.com`), and initial project (`Commercial Avionics Harness WD-777`).
- **Dependencies**:
  - Added `asyncpg>=0.29.0` and `redis>=5.0.0` to `backend/requirements.txt` for PostgreSQL and Redis support.
- **Verification**:
  - `make test`: All **35/35 tests passing**.
  - `make build`: Next.js production build succeeds with **0 errors**.
  - Database seeder tested and verified idempotent.

---

## [Phase 6: Frontend SaaS Application (MVP-1)] — 2026-09-25

### Added
- **Modern Next.js 16 (App Router) + TypeScript Architecture (`frontend/`)**:
  - Initialized with React 19, Lucide React icons, Turbopack, and strict TypeScript configurations.
  - Clean, high-contrast white professional enterprise design system configured in `frontend/src/app/globals.css` with responsive cards, soft elevation shadows, crisp typography, and authentic drafting grid patterns.
  - Resolved SSR hydration warnings by replacing dynamic `Date.now()` and locale date evaluations with static ISO strings and deterministic formatting.
  - Added `suppressHydrationWarning` on `<html>` and `<body>` to prevent third-party browser translation/extension injection errors.
  - Added mouse wheel zoom (`onWheel`) support to the interactive schematic canvas.
- **Data Models & API Client (`frontend/src/types/`, `frontend/src/lib/`)**:
  - `types/index.ts`: Strong typing mirroring FastAPI Pydantic models (`QCRun`, `QCFinding`, `BoundingBox`, `Organization`, `User`, `Severity`).
  - `lib/api.ts`: Robust API client communicating with FastAPI endpoints (`/auth`, `/documents`, `/qc-runs`, `/organizations`), equipped with graceful fallbacks to high-fidelity engineering mock data for offline preview and demonstration resilience.
  - `lib/mockData.ts`: Realistic aerospace/industrial drawing datasets (Boeing 777X Avionics Harness Rev D, ABB Industrial Panels, Siemens S7 PLCs) with 6 verified discrepancy findings.
  - `lib/auth-context.tsx`: Context provider tracking active engineer session, organization details, and dynamic credit metering.
- **Component Architecture (`frontend/src/components/`)**:
  - **`Navbar.tsx`**: Top header featuring Spandsons Horizon branding, live AI engine online badge, active standards badges (`IPC-WHMA-A-620D Class 3`, `UL 508A`), dynamic credit counter (`⚡ 248 credits`), and user profile avatar.
  - **`Sidebar.tsx`**: Navigation menu supporting fluid switching between Dashboard, Manual Ingestion, QC Inspector, Standards Matrix, and Compliance Audit Trail.
  - **`DashboardView.tsx`**: Executive engineering dashboard featuring 4 KPI metrics (Drawings Checked, First Pass Yield 88.4%, Open Discrepancies by severity, Mean Engine Turnaround 1.84s), defect breakdown bar distribution, standards adherence gauges, and recent inspection data table.
  - **`UploadView.tsx`**: Drag-and-drop file ingestion zone with multi-format support (`.pdf`, `.dxf`, `.tiff`, `.png`), regulatory standards selector checklist, and interactive 4-stage processing progress simulator (S3 Staging -> OCR/IDR -> Deterministic Rules -> AI Synthesis).
  - **`SplitScreenViewer.tsx`**:
    - **Interactive Canvas (60% Pane)**: High-resolution SVG wiring diagram with smooth Pan and Zoom (zoom in/out, fit-to-screen, mouse drag), circuit breaker bank, wiring runs, pin interfaces, and bounding box overlays styled and colored by severity.
    - **Discrepancy Drawer (40% Pane)**: Filterable findings list sorted by severity with keyword search, standard citations, exact requirement excerpts, extracted diagram evidence, AI recommendations, confidence indicators, and interactive feedback buttons (`[✓ Correct]`, `[✗ False Positive]`, `[? Flag Review]`).
    - **Synchronized Bidirectional Highlight**: Clicking a bounding box on the schematic automatically scrolls to and selects the card in the drawer; selecting a card highlights and pulses the bounding box on the canvas.
    - **Report Export Actions**: One-click modal exports for formal PDF compliance reports and Excel XLSX discrepancy matrices.
  - **`StandardsView.tsx`**: Interactive rule catalog displaying deterministic rule parameters, clause citations, and zero-false-positive acceptance thresholds.
  - **`AuditLogView.tsx`**: AS9100 / ISO 9001 compliance audit trail logging document uploads, inspections, and feedback actions.
- **Verification**:
  - `npm run build` completed with zero TypeScript errors or build warnings on Turbopack.
  - Full Python test suite verified: **35/35 tests passing**.

---

## [Phase 5: Asynchronous QC Worker Pipeline] — 2026-09-25

### Added
- **Document & QC Schemas (`backend/src/api/document_schemas.py`)**:
  - Pydantic models for project creation, presigned upload intent, document confirmation, QC run execution requests, run status responses, and finding details with spatial coordinates.
- **Background QC Worker Service (`backend/src/services/qc_worker.py`)**:
  - `process_qc_job`: Consumes enqueued payloads, transitions status to `PROCESSING`, executes `QCAnalysisEngine.analyze()`, maps and persists findings to `qc_findings`, records compliance audit logs, and handles failures with automatic credit refunding on system errors.
- **Documents & Projects Router (`backend/src/api/routers/documents.py`)**:
  - `POST /api/v1/projects`: Creates tenant-isolated project containers.
  - `GET /api/v1/projects`: Lists projects belonging strictly to caller's organization.
  - `POST /api/v1/documents/upload-intent`: Issues S3 presigned POST upload URLs partitioned by tenant path: `tenants/{org_id}/documents/{doc_id}/original/{filename}`.
  - `POST /api/v1/documents/{id}/confirm`: Validates file size, checksum, and registers document record in PostgreSQL.
  - `GET /api/v1/documents`: Lists documents filtered by project and organization.
  - `GET /api/v1/documents/{id}`: Retrieves document metadata with tenant access check.
- **QC Runs & Findings Router (`backend/src/api/routers/qc_runs.py`)**:
  - `POST /api/v1/qc-runs`: Deducts 1 check credit from organization atomically, creates `QCRun` (`QUEUED`), and enqueues job onto `TaskQueue`. Blocks execution with `402 Payment Required` if organization credits are exhausted.
  - `GET /api/v1/qc-runs/{id}`: Polls execution status, checks summary, and pass/fail verdict.
  - `GET /api/v1/qc-runs/{id}/findings`: Returns structured findings filterable by severity and page number.
  - `GET /api/v1/qc-runs/{id}/stream`: Server-Sent Events (SSE) streaming real-time progress events (`10%` -> `50%` -> `100%`) to eliminate aggressive polling.
- **Pipeline Integration Test Suites**:
  - `tests/integration/test_document_pipeline.py`: Tests project creation, upload intent, confirm, and document query endpoints.
  - `tests/integration/test_qc_execution_pipeline.py`: Tests end-to-end background worker processing, finding persistence in database, credit deductions, SSE progress stream, and 402 credit exhaustion block.
  - Test result: **35/35 tests passed across all suites**.

---

## [Phase 4: Authentication, RBAC & Multi-Tenancy] — 2026-09-25

### Added
- **Security & Cryptography (`backend/src/core/security.py`)**:
  - Salted password hashing and verification using `bcrypt`.
  - Signed JWT token creation and validation (`pyjwt`) encoding user ID, tenant ID, and role claims.
  - Expiration and tamper-evident signature validation.
- **Auth & RBAC Schemas (`backend/src/api/auth_schemas.py`)**:
  - `UserRole` enumeration (`OWNER`, `ADMIN`, `ENGINEER`, `INSPECTOR`, `VIEWER`, `SUPER_ADMIN`) with explicit hierarchy levels.
  - Pydantic models for registration, login, JWT token responses, user profiles, organization summaries, and member invitations.
- **Authentication & RBAC Route Guards (`backend/src/api/deps_auth.py`)**:
  - `oauth2_scheme` integration for OpenAPI Bearer auth.
  - `get_current_user`: Token extraction, signature verification, and active database user loading.
  - `require_role(minimum_role)`: Strict hierarchical authorization guard preventing privilege escalation.
- **Authentication Router (`backend/src/api/routers/auth.py`)**:
  - `POST /api/v1/auth/register`: Atomic organization provisioning and initial OWNER user creation with free trial credits. Duplicate email and slug rejection.
  - `POST /api/v1/auth/login`: Credential validation and JWT access token issuance.
  - `GET /api/v1/auth/me`: Authenticated user identity and active tenant context.
- **Organization & Member Router (`backend/src/api/routers/organizations.py`)**:
  - `GET /api/v1/organizations/me`: Current tenant organization details and remaining check quota.
  - `GET /api/v1/organizations/members`: Isolated listing of users belonging strictly to caller's organization.
  - `POST /api/v1/organizations/members`: Member invitation endpoint guarded by `require_role(UserRole.ADMIN)` with privilege escalation checks.
- **Cross-Tenant Security & RBAC Test Suites**:
  - `tests/unit/test_security.py`: Password hashing, JWT claims, expiration, and tampered token detection.
  - `tests/integration/test_auth_api.py`: Registration, duplicate rejection, login, profile, and role-based invitation restrictions.
  - `tests/integration/test_multi_tenancy_isolation.py`: Explicit IDOR / cross-tenant attack tests verifying that Company Beta cannot view or leak Company Alpha's users or resources.
  - Test result: **32/32 tests passed across all suites**.

---

## [Phase 3: Database & Backend Foundation] — 2026-09-25

### Added
- **Core Configuration (`backend/src/core/config.py`)**:
  - Pydantic `BaseSettings` for database URL, security secrets, S3 buckets, CORS origins, and runtime environments.
- **Structured Logging (`backend/src/core/logging.py`)**:
  - `structlog` pipeline formatting JSON in production and readable color console in development with request ID and latency context.
- **Async Database Layer (`backend/src/infrastructure/database.py`)**:
  - SQLAlchemy 2.0 `create_async_engine`, `async_sessionmaker`, `Base` declarative mapping, and FastAPI dependency provider `get_db_session()`.
- **Relational Data Models (`backend/src/infrastructure/models.py`)**:
  - Multi-tenant data model implementing:
    - `Organization`: Root tenant entity with plan tiers (`PAY_PER_CHECK`, `SUBSCRIPTION`), credits, and relations.
    - `User`: Email, password hash, role (`OWNER`, `ADMIN`, `ENGINEER`, `INSPECTOR`, `VIEWER`), org foreign key.
    - `Project`: Project grouping scoped to organization.
    - `Document`: Manual metadata, file size, SHA256 checksum, page count, and status.
    - `QCRun`: Execution records, status, checks summary, version audit, token usage, and processing latency.
    - `QCFinding`: Discrepancy details linked to run with bounding box JSON, severity, and standards citation.
    - `FindingFeedback`: Human inspector review status (`CORRECT`, `INCORRECT`, `NEEDS_REVIEW`).
    - `AuditLog`: Immutable audit trail for compliance and security events.
- **Object Storage Service (`backend/src/infrastructure/storage.py`)**:
  - `S3StorageService`: Boto3 S3 client generating presigned upload/download URLs partitioned by tenant path:
    `tenants/{org_id}/documents/{doc_id}/original/{filename}`.
  - `LocalMockStorageService`: Offline fallback for local development and unit tests.
- **Asynchronous Task Queue Abstraction (`backend/src/infrastructure/queue.py`)**:
  - `TaskQueueInterface` and `AsyncInMemoryQueue` for decoupled background QC job processing.
- **FastAPI Application Skeleton (`backend/src/api/main.py` & `backend/src/api/deps.py`)**:
  - FastAPI application instance with CORS middleware, Request ID injection (`X-Request-ID`), and latency headers (`X-Process-Time-Ms`).
  - Probes: `GET /health` (liveness), `GET /ready` (readiness with DB check), and `GET /api/v1/info`.
  - Dependency injection providers in `backend/src/api/deps.py`.
- **Database Migrations (`backend/alembic/`)**:
  - Alembic configuration supporting async migrations (`alembic.ini`, `env.py`).
  - Initial migration `001_initial_schema.py` creating all tables and composite indexes.
  - Verified reversible migration (`upgrade head` -> `downgrade -1` -> `upgrade head`).
- **Integration Test Suite (`tests/integration/`)**:
  - `test_database_models.py`: Validates model creation, foreign key relations, and cascading deletes.
  - `test_storage.py`: Validates tenant storage path isolation and presigned URL parameters.
  - `test_api_health.py`: Validates health probes and request ID middleware.
  - Test result: **24/24 tests passed across all suites**.

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
