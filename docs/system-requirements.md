# System Requirements Specification (SRS)
**Project**: Wiring Diagram QC Assistant  
**Client / Product Owner**: Spandsons Horizon Engineering Pvt. Ltd.  
**Version**: 1.0.0 | **Date**: 2026-09-25

---

## 1. Runtime & Infrastructure Requirements
* **Operating System**: Linux (Ubuntu 22.04 LTS / Debian Bookworm in containers).
* **Python Runtime**: Python 3.11+ (Typed, `asyncio`, FastAPI).
* **Node.js Runtime**: Node.js 20 LTS (Next.js 14+ App Router, TypeScript).
* **Database**: PostgreSQL 16 with `pgvector` extension.
* **Cache & State Store**: Redis 7.2+ (Task queue broker, cache, pub/sub for SSE).
* **Object Storage**: S3 API-compatible (AWS S3 with SSE-KMS / MinIO for local dev).
* **System Utilities**: Poppler utilities (`pdftoppm`), Tesseract OCR v5, libmagic.

## 2. Scalability & Sizing Targets
* **Concurrent Users**: Minimum 100 active inspectors simultaneously querying reports.
* **Concurrent QC Processing**: Dynamic auto-scaling worker pool from 2 to 20 workers based on SQS queue backlog.
* **File Constraints**:
  * Maximum file size: 50 MB.
  * Maximum page count per manual: 100 pages.
  * Maximum resolution per rendered page: 300 DPI (~3300 x 2550 px for standard letter/A4, up to 7000 x 5000 px for D-size/A1 schematics).
* **Latency Budgets**:
  * Metadata API endpoints: $p95 \le 200\text{ ms}$.
  * Single-page diagram analysis: $p90 \le 30\text{ s}$.
  * 10-page drawing package analysis: $p90 \le 180\text{ s}$.

## 3. Reliability & Fault Tolerance
* Zero data loss on failed worker execution. All job states are tracked in PostgreSQL (`QUEUED`, `PROCESSING`, `COMPLETED`, `FAILED`).
* Redis/SQS message retention with Dead-Letter Queues (DLQ) after 3 failed processing attempts.
* Graceful degradation: If a visual model API experiences transient rate limits, the system implements exponential backoff with jitter and falls back to secondary provider adapters.
