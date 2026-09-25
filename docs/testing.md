# Quality Assurance, Testing Strategy & Verification Framework

**Project**: Wiring Diagram QC Assistant  
**Client**: Spandsons Horizon Engineering Pvt. Ltd.  
**Version**: 2.0.0 (Phase 0 Architecture Release)  
**Date**: 2026-09-25  

---

## 1. Testing Philosophy & Definition of Done

> **A feature is NOT complete simply because the code compiles or the frontend builds.**

In an aerospace and mission-critical engineering SaaS platform, quality verification must be continuous, automated, and multi-layered. Every phase and pull request must satisfy strict quality gates:
1. **Zero Fake Implementations**: Zero `TODO`, `pass`, or mock stubs in production business logic paths.
2. **Deterministic Test Verification**: All business logic, tenant isolation, and security controls verified via automated suites.
3. **Multi-Tenancy Isolation Verified**: Automated security tests explicitly attempting cross-tenant access attacks.
4. **AI Output & Ground Truth Calibrated**: Deterministic benchmark fixtures evaluated for precision and recall.

---

## 2. Testing Pyramid & Test Architecture

```
                 / \
                /   \
               / E2E \       Playwright End-to-End User Workflows
              /-------\      (Upload -> QC -> Split-Screen -> PDF Export)
             /         \
            /Integration\    FastAPI TestClient + Async SQLAlchemy + Redis
           /-------------\   (Auth, RBAC, S3 Staging, Worker Pipeline, SSE)
          /               \
         /   Unit Tests    \  Domain Rule Engine, Pydantic Validation,
        /-------------------\ Security Cryptography, Metrics Engine
```

---

## 3. Test Suites Catalog

### 3.1 Unit Test Suite (`tests/unit/`)
- `test_schemas.py`: Verifies Pydantic models, bounding box coordinate boundaries ($0.0 \le x, y, w, h \le 1.0$), finding code prefixes (`FIND-`), and serialization.
- `test_security.py`: Validates bcrypt password hashing ($12$ rounds), JWT token creation, signature verification, expiration rejection, and tampered token detection.
- `test_rules.py`: Evaluates deterministic engineering logic for missing wire gauges, duplicate reference designators, color code ambiguities, and incomplete title blocks.
- `test_metrics.py`: Tests mathematical calculations for Precision, Recall, F1-score, and zero-division resilience.
- `test_engine.py`: Tests end-to-end `QCAnalysisEngine` integration with mocked intermediate document models.

### 3.2 Integration Test Suite (`tests/integration/`)
- `test_api_health.py`: Liveness (`/health`), readiness probe (`/ready`), and API info (`/api/v1/info`).
- `test_auth_api.py`: Organization self-service registration, duplicate slug/email rejection, login authentication, user profile `/me`, and role-based invitation restrictions.
- `test_database_models.py`: SQLAlchemy async models, foreign key relationships, cascade deletion of child records, and transaction rollback.
- `test_multi_tenancy_isolation.py`: Cross-tenant security tests ensuring User from Tenant A cannot view Tenant B's documents, members, or QC runs.
- `test_storage.py`: S3 and local storage presigned URL generation, key sanitization, and tenant path partitioning (`tenants/{org_id}/...`).
- `test_document_pipeline.py`: Project creation, upload intent issuance, document confirmation, and listing.
- `test_qc_execution_pipeline.py`: Asynchronous worker dispatch, job execution, credit deduction metering, SSE progress streaming, and HTTP 402 rejection on credit exhaustion.

### 3.3 AI Evaluation & Gold Dataset Benchmark (`tests/evaluation/`)
- `test_benchmark_regression.py`: Executes the QC engine across the **10-Case Gold Benchmark Dataset** (`data/gold_dataset/`):
  - 8 defective drawings covering all target discrepancy categories.
  - 2 golden clean drawings.
- **Pass Criteria**:
  - Precision $\ge 90.0\%$
  - Recall $\ge 95.0\%$
  - Zero false positives on clean drawings ($100\%$ precision).

### 3.4 End-to-End (E2E) Flow with Playwright (`tests/e2e/`)
The critical user journey automated in browser tests:
```
1. Engineer registers organization & signs in
2. Navigates to Ingest Manual -> Selects IPC-620 & UL 508A
3. Drags & drops multi-page PDF wiring manual
4. Verifies 4-stage upload progress completes
5. Enters Flagship Split-Screen QC Inspector
6. Verifies SVG canvas renders drawing and bounding boxes
7. Clicks Critical finding box -> drawer scrolls to finding card
8. Clicks [✓ Correct] feedback button -> status updates
9. Clicks [Download PDF] -> verifies audit report file generated
10. Returns to Dashboard -> verifies new run appears in recent inspections
```

---

## 4. Test Execution Commands & Quality Gates

```bash
# Run complete Python test suite
.venv/bin/pytest -v

# Run with code coverage report
.venv/bin/pytest --cov=backend/src --cov-report=term-missing --cov-fail-under=85

# Run Gold Dataset AI evaluation benchmark CLI
python -m backend.src.evaluation.runner

# Run Playwright E2E tests
npm --prefix frontend run test:e2e
```
