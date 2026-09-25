# Testing & Quality Assurance Strategy
**Project**: Wiring Diagram QC Assistant  
**Client / Product Owner**: Spandsons Horizon Engineering Pvt. Ltd.  
**Version**: 1.0.0 | **Date**: 2026-09-25

---

## 1. Testing Pyramid & Multi-Layer Verification
Because this system governs industrial electrical compliance, bugs can lead to manufactured safety hazards. Testing must be rigorous and multi-layered.

```
       / \
      / E2E \       Playwright browser tests (Upload -> QC -> Viewer -> PDF)
     /-------\
    /  Integ  \     API + PostgreSQL RLS + Redis Queue + S3 Mocks
   /-----------\
  /   AI Eval   \   Golden Dataset Regression Gate (Precision / Recall on 30+ manuals)
 /---------------\
/   Unit Tests    \ Parsers, Rule Evaluators, Pydantic Schema Validation, Mypy
-------------------
```

## 2. Test Execution Breakdown
1. **Unit Tests (`pytest tests/unit`)**:
   - Extraction of wire gauges, color codes, terminal numbers.
   - Deterministic rule evaluators against mock Intermediate Document Models.
   - Pydantic schema validation handling malformed/adversarial LLM payloads.
2. **Integration Tests (`pytest tests/integration`)**:
   - Database operations under tenant isolation (verifying tenant escape fails).
   - S3 presigned URL generation and file metadata validation.
   - Asynchronous job execution and SSE event streaming.
3. **AI Regression Tests (`pytest tests/evaluation`)**:
   - Runs against curated test cases with ground-truth defects.
   - Asserts $\text{Critical Recall} \ge 98\%$.
4. **End-to-End Tests (`playwright test`)**:
   - Inspector workflow: Login -> Upload PDF -> Wait for QC complete -> Validate bounding box interaction -> Download PDF & Excel reports.
