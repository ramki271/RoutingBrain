"use client";

import { useState } from "react";
import {
  fetchBudgetStatus,
  sendMessage,
  simulateRouting,
  SimulateResult,
  BudgetStatusResponse,
  getSavedApiKey,
  setSavedApiKey,
} from "@/lib/api";
import { TestTube2, PlayCircle, Wallet, MessageSquare } from "lucide-react";

const TASK_TYPES = ["code_generation","code_review","test_generation","debugging","architecture_design","documentation","requirement_analysis","question_answer","data_analysis","math_reasoning","general"];
const COMPLEXITIES = ["simple","medium","complex"];
const DEPARTMENTS = ["rd","sales","marketing","hr","finance","general"];
const RISK_LEVELS = ["auto","low","medium","high","regulated"];
type RoutingApiError = Error & { message: string };

export default function LabPage() {
  const [apiKey, setApiKey] = useState(getSavedApiKey());
  const [tenantId, setTenantId] = useState("acme");
  const [userId, setUserId] = useState("user-1");
  const [department, setDepartment] = useState("rd");
  const [taskType, setTaskType] = useState("code_generation");
  const [complexity, setComplexity] = useState("simple");
  const [riskLevel, setRiskLevel] = useState("auto");
  const [budgetPct, setBudgetPct] = useState(0);
  const [prompt, setPrompt] = useState("Write a Python function to reverse a linked list");
  const [sim, setSim] = useState<SimulateResult | null>(null);
  const [budget, setBudget] = useState<BudgetStatusResponse | null>(null);
  const [chatResult, setChatResult] = useState<string>("");
  const [chatRouting, setChatRouting] = useState<unknown>(null);
  const [loadingSim, setLoadingSim] = useState(false);
  const [loadingBudget, setLoadingBudget] = useState(false);
  const [loadingChat, setLoadingChat] = useState(false);
  const [error, setError] = useState<string>("");

  const selectStyle: React.CSSProperties = {
    background: "var(--bg-3)",
    border: "1px solid var(--border-2)",
    borderRadius: 6,
    color: "var(--text)",
    fontSize: 12,
    padding: "6px 10px",
  };

  const runSimulate = async () => {
    setLoadingSim(true);
    setError("");
    try {
      const result = await simulateRouting({
        api_key: apiKey,
        tenant_id: tenantId,
        task_type: taskType,
        complexity,
        department,
        risk_level: riskLevel === "auto" ? undefined : riskLevel,
        budget_pct: budgetPct,
      });
      setSim(result);
    } catch (e: unknown) {
      const err = e as RoutingApiError;
      setError(err?.message || "Simulation failed");
    } finally {
      setLoadingSim(false);
    }
  };

  const runBudgetStatus = async () => {
    setLoadingBudget(true);
    setError("");
    try {
      const result = await fetchBudgetStatus({
        api_key: apiKey,
        tenant_id: tenantId,
        user_id: userId,
        department,
      });
      setBudget(result);
    } catch (e: unknown) {
      const err = e as RoutingApiError;
      setError(err?.message || "Budget status failed");
    } finally {
      setLoadingBudget(false);
    }
  };

  const runLiveChat = async () => {
    setLoadingChat(true);
    setError("");
    setChatResult("");
    setChatRouting(null);
    try {
      const result = await sendMessage({
        messages: [{ role: "user", content: prompt }],
        department,
        tenantId,
        userId,
        apiKey,
        stream: false,
      });
      setChatResult(result.content);
      setChatRouting(result.routing);
    } catch (e: unknown) {
      const err = e as RoutingApiError;
      setError(err?.message || "Live chat failed");
    } finally {
      setLoadingChat(false);
    }
  };

  return (
    <div style={{ padding: "24px 28px", maxWidth: 1100, margin: "0 auto" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
        <TestTube2 size={16} color="var(--accent)" />
        <h1 style={{ fontSize: 18, fontWeight: 600, margin: 0 }}>Governance Lab</h1>
      </div>
      <div style={{ fontSize: 12, color: "var(--text-2)", marginBottom: 18 }}>
        Test tenant-aware routing and live Redis budget enforcement without leaving the UI.
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr auto", gap: 8, marginBottom: 12 }}>
        <input
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          placeholder="API key"
          style={{ ...selectStyle, width: "100%", fontFamily: "var(--font-geist-mono)" }}
        />
        <button
          onClick={() => setSavedApiKey(apiKey)}
          style={btnStyle("var(--accent)")}
        >
          Save Key
        </button>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: 10, marginBottom: 14 }}>
        <input value={tenantId} onChange={(e) => setTenantId(e.target.value)} placeholder="tenant_id" style={{ ...selectStyle, width: "100%" }} />
        <input value={userId} onChange={(e) => setUserId(e.target.value)} placeholder="user_id" style={{ ...selectStyle, width: "100%" }} />
        <select value={department} onChange={(e) => setDepartment(e.target.value)} style={selectStyle}>
          {DEPARTMENTS.map((d) => <option key={d} value={d}>{d.toUpperCase()}</option>)}
        </select>
        <input type="number" min={0} max={200} value={budgetPct} onChange={(e) => setBudgetPct(Number(e.target.value))} placeholder="budget %" style={{ ...selectStyle, width: "100%" }} />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 10, marginBottom: 14 }}>
        <select value={taskType} onChange={(e) => setTaskType(e.target.value)} style={selectStyle}>
          {TASK_TYPES.map((t) => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}
        </select>
        <select value={complexity} onChange={(e) => setComplexity(e.target.value)} style={selectStyle}>
          {COMPLEXITIES.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        <select value={riskLevel} onChange={(e) => setRiskLevel(e.target.value)} style={selectStyle}>
          {RISK_LEVELS.map((r) => <option key={r} value={r}>{r}</option>)}
        </select>
      </div>

      <textarea
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        rows={4}
        style={{ ...selectStyle, width: "100%", resize: "vertical", marginBottom: 12, fontFamily: "inherit" }}
      />

      <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
        <button onClick={runSimulate} disabled={loadingSim} style={btnStyle("var(--accent)")}>
          <PlayCircle size={14} /> {loadingSim ? "Running…" : "Simulate Routing"}
        </button>
        <button onClick={runBudgetStatus} disabled={loadingBudget} style={btnStyle("var(--green)")}>
          <Wallet size={14} /> {loadingBudget ? "Checking…" : "Check Budget"}
        </button>
        <button onClick={runLiveChat} disabled={loadingChat} style={btnStyle("var(--amber)")}>
          <MessageSquare size={14} /> {loadingChat ? "Sending…" : "Send Live Chat"}
        </button>
      </div>

      {error && <div style={{ color: "var(--red)", fontSize: 12, marginBottom: 12 }}>{error}</div>}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        <Card title="Simulation Result">{sim ? <JsonView data={sim} /> : <Empty text="Run simulation to view policy trace/result." />}</Card>
        <Card title="Budget Status">{budget ? <JsonView data={budget} /> : <Empty text="Check budget to view live Redis counters and budget %." />}</Card>
      </div>

      <div style={{ marginTop: 12 }}>
        <Card title="Live Chat Result">
          {chatRouting ? (
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              <div>
                <div style={{ fontSize: 11, color: "var(--text-3)", marginBottom: 6 }}>Response</div>
                <pre style={preStyle}>{chatResult || "(empty response)"}</pre>
              </div>
              <div>
                <div style={{ fontSize: 11, color: "var(--text-3)", marginBottom: 6 }}>Routing Metadata</div>
                <pre style={preStyle}>{JSON.stringify(chatRouting, null, 2)}</pre>
              </div>
            </div>
          ) : (
            <Empty text="Send live chat to inspect x_routing_decision with tenant/user headers." />
          )}
        </Card>
      </div>
    </div>
  );
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ border: "1px solid var(--border)", borderRadius: 8, background: "var(--bg-1)", overflow: "hidden" }}>
      <div style={{ padding: "10px 12px", borderBottom: "1px solid var(--border)", fontSize: 12, color: "var(--text-2)" }}>{title}</div>
      <div style={{ padding: 12 }}>{children}</div>
    </div>
  );
}

function JsonView({ data }: { data: unknown }) {
  return <pre style={preStyle}>{JSON.stringify(data, null, 2)}</pre>;
}

function Empty({ text }: { text: string }) {
  return <div style={{ fontSize: 12, color: "var(--text-3)" }}>{text}</div>;
}

function btnStyle(color: string): React.CSSProperties {
  return {
    display: "inline-flex",
    alignItems: "center",
    gap: 6,
    border: "none",
    background: color,
    color: "white",
    borderRadius: 6,
    padding: "7px 12px",
    fontSize: 12,
    cursor: "pointer",
  };
}

const preStyle: React.CSSProperties = {
  margin: 0,
  background: "var(--bg-2)",
  border: "1px solid var(--border)",
  borderRadius: 6,
  padding: "10px 12px",
  fontSize: 11,
  fontFamily: "var(--font-geist-mono)",
  color: "var(--text-2)",
  maxHeight: 300,
  overflow: "auto",
  whiteSpace: "pre-wrap",
  wordBreak: "break-word",
};
