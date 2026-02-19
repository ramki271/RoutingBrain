# Cost-Benefit Analysis: Intelligent LLM Routing Platform

## Baseline Assumptions

**Current default**: Claude Sonnet 4.5 — **$3.00/MTok input, $15.00/MTok output**

**Three routing scenarios are modeled below:**

| Scenario | Description |
|---|---|
| **A — Commercial only** | Routes across Haiku / Sonnet / Opus / o1 |
| **B — Commercial + OSS** | Self-hosted OSS for simple tasks (any data), commercial for medium/complex |
| **C — OSS-first (optimistic)** | OSS handles simple + medium tasks, commercial only for complex |

> **Data Privacy Clarification**: Since OSS models are **self-hosted** (Ollama/vLLM on your infra), **all data — including sensitive/proprietary — is safe to route to OSS**. The routing decision is purely based on **task complexity and required accuracy**, not data sensitivity.

---

### Routing Decision Framework: Complexity × Accuracy, Not Sensitivity

| Task Complexity | Required Accuracy | Routing Decision | Reason |
|---|---|---|---|
| Simple | Moderate OK | **OSS** (Llama 3.1 70B / CodeLlama 34B / DeepSeek Coder 33B) | Self-hosted = safe; OSS quality sufficient |
| Medium | High | **Commercial fast_cheap** (Haiku / GPT-4o-mini) | OSS may miss nuance; cheap commercial closes gap |
| Medium | Very high | **Commercial balanced** (Sonnet) | Proprietary logic, security review needs top accuracy |
| Complex | Highest | **Commercial powerful** (Opus / o1) | OSS cannot match frontier models on hard reasoning |

**OSS models selected (self-hosted):**
- **Llama 3.1 70B** — General tasks, internal Q&A, documentation, summarization
- **CodeLlama 34B** — Code generation boilerplate, unit test scaffolding, inline comments
- **DeepSeek Coder 33B** — Code-specialized, competitive with GPT-4 on coding benchmarks; handles proprietary code safely since self-hosted

**Tasks suited for OSS (simple, any data):**
- Boilerplate code generation, unit test scaffolding
- Internal doc drafts, inline code comments, summarization
- Code reformatting, style fixes, well-understood refactoring patterns
- Internal Q&A on public/internal knowledge bases
- Simple debugging of common errors (null checks, type errors, off-by-one)
- Proprietary code summarization (safe — self-hosted, just lower complexity needed)

**Tasks requiring commercial models (medium/complex, accuracy-critical):**
- Security-sensitive code review and architecture decisions
- Complex multi-file debugging with subtle logic errors
- Novel algorithm design and system architecture trade-off analysis
- Customer-facing content generation requiring polished output
- Complex reasoning over proprietary business logic

---

### Scenario A — Commercial Only Router Behavior
- ~40% simple → `fast_cheap` tier (Haiku/GPT-4o-mini, ~$0.50/MTok blended)
- ~45% medium → `balanced` tier (Sonnet, ~$3.00/MTok)
- ~15% complex → `powerful` tier (Opus/o1, ~$20/MTok blended)
- Meta-LLM routing overhead: ~$0.001/call (Haiku classification)

### Scenario B — Commercial + Self-Hosted OSS Router Behavior
Self-hosted models (Llama 3.1 70B, CodeLlama 34B, DeepSeek Coder 33B via Ollama/vLLM).
GPU infra cost amortized: **~$0.0005/call** (conservative blended).

- ~40% simple (any data) → `local` OSS (~$0.0005/call infra only)
- ~20% medium → `fast_cheap` commercial (Haiku, ~$0.50/MTok)
- ~25% medium high-accuracy → `balanced` tier (Sonnet, ~$3.00/MTok)
- ~15% complex → `powerful` tier (Opus/o1, ~$20/MTok)

### Scenario C — OSS-First Router Behavior
OSS handles simple AND medium tasks where accuracy is not critical.

- ~40% simple → `local` OSS (~$0.0005/call)
- ~20% medium moderate-accuracy → `local` OSS (~$0.0005/call)
- ~25% medium high-accuracy → `balanced` Sonnet
- ~15% complex → `powerful` Opus/o1

