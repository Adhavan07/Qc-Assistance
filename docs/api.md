# REST API Specification & Contracts

**Project**: Wiring Diagram QC Assistant  
**Client**: Spandsons Horizon Engineering Pvt. Ltd.  
**Version**: 2.0.0 (Phase 0 Architecture Release)  
**Date**: 2026-09-25  

---

## 1. API Design Principles & Conventions

1. **Versioned Base Path**: All customer-facing resources are nested under `/api/v1/`. Health probes live at root (`/health`, `/ready`).
2. **Stateless Authentication**: Protected endpoints require standard HTTP Bearer authentication:  
   `Authorization: Bearer <jwt_access_token>`
3. **Structured Error Envelope**: All 4xx and 5xx errors return a uniform schema with unique support tracing IDs:
   ```json
   {
     "error": {
       "code": "INSUFFICIENT_CREDITS",
       "message": "Organization has exhausted its available QC check credits. Please recharge or upgrade plan.",
       "request_id": "req-9a7c3b21-4f81",
       "timestamp": "2026-09-25T14:30:00Z"
     }
   }
   ```
4. **Standard Pagination**: List endpoints accept `page` (default: 1) and `limit` (default: 20, max: 100), returning pagination metadata headers: `X-Total-Count`, `X-Page`, `X-Per-Page`.

---

## 2. API Endpoint Catalog

### 2.1 Authentication & Profile (`/api/v1/auth`)

| Method | Path | Description | Access Level |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/auth/register` | Provisions new organization & creates initial OWNER user | Public |
| `POST` | `/api/v1/auth/login` | Authenticates credentials and returns JWT bearer token | Public |
| `POST` | `/api/v1/auth/logout` | Invalidates session / clears authentication cookies | Authenticated |
| `GET` | `/api/v1/auth/me` | Retrieves current authenticated user profile & tenant context | Authenticated |

### 2.2 Organizations & Members (`/api/v1/organizations`)

| Method | Path | Description | Access Level |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/organizations/me` | Organization profile, subscription tier, credit balance | Authenticated |
| `GET` | `/api/v1/organizations/members` | Lists team members in caller's organization | Authenticated |
| `POST` | `/api/v1/organizations/members` | Invites a new user with designated role | `ADMIN` or higher |

### 2.3 Projects & Documents (`/api/v1/projects`, `/api/v1/documents`)

| Method | Path | Description | Access Level |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/projects` | Lists projects belonging to organization | Authenticated |
| `POST` | `/api/v1/projects` | Creates a new project container | `ENGINEER` or higher |
| `POST` | `/api/v1/documents/upload-intent` | Requests presigned S3 POST URL for direct upload | `ENGINEER` or higher |
| `POST` | `/api/v1/documents/{id}/confirm` | Validates upload completion, checksum, and registers document | `ENGINEER` or higher |
| `GET` | `/api/v1/documents` | Lists documents (filterable by `project_id`) | Authenticated |
| `GET` | `/api/v1/documents/{id}` | Retrieves document metadata & page count | Authenticated |

### 2.4 QC Execution & Findings (`/api/v1/qc-runs`)

| Method | Path | Description | Access Level |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/qc-runs` | Deducts credit, creates QC run record, and dispatches background worker job | `ENGINEER` or higher |
| `GET` | `/api/v1/qc-runs/{id}` | Polls QC run execution status, duration, and pass/fail summary | Authenticated |
| `GET` | `/api/v1/qc-runs/{id}/findings` | Lists structured discrepancy findings (filterable by `severity`, `page`) | Authenticated |
| `GET` | `/api/v1/qc-runs/{id}/stream` | Server-Sent Events (SSE) streaming real-time stage progress updates | Authenticated |
| `POST` | `/api/v1/qc-runs/{run_id}/findings/{finding_id}/feedback` | Records inspector review feedback (`CORRECT`, `INCORRECT`, `NEEDS_REVIEW`) | `REVIEWER` or higher |

### 2.5 Compliance Reports & Audit Logs (`/api/v1/reports`, `/api/v1/audit-logs`)

| Method | Path | Description | Access Level |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/reports` | Lists generated compliance reports | Authenticated |
| `GET` | `/api/v1/reports/{id}` | Report summary and checks verdict | Authenticated |
| `GET` | `/api/v1/reports/{id}/pdf` | Downloads formal audit-grade PDF document | Authenticated |
| `GET` | `/api/v1/reports/{id}/excel` | Downloads structured multi-tab Excel XLSX workbook | Authenticated |
| `GET` | `/api/v1/audit-logs` | Queries immutable compliance audit events | `READ_ONLY` or higher |

### 2.6 System Probes

| Method | Path | Description | Access Level |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | Liveness probe returning operational status & service version | Public |
| `GET` | `/ready` | Readiness probe verifying database and cache connectivity | Public |
| `GET` | `/api/v1/info` | Service runtime metadata and API prefix | Public |

---

## 3. Server-Sent Events (SSE) Schema (`GET /qc-runs/{id}/stream`)

```
event: progress
data: {"status": "EXTRACTING", "percent": 25, "message": "Parsing vector geometry & text blocks"}

event: progress
data: {"status": "CHECKING_RULES", "percent": 50, "message": "Executing deterministic rules engine"}

event: progress
data: {"status": "AI_REASONING", "percent": 75, "message": "Correlating standard clauses & drawing evidence"}

event: complete
data: {"status": "COMPLETED", "percent": 100, "checks_total": 48, "checks_failed": 4, "overall_status": "FAIL"}
```
