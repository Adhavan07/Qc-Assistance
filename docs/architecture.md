# System Architecture Document

**Project**: Wiring Diagram QC Assistant  
**Client**: Spandsons Horizon Engineering Pvt. Ltd.  
**Version**: 2.0.0 (Phase 0 Architecture Release)  
**Date**: 2026-09-25  

---

## 1. Architectural Philosophy & Principles

The Wiring Diagram QC Assistant is engineered as a **Modular Monolith** with decoupled background workers. This pattern avoids the premature operational overhead, network latency, and distributed transaction complexity of microservices, while enforcing strict domain boundaries that allow individual services to be extracted into independent containers should scale require it.

Core engineering principles:
1. **Clean Domain Boundaries**: Business rules and engineering validations reside entirely within pure Python domain modules, independent of frameworks (FastAPI), databases (SQLAlchemy), or AI SDKs.
2. **Deterministic Rules Ahead of AI**: Generative AI is never treated as the authoritative ground truth for safety-critical engineering checks. A deterministic rules engine runs first; the AI layer provides multimodal contextual understanding, OCR disambiguation, and plain-language remedial explanations.
3. **Defense-in-Depth Multi-Tenancy**: Tenant isolation is enforced at the database query level, API dependency injection layer, and storage path partitioning. Tenant IDs are derived exclusively from cryptographically signed session tokens, never from unverified request payloads.
4. **Asynchronous Non-Blocking Processing**: Long-running document parsing, OCR, and AI analysis are strictly executed in background worker pools via task queues. Synchronous HTTP endpoints never block on heavy document workloads.

---

## 2. High-Level System Architecture Diagram

```mermaid
graph TD
    subgraph "Client Layer"
        Browser["Engineer Browser (Desktop / Tablet)"]
    end

    subgraph "Edge / Ingress Layer"
        CDN["CloudFront CDN / Static Assets"]
        WAF["AWS WAF (DDoS / Rate Limiting)"]
        ALB["Application Load Balancer (HTTPS / TLS 1.3)"]
    end

    subgraph "Application Compute Layer (ECS Fargate)"
        Web["Next.js 16 Web Application (SSR / App Router)"]
        API["FastAPI Modular Monolith API (ASGI)"]
        Worker["Background QC Worker Pool"]
    end

    subgraph "Data & State Storage Layer"
        PG[("PostgreSQL 16 Multi-AZ (ACID Relational)")]
        Redis[("ElastiCache Redis (Queue / Cache / SSE)")]
        S3[("Encrypted S3 Bucket (Documents & Reports)")]
    end

    subgraph "External AI Services Layer"
        OpenAI["OpenAI GPT-4o / Vision API"]
        Anthropic["Anthropic Claude 3.5 Sonnet"]
        Gemini["Google Gemini 1.5 Pro"]
    end

    Browser -->|HTTPS| CDN
    Browser -->|API Requests| WAF
    WAF --> ALB
    ALB -->|/api/v1/*| API
    ALB -->|/*| Web
    Web -->|Internal API Calls| API

    API -->|Auth / Metadata| PG
    API -->|Presigned Upload URLs| S3
    API -->|Enqueue QC Jobs| Redis
    API -->|SSE Stream Events| Redis

    Worker -->|Consume Jobs| Redis
    Worker -->|Fetch Document Files| S3
    Worker -->|Read/Write QC Runs & Findings| PG
    Worker -->|Multimodal Reasoning| OpenAI
    Worker -->|Multimodal Fallback| Anthropic
    Worker -->|Multimodal Fallback| Gemini
    Worker -->|Store Generated PDF & XLSX| S3
```

---

## 3. Component Map & Layered Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                        1. PRESENTATION LAYER                           │
│  - Next.js 16 Web Application (App Router, React 19, TypeScript)       │
│  - FastAPI REST Endpoints (/api/v1/auth, /projects, /documents, /qc)   │
│  - Server-Sent Events (SSE) Progress Broadcaster                       │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│                        2. APPLICATION LAYER                            │
│  - Auth & RBAC Security Guards (JWT, Salted Bcrypt, Role Hierarchies)  │
│  - QC Job Orchestration Service (State Machine Management)             │
│  - Document Ingestion Service (MIME Sniffing, Checksums, S3 Staging)   │
│  - Report Generation Service (ReportLab PDF & OpenPyXL XLSX)          │
│  - Metering & Credit Consumption Service                               │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│                          3. DOMAIN LAYER                               │
│  - Intermediate Document Representation (IDR) Schemas                  │
│  - Deterministic Rule Engine & Rule Pack Registry                      │
│  - Engineering Domain Entities: WireNet, Terminal, Connector, Finding │
│  - Evaluation & Precision/Recall Metrics Engine                        │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│                     4. INFRASTRUCTURE LAYER                            │
│  - SQLAlchemy 2.0 Async PostgreSQL Repositories                        │
│  - Redis Task Queue & Distributed Locking Adapters                     │
│  - AWS S3 / MinIO Object Storage Adapter                               │
│  - AI Provider Adapters (OpenAI, Anthropic, Gemini, Mock Engine)       │
│  - Document Parsers (PyMuPDF, pdfplumber, OpenCV, Tesseract OCR)      │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 4. End-to-End Request & Execution Flows