### Self-Hosted OSS Infrastructure Cost
| GPU Setup | Monthly Cost | Daily Capacity | Cost/call (amortized) | Best For |
|---|---|---|---|---|
| 1× A10G (24GB) | ~$900/mo | ~50K calls | ~$0.0006/call | Mistral 7B, CodeLlama 13B — simple tasks |
| 1× A100 (80GB) | ~$3,000/mo | ~100K calls | ~$0.0010/call | Llama 3.1 70B, DeepSeek Coder 33B |
| 2× A100 — dual model | ~$6,000/mo | ~200K calls | ~$0.0010/call | Llama 70B + CodeLlama 34B in parallel |

*Blended OSS infra cost used in calculations: **$0.0005/call** (conservative)*

- Meta-LLM routing overhead: ~$0.001/call (Haiku classification)

---

## Request Size Tiers

| Size | Input Tokens | Output Tokens | Sonnet Cost/call (Baseline) |
|---|---|---|---|
| Small | 500 | 300 | $0.0060 |
| Medium | 2,000 | 800 | $0.0180 |
| Large | 5,000 | 2,000 | $0.0450 |

---

## Per-Call Cost: Baseline vs. All Three Scenarios

> All OSS routing uses self-hosted models — data privacy is maintained for **all data types** including sensitive/proprietary. Routing is based on complexity and accuracy requirements only.

### Small Requests (500 in / 300 out) — Baseline: $0.0060/call

| Scenario | Routing Mix | Cost/call | Savings vs Baseline |
|---|---|---|---|
| **A — Commercial** | 40% Haiku + 45% Sonnet + 15% Opus + meta | $0.00606 | ~0% |
| **B — Commercial + OSS** | 40% OSS + 20% Haiku + 25% Sonnet + 15% Opus + meta | **$0.00412** | **32%** |
| **C — OSS-first** | 60% OSS + 10% Haiku + 15% Sonnet + 15% Opus + meta | **$0.00330** | **45%** |

### Medium Requests (2,000 in / 800 out) — Baseline: $0.0180/call

| Scenario | Routing Mix | Cost/call | Savings vs Baseline |
|---|---|---|---|
| **A — Commercial** | 40% Haiku + 45% Sonnet + 15% Opus + meta | $0.01600 | **11%** |
| **B — Commercial + OSS** | 40% OSS + 20% Haiku + 25% Sonnet + 15% Opus + meta | **$0.01003** | **44%** |
| **C — OSS-first** | 60% OSS + 25% Sonnet + 15% Opus + meta | **$0.00778** | **57%** |

### Large Requests (5,000 in / 2,000 out) — Baseline: $0.0450/call

| Scenario | Routing Mix | Cost/call | Savings vs Baseline |
|---|---|---|---|
| **A — Commercial** | 40% Haiku + 45% Sonnet + 15% Opus + meta | $0.03850 | **14%** |
| **B — Commercial + OSS** | 40% OSS + 20% Haiku + 25% Sonnet + 15% Opus + meta | **$0.02258** | **50%** |
| **C — OSS-first** | 60% OSS + 25% Sonnet + 15% Opus + meta | **$0.01755** | **61%** |

> **Why OSS savings increase with request size**: OSS infra cost is flat at $0.0005/call regardless of token count. The commercial API cost avoided scales with tokens — so larger requests see proportionally bigger savings from OSS routing.

---

## Annual Savings by Scale × Request Size × Scenario

> OSS infra cost ($0.0005/call) and GPU server cost (~$72K/yr at scale) already deducted from B and C figures.

### 500–5,000 calls/day (~1M calls/year)

| Request Size | Baseline $/yr | Scenario A saved | Scenario B saved (+OSS) | Scenario C saved (OSS-first) |
|---|---|---|---|---|
| Small | $6,000 | ~$0 | **+$1,880** | **+$2,700** |
| Medium | $18,000 | +$2,000 | **+$7,970** | **+$10,220** |
| Large | $45,000 | +$6,500 | **+$22,580** | **+$27,450** |

### 5,000–50,000 calls/day (~10M calls/year)

