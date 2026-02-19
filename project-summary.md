# RoutingBrain — Project Summary

**Tagline:** Enterprise AI Governance Platform — routes every LLM request to the right model at the right cost with the right risk controls.

---

## What We Built

RoutingBrain is an **OpenAI-compatible proxy** that sits in front of any LLM stack. Clients use their existing OpenAI SDK unchanged (just point `base_url` at this service) and RoutingBrain automatically classifies each request, applies risk and governance rules, and routes to the most appropriate model.

```
Client (OpenAI SDK, base_url=RoutingBrain)
        │
        ▼
POST /v1/chat/completions
        │
        ├── Auth Middleware          API key → tenant/user/dept
        ├── RequestId Middleware     Attaches X-Request-Id to every request
        │
        ▼
RoutingEngine.route()
        │
        ├── 1. PreAnalyzer          Free heuristics: token count, code blocks, keyword signals
        ├── 2. RiskAnalyzer         Deterministic gate: PII/PHI/legal/financial → risk level
        ├── 3. RoutingBrain         Claude Haiku classifies: task type, complexity, confidence
        │        └── fallback to heuristics if timeout or confidence < 0.6
        ├── 4. PolicyEngine         YAML rules → model selection; risk floor enforced; budget guardrails
        └── 5. ProviderRegistry     Calls actual LLM; retries on fallback chain
                │
                ├── anthropic.py / openai.py / gemini.py / ollama.py
                └── Normalized SSE streaming
        │
        ▼
Response → Client
x_routing_decision → embedded in response (task type, complexity, risk, model, rationale)
```

---

## Key Differentiators vs Generic Routers

| Capability | LiteLLM / OpenRouter / Bedrock | RoutingBrain |
|---|---|---|
| Multi-model routing | ✅ | ✅ |
| Fallback chains | ✅ | ✅ |
| Cost tracking | ✅ | ✅ (Phase 3) |
| Prompt complexity routing | ✅ | ✅ |
| **Department-aware routing** | ❌ | ✅ |
| **Business policy engine (YAML)** | ❌ | ✅ |
| **Risk-based governance** | ❌ | ✅ |
| **Data residency enforcement** | ❌ | ✅ |
| **Task type classification (10 types)** | ❌ | ✅ |
| **Outcome-based escalation** | ❌ | Roadmap |
| **Org-level AI governance dashboard** | ❌ | Roadmap |

> Generic routers answer: "Which model fits this prompt?"
> RoutingBrain answers: "Which AI path is correct for this business context at the right cost and risk level?"

---

## Tech Stack

| Layer | Technology |
|---|---|
| Runtime | Python 3.11 + FastAPI (async) |
| RoutingBrain classifier | Claude Haiku 4.5 (~$0.001/call overhead) |
| Providers | Anthropic, OpenAI, Google Gemini, Ollama, vLLM |
| Interface | OpenAI-compatible `/v1/chat/completions` |
| Config | YAML routing policies (hot-reloadable) |
| Frontend | Next.js 16 + Tailwind CSS + Geist font |
| Storage (Phase 3) | PostgreSQL (SQLAlchemy async) + Redis |
| Observability (Phase 3) | Prometheus metrics + JSONL audit log |

---

## Project Structure

