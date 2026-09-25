# ADR 0005: AI Provider Abstraction & Strict Schema Validation

**Status**: Accepted  
**Date**: 2026-09-25  
**Deciders**: Principal Software Architect, AI/ML Engineer  

---

## Context & Problem Statement
AI foundation models (OpenAI GPT-4o, Anthropic Claude 3.5 Sonnet, Google Gemini 1.5 Pro) evolve rapidly in capability, pricing, and API semantics. Coupling the application directly to a single vendor's SDK introduces high vendor lock-in risks. Furthermore, LLM non-determinism can produce malformed outputs that break downstream report generation.

## Decision Drivers
1. **Vendor Agility & Redundancy**: Ability to switch providers or fallback during external provider outages without touching application code.
2. **Deterministic Output Integrity**: Downstream components (database, UI, PDF/Excel generators) require strictly typed JSON objects.
3. **Local Testing Independence**: Automated CI/CD test runs must run fast and without external API dependencies or costs.

## Considered Options
1. **Direct OpenAI SDK Integration**: Call `openai.chat.completions.create` directly across services.
2. **AI Provider Abstraction Interface with Pydantic Validation**: Encapsulate all model interactions behind `AIProviderInterface`, enforcing Pydantic schema validation on all model responses.

## Decision Outcome
**Chosen Option**: AI Provider Abstraction Interface with Strict Pydantic Schema Validation.

The system defines `AIProviderInterface` with concrete implementations for OpenAI, Anthropic, Gemini, and a deterministic Mock provider. All model responses are validated through `NormalizedFinding` Pydantic models. Malformed responses trigger automated retries.

### Positive Consequences
- Zero vendor lock-in; provider configurable via `AI_PROVIDER` environment variable.
- Unit and integration tests run offline at zero cost using `MockQCProvider`.
- Downstream report generators and frontend components receive guaranteed valid typed structures.

### Negative Consequences
- Slight boilerplate for maintaining adapter classes across multiple provider SDKs.
