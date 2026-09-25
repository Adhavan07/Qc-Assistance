# Architecture Decision Log (ADR)
**Project**: Wiring Diagram QC Assistant  
**Client / Product Owner**: Spandsons Horizon Engineering Pvt. Ltd.  
**Version**: 1.0.0 | **Date**: 2026-09-25

---

## ADR-001: Hybrid Deterministic Rule Engine + Multimodal LLM vs. Pure LLM
* **Status**: Accepted
* **Context**: The client's initial charter proposed passing the diagram directly to an LLM with a prompt.
* **Decision**: We rejected the pure `PDF -> LLM -> answer` approach. We established a hybrid architecture where deterministic checks (wire gauge missing, terminal mismatch, title block validation) run programmatically on an Intermediate Document Representation (IDR), while the Multimodal LLM is used selectively for visual context and complex standards reasoning.
* **Consequences**: Eliminates hallucinated findings, reduces token costs by $>60\%$, provides $100\%$ reproducible results for hard engineering rules, and guarantees deterministic evidence.

---

## ADR-002: PostgreSQL + pgvector for RAG vs. Dedicated Vector Database (Pinecone/Weaviate)
* **Status**: Accepted
* **Context**: Standards clauses and customer SOPs require vector search for RAG.
* **Decision**: Adopt PostgreSQL 16 with the `pgvector` extension instead of adding a separate vector database service.
* **Consequences**: Drastically simplifies infrastructure (single database to backup, monitor, and scale). Simplifies tenant isolation by keeping vector chunks in the same transactional boundaries with relational tenant data and foreign keys.

---

## ADR-003: FastAPI + Celery/ARQ Worker Architecture
* **Status**: Accepted
* **Context**: QC processing requires 15–180 seconds per document, which exceeds standard HTTP gateway timeouts (typically 30–60s).
* **Decision**: Implement an asynchronous job queue using Redis/SQS with Celery/ARQ workers and provide live real-time progress via Server-Sent Events (SSE).
* **Consequences**: Reliable, non-blocking HTTP requests; automatic job retries; decoupled scaling of API endpoints and compute-intensive OCR/vision workers.

---

## ADR-004: Logical Multi-Tenancy with Row Level Security (RLS)
* **Status**: Accepted
* **Context**: Engineering schematics are confidential. Multi-tenancy must be bulletproof without incurring the cost of separate databases per customer.
* **Decision**: Use pooled multi-tenancy with mandatory `organization_id` on all tables, application-level query filtering, and PostgreSQL RLS policies.
* **Consequences**: Low operational cost, high scalability, and robust defense-in-depth against accidental data leakage across client organizations.