| Request Size | Baseline $/yr | Scenario A saved | Scenario B saved (+OSS) | Scenario C saved (OSS-first) |
|---|---|---|---|---|
| Small | $60,000 | ~$0 | **+$18,800** | **+$27,000** |
| Medium | $180,000 | +$20,000 | **+$79,700** | **+$102,200** |
| Large | $450,000 | +$65,000 | **+$225,800** | **+$274,500** |

### > 50,000 calls/day (~27.4M calls/year)

| Request Size | Baseline $/yr | Scenario A saved | Scenario B saved (+OSS) | Scenario C saved (OSS-first) |
|---|---|---|---|---|
| Small | $164,400 | ~$0 | **+$51,500** | **+$74,000** |
| Medium | $493,200 | +$54,800 | **+$218,500** | **+$280,200** |
| Large | $1,233,000 | +$178,100 | **+$618,700** | **+$752,300** |

---

## The Hidden Value: Quality-Adjusted Savings

The raw cost numbers above are **conservative** — they don't account for:

| Benefit | Impact |
|---|---|
| **Correct model for complex tasks** | Using Opus/o1 for architecture design reduces engineering rework. 10 min saved/week × 50 engineers = **500 hrs/yr** |
| **Faster responses on simple tasks** | Haiku is 3–5× faster than Opus. Dev velocity improvement for autocomplete/Q&A |
| **Budget guardrails** | Prevents runaway spend from a single user hammering expensive models |
| **Departmental expansion** | Adding Sales/Marketing/HR routing multiplies savings — zero engineering, just a YAML file |
| **Cost chargeback** | Every routing decision is logged — enables per-team cost attribution |

---

## Cost of Building vs. Not Building

| | Build It | Don't Build It |
|---|---|---|
| Engineering cost | ~4 weeks (1 engineer sprint) | $0 |
| Annual savings (medium/large, 5K–50K calls/day) | **$20K–$65K/yr** | $0 |
| Payback period | **< 1 month** at scale | — |
| Marginal cost per new department | ~1 day (YAML config file) | N/A |

---

## Key Takeaway

| Scale | Scenario A (Commercial) | Scenario B (+ OSS) | Scenario C (OSS-first) |
|---|---|---|---|
| 500–5K calls/day | Up to $6,500/yr | Up to **$22,580/yr** | Up to **$27,450/yr** |
| 5K–50K calls/day | Up to $65,000/yr | Up to **$225,800/yr** | Up to **$274,500/yr** |
| >50K calls/day | Up to $178,100/yr | Up to **$618,700/yr** | Up to **$752,300/yr** |

> Since OSS models are **self-hosted**, both sensitive and non-sensitive data can be routed to them safely. This unlocks the full OSS cost advantage — routing is now purely a **quality/accuracy** decision, not a data residency decision. This is why B and C savings are significantly higher than the previous version of this analysis.

> Adding self-hosted OSS models delivers **3–4× more savings** than commercial routing alone.

---

## Recommended Strategy by Org Maturity

| Stage | Recommendation | Expected Savings |
|---|---|---|
| **Start (Month 1)** | Deploy commercial-only router (Scenario A) | 11–14% |
| **Month 2–3** | Add self-hosted OSS (Llama 3.1 70B + CodeLlama 34B + DeepSeek Coder 33B) for simple tasks across ALL data types (Scenario B) | 44–50% |
| **Month 4+** | Tune OSS to handle medium-complexity tasks too; expand to Sales/Marketing (Scenario C) | 57–61% |

**OSS model selection for self-hosted stack:**
- **Llama 3.1 70B** → General tasks, Q&A, documentation, summarization (all data safe)
- **CodeLlama 34B** → Code boilerplate, unit tests, comments, reformatting (proprietary code safe)
- **DeepSeek Coder 33B** → Code-specialized tasks competitive with GPT-4 on benchmarks (proprietary code safe)

---

## Sensitivity: If Complex Task Rate is 5% (instead of 15%)

At a **5% complex rate** (more realistic for most orgs after routing optimizes):
- routing sends even less to expensive Opus/o1

| Scale | Scenario A | Scenario B (+OSS) | Scenario C (OSS-first) |
|---|---|---|---|
| 5K–50K/day, Large | ~$117K/yr | **~$280K/yr** | **~$340K/yr** |
| >50K/day, Large | ~$320K/yr | **~$770K/yr** | **~$935K/yr** |
