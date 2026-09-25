# ADR 0004: Asynchronous QC Job Queue & Server-Sent Events (SSE)

**Status**: Accepted  
**Date**: 2026-09-25  
**Deciders**: Principal Software Architect, Backend Systems Engineer  

---

## Context & Problem Statement
Document ingestion, rasterization, high-resolution OCR, rule checking, and vision LLM calls take between 2 to 30 seconds depending on document size. Executing this synchronously within an HTTP request leads to reverse proxy gateway timeouts (e.g. AWS ALB 60s timeout, CloudFront 30s timeout) and degraded server throughput.

## Decision Drivers
1. **HTTP Gateway Resilience**: Keep HTTP request/response lifecycles sub-second ($< 200\text{ms}$).
2. **Scalability & Concurrency**: Decouple ingestion API capacity from worker compute capacity.
3. **User Experience**: Engineers should see real-time progress indicators rather than a frozen spinner.

## Considered Options
1. **Synchronous HTTP Execution**: Hold HTTP connection open until inspection completes.
2. **Asynchronous Task Queue with Polling**: Return job ID immediately; client polls `GET /qc-runs/{id}` every 2 seconds.
3. **Asynchronous Task Queue with Server-Sent Events (SSE)**: Enqueue job to Redis; worker publishes stage updates; client receives push events over single HTTP stream.

## Decision Outcome
**Chosen Option**: Asynchronous Task Queue with Server-Sent Events (SSE).

When an engineer triggers a QC run, the API deducts credits, creates a `QUEUED` run record, pushes a payload to the task queue, and returns immediately ($< 50\text{ms}$). The frontend connects to an SSE endpoint (`/stream`), receiving live stage updates (`EXTRACTING` $\to$ `CHECKING_RULES` $\to$ `AI_REASONING` $\to$ `COMPLETED`).

### Positive Consequences
- Zero HTTP timeout risks regardless of drawing size.
- Real-time animated progress bar in the UI without aggressive HTTP polling.
- Independent autoscaling of worker containers based on queue depth.

### Negative Consequences
- Requires Redis infrastructure for queueing and pub/sub.
