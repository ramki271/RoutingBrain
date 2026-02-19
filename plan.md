# Intelligent LLM Routing Platform — Implementation Plan

## Context

SaaS organizations using LLMs across departments (R&D, Sales, Marketing, HR, Finance) today manually configure which LLM to call per tool/team. This leads to over-spending (using Opus-tier models for simple Q&A) or under-performance (using cheap models for complex architecture work). The goal is a self-managing routing layer that **automatically understands the intent and complexity of every request** and routes to the most cost-effective capable model — no manual configuration needed per use case.

Initial focus: **R&D department** (coding, code review, debugging, architecture design, documentation). Extensible to other departments via YAML config.

---

## Architecture Overview

```
Client (uses OpenAI SDK, base_url=this service)
        │
        ▼
POST /v1/chat/completions   ← OpenAI-compatible proxy
        │
        ├── Auth Middleware      (API key → tenant/user/dept)
        ├── Rate Limit Middleware (Redis per-user RPM/TPM)
        │
        ▼
RoutingEngine.route()
        │
        ├── 1. PreAnalyzer       (heuristic signals: token count, code blocks, keywords)
        ├── 2. RoutingBrain (Claude Haiku classifies: task type, complexity, dept)
        │        └── fallback to heuristics if timeout or confidence < 0.6
        ├── 3. PolicyEngine      (matches YAML rules → primary + fallback model list)
        │        └── applies budget guardrails from Redis cost counters
        └── 4. ProviderRegistry  (selects adapter, calls LLM, retries on fallback)
                │
                ├── anthropic.py / openai.py / gemini.py / ollama.py / vllm.py
                └── Normalized SSE streaming (same format regardless of provider)
        │
        ▼
Response → Client
BackgroundTask → CostRecord (DB) + AuditLog (JSONL) + Prometheus metrics
```

---

## Tech Stack

- **Runtime**: Python 3.12 + FastAPI (async)
- **Routing brain**: Claude Haiku 4.5 (RoutingBrain classifier, ~$0.001/call overhead)
- **Providers**: Anthropic, OpenAI, Google Gemini, Ollama (local), vLLM (self-hosted)
- **Interface**: OpenAI-compatible `/v1/chat/completions` — zero client-side changes
- **Storage**: PostgreSQL (SQLAlchemy async + Alembic) + Redis (budgets, rate limits)
- **Observability**: Prometheus metrics, OpenTelemetry traces, structured JSONL audit log
- **Config**: YAML routing policies (hot-reloadable, no restart needed)
- **Packaging**: `pyproject.toml` + Docker Compose for local dev

---

## Project Structure

