# Data Model & Database Architecture
**Project**: Wiring Diagram QC Assistant  
**Client / Product Owner**: Spandsons Horizon Engineering Pvt. Ltd.  
**Version**: 1.0.0 | **Date**: 2026-09-25

---

## 1. Database Technology Selection
* **Engine**: PostgreSQL 16 (Relational integrity, JSONB support, ACID transactions).
* **Extensions**: `uuid-ossp` (Primary keys), `pgcrypto` (Data masking/hashing), `vector` (`pgvector` for standards chunk embeddings).
* **ORM**: SQLAlchemy 2.0 (Async engine with Mypy type hints).
* **Migrations**: Alembic with auto-generation and strict down-revisions.

## 2. Entity Relationship Overview
All tenant data is strictly partitioned by `organization_id`. 

```
organizations (1) ────< users (N)
organizations (1) ────< projects (N) ────< documents (N) ────< qc_runs (N) ────< qc_findings (N)
organizations (1) ────< audit_logs (N)
organizations (1) ────< standards (N) [Custom SOPs]
standards (1) ────< standard_chunks (N) [vector(1536) embeddings]
qc_findings (1) ────< finding_feedback (N)
qc_runs (1) ────< reports (N)
```

## 3. Database Migration & RLS Plan
* Every production table containing customer data has PostgreSQL Row Level Security enabled:
```sql
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_policy ON documents
    USING (organization_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);
```
* The application sets the tenant session variable upon acquiring a connection:
```python
await db_session.execute(text("SET LOCAL app.current_tenant_id = :org_id"), {"org_id": str(org_id)})
```