### 4.1 Document Upload & Registration Flow

```mermaid
sequenceDiagram
    autonumber
    actor Engineer as Quality Engineer
    participant Web as Next.js Web App
    participant API as FastAPI Backend
    participant Storage as S3 / MinIO
    participant DB as PostgreSQL DB

    Engineer->>Web: Drops wiring diagram file (PDF / PNG)
    Web->>API: POST /api/v1/documents/upload-intent {filename, size, project_id}
    API->>API: Verify session JWT & tenant membership
    API->>Storage: Generate presigned S3 POST URL (partitioned by tenant_id)
    API-->>Web: Return presigned URL, headers & internal document_id
    Web->>Storage: Direct multipart upload from browser to S3 bucket
    Storage-->>Web: Upload HTTP 201 Created (ETag received)
    Web->>API: POST /api/v1/documents/{id}/confirm {sha256, page_count}
    API->>Storage: Verify object exists, matches size & valid magic bytes
    API->>DB: Insert Document record (status = 'UPLOADED')
    API->>DB: Insert AuditLog ('DOCUMENT_UPLOADED')
    API-->>Web: Return confirmed Document metadata
```

### 4.2 QC Inspection & Background Worker Flow

```mermaid
sequenceDiagram
    autonumber
    actor Engineer as Quality Engineer
    participant Web as Next.js Web App
    participant API as FastAPI Backend
    participant Queue as Redis Queue
    participant Worker as QC Worker Pool
    participant S3 as S3 Object Storage
    participant Engine as Deterministic Rules + AI
    participant DB as PostgreSQL DB

    Engineer->>Web: Selects standards (IPC-620, UL 508A) & clicks "Launch Inspection"
    Web->>API: POST /api/v1/qc-runs {document_id, standards}
    API->>DB: Check tenant credits quota
    API->>DB: Atomically deduct 1 check credit
    API->>DB: Insert QCRun record (status = 'QUEUED')
    API->>Queue: Push QCJobPayload(qc_run_id, doc_id, file_path)
    API-->>Web: Return QCRunResponse (id, status = 'QUEUED')
    Web->>API: Connect to SSE stream: GET /api/v1/qc-runs/{id}/stream
    
    Worker->>Queue: Pop job from task queue
    Worker->>DB: Update QCRun status = 'PROCESSING'
    Worker->>API: Publish SSE event (status: 'EXTRACTING', 25%)
    Worker->>S3: Download original document
    Worker->>Worker: Page extraction & OCR -> Build Intermediate Doc Representation (IDR)
    Worker->>API: Publish SSE event (status: 'CHECKING_RULES', 50%)
    Worker->>Engine: Run Deterministic Rules Engine (Gauge, Pinout, Bend, Color)
    Worker->>API: Publish SSE event (status: 'AI_REASONING', 75%)
    Worker->>Engine: Multimodal AI reasoning for visual callouts & evidence quotes
    Worker->>DB: Persist findings in qc_findings table
    Worker->>DB: Update QCRun (status = 'COMPLETED', checks counts, duration)
    Worker->>API: Publish SSE event (status: 'COMPLETED', 100%)
    
    Web->>API: Fetch full findings: GET /api/v1/qc-runs/{id}/findings
    API->>DB: Query tenant-isolated findings
    API-->>Web: Return findings list with coordinates & recommendations
    Web->>Engineer: Render interactive Split-Screen Viewer
```

---

## 5. Document Processing Pipeline & Intermediate Document Representation (IDR)

To decouple raw file formats from quality checking, all documents pass through a normalization pipeline producing a structured **Intermediate Document Representation (IDR)**:

```mermaid
graph LR
    Input[Raw PDF / Scanned Image] --> Parser{Format Type}
    Parser -->|Vector PDF| VectorExtractor[PyMuPDF / pdfplumber Text & Line Art]
    Parser -->|Scanned / Raster| OCR[Tesseract / OpenCV Pre-processing]
    
    VectorExtractor --> Segmenter[Page Segmenter & Bounding Box Mapper]
    OCR --> Segmenter
    
    Segmenter --> IDR[Intermediate Document Model IDR]
    
    subgraph "IDR Model Elements"
        IDR --> Wires["Wire Runs (ID, AWG, Color, Shielding)"]
        IDR --> Components["Components (RefDes, Type, Rating)"]
        IDR --> Connectors["Connectors (Designator, Pins, Contacts)"]
        IDR --> TitleBlock["Title Block (Doc No, Rev, Cage Code, Signatures)"]
        IDR --> Notes["General Drawing Notes (Standards, Specs)"]
    end
    
    IDR --> RulesEngine[Deterministic QC Rules Engine]
    IDR --> AIReasoner[Multimodal LLM Reasoning Layer]
```

Every extracted entity in the IDR retains its **provenance**:
- `document_id`: UUID of the parent document.
- `page_number`: 1-indexed page where the element appears.
- `location_bbox`: Spatial coordinates `[x, y, width, height]` in normalized percentages $(0.0 - 1.0)$ relative to page dimensions, guaranteeing that bounding boxes display accurately on any screen resolution.
