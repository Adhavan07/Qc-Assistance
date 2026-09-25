# ADR 0003: Multi-Tenancy via Query-Level Scoping and Token Claims

**Status**: Accepted  
**Date**: 2026-09-25  
**Deciders**: Principal Software Architect, Security Engineer  

---

## Context & Problem Statement
The platform serves multiple enterprise customers whose wiring diagrams contain proprietary designs and competitive secrets. Complete data isolation between tenants is a mandatory security requirement.

## Decision Drivers
1. **Zero Data Leakage**: Absolute prevention of cross-tenant visibility or unauthorized access.
2. **Infrastructure Cost Efficiency**: Separate physical databases per tenant (Database-per-Tenant) would create prohibitive infrastructure costs and migration overhead for early-stage B2B SaaS.
3. **Simplicity & Operational Maintainability**: Unified schema migrations across all organizations.

## Considered Options
1. **Database-per-Tenant**: Spin up dedicated PostgreSQL instances or schemas for each tenant.
2. **Row-Level Organization ID Scoping (Shared Schema)**: Single shared PostgreSQL database where every tenant-owned table features an `organization_id` foreign key, enforced via API dependencies and database query scoping.

## Decision Outcome
**Chosen Option**: Row-Level Organization ID Scoping with Cryptographically Derived Tenant Identity.

The client's authenticated session JWT encodes `organization_id` in its signed claims. Every FastAPI protected endpoint derives `current_user.organization_id` from the token and injects it into repository queries (`WHERE organization_id = :org_id`). S3 object keys are partitioned by `tenants/{org_id}/...`.

### Positive Consequences
- Low operational cost and instant onboarding of new organizations.
- Centralized Alembic database migrations.
- Tested and verified by automated cross-tenant security test suites.

### Negative Consequences
- Developers must maintain vigilance to always include `organization_id` in query filters (enforced via base repository classes and security code reviews).
