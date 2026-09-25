# ADR 0001: Modular Monolith Architecture Over Microservices

**Status**: Accepted  
**Date**: 2026-09-25  
**Deciders**: Principal Software Architect, Full-Stack Engineering Team  

---

## Context & Problem Statement
The Wiring Diagram QC Assistant is a commercial B2B SaaS platform that processes engineering drawings, runs compliance checks, and generates audit reports. A key architectural decision is whether to partition the backend into multiple distributed microservices (e.g. Auth Service, Document Service, QC Service, Report Service) or construct a unified Modular Monolith with asynchronous background workers.

## Decision Drivers
1. **Time-to-Market & Simplicity**: Early-stage SaaS agility requires rapid feature iteration without distributed deployment friction.
2. **ACID Transactional Integrity**: Operations like deducting credits, recording runs, and persisting findings require atomic consistency.
3. **Operational Overhead**: Microservices require service mesh, distributed tracing, complex network policies, and multiple container deployments.
4. **Latency & Throughput**: In-process domain calls are orders of magnitude faster than inter-service gRPC or HTTP RPC calls.

## Considered Options
1. **Microservices Architecture**: Separate containerized microservices communicating over HTTP/gRPC.
2. **Modular Monolith with Background Workers**: Single cohesive backend codebase divided into strictly isolated Python packages, backed by asynchronous task workers.

## Decision Outcome
**Chosen Option**: Modular Monolith with Background Workers.

The backend is built as a single Python codebase (`backend/src/`) organized into clean domain modules (`domain/`, `services/`, `infrastructure/`, `api/`). Heavy operations (OCR, PDF parsing, AI analysis) run in worker processes sharing the same domain model.

### Positive Consequences
- Streamlined local development via Docker Compose.
- Zero network latency for internal business logic execution.
- Relational integrity and single-transaction atomicity across documents, runs, and audit logs.
- Clear module boundaries allow future extraction into microservices if specific high-throughput components require independent autoscaling.

### Negative Consequences
- Team must enforce modular discipline so domain boundaries are not bypassed with circular imports (enforced via linting and static analysis).
