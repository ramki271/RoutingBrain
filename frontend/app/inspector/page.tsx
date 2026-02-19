"use client";

import { useState, useEffect } from "react";
import { fetchPolicies, fetchHealth, reloadPolicies, simulateRouting, SimulateResult } from "@/lib/api";
import { GitBranch, RefreshCw, AlertCircle, ChevronDown, ChevronRight, FlaskConical, ShieldAlert } from "lucide-react";

const TASK_TYPES = ["code_generation","code_review","test_generation","debugging","architecture_design","documentation","requirement_analysis","question_answer","data_analysis","math_reasoning","general"];
const COMPLEXITIES = ["simple","medium","complex"];
const DEPARTMENTS = ["rd","sales","marketing","hr","finance","general"];
const RISK_LEVELS = ["auto","low","medium","high","regulated"];

const TRACE_COLORS: Record<string, string> = {
  matched: "var(--green)",
  skipped: "var(--text-3)",
  risk_override: "var(--amber)",
  budget_override: "var(--amber)",
  fallback_filtered: "var(--red)",
};

function PolicySimulator() {
  const [taskType, setTaskType] = useState("code_generation");
  const [complexity, setComplexity] = useState("medium");
  const [department, setDepartment] = useState("rd");
  const [riskLevel, setRiskLevel] = useState("auto");
  const [budgetPct, setBudgetPct] = useState(0);
  const [result, setResult] = useState<SimulateResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await simulateRouting({
        task_type: taskType,
        complexity,
        department,
        risk_level: riskLevel === "auto" ? undefined : riskLevel,
        budget_pct: budgetPct,
      });
      setResult(res);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Simulation failed");
    } finally {
      setLoading(false);
    }
  };

  const selectStyle = {
    background: "var(--bg-3)", border: "1px solid var(--border-2)", borderRadius: 5,
    color: "var(--text)", fontSize: 12, padding: "5px 10px", cursor: "pointer", fontFamily: "inherit",
  };

  const riskConfig: Record<string, { color: string }> = {
    low: { color: "var(--green)" }, medium: { color: "var(--accent)" },
    high: { color: "var(--amber)" }, regulated: { color: "var(--red)" },
  };

  return (
    <div style={{ border: "1px solid var(--accent-border)", borderRadius: 8, overflow: "hidden", marginBottom: 28, background: "var(--accent-dim)" }}>
      {/* Header */}
      <div style={{ padding: "14px 18px", borderBottom: "1px solid var(--accent-border)", display: "flex", alignItems: "center", gap: 8 }}>
        <FlaskConical size={14} color="var(--accent)" strokeWidth={1.5} />
        <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text)" }}>Policy Simulator</span>
        <span style={{ fontSize: 11, color: "var(--text-2)", marginLeft: 4 }}>Simulate routing without calling any LLM</span>
      </div>

      <div style={{ padding: "16px 18px" }}>
        {/* Controls */}
        <div style={{ display: "flex", flexWrap: "wrap", gap: 10, marginBottom: 14, alignItems: "center" }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <span style={{ fontSize: 10, color: "var(--text-3)", textTransform: "uppercase", letterSpacing: "0.06em" }}>Task Type</span>
            <select value={taskType} onChange={e => setTaskType(e.target.value)} style={selectStyle}>
              {TASK_TYPES.map(t => <option key={t} value={t}>{t.replace(/_/g, " ")}</option>)}
            </select>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <span style={{ fontSize: 10, color: "var(--text-3)", textTransform: "uppercase", letterSpacing: "0.06em" }}>Complexity</span>
            <select value={complexity} onChange={e => setComplexity(e.target.value)} style={selectStyle}>
              {COMPLEXITIES.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <span style={{ fontSize: 10, color: "var(--text-3)", textTransform: "uppercase", letterSpacing: "0.06em" }}>Department</span>
            <select value={department} onChange={e => setDepartment(e.target.value)} style={selectStyle}>
              {DEPARTMENTS.map(d => <option key={d} value={d}>{d.toUpperCase()}</option>)}
            </select>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <span style={{ fontSize: 10, color: "var(--text-3)", textTransform: "uppercase", letterSpacing: "0.06em" }}>Risk Level</span>
            <select value={riskLevel} onChange={e => setRiskLevel(e.target.value)} style={selectStyle}>
              {RISK_LEVELS.map(r => <option key={r} value={r}>{r}</option>)}
            </select>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <span style={{ fontSize: 10, color: "var(--text-3)", textTransform: "uppercase", letterSpacing: "0.06em" }}>Budget Used %</span>
            <input
              type="number" min={0} max={120} value={budgetPct}
              onChange={e => setBudgetPct(Number(e.target.value))}
              style={{ ...selectStyle, width: 70 }}
            />
          </div>
          <button
            onClick={run}
            disabled={loading}
            style={{
              alignSelf: "flex-end", padding: "6px 16px", borderRadius: 6,
              background: "var(--accent)", border: "none", color: "white",
              fontSize: 12, fontWeight: 500, cursor: "pointer", opacity: loading ? 0.6 : 1,
            }}
          >
            {loading ? "Running…" : "Simulate"}
          </button>
        </div>

        {error && (
          <div style={{ fontSize: 12, color: "var(--red)", padding: "8px 12px", background: "var(--red-dim)", borderRadius: 6, marginBottom: 10 }}>
            {error}
          </div>
        )}

        {result && (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
            {/* Result */}
            <div style={{ padding: "14px", borderRadius: 7, background: "var(--bg-2)", border: "1px solid var(--border)" }}>
              <div style={{ fontSize: 11, color: "var(--text-3)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 10 }}>Result</div>

              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
                <ShieldAlert size={13} color={riskConfig[result.risk.level]?.color || "var(--text-2)"} />
                <span style={{ fontSize: 11, fontWeight: 600, color: riskConfig[result.risk.level]?.color || "var(--text-2)", fontFamily: "var(--font-geist-mono)" }}>
                  {result.risk.level.toUpperCase()} RISK
                </span>
                {result.risk.audit_required && (
                  <span style={{ fontSize: 10, color: "var(--amber)", background: "var(--amber-dim)", padding: "1px 6px", borderRadius: 3, fontFamily: "var(--font-geist-mono)" }}>AUDIT</span>
                )}
              </div>

              <div style={{ fontFamily: "var(--font-geist-mono)", fontSize: 13, fontWeight: 600, color: "var(--text)", marginBottom: 4 }}>
                {result.result.primary_model}
              </div>
              <div style={{ fontSize: 11, color: "var(--text-2)", marginBottom: 8 }}>
                via <span style={{ color: "var(--text)" }}>{result.result.provider}</span>
                {" · "}
                <span style={{ color: TIER_COLORS[result.result.model_tier] || "var(--text-2)" }}>{result.result.model_tier.replace("_", " ")}</span>
              </div>
              <div style={{ fontSize: 11, color: "var(--text-3)", marginBottom: 6 }}>Rule: <span style={{ color: "var(--text-2)", fontFamily: "var(--font-geist-mono)" }}>{result.result.rule_matched}</span></div>
              <div style={{ fontSize: 11, color: "var(--text-3)", marginBottom: result.result.fallback_models.length > 0 ? 6 : 0 }}>{result.result.rationale}</div>
              {result.result.fallback_models.length > 0 && (
                <div style={{ fontSize: 10, color: "var(--text-3)", fontFamily: "var(--font-geist-mono)" }}>
                  Fallbacks: {result.result.fallback_models.join(" → ")}
                </div>
              )}
              {result.constraints_applied.length > 0 && (
                <div style={{ marginTop: 8, display: "flex", flexWrap: "wrap", gap: 5 }}>
                  {result.constraints_applied.map((c, i) => (
                    <span key={i} style={{ fontSize: 10, color: "var(--amber)", background: "var(--amber-dim)", padding: "2px 7px", borderRadius: 3, fontFamily: "var(--font-geist-mono)" }}>
                      {c}
                    </span>
                  ))}
                </div>
              )}
            </div>

            {/* Policy trace */}
            <div style={{ padding: "14px", borderRadius: 7, background: "var(--bg-2)", border: "1px solid var(--border)" }}>
              <div style={{ fontSize: 11, color: "var(--text-3)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 10 }}>
                Policy Trace
                <span style={{ marginLeft: 8, color: "var(--text-3)", fontWeight: 400, letterSpacing: 0, textTransform: "none" }}>
                  ({result.policy_trace.filter(t => t.result === "skipped").length} rules skipped)
                </span>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                {/* Only show non-skipped entries */}
                {result.policy_trace.filter(t => t.result !== "skipped").map((entry, i) => (
                  <div key={i} style={{ display: "flex", gap: 8, alignItems: "flex-start", fontSize: 11 }}>
                    <span style={{ color: TRACE_COLORS[entry.result] || "var(--text-2)", fontFamily: "var(--font-geist-mono)", flexShrink: 0, fontWeight: 700, fontSize: 13 }}>
                      {entry.result === "matched" ? "✓" : "↑"}
                    </span>
                    <div>
                      <span style={{ color: "var(--text)", fontFamily: "var(--font-geist-mono)" }}>{entry.rule}</span>
                      <span style={{ color: TRACE_COLORS[entry.result] || "var(--text-3)", marginLeft: 6, fontWeight: entry.result !== "matched" ? 500 : 400 }}>
                        {entry.result !== "matched" ? `[${entry.result}] ` : ""}{entry.reason}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

const TIER_COLORS: Record<string, string> = {
  fast_cheap: "var(--green)",
  balanced: "var(--accent)",
  powerful: "var(--amber)",
  local: "var(--text-2)",
};

const TIER_LABELS: Record<string, string> = {
  fast_cheap: "Fast / Cheap",
  balanced: "Balanced",
  powerful: "Powerful",
  local: "Local OSS",
};

interface Rule {
  name: string;
  task_type: string | null;
  complexity: string | null;
  primary_model: string;
  virtual_model: string | null;
  provider: string;
  model_tier: string;
  rationale: string;
}

interface Policy {
  department: string;
  version: string;
  description: string;
  rule_count: number;
  rules: Rule[];
}

interface HealthData {
  status: string;
  providers: Record<string, boolean>;
}

function StatusDot({ ok }: { ok: boolean }) {
  return (
    <span
      style={{
        display: "inline-block",
        width: 7,
        height: 7,
        borderRadius: "50%",
        background: ok ? "var(--green)" : "var(--red)",
        flexShrink: 0,
      }}
    />
  );
}

function PolicySection({ dept, policy }: { dept: string; policy: Policy }) {
  const [open, setOpen] = useState(dept === "rd");

  return (
    <div style={{ border: "1px solid var(--border)", borderRadius: 8, overflow: "hidden" }}>
      {/* Header */}
      <button
        onClick={() => setOpen(!open)}
        style={{
          width: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "14px 18px",
          background: "var(--bg-2)",
          border: "none",
          cursor: "pointer",
          gap: 12,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          {open ? <ChevronDown size={14} color="var(--text-2)" /> : <ChevronRight size={14} color="var(--text-2)" />}
          <span style={{ fontWeight: 600, fontSize: 13, color: "var(--text)", textTransform: "uppercase", letterSpacing: "0.04em", fontFamily: "var(--font-geist-mono)" }}>
            {dept}
          </span>
          <span style={{ fontSize: 11, color: "var(--text-3)" }}>{policy.description}</span>
        </div>
        <span
          style={{
            fontSize: 11,
            color: "var(--text-2)",
            background: "var(--bg-3)",
            border: "1px solid var(--border-2)",
            borderRadius: 4,
            padding: "2px 8px",
            fontFamily: "var(--font-geist-mono)",
          }}
        >
          {policy.rule_count} rules · v{policy.version}
        </span>
      </button>

      {open && (
        <div>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ background: "var(--bg-1)" }}>
                {["Rule", "Task Type", "Complexity", "Model", "Provider", "Tier", "Rationale"].map((h) => (
                  <th
                    key={h}
                    style={{
                      padding: "8px 14px",
                      textAlign: "left",
                      fontSize: 11,
                      fontWeight: 500,
                      color: "var(--text-3)",
                      letterSpacing: "0.05em",
                      textTransform: "uppercase",
                      borderBottom: "1px solid var(--border)",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {policy.rules.map((rule, i) => (
                <tr
                  key={i}
                  style={{ borderBottom: "1px solid var(--border)" }}
                  onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = "var(--bg-2)"; }}
                  onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = "transparent"; }}
                >
                  <td style={{ padding: "9px 14px", fontFamily: "var(--font-geist-mono)", fontSize: 11, color: "var(--text-2)" }}>
                    {rule.name}
                  </td>
                  <td style={{ padding: "9px 14px", fontSize: 12, color: "var(--text)" }}>
                    {rule.task_type ? rule.task_type.replace(/_/g, " ") : <span style={{ color: "var(--text-3)" }}>any</span>}
                  </td>
                  <td style={{ padding: "9px 14px" }}>
                    {rule.complexity ? (
                      <span
                        style={{
                          fontSize: 11,
                          fontFamily: "var(--font-geist-mono)",
                          color:
                            rule.complexity === "simple" ? "var(--green)" :
                            rule.complexity === "complex" ? "var(--amber)" : "var(--accent)",
                        }}
                      >
                        {rule.complexity}
                      </span>
                    ) : (
                      <span style={{ color: "var(--text-3)", fontSize: 11 }}>any</span>
                    )}
                  </td>
                  <td style={{ padding: "9px 14px" }}>
                    <div style={{ fontFamily: "var(--font-geist-mono)", fontSize: 11, color: "var(--text)" }}>
                      {rule.primary_model}
                    </div>
                    {rule.virtual_model && (
                      <div style={{ fontSize: 10, color: "var(--accent)", fontFamily: "var(--font-geist-mono)", marginTop: 2, opacity: 0.7 }}>
                        {rule.virtual_model}
                      </div>
                    )}
                  </td>
                  <td style={{ padding: "9px 14px", fontSize: 12, color: "var(--text-2)" }}>
                    {rule.provider}
                  </td>
                  <td style={{ padding: "9px 14px" }}>
                    <span
                      style={{
                        fontSize: 11,
                        color: TIER_COLORS[rule.model_tier] || "var(--text-2)",
                        fontFamily: "var(--font-geist-mono)",
                      }}
                    >
                      {TIER_LABELS[rule.model_tier] || rule.model_tier}
                    </span>
                  </td>
                  <td style={{ padding: "9px 14px", fontSize: 11, color: "var(--text-3)", maxWidth: 240 }}>
                    {rule.rationale}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default function InspectorPage() {
  const [policies, setPolicies] = useState<Record<string, Policy>>({});
  const [health, setHealth] = useState<HealthData | null>(null);
  const [reloading, setReloading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  const load = async () => {
    setLoadError(null);
    try {
      const [p, h] = await Promise.all([fetchPolicies(), fetchHealth()]);
      setPolicies(p);
      setHealth(h);
    } catch (err: unknown) {
      setLoadError(err instanceof Error ? err.message : "Failed to connect to backend");
    }
  };

  useEffect(() => { load(); }, []);

  const handleReload = async () => {
    setReloading(true);
    try {
      await reloadPolicies();
      await load();
    } finally {
      setReloading(false);
    }
  };

  return (
    <div style={{ padding: "28px 32px", maxWidth: 1100, margin: "0 auto" }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: 28 }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
            <GitBranch size={16} color="var(--accent)" strokeWidth={1.5} />
            <h1 style={{ fontSize: 18, fontWeight: 600, color: "var(--text)", letterSpacing: "-0.02em" }}>
              Routing Inspector
            </h1>
          </div>
          <p style={{ fontSize: 12, color: "var(--text-2)" }}>
            Live view of routing policies and provider health
          </p>
        </div>
        <button
          onClick={handleReload}
          disabled={reloading}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 6,
            padding: "7px 14px",
            borderRadius: 6,
            border: "1px solid var(--border-2)",
            background: "var(--bg-2)",
            color: "var(--text-2)",
            fontSize: 12,
            cursor: "pointer",
          }}
        >
          <RefreshCw size={13} strokeWidth={1.5} style={{ animation: reloading ? "spin 0.8s linear infinite" : "none" }} />
          {reloading ? "Reloading…" : "Hot Reload Policies"}
        </button>
      </div>

      {loadError && (
        <div style={{ padding: "12px 16px", borderRadius: 7, background: "var(--red-dim)", border: "1px solid var(--red)22", fontSize: 12, color: "var(--red)", marginBottom: 24, display: "flex", alignItems: "center", gap: 8 }}>
          <AlertCircle size={14} />
          {loadError} — make sure the backend is running on port 8000
        </div>
      )}

      {/* Policy Simulator */}
      <PolicySimulator />

      {/* Provider health */}
      {health && (
        <div style={{ marginBottom: 28 }}>
          <div style={{ fontSize: 11, color: "var(--text-3)", letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: 10 }}>Provider Status</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            {Object.entries(health.providers).map(([name, ok]) => (
              <div
                key={name}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 7,
                  padding: "6px 12px",
                  borderRadius: 6,
                  background: ok ? "var(--green-dim)" : "var(--red-dim)",
                  border: `1px solid ${ok ? "var(--green)" : "var(--red)"}22`,
                  fontSize: 12,
                }}
              >
                <StatusDot ok={ok} />
                <span style={{ fontFamily: "var(--font-geist-mono)", color: "var(--text)" }}>{name}</span>
                <span style={{ color: ok ? "var(--green)" : "var(--red)" }}>{ok ? "online" : "offline"}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Policies */}
      <div style={{ fontSize: 11, color: "var(--text-3)", letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: 10 }}>
        Routing Policies
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {Object.entries(policies).length === 0 && !loadError && (
          <div style={{ padding: 32, textAlign: "center", color: "var(--text-3)", fontSize: 12 }}>
            Loading policies…
          </div>
        )}
        {Object.entries(policies).map(([dept, policy]) => (
          <PolicySection key={dept} dept={dept} policy={policy} />
        ))}
      </div>

      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}
