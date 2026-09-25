# System Architecture Document
**Project**: Wiring Diagram QC Assistant  
**Client / Product Owner**: Spandsons Horizon Engineering Pvt. Ltd.  
**Version**: 1.0.0 | **Date**: 2026-09-25

---

## 1. Architectural Philosophy
The system follows **Clean Architecture** principles, decoupling business domain logic from web frameworks, database mechanics, and external AI providers.

```
┌──────────────────────────────────────────────────────────┐
│                   Presentation Layer                     │
│   Next.js 14 Web App  │  FastAPI REST Endpoints & SSE    │
└────────────────────────────┬─────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────┐
│                    Application Layer                     │
│    QC Orchestrator  │  Auth & RBAC  │  Billing Service   │
└────────────────────────────┬─────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────┐
│                      Domain Layer                        │
│   Intermediate Doc Model  │  Rule Engine  │  Validators  │
└────────────────────────────┬─────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────┐
│                  Infrastructure Layer                    │
│ PostgreSQL / pgvector │ Redis │ S3 │ LLM Adapters │ OCR  │
└──────────────────────────────────────────────────────────┘
```

## 2. Component Boundaries
1. **Core Domain (`backend/src/domain/`)**:
   - Entities: `Document`, `Page`, `Rule`, `Finding`, `AuditLog`, `Organization`.
   - Value Objects: `BoundingBox`, `Confidence`, `Severity`.
   - Pure interfaces: `LLMProviderInterface`, `StorageRepositoryInterface`, `EmbeddingServiceInterface`.
2. **Application Services (`backend/src/services/`)**:
   - `QCOrchestratorService`: Manages end-to-end QC execution state machine.
   - `DocumentIngestionService`: Handles validation, page rasterization, and metadata indexing.
   - `RulesEngineService`: Executes deterministic checks against the Intermediate Document Model.
   - `ReportGenerationService`: Compiles findings into PDF and XLSX binaries.
3. **Infrastructure (`backend/src/infrastructure/`)**:
   - Database: SQLAlchemy 2.0 async models, connection pooling, and Alembic migrations.
   - Storage: Boto3 S3 adapter with presigned URL signing.
   - AI Providers: Adapters for OpenAI, Anthropic, Google Gemini, and local OCR.
4. **Presentation (`backend/src/api/` & `frontend/`)**:
   - FastAPI routers, Pydantic schemas, dependency injection for auth/DB sessions.
   - Next.js frontend with split-screen inspection viewer.

## 3. Asynchronous Execution Model
To prevent HTTP gateway timeouts, all document ingestion and QC checks execute asynchronously:
1. Client calls `POST /api/v1/qc-runs`.
2. Backend validates permissions and quota, creates a `qc_runs` record with status `QUEUED`, and enqueues a job payload onto Redis/SQS.
3. A background worker picks up the job, streams progress events to Redis Pub/Sub, and updates the database upon completion.
4. Frontend connects to `GET /api/v1/qc-runs/{id}/stream` to receive real-time SSE progress events.
