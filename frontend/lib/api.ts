const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type RoutingApiError = Error & {
  governance_blocked?: boolean;
  error_code?: string;
};

export interface RoutingDecision {
  request_id: string;
  task_type: string;
  complexity: string;
  department: string;
  confidence: number;
  classified_by: string;
  routing_rationale: string;
  model_selected: string;
  provider: string;
  model_tier: string;
  rule_matched: string;
  fallback_used: boolean;
  latency_ms: number;
  risk_level: string;
  risk_rationale: string;
  data_residency_note: string;
  audit_required: boolean;
}

export interface ChatMessage {
  role: "user" | "assistant" | "system";
  content: string;
}

export interface SendMessageOptions {
  messages: ChatMessage[];
  department?: string;
  tenantId?: string;
  userId?: string;
  stream?: boolean;
  onToken?: (token: string) => void;
  onRoutingDecision?: (decision: RoutingDecision) => void;
}

export async function sendMessage(opts: SendMessageOptions): Promise<{
  content: string;
  routing: RoutingDecision | null;
}> {
  const { messages, department = "rd", tenantId, userId, stream = true, onToken, onRoutingDecision } = opts;

  const response = await fetch(`${API_BASE}/v1/chat/completions`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: "Bearer rb-dev-key-1",
      "X-Department": department,
      ...(tenantId ? { "X-Tenant-Id": tenantId } : {}),
      ...(userId ? { "X-User-Id": userId } : {}),
    },
    body: JSON.stringify({
      model: "auto",
      messages,
      stream,
    }),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    const errObj = err?.error || {};
    // Attach governance_blocked flag so the UI can show a specific message
    const error: RoutingApiError = new Error(errObj.message || `HTTP ${response.status}`);
    error.governance_blocked = errObj.governance_blocked ?? false;
    error.error_code = errObj.code ?? "";
    throw error;
  }

  if (!stream) {
    const data = await response.json();
    const content = data.choices?.[0]?.message?.content || "";
    const routing = data.x_routing_decision || null;
    if (routing && onRoutingDecision) onRoutingDecision(routing);
    return { content, routing };
  }

  // SSE streaming
  const reader = response.body!.getReader();
  const decoder = new TextDecoder();
  let content = "";
  let routing: RoutingDecision | null = null;

  // Extract routing from response headers
  const reqId = response.headers.get("X-Request-Id");
  const model = response.headers.get("X-Routing-Model");
  const provider = response.headers.get("X-Routing-Provider");
  const taskType = response.headers.get("X-Task-Type");
  const complexity = response.headers.get("X-Complexity");
  const riskLevel = response.headers.get("X-Risk-Level");
  const auditRequired = response.headers.get("X-Audit-Required");

  if (reqId && model) {
    routing = {
      request_id: reqId,
      task_type: taskType || "",
      complexity: complexity || "",
      department,
      confidence: 0,
      classified_by: "",
      routing_rationale: "",
      model_selected: model,
      provider: provider || "",
      model_tier: "",
      rule_matched: "",
      fallback_used: false,
      latency_ms: 0,
      risk_level: riskLevel || "low",
      risk_rationale: "",
      data_residency_note: "",
      audit_required: auditRequired === "true",
    };
    if (onRoutingDecision) onRoutingDecision(routing!);
  }

  let lastEvent = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const chunk = decoder.decode(value, { stream: true });
    const lines = chunk.split("\n");

    for (const line of lines) {
      // Track event type for named SSE events
      if (line.startsWith("event: ")) {
        lastEvent = line.slice(7).trim();
        continue;
      }

      if (!line.startsWith("data: ")) {
        if (line === "") lastEvent = ""; // blank line resets event
        continue;
      }

      const data = line.slice(6).trim();
      if (data === "[DONE]") break;

      try {
        const parsed = JSON.parse(data);

        // Named routing_decision event — full metadata from server
        if (lastEvent === "routing_decision" || parsed.event === "routing_decision") {
          const rd = parsed.data || parsed;
          routing = {
            request_id: rd.request_id || "",
            task_type: rd.task_type || "",
            complexity: rd.complexity || "",
            department: rd.department || department,
            confidence: rd.confidence ?? 0,
            classified_by: rd.classified_by || "",
            routing_rationale: rd.routing_rationale || "",
            model_selected: rd.model_selected || "",
            provider: rd.provider || "",
            model_tier: rd.model_tier || "",
            rule_matched: rd.rule_matched || "",
            fallback_used: rd.fallback_used ?? false,
            latency_ms: rd.latency_ms ?? 0,
            risk_level: rd.risk_level || "low",
            risk_rationale: rd.risk_rationale || "",
            data_residency_note: rd.data_residency_note || "",
            audit_required: rd.audit_required ?? false,
          };
          if (onRoutingDecision) onRoutingDecision(routing);
          lastEvent = "";
          continue;
        }

        // Normal token delta
        const delta = parsed.choices?.[0]?.delta?.content;
        if (delta) {
          content += delta;
          if (onToken) onToken(delta);
        }
      } catch {
        // skip malformed chunks
      }
    }
  }

  return { content, routing };
}