```
llm-router/
├── pyproject.toml
├── Makefile
├── docker-compose.yml
├── .env.example
│
├── config/
│   ├── models.yaml                    # All models + pricing
│   ├── settings.yaml                  # App-level settings
│   ├── meta_llm_system_prompt.txt     # Versioned classifier prompt
│   └── routing_policies/
│       ├── base.yaml                  # Default/fallback policy
│       ├── rd.yaml                    # R&D routing matrix (Phase 1)
│       ├── sales.yaml                 # (Phase 2)
│       └── marketing.yaml             # (Phase 2)
│
├── app/
│   ├── main.py                        # FastAPI app factory + lifespan
│   ├── core/
│   │   ├── config.py                  # Pydantic Settings
│   │   ├── logging.py                 # Structured JSON logging
│   │   └── exceptions.py             # Custom exceptions + handlers
│   ├── api/
│   │   ├── v1/
│   │   │   ├── chat.py                # POST /v1/chat/completions ← CORE
│   │   │   ├── models.py              # GET /v1/models
│   │   │   └── embeddings.py
│   │   └── internal/
│   │       ├── routing.py             # Admin: view decisions, force overrides
│   │       ├── analytics.py           # Cost + routing stats dashboards
│   │       └── health.py              # /health, /ready
│   ├── routing/
│   │   ├── engine.py                  # Orchestrator ← CENTRAL
│   │   ├── analyzer.py                # Heuristic pre-analysis
│   │   ├── routing_brain.py                # Meta-LLM classifier ← INTELLIGENCE CORE
│   │   ├── policy.py                  # YAML policy loader + rule matching
│   │   └── selector.py                # Final model selection
│   ├── providers/
│   │   ├── base.py                    # Abstract BaseProvider ← KEY INTERFACE
│   │   ├── anthropic.py
│   │   ├── openai.py
│   │   ├── gemini.py
│   │   ├── ollama.py
│   │   ├── vllm.py
│   │   └── registry.py
│   ├── models/
│   │   ├── request.py                 # ChatCompletionRequest (OpenAI-compat)
│   │   ├── response.py
│   │   ├── routing.py                 # ClassificationResult, RoutingDecision ← KEY
│   │   ├── cost.py                    # CostRecord, ModelPricing
│   │   └── policy.py                  # RoutingRule, DepartmentPolicy
│   ├── cost/
│   │   ├── tracker.py
│   │   ├── pricing.py                 # Loads from models.yaml
│   │   └── aggregator.py
│   ├── observability/
│   │   ├── audit_log.py               # Structured JSONL per routing decision
│   │   └── metrics.py                 # Prometheus counters/histograms
│   ├── storage/
│   │   ├── database.py                # SQLAlchemy async engine
│   │   ├── redis_client.py
│   │   └── migrations/
│   └── middleware/
│       ├── auth.py
│       ├── rate_limit.py
│       └── request_id.py
│
└── tests/
    ├── unit/
    │   ├── test_analyzer.py
    │   ├── test_routing_brain.py
    │   ├── test_policy.py
    │   └── test_cost_tracker.py
    └── integration/
        ├── test_chat_endpoint.py
        └── test_routing_pipeline.py
```

---

## Routing Intelligence Design

### Step 1: PreAnalyzer (heuristic, free, fast)
Extracts signals before calling the RoutingBrain:
- Estimated token count (via `tiktoken`)
- Code block detection, programming language detection
- Keyword matching: `debug`, `refactor`, `review`, `architecture`, `trace`, `test`
- Department hint from `X-Department` header or system prompt
- Conversation turn count

### Step 2: RoutingBrain (Claude Haiku 4.5, 3s timeout)
Receives PreAnalysis + message excerpts, returns structured JSON:

```json
{
  "task_type": "code_review",
  "complexity": "medium",
  "department": "rd",
  "required_capability": ["code_execution", "deep_reasoning"],
  "estimated_output_length": "medium",
  "confidence": 0.91,
  "routing_rationale": "Python refactoring with performance focus, R&D context confirmed"
}
```

**Fallback**: If timeout or `confidence < 0.6` → heuristic rule matching from PreAnalysis signals.

### Step 3: PolicyEngine (YAML rules, no LLM)
Matches `ClassificationResult` against `rd.yaml` rules top-to-bottom (first match wins).
Applies Redis budget guardrails:
- >80% daily budget → downgrade one tier
- >100% budget → force `fast_cheap` tier

### Step 4: Provider call with fallback chain
If primary model fails (429/503/timeout) → auto-retry with `fallback_models[0]`, then `[1]`.
Actual model used recorded in `RoutingOutcome.actual_model_used`.

---

## R&D Routing Matrix (rd.yaml — key rules)

| Task | Complexity | Primary Model | Rationale |
|---|---|---|---|
| `code_generation` | simple | claude-haiku-4-5 | Fast, cheap, strong on boilerplate |
| `code_generation` | medium | claude-sonnet-4-5 | Best code quality/cost balance |
| `code_generation` | complex | claude-opus-4-5 | Novel algorithms need max capability |
| `code_review` | simple | gpt-4o-mini | Pattern matching, fast |
| `code_review` | medium | claude-sonnet-4-5 | Nuanced structural reasoning |
| `debugging` | complex | o1 | Extended thinking for hard bugs |
| `architecture_design` | complex | claude-opus-4-5 | Best for trade-off analysis |
| `documentation` | medium | claude-sonnet-4-5 | Clear technical prose |
| `question_answer` | simple | gemini-2.0-flash | Lowest latency + cheapest |
| `data_analysis` | complex | gemini-2.0-pro | 2M context for large codebases |
| `math_reasoning` | complex | o1 | Built specifically for this |

