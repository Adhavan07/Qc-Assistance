# Deterministic QC Rules Engine & Rule Pack System

**Project**: Wiring Diagram QC Assistant  
**Client**: Spandsons Horizon Engineering Pvt. Ltd.  
**Version**: 2.0.0 (Phase 0 Architecture Release)  
**Date**: 2026-09-25  

---

## 1. Engine Philosophy: Determinism Over Probabilistic Inference

In mission-critical aerospace, defense, and industrial electrical manufacturing, quality control **cannot rely exclusively on probabilistic LLMs**. An LLM may hallucinate that a wire gauge is present when it is absent, or misinterpret ampacity tables under varying temperatures.

The platform employs a **Deterministic-First Architecture**:
1. **Deterministic Rule Engine**: Executes rigorous, mathematical, regex, and graph-traversal checks on structured entities (wire runs, breaker ratings, terminal callouts, contact pin sizes).
2. **AI Reasoning Layer**: Acts as an interpretive assistant for edge cases (e.g., complex general drawing notes, spatial layout ambiguities, and plain-language remedial guidance).

```
┌────────────────────────────────────────────────────────┐
│        Intermediate Document Representation (IDR)      │
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│          Deterministic QC Rules Engine                 │
│  - Mathematical Overcurrent Checking (Wire vs. CB)     │
│  - Contact Pin Cavity & Gauge Equivalence              │
│  - Harness Curvature & Minimum Bend Radius Ratio       │
│  - Color Code Palette Matching (AC/DC / Ground)        │
│  - Component Reference Designator Prefix Compliance    │
│  - Title Block Completeness & Approval Signatures      │
└───────────────────────────┬────────────────────────────┘
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
        [Pass Results]             [Fail Discrepancies]
              │                           │
              │             ┌─────────────▼─────────────┐
              │             │  Multimodal AI Reasoning  │
              │             │  - Correlate Drawing Notes│
              │             │  - Synthesize Evidence    │
              │             │  - Draft Recommendations  │
              │             └─────────────┬─────────────┘
              │                           │
              └─────────────┬─────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│      Consolidated Audit-Grade QC Run Results           │
└────────────────────────────────────────────────────────┘
```

---

## 2. Core Rule Definitions & Engineering Logic

### 2.1 Wire Sizing & Overcurrent Protection (`RULE-WIRE-001`)
- **Category**: `WIRE_SIZING`
- **Default Severity**: `CRITICAL`
- **Engineering Logic**: For every wire run connected to an overcurrent protective device (circuit breaker, fuse), the conductor gauge (AWG or $\text{mm}^2$) must be explicitly stated, and its allowable continuous ampacity must equal or exceed the breaker rating multiplied by the continuous load factor ($1.25\times$).
- **Standard Citation**: `IPC-WHMA-A-620D §13.4.1`, `UL 508A Table 28.1`
- **Violation Condition**: Missing wire gauge OR wire ampacity $<$ breaker rating.

### 2.2 Connector Contact Pin Matching (`RULE-CONN-002`)
- **Category**: `CONNECTOR_PINOUT`
- **Default Severity**: `MAJOR`
- **Engineering Logic**: For any mated connector pair (e.g., receptacle $J101$ mating with plug $P101$), each pin contact number must have matching wire gauge and contact size ratings across the interface.
- **Standard Citation**: `IPC-WHMA-A-620D §9.2.3`
- **Violation Condition**: Pin contact gauge on receptacle $\neq$ contact gauge on mating plug.

### 2.3 Harness Minimum Bend Radius (`RULE-BEND-001`)
- **Category**: `HARNESS_ROUTING`
- **Default Severity**: `MAJOR`
- **Engineering Logic**: Harness bundle bend radii must not fall below minimum standards relative to bundle outer diameter ($OD$):
  - Unshielded wire bundles: Minimum radius $\ge 3\times OD$.
  - Shielded / coaxial cables: Minimum radius $\ge 6\times OD$.
- **Standard Citation**: `IPC-WHMA-A-620D §13.1.2`
- **Violation Condition**: Annotated bend radius $<$ required ratio $\times OD$.

