# Differentiating an Enterprise LLM Routing Brain

*(Notes for Architecture Review / Claude Code Analysis)*

---

## 1. Core Positioning

### ❌ What NOT to be

* Another generic LLM router
* Infra-only API gateway
* Simple model switcher (OSS vs commercial)

### ✅ What to become

**Enterprise AI Control Plane** that optimizes:

> Cost per business outcome
> instead of
> Cost per prompt

---

## 2. What Existing Routers Already Do

| Capability                  | Existing Tools (LiteLLM, Bedrock, Azure, OpenRouter, etc.) |
| --------------------------- | ---------------------------------------------------------- |
| Multi-model routing         | Yes                                                        |
| Fallback chains             | Yes                                                        |
| Cost tracking               | Yes                                                        |
| Load balancing              | Yes                                                        |
| Latency optimization        | Yes                                                        |
| Prompt complexity routing   | Yes                                                        |
| Department-aware routing    | No                                                         |
| Business policy engine      | No                                                         |
| Risk-based governance       | No                                                         |
| Budget enforcement per team | No                                                         |
| Outcome-based escalation    | Rare                                                       |
| Org-level AI governance     | No                                                         |

---

## 3. Core Differentiation Strategy

### Existing Routers

```
Prompt → Model Selection
```

### Proposed System (Enterprise Routing Brain)

```
User + Department + Risk + Budget + Task
            ↓
       Policy Engine
            ↓
      Routing Decision
            ↓
   OSS / Commercial Model
            ↓
      Quality Evaluation
            ↓
     Escalate if Needed
```

---

## 4. Key Differentiators (Must-Have Layers)

### 4.1 Department-Aware Routing

Routing includes metadata:

* department (R&D / Sales / Marketing / Finance / Legal)
* audience (internal / external)
* channel (Slack / Web / API)
* business context

Example policies:

* Sales → cheap + fast unless proposal/contract
* Marketing → creative model
* R&D → reasoning + coding model
* Legal/Finance → premium only

---

### 4.2 Risk-Based Routing (Major Differentiator)

Add risk classification:

* low → OSS allowed
* medium → balanced models
* high → premium only
* regulated → approved boundary models only

Risk signals:

* legal terms
* pricing
* contracts
* PHI/PII indicators
* executive communications

---

### 4.3 Budget-Aware Governance

Per-department controls:

* monthly budget caps
* auto downgrade when budget exceeded
* preferred model tiers

Example:

```
Sales: $3K/month
Marketing: $1K/month
R&D: premium allowed
```

---

### 4.4 Outcome-Based Escalation (Strong Advantage)

Instead of routing only once:

1. Route to cheap/OSS model first.
2. Run automatic quality checks.
3. Escalate to commercial model if failed.

Possible quality checks:

* JSON schema validation
* required sections present
* refusal detection
* confidence score
* lightweight grader model

This enables real cost savings.

---

### 4.5 Policy-as-Code Engine

Example rule structure:

```yaml
- if department: Legal
  allow_models: [premium_models]
  forbid_oss: true

- if task_type: coding
  prefer: oss_code_model
  fallback: premium_reasoning_model

- if budget_exceeded:
  route: oss_only
```

---

## 5. Router Architecture (Recommended)

### Layer 1 — Policy Gate (Deterministic)

Hard rules:

* security
* compliance
* risk boundaries
* department constraints

### Layer 2 — Haiku Router (Intelligent Decision)

Haiku selects among **allowed candidates** only.

Outputs:

* chosen model
* reasoning
* confidence
* fallback chain

### Layer 3 — Execution + Evaluation

* run selected model
* validate output
* escalate if needed

---

## 6. Why This Is Different From Existing Tools

Existing routers optimize:

* latency
* cost
* prompt complexity

This system optimizes:

* organizational policy
* governance
* spend allocation
* business risk
* outcome quality

---

## 7. Product Positioning (Important)

Avoid calling it:

* LLM Router
* Model Switcher

Position as:

* Enterprise AI Control Plane
* AI Cost Governance Platform
* AI Policy & Routing Engine

---

## 8. Suggested Metrics (Executive-Level)

Track:

* spend per department
* OSS vs commercial usage ratio
* escalation rate
* cost saved via routing
* quality pass/fail rate
* average cost per task type

---

## 9. Evolution Roadmap (Conceptual)

### Tier 1 — Infra Router

* model switching
* fallback
* basic cost tracking

### Tier 2 — Policy Router

* department rules
* risk-aware routing
* budget limits

### Tier 3 — AI Control Plane

* governance dashboards
* outcome evaluation
* policy-as-code

### Tier 4 — Autonomous Optimization

* learns best model per task
* auto-adjusts thresholds
* predicts budget burn
* recommends routing changes

---

## 10. Key Design Principle

Existing systems answer:

> “Which model fits this prompt?”

Target system answers:

> “Which AI path is correct for this business context at the right cost and risk level?”

---

## 11. Notes for Claude Code Review

Areas to validate:

* Is policy enforcement deterministic before model routing?
* Are forbidden routes impossible regardless of Haiku output?
* Is routing output structured (JSON schema)?
* Is escalation logic measurable and testable?
* Are routing decisions logged for analytics?
* Can new departments/policies be added without code changes?
* Is budget enforcement runtime-safe?
* Are risk classifications auditable?

---

## 12. Optional Next-Level Enhancements

Future possibilities:

* Agent-aware routing:

  ```
  Request → Agent Type → Toolchain → Model
  ```

* Dynamic confidence scoring

* Adaptive routing based on historical success

* Automatic model benchmarking per task category

---

END