```
RoutingBrain/
├── Makefile                          # Dev commands
├── docker-compose.yml                # Full stack (Phase 3+)
├── plan.md                           # Original implementation plan
├── savings.md                        # Cost-benefit analysis
├── roadmap.md                        # Differentiation strategy
│
├── backend/
│   ├── pyproject.toml
│   ├── .env.example
│   ├── config/
│   │   ├── models.yaml               # All models + pricing
│   │   ├── meta_llm_system_prompt.txt # RoutingBrain classifier prompt
│   │   └── routing_policies/
│   │       ├── base.yaml             # Default fallback policy
│   │       └── rd.yaml               # R&D department policy (23 rules)
│   └── app/
│       ├── main.py                   # FastAPI app factory
│       ├── core/
│       │   ├── config.py             # Pydantic settings
│       │   ├── logging.py            # Structured JSON logging
│       │   └── exceptions.py        # Custom exception handlers
│       ├── api/
│       │   ├── v1/
│       │   │   ├── chat.py           # POST /v1/chat/completions ← CORE
│       │   │   └── models.py         # GET /v1/models
│       │   └── internal/
│       │       ├── health.py         # GET /health, /ready
│       │       └── routing.py        # Policy reload + inspection
│       ├── routing/
│       │   ├── analyzer.py           # Heuristic pre-analysis
│       │   ├── risk_analyzer.py      # Risk/governance gate ← DIFFERENTIATOR
│       │   ├── routing_brain.py      # Claude Haiku classifier
│       │   ├── policy.py             # YAML policy engine
│       │   └── engine.py             # Full pipeline orchestrator
│       ├── providers/
│       │   ├── base.py               # Abstract BaseProvider
│       │   ├── anthropic.py
│       │   ├── openai.py
│       │   ├── gemini.py
│       │   ├── ollama.py
│       │   └── registry.py           # Provider factory + health checks
│       └── models/
│           ├── request.py            # ChatCompletionRequest (OpenAI-compat)
│           ├── response.py
│           ├── routing.py            # ClassificationResult, RoutingOutcome
│           ├── cost.py
│           └── policy.py
│
└── frontend/
    ├── app/
    │   ├── page.tsx                  # Playground (chat + routing panel)
    │   ├── inspector/page.tsx        # Routing rules + provider health
    │   └── analytics/page.tsx        # Cost projections + savings
    ├── components/
    │   ├── nav.tsx                   # Sidebar navigation
    │   └── routing-panel.tsx         # Live routing decision panel
    └── lib/
        └── api.ts                    # Backend API client
```

---

## Routing Pipeline (5 Steps)

### Step 1 — PreAnalyzer (free, ~0ms)
Extracts heuristic signals without any LLM call:
- Estimated token count via `tiktoken`
- Code block and language detection
- Keyword matching → heuristic task type + complexity
- Department hint from `X-Department` header

### Step 2 — RiskAnalyzer (free, ~0ms)
Deterministic pattern-matching gate. Runs **before** RoutingBrain so risk is never overridden.

| Risk Level | Trigger | Provider Constraint |
|---|---|---|
| `low` | No signals | All providers allowed |
| `medium` | Customer data, business metrics, external comms | All providers allowed, logged |
| `high` | Legal contracts, NDA, exec comms, M&A, credentials | Direct commercial APIs forbidden; OSS + Bedrock/Azure only |
| `regulated` | PII, PHI, HIPAA, SOX, PCI-DSS, GDPR | Direct commercial APIs forbidden; OSS + Bedrock/Azure only; audit required |

**Key insight:** OSS (Ollama/vLLM) is self-hosted — data never leaves your infra — so it is **always allowed** for any risk level. Direct commercial APIs (Anthropic/OpenAI/Gemini direct) send data off-prem, so they are forbidden for high/regulated content. AWS Bedrock and Azure AI Foundry have BAA/DPA agreements and are allowed for regulated content.

### Step 3 — RoutingBrain (Claude Haiku 4.5, 3s timeout)
Classifies the request and returns structured JSON:
```json
{
  "task_type": "code_review",
  "complexity": "medium",
  "department": "rd",
  "required_capability": ["deep_reasoning"],
  "confidence": 0.91,
  "routing_rationale": "Python refactoring with performance focus"
}
```
Falls back to heuristics if timeout or confidence < 0.6.

### Step 4 — PolicyEngine (YAML rules, ~0ms)
Matches classification against department YAML policy. Risk floor applied first (hard gate), then budget guardrails.

### Step 5 — Provider call with fallback chain
Calls primary model → retries with fallback chain on 429/503/timeout. Forbidden providers are stripped from fallback chain at policy time.

---

## Task Types Supported

| Task Type | Example | Default Model (R&D) |
|---|---|---|
| `code_generation` | Write a function, QA automation scripts | Haiku (simple) → Sonnet (medium) → Opus (complex) |
| `code_review` | PR review, security audit | GPT-4o-mini (simple) → Sonnet (medium) → Opus (complex) |
| `test_generation` | Unit tests, Playwright E2E | Haiku (simple) → Sonnet (medium) → Opus (complex) |
| `debugging` | Bug tracing, race conditions | Haiku (simple) → Sonnet (medium) → o1 (complex) |
| `architecture_design` | System design, trade-offs | Sonnet (simple) → Opus (complex) |
| `documentation` | Docstrings, READMEs, API docs | Haiku (simple) → Sonnet (medium) |
| `requirement_analysis` | PRD evaluation, gap analysis | Sonnet (medium) → Opus (complex) |
| `question_answer` | How-to, concepts | Gemini Flash (simple) → Sonnet (medium) |
| `data_analysis` | Log analysis, SQL, large datasets | Gemini Flash (simple) → Gemini Pro (complex, 2M ctx) |
| `math_reasoning` | Algorithms, complexity proofs | o1 (complex) |

