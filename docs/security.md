# Security Model & Threat Assessment Document

**Project**: Wiring Diagram QC Assistant  
**Client**: Spandsons Horizon Engineering Pvt. Ltd.  
**Version**: 2.0.0 (Phase 0 Architecture Release)  
**Date**: 2026-09-25  

---

## 1. Security Philosophy & Defense-in-Depth

Engineering wiring diagram manuals, avionics schematics, and industrial panel drawings constitute **highly confidential trade secrets** and proprietary client intellectual property. The SaaS platform treats security as a fundamental quality gate rather than an afterthought.

The system enforces a multi-layered **Defense-in-Depth** model:
1. **Network Layer**: AWS WAF rate limiting, DDoS shielding, VPC private subnet isolation for databases/workers, and TLS 1.3 encryption in transit.
2. **Identity & Access Layer**: Salted bcrypt password hashing, signed JWT tokens, strict Role-Based Access Control (RBAC), and session invalidation.
3. **Application & Tenant Layer**: Defense-in-depth multi-tenancy where `organization_id` is derived strictly from verified credentials; zero cross-tenant leakage.
4. **Data & Storage Layer**: AES-256 encryption at rest via AWS KMS, presigned S3 URLs with short TTLs (15 minutes), and zero public bucket access.
5. **AI & Prompt Protection**: System instructions and validated QC prompts are treated as proprietary trade secrets. They are managed strictly server-side and never returned in API payloads or client-side bundles.

---

## 2. Multi-Tenant Isolation Architecture

```
┌────────────────────────────────────────────────────────┐
│               Client Request (Bearer JWT)              │
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│      1. Token Extraction & Signature Verification      │
│  - Decodes token using HS256 / RS256                   │
│  - Rejects expired, tampered, or malformed tokens      │
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│      2. Context Derivation (Never Trust Payload)       │
│  - Current User: user_id = token.sub                   │
│  - Current Tenant: organization_id = token.org_id      │
│  - Current Role: role = token.role                     │
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│        3. RBAC Hierarchy Authorization Guard           │
│  - Checks minimum required permission level            │
│  - Rejects unauthorized roles with HTTP 403 Forbidden  │
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│           4. Tenant-Scoped Database Query              │
│  SELECT * FROM documents                               │
│  WHERE id = :requested_id                              │
│    AND organization_id = :authenticated_org_id;        │
│  (Guarantees zero cross-tenant data visibility)        │
└────────────────────────────────────────────────────────┘
```

---

## 3. Role-Based Access Control (RBAC) Matrix

| Endpoint Group / Capability | PLATFORM_ADMIN | TENANT_ADMIN | ENGINEER | REVIEWER | CUSTOMER_USER | READ_ONLY |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| Global Tenant Management | **Full** | None | None | None | None | None |
| Manage Organization Members | **Full** | **Full** | None | None | None | None |
| Purchase Credits / Billing | **Full** | **Full** | None | None | None | None |
| Create Projects & Upload Docs | **Full** | **Full** | **Full** | None | None | None |
| Trigger QC Analysis Jobs | **Full** | **Full** | **Full** | None | None | None |
| Submit Discrepancy Feedback | **Full** | **Full** | **Full** | **Full** | None | None |
| View Findings & Reports | **Full** | **Full** | **Full** | **Full** | **Full** | **Full** |
| Download PDF & Excel Reports | **Full** | **Full** | **Full** | **Full** | **Full** | None |
| View Compliance Audit Logs | **Full** | **Full** | None | None | None | **Full** |

---

## 4. File Upload & Document Ingestion Hardening

1. **Magic-Byte / MIME Validation**:
   - The server verifies binary headers (e.g. `%PDF-` for PDFs, `\x89PNG\r\n\x1a\n` for PNGs) using `python-magic` or direct header sniffing.
   - Files with mismatched extensions or disguised executables are rejected immediately.
2. **Filename Sanitization & Internal Key Generation**:
   - Original user filenames are never used on the filesystem or S3 object keys.
   - Storage keys follow strict tenant-partitioned patterns:  
     `tenants/{organization_id}/documents/{document_id}/original/{uuid4}.pdf`
   - Path traversal sequences (`../../`, null bytes) are stripped.
3. **Decompression Bomb & Resource Exhaustion Defense**:
   - Upload file size capped at 100 MB per file.
   - Rasterization renders at a maximum dimension of $4096 \times 4096$ pixels at 300 DPI, preventing memory exhaustion attacks.
4. **Presigned Upload Workflow**:
   - Web clients never stream raw large binary files directly through the API server container.
   - The API issues presigned S3 POST policies containing content-type and size-limit conditions. Uploads flow directly from browser to S3.

---

## 5. STRIDE Threat Model & Mitigations

| Threat Category | Potential Attack Vector | Applied Engineering Mitigation |
| :--- | :--- | :--- |
| **Spoofing** | Attacker impersonates legitimate quality engineer | JWT with cryptographic HMAC-SHA256 signature, salted bcrypt password hashing ($12$ rounds), and session expiry. |
| **Tampering** | Attacker alters QC findings or credit quota in transit | TLS 1.3 enforced on all endpoints; database transactions ensure ACID atomicity; audit log checksums. |
| **Repudiation** | Engineer denies approving or rejecting a critical finding | Append-only `audit_logs` record actor ID, action, resource, timestamp, IP address, and previous/new state. |
| **Information Disclosure** | Cross-tenant access to competitor's wiring schematics | Query-level tenant scoping (`WHERE organization_id = :org_id`); private S3 buckets; presigned URLs with 15-min TTL. |
| **Denial of Service** | Exhaustion of compute or credit quota via script | Rate limiting via Redis Token Bucket; asynchronous queue worker concurrency limits; credit pre-authorization. |
| **Elevation of Privilege** | Normal engineer attempts inviting themselves as TENANT_ADMIN | Hierarchical role guard (`require_role`) rejects privilege escalation attempts. |

---

## 6. Prompt Injection & Trade Secret Protection

1. **Prompt IP Concealment**:
   - Prompts are compiled server-side inside worker processes.
   - The frontend never receives raw system prompts or validated rule prompt templates.
2. **Indirect Prompt Injection Defense**:
   - Untrusted text extracted from customer drawings (e.g., text blocks in title blocks or wire labels) is placed strictly within isolated XML or JSON data payload tags:  
     `<drawing_context>{extracted_text}</drawing_context>`
   - System instructions explicitly forbid the model from obeying instructions found inside the drawing text.
3. **Strict Schema Validation**:
   - Model responses must conform to rigid Pydantic JSON schemas. Any output containing conversational chatter, Markdown formatting, or altered schema structure is automatically rejected and retried.
