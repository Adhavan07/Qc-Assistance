# ADR 0002: Deterministic Rule Engine Before AI Reasoning

**Status**: Accepted  
**Date**: 2026-09-25  
**Deciders**: Principal Software Architect, Lead AI/ML Engineer  

---

## Context & Problem Statement
Engineering compliance verification against industry standards (IPC-WHMA-A-620, UL 508A) requires absolute accuracy. Relying solely on large language models (LLMs) to inspect drawings introduces non-deterministic outputs, hallucinated findings, and missed violations.

## Decision Drivers
1. **Safety & Regulatory Compliance**: Aerospace and industrial manufacturing cannot tolerate probabilistic uncertainty on mandatory safety rules (e.g. breaker rating vs wire ampacity).
2. **Explainability & Auditability**: Every discrepancy must map to a specific standard clause with exact mathematical or logical proof.
3. **Cost & Latency Optimization**: Deterministic code executes in milliseconds at zero marginal cost, whereas calling multimodal vision APIs costs money and takes seconds.

## Considered Options
1. **Pure LLM Pipeline**: Pass drawing text and images directly to a multimodal model with an extensive prompt.
2. **Deterministic Rules Engine Ahead of AI**: Extract an Intermediate Document Representation (IDR), run deterministic rule checks first, and use AI strictly for visual ambiguity, unstructured notes, and remedial explanations.

## Decision Outcome
**Chosen Option**: Deterministic Rules Engine Ahead of AI Reasoning.

The system vectorizes drawing geometry and text, builds an Intermediate Document Representation (IDR), and executes deterministic mathematical and regex checks. The AI layer then verifies visual anomalies, general drawing notes, and synthesizes clear recommendations.

### Positive Consequences
- Guarantees $100\%$ precision on standard deterministic violations (e.g. missing wire gauges).
- Dramatically lowers token consumption and API operational costs.
- Provides defensible, auditable citations for regulatory audits.

### Negative Consequences
- Requires continuous maintenance of rule logic and parsing heuristics for diverse CAD drawing styles.
