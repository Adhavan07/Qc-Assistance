# API Specification (FastAPI / OpenAPI v1)
**Project**: Wiring Diagram QC Assistant  
**Client / Product Owner**: Spandsons Horizon Engineering Pvt. Ltd.  
**Version**: 1.0.0 | **Date**: 2026-09-25

---

## 1. Global Conventions
* Base URL: `/api/v1`
* Content-Type: `application/json` (except file uploads and report downloads)
* Authentication: `Authorization: Bearer <JWT>` or HTTP-only Session Cookie.
* Consistent Error Envelope:
```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "The requested document does not exist or does not belong to your organization.",
    "request_id": "req_01JC...48A"
  }
}
```

## 2. Core Endpoints Summary

### Auth & Tenant Management
* `POST /api/v1/auth/register`: Create account & organization.
* `POST /api/v1/auth/login`: Issue authentication tokens.
* `GET  /api/v1/auth/me`: Profile & active organization context.
* `GET  /api/v1/organizations/members`: List organization members and roles.

### Document Pipeline
* `POST /api/v1/documents/upload-intent`: Request presigned S3 upload URL.
* `POST /api/v1/documents/{document_id}/confirm`: Confirm upload completion; begins page rasterization.
* `GET  /api/v1/documents`: List documents with pagination and status filters.
* `GET  /api/v1/documents/{document_id}`: Document details, page count, and status.
* `GET  /api/v1/documents/{document_id}/pages/{page_number}/image`: Temporary URL for rendered 300 DPI page image.

### QC Runs & Findings
* `POST /api/v1/qc-runs`: Trigger new QC job.
* `GET  /api/v1/qc-runs/{qc_run_id}`: Get overall status, metrics, and pass/fail summary.
* `GET  /api/v1/qc-runs/{qc_run_id}/stream`: Real-time Server-Sent Events (SSE) progress.
* `GET  /api/v1/qc-runs/{qc_run_id}/findings`: Paginated, filterable findings (by severity, page, category).
* `POST /api/v1/findings/{finding_id}/feedback`: Submit human feedback (`CORRECT`, `INCORRECT`, `NEEDS_REVIEW`).

### Reports
* `GET  /api/v1/qc-runs/{qc_run_id}/report/pdf`: Stream/download audit-grade PDF.
* `GET  /api/v1/qc-runs/{qc_run_id}/report/xlsx`: Stream/download formatted Excel workbook.
