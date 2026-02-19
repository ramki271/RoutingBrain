const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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
  stream?: boolean;
  onToken?: (token: string) => void;
  onRoutingDecision?: (decision: RoutingDecision) => void;
}

export async function sendMessage(opts: SendMessageOptions): Promise<{
  content: string;
  routing: RoutingDecision | null;
}> {
  const { messages, department = "rd", stream = true, onToken, onRoutingDecision } = opts;

  const response = await fetch(`${API_BASE}/v1/chat/completions`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: "Bearer rb-dev-key-1",
      "X-Department": department,
    },
    body: JSON.stringify({
      model: "auto",
      messages,
      stream,
    }),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err?.error?.message || `HTTP ${response.status}`);
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

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const chunk = decoder.decode(value, { stream: true });
    const lines = chunk.split("\n");

    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      const data = line.slice(6).trim();
      if (data === "[DONE]") break;

      try {
        const parsed = JSON.parse(data);
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

export async function fetchHealth() {
  const res = await fetch(`${API_BASE}/health`, {
    headers: { Authorization: "Bearer rb-dev-key-1" },
  });
  return res.json();
}