### 2.4 AC/DC Conductor Color Coding (`RULE-COLOR-003`)
- **Category**: `COLOR_CODING`
- **Default Severity**: `MINOR`
- **Engineering Logic**: Field and factory conductors must follow standardized color identification:
  - AC Grounded Neutral: Continuous White, Natural Gray, or Light Blue.
  - Equipment Ground / PE: Continuous Green with or without Yellow stripe.
  - DC Positive: Red; DC Negative: Black (or Blue for control).
- **Standard Citation**: `UL 508A Table 28.1`, `MIL-STD-681D Notice 2`
- **Violation Condition**: Prohibited color used for neutral or protective earth return paths.

### 2.5 Terminal Lug Fastening Torque Callouts (`RULE-TERM-004`)
- **Category**: `TERMINATIONS`
- **Default Severity**: `MINOR`
- **Engineering Logic**: All screw-type terminal connections, power lugs, and busbar joints must feature an explicit tightening torque callout ($\text{N}\cdot\text{m}$ or $\text{in-lb}$) either directly or in general drawing notes.
- **Standard Citation**: `UL 508A §29.3`
- **Violation Condition**: High-current terminal block connection lacks torque callout.

### 2.6 Reference Designator Standardization (`RULE-REV-005`)
- **Category**: `DESIGNATORS`
- **Default Severity**: `INFO`
- **Engineering Logic**: Electrical component tags must follow standardized class letter prefixes (e.g., $K$ for electromechanical relays, $CB$ for circuit breakers, $R$ for resistors, $TB$ for terminal blocks).
- **Standard Citation**: `IEEE 315 / MIL-STD-12D`
- **Violation Condition**: Non-standard designator prefix used without explanatory general note.

---

## 3. Rule Pack Architecture & Legal/IP Safety

### Copyright Protection & Safety Principle
> **The platform never infringes on copyrighted standards bodies.** Full standard texts (e.g. ISO, IEC, IPC) are never copied into the database or public repositories without license. Instead, the architecture models standards as **parameterized rule packs** referencing public clauses, client-supplied internal SOPs, or customer-specific engineering standards.

```
Standard Definition
  │ (e.g. IPC-WHMA-A-620D Class 3)
  ▼
Rule Pack
  │ (Version 1.0, Organization: Spandsons Horizon)
  ├── Rule 1: Min Breaker Margin = 1.25x
  ├── Rule 2: Min Shielded Bend Ratio = 6.0x
  ├── Rule 3: Allowable Neutral Colors = ["WHT", "GRY", "BLU"]
  └── Rule 4: Mandatory Torque Units = ["N·m", "in-lb"]
```

### Configurable Parameters
Tenant administrators can customize:
- `is_enabled`: Toggle specific rules on/off per project.
- `severity_override`: Elevate a `MINOR` rule to `CRITICAL` for aerospace projects.
- `tolerance_parameters`: Adjust numerical thresholds (e.g., relax bend radius ratio from $6.0\times$ to $5.0\times$ for flexible high-strand conductors).

---

## 4. QC Result Model & Metric Calculation

Every completed QC run yields an immutable result record:

| Metric | Definition | Example Value |
| :--- | :--- | :--- |
| **Overall Status** | `PASS` (0 Critical/Major), `FAIL` ($\ge 1$ Critical/Major), `REVIEW_REQUIRED` (Only Minor/Info) | `FAIL` |
| **Checks Total** | Total individual rule assertions evaluated across all sheets | `156` |
| **Checks Passed** | Assertions meeting engineering acceptance criteria | `112` |
| **Checks Failed** | Assertions failing criteria (generating discrepancy findings) | `24` |
| **Checks N/A** | Rules not applicable to this drawing type | `20` |
| **Critical Count** | Severe defects compromising electrical safety or functionality | `6` |
| **Major Count** | Defects causing mating failures, assembly errors, or warranty risks | `10` |
| **Minor Count** | Documentation, color, or torque callout ambiguities | `8` |
