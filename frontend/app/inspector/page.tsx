"use client";

import { useState, useEffect } from "react";
import { fetchPolicies, fetchHealth, reloadPolicies } from "@/lib/api";
import { GitBranch, RefreshCw, CheckCircle, XCircle, AlertCircle, ChevronDown, ChevronRight } from "lucide-react";

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
                  <td style={{ padding: "9px 14px", fontFamily: "var(--font-geist-mono)", fontSize: 11, color: "var(--text)" }}>
                    {rule.primary_model}
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