**Cost Tiers:**
- `fast_cheap`: Haiku, GPT-4o-mini, Gemini Flash — ~$0.10–$1.00/MTok input
- `balanced`: Sonnet, GPT-4o, Gemini Pro — ~$2.50–$5.00/MTok input
- `powerful`: Opus, o1 — ~$5.00–$60.00/MTok input
- `local`: Ollama/vLLM — $0.00/MTok

---

## Key Data Models

**`ClassificationResult`** (`app/models/routing.py`): Output of RoutingBrain — task_type, complexity, department, required_capability, confidence, classified_by (meta_llm | heuristic_fallback)

**`RoutingDecision`** (`app/models/routing.py`): primary_model, provider, fallback_models, model_tier, cost_budget_applied, policy_name

**`ChatCompletionRequest`** (`app/models/request.py`): Standard OpenAI format + optional `X-Department` and `X-Budget-Tier` extension fields

**`CostRecord`** (`app/models/cost.py`): Per-request cost breakdown including `meta_llm_cost_usd` (overhead tracking)

**`DepartmentPolicy`** (`app/models/policy.py`): Top-level YAML structure with `rules: list[RoutingRule]` and `budget_controls`

---

## Key API Endpoints

**Proxy (OpenAI-compatible):**
- `POST /v1/chat/completions` — core routing endpoint
- `GET /v1/models` — list all routable model IDs
- `POST /v1/embeddings`

**Internal Admin:**
- `GET /internal/routing/decision/{request_id}` — inspect routing decision for any request
- `POST /internal/routing/policies/reload` — hot-reload YAML without restart
- `GET /internal/analytics/cost?group_by=department&start=...` — cost breakdown
- `GET /internal/analytics/routing-stats` — tier distribution, RoutingBrain overhead %, fallback rate
- `GET /health` — provider connectivity status

---

## Build Sequence (4 Phases)

### Phase 1 — Working Proxy (no routing yet)
1. FastAPI app factory (`main.py`, `core/config.py`)
2. OpenAI-compatible request/response models
3. Single provider adapter (`providers/openai.py` + `providers/base.py`)
4. Pass-through `/v1/chat/completions` endpoint
5. Auth middleware (API key → user/dept)

### Phase 2 — Routing Intelligence
6. `routing/analyzer.py` — heuristic pre-analysis
7. `config/models.yaml` + `config/routing_policies/rd.yaml`
8. `routing/policy.py` — YAML loader + rule matching
9. `routing/routing_brain.py` — RoutingBrain classifier + timeout fallback
10. `routing/engine.py` — full orchestration pipeline

### Phase 3 — All Providers + Cost Tracking
11. All provider adapters (Anthropic, Gemini, Ollama, vLLM)
12. `providers/registry.py` — provider factory
13. `cost/pricing.py` + `cost/tracker.py`
14. PostgreSQL storage (SQLAlchemy async + Alembic)
15. Redis client + budget enforcement

### Phase 4 — Observability + Admin
16. `observability/audit_log.py` — structured JSONL routing log
17. `observability/metrics.py` — Prometheus metrics
18. Internal admin API endpoints
19. Rate limiting middleware
20. Integration tests + Docker Compose

---

## Verification Plan

1. **Unit tests**: `pytest tests/unit/` — test analyzer keyword detection, policy rule matching, cost calculation, RoutingBrain JSON parsing
2. **Integration test**: Send a Python code review request to `/v1/chat/completions` — verify it routes to `claude-sonnet-4-5`, not Opus or Haiku
3. **Cost overhead check**: Run 100 requests, query `/internal/analytics/routing-stats` — confirm RoutingBrain overhead is < 5% of total spend
4. **Budget guardrail test**: Set `daily_limit_usd_per_user: 0.01`, send complex request — verify it downgrades to `fast_cheap` tier
5. **Fallback test**: Disable primary provider in config, confirm fallback model is used transparently
6. **OpenAI SDK compatibility**: Use `openai` Python SDK with `base_url` pointing to this service — confirm existing code works unchanged
7. **Policy hot-reload**: Update `rd.yaml`, call `POST /internal/routing/policies/reload`, verify next request uses updated rules without restart