---

## Cost Tiers

| Tier | Models | Cost/MTok input | Use case |
|---|---|---|---|
| `fast_cheap` | Haiku, GPT-4o-mini, Gemini Flash | ~$0.10–$0.80 | Simple tasks, boilerplate |
| `balanced` | Sonnet, GPT-4o, Gemini Pro | ~$2.50–$3.00 | Medium complexity |
| `powerful` | Opus, o1 | ~$15–$60 | Complex reasoning, architecture |
| `local` | Llama 3.1 70B, CodeLlama 34B, DeepSeek Coder 33B | $0.00 | Self-hosted OSS |

Expected savings vs always-using-Sonnet (from savings.md):
- **Scenario A** (commercial routing only): 11–14%
- **Scenario B** (commercial + OSS): 44–50%
- **Scenario C** (OSS-first): 57–61%

---

## Frontend — 3 Pages

### Playground (`/`)
- Chat interface with SSE streaming
- Live routing decision panel (right sidebar) showing: model selected, tier, task type, complexity, confidence bar, risk level with shield icon, routing rationale
- Department selector (RD / Sales / Marketing / HR / Finance)
- Test templates organized by: Risk Classification, Code Generation, Code Review, Test Generation, Debugging, Architecture Design, Documentation, Requirement Analysis, Q&A, Math/Algorithms
- Each template shows expected risk/complexity/tier badges for easy validation

### Routing Inspector (`/inspector`)
- Live table of all routing rules per department
- Provider health status (parallel 3s timeout checks)
- Hot-reload button — reloads YAML policies without restart

### Analytics (`/analytics`)
- Routing tier distribution chart
- Task type breakdown
- Cost savings scenarios (A/B/C from savings.md)
- Recommended rollout strategy timeline

---

## API Endpoints

### OpenAI-Compatible
| Method | Path | Description |
|---|---|---|
| `POST` | `/v1/chat/completions` | Core routing endpoint — returns `x_routing_decision` in response |
| `GET` | `/v1/models` | Lists all routable model IDs |

### Internal Admin
| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Provider connectivity status (parallel checks) |
| `GET` | `/ready` | Readiness probe |
| `GET` | `/internal/routing/policies` | Inspect all loaded routing rules |
| `POST` | `/internal/routing/policies/reload` | Hot-reload YAML without restart |

---

## Routing Decision Response (x_routing_decision)
Every non-streaming response includes:
```json
{
  "task_type": "code_generation",
  "complexity": "simple",
  "department": "rd",
  "confidence": 0.97,
  "classified_by": "meta_llm",
  "routing_rationale": "Simple boilerplate generation, R&D context",
  "model_selected": "claude-haiku-4-5-20251001",
  "provider": "anthropic",
  "model_tier": "fast_cheap",
  "rule_matched": "code_gen_simple",
  "fallback_used": false,
  "latency_ms": 312,
  "risk_level": "low",
  "risk_rationale": "No sensitive signals detected — all providers available",
  "data_residency_note": "",
  "audit_required": false
}
```

---

## What's Next (Phases 3 & 4)

### Phase 3 — Cost Tracking + Budget Enforcement
- PostgreSQL: persist every routing decision + cost record
- Redis: per-user/per-tenant daily budget counters
- Live budget guardrails (80% → downgrade tier, 100% → force fast_cheap)
- Real cost metrics in Analytics dashboard

### Phase 4 — Observability + Governance
- JSONL audit log (every routing decision, especially high/regulated)
- Prometheus metrics: routing distribution, RoutingBrain overhead %, fallback rate
- AWS Bedrock + Azure AI Foundry providers (compliant cloud for regulated content)
- Outcome-based escalation: try cheap model first → auto-escalate if quality check fails
- Sales / Marketing / HR / Finance department policies
- Per-department spend dashboards

---

## Running Locally

```bash
# First time setup
make env                  # copy .env.example → .env
# edit backend/.env — add ANTHROPIC_API_KEY

make install-backend      # pip install
make install-frontend     # npm install

# Run (two terminals)
make backend              # http://localhost:8000
make frontend             # http://localhost:3000
```

> Note: No Postgres or Redis needed for Phase 1 & 2. The routing pipeline runs entirely in-memory.
