# RoutingBrain — Architecture Improvement Suggestions (For Claude Code Review)

**Purpose:**
This document captures architectural improvements and future-proofing recommendations for RoutingBrain based on the current implementation.

Goal: reduce long-term maintenance, improve model evolution handling, strengthen governance, and move toward a true **Enterprise AI Control Plane**.

---

# 1. Current Strengths (Do NOT Change)

These are strong architectural decisions already in place:

## 1.1 Layered Routing Pipeline

```
PreAnalyzer
   ↓
RiskAnalyzer (deterministic gate)
   ↓
RoutingBrain (Haiku classifier)
   ↓
PolicyEngine (YAML rules)
   ↓
ProviderRegistry
```

Why this is good:

* Risk is deterministic and cannot be overridden.
* RoutingBrain is advisory, not authoritative.
* Policy engine controls governance.
* Provider layer is abstracted.

---

## 1.2 OpenAI-Compatible API Boundary

Current endpoints:

* `POST /v1/chat/completions`
* `GET /v1/models`

This allows plug-and-play integration with:

* LangChain / LangGraph
* CrewAI
* AutoGen
* OpenAI SDK clients

---

## 1.3 Embedded Routing Decision Metadata

`x_routing_decision` is a major differentiator:

* explainability
* auditing
* debugging
* analytics foundation

Keep this concept.

---

## 1.4 Department-Based YAML Policies

This is a key enterprise differentiator.

---

# 2. Major Architectural Risks (Future Maintenance Issues)

## 2.1 Model Name Coupling (HIGH PRIORITY)

Current issue:

Policies and routing decisions reference concrete models:

```json
"model_selected": "claude-haiku-4-5-20251001"
```

Problem:

* model versions change frequently
* pricing changes
* capability shifts
* policy files require constant edits

---

### REQUIRED FIX — Virtual Models Layer

Introduce abstract model identifiers:

Examples:

```
rb://fast_cheap_code
rb://balanced_reasoning
rb://deep_architecture
rb://regulated_safe_reasoning
```

Policies should reference virtual models only.

Example:

```yaml
task_type: code_generation
route_to: rb://fast_cheap_code
```

Provider registry maps virtual → real model:

```yaml
rb://fast_cheap_code:
  provider: anthropic
  model: claude-haiku-4-5-20251001
```

Benefits:

* policies never change when models evolve
* safer upgrades
* easier experimentation

---

## 2.2 Task-Type Taxonomy Drift

Current:

```
task_type → model
```

Problem:

Models evolve and task categories blur over time.

---

### REQUIRED FIX — Capability-Based Routing

Introduce capability layer.

New flow:

```
task_type → required_capabilities → ranked_models
```

Example capabilities:

* deep_reasoning
* code_analysis
* structured_output_strict
* long_context
* low_latency
* regulated_safe
* tool_calling_stable

Model registry:

```yaml
claude-sonnet:
  capabilities:
    - deep_reasoning
    - code_analysis
```

Benefits:

* routing adapts automatically to new models
* lower maintenance
* easier benchmarking

---

## 2.3 Missing Continuous Evaluation Loop

Current system:

* rule-driven
* static assumptions about model quality

Risk:

* model quality drifts silently
* routing decisions degrade over time

---

### REQUIRED ADDITION — Shadow Evaluation Loop

Weekly or scheduled process:

1. Sample real routing requests.
2. Replay across candidate models.
3. Score outputs.

Metrics:

* schema validity
* required sections present
* tool-call correctness
* latency
* cost
* grader score (optional lightweight LLM)

Outcome:

* update ranking weights
* reorder fallback chains
* detect regressions

---

## 2.4 Risk Analyzer Is Fully Deterministic

Current:

* pattern matching only.

Risk:

* misses subtle executive or regulated content.
* false negatives possible.

---

### FUTURE IMPROVEMENT — Hybrid Risk Scoring

Combine:

* deterministic rules (hard safety)
* lightweight classifier score (secondary signal)

Example:

```
risk_final = max(deterministic_risk, classifier_risk)
```

Deterministic rules remain authoritative.

---

## 2.5 Budget Logic Coupling Risk

When Phase 3 budget enforcement is added:

Do NOT merge budget logic into PolicyEngine.

Correct layering:

```
PolicyEngine → ideal model
BudgetGuard → possible downgrade
```

Budget should be a separate enforcement step.

---

# 3. Agentic Workflow Compatibility Improvements

## 3.1 Tool Calling Compatibility (Critical)

Ensure full support for:

* OpenAI tool schema
* multi-tool calls
* streaming tool call deltas
* argument JSON fidelity

Add integration tests using:

* LangGraph
* CrewAI
* AutoGen

---

## 3.2 Idempotency Support

Agents retry frequently.

Add:

```
Idempotency-Key header support
```

Requirements:

* prevent duplicate tool execution
* return same routing decision for retries

---

## 3.3 Add `/v1/responses` Endpoint

Many modern agent frameworks are moving here.

Implementation:

* wrapper over existing chat pipeline.
* maintain same routing logic.

---

# 4. Governance Improvements

## 4.1 Policy Trace (Auditability)

Extend `x_routing_decision`:

```json
"policy_trace": [
  {"rule":"regulated_block_direct_openai","result":"matched"},
  {"rule":"rd_code_simple","result":"matched"}
]
```

Benefits:

* enterprise audit readiness
* debugging clarity

---

## 4.2 Constraint Visibility

Add:

```json
"constraints_applied": [
  "risk_floor_regulated",
  "budget_downgrade"
]
```

---

# 5. Observability Enhancements

## 5.1 OpenTelemetry Support

Add spans:

* preanalyzer
* risk analyzer
* routing brain call
* policy match
* provider call
* fallback events

Support `traceparent` propagation.

---

## 5.2 Streaming Routing Metadata

Streaming responses should emit routing decision early:

* SSE initial event OR headers.

---

# 6. Product-Level Differentiation Enhancements

## 6.1 Workflow Profiles (Recommended)

Beyond departments, define:

Examples:

* jira_story_eval
* pr_code_review
* incident_triage
* proposal_generation

Each profile defines:

* tools allowed
* required output format
* risk floor
* preferred virtual model

---

## 6.2 Policy Simulator (Inspector UI)

Add interface:

Input:

* prompt
* department
* workflow
* risk hints

Output:

* rules matched
* blocked providers
* selected virtual model
* fallback chain

Major enterprise differentiator.

---

# 7. Recommended Evolution Path

## Phase A (High Priority)

* Virtual model abstraction
* Capability-based registry
* `/v1/responses` endpoint
* Tool-calling compatibility tests
* Idempotency support

---

## Phase B (Control Plane Evolution)

* Policy trace output
* Workflow profiles
* Budget guard middleware
* OTel tracing

---

## Phase C (Self-Optimizing Routing)

* Shadow evaluation pipeline
* Automated model ranking
* Outcome-based escalation

---

# 8. Long-Term Design Principle

RoutingBrain should answer:

> “Which AI path is correct for this business context?”

NOT:

> “Which model should I call?”

---

# 9. Expected Outcome After Changes

* minimal policy churn when models evolve
* reduced maintenance overhead
* better enterprise governance story
* stronger differentiation vs generic routers
* safer long-term scaling

---

END