export async function reloadPolicies(): Promise<void> {
  await fetch(`${API_BASE}/internal/routing/policies/reload`, {
    method: "POST",
    headers: { Authorization: "Bearer rb-dev-key-1" },
  });
}

export async function fetchPolicies() {
  const res = await fetch(`${API_BASE}/internal/routing/policies`, {
    headers: { Authorization: "Bearer rb-dev-key-1" },
  });
  return res.json();
}

export interface SimulateRequest {
  prompt?: string;
  tenant_id?: string;
  task_type: string;
  complexity: string;
  department: string;
  risk_level?: string;
  budget_pct?: number;
}

export interface SimulateResult {
  input: { tenant_id: string; task_type: string; complexity: string; department: string; budget_pct: number };
  risk: { level: string; rationale: string; direct_commercial_forbidden: boolean; audit_required: boolean };
  result: { rule_matched: string; primary_model: string; provider: string; model_tier: string; fallback_models: string[]; rationale: string };
  policy_trace: { rule: string; result: string; reason: string }[];
  constraints_applied: string[];
}

export async function simulateRouting(body: SimulateRequest): Promise<SimulateResult> {
  const res = await fetch(`${API_BASE}/internal/routing/simulate`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: "Bearer rb-dev-key-1" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Simulate failed: ${res.status}`);
  return res.json();
}

export interface AuditEntry {
  request_id: string;
  timestamp: string;
  tenant_id: string;
  department: string;
  user_id: string;
  policy_version: string;
  rule_matched: string;
  risk_level: string;
  risk_rationale: string;
  audit_required: boolean;
  model_selected: string;
  provider: string;
  model_tier: string;
  fallback_used: boolean;
  latency_ms: number;
  prompt_tokens: number;
  completion_tokens: number;
  estimated_cost_usd: number;
  data_residency_note: string;
  constraints_applied: string[];
  policy_trace: { rule: string; result: string; reason: string }[];
  classification_snapshot: {
    task_type: string;
    complexity: string;
    confidence: number;
    classified_by: string;
    department: string;
    risk_signals: string[];
  } | null;
  error: string | null;
}

export interface AuditLogsResponse {
  entries: AuditEntry[];
  total: number;
  filtered: number;
  log_path: string;
}

export async function fetchAuditLogs(params?: {
  limit?: number;
  risk_level?: string;
  department?: string;
  audit_required?: boolean;
}): Promise<AuditLogsResponse> {
  const qs = new URLSearchParams();
  if (params?.limit) qs.set("limit", String(params.limit));
  if (params?.risk_level) qs.set("risk_level", params.risk_level);
  if (params?.department) qs.set("department", params.department);
  if (params?.audit_required !== undefined) qs.set("audit_required", String(params.audit_required));
  const res = await fetch(`${API_BASE}/internal/audit/logs?${qs}`, {
    headers: { Authorization: "Bearer rb-dev-key-1" },
  });
  if (!res.ok) throw new Error(`Audit log fetch failed: ${res.status}`);
  return res.json();
}

export async function fetchHealth() {
  const res = await fetch(`${API_BASE}/health`, {
    headers: { Authorization: "Bearer rb-dev-key-1" },
  });
  return res.json();
}

export interface BudgetStatusRequest {
  tenant_id: string;
  user_id: string;
  department: string;
}

export interface BudgetStatusResponse {
  tenant_id: string;
  user_id: string;
  department: string;
  policy_found: boolean;
  policy_version?: string;
  budget_pct: number;
  limits: {
    daily_limit_usd_per_tenant?: number;
    daily_limit_usd_per_user?: number;
    max_tier?: string;
    downgrade_at_percent?: number;
    force_cheap_at_percent?: number;
  };
  spend: {
    tenant_spend_usd: number;
    user_spend_usd: number;
    date_key?: string;
  };
}

export async function fetchBudgetStatus(body: BudgetStatusRequest): Promise<BudgetStatusResponse> {
  const res = await fetch(`${API_BASE}/internal/routing/budget/status`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: "Bearer rb-dev-key-1" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Budget status failed: ${res.status}`);
  return res.json();
}
