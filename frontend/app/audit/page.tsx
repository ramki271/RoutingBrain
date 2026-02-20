"use client";

import { useState, useEffect, useCallback } from "react";
import { fetchAuditLogs, AuditEntry } from "@/lib/api";
import { ShieldCheck, RefreshCw, AlertCircle, ChevronDown, ChevronRight, ShieldAlert, Filter } from "lucide-react";

const RISK_COLORS: Record<string, string> = {
  low: "var(--green)", medium: "var(--accent)", high: "var(--amber)", regulated: "var(--red)",
};
const RISK_DIM: Record<string, string> = {
  low: "var(--green-dim)", medium: "var(--accent-dim)", high: "var(--amber-dim)", regulated: "var(--red-dim)",
};
const TIER_COLORS: Record<string, string> = {
  fast_cheap: "var(--green)", balanced: "var(--accent)", powerful: "var(--amber)", local: "var(--text-2)",
};

function Badge({ label, color, dim }: { label: string; color: string; dim: string }) {
  return (
    <span style={{
      fontSize: 10, padding: "1px 7px", borderRadius: 3, fontFamily: "var(--font-geist-mono)",
      fontWeight: 600, color, background: dim, border: `1px solid ${color}22`,
    }}>
      {label}
    </span>
  );
}

function EntryRow({ entry }: { entry: AuditEntry }) {
  const [expanded, setExpanded] = useState(false);
  const ts = new Date(entry.timestamp);
  const timeStr = ts.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  const dateStr = ts.toLocaleDateString([], { month: "short", day: "numeric" });
  const riskColor = RISK_COLORS[entry.risk_level] || "var(--text-2)";
  const riskDim = RISK_DIM[entry.risk_level] || "var(--bg-2)";

  return (
    <div style={{ borderBottom: "1px solid var(--border)" }}>
      {/* Main row */}
      <div
        onClick={() => setExpanded(!expanded)}
        style={{
          display: "grid",
          gridTemplateColumns: "16px 120px 80px 180px 80px 80px 80px 80px 1fr",
          gap: 12,
          alignItems: "center",
          padding: "10px 16px",
          cursor: "pointer",
          transition: "background 0.1s",
        }}
        onMouseEnter={e => (e.currentTarget.style.background = "var(--bg-2)")}
        onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
      >
        <span style={{ color: "var(--text-3)" }}>
          {expanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
        </span>

        {/* Timestamp */}
        <div>
          <div style={{ fontSize: 11, color: "var(--text)", fontFamily: "var(--font-geist-mono)" }}>{timeStr}</div>
          <div style={{ fontSize: 10, color: "var(--text-3)" }}>{dateStr}</div>
        </div>

        {/* Dept */}
        <span style={{ fontSize: 11, color: "var(--text-2)", fontFamily: "var(--font-geist-mono)", textTransform: "uppercase" }}>
          {entry.department}
        </span>

        {/* Model */}
        <div>
          <div style={{ fontSize: 11, color: "var(--text)", fontFamily: "var(--font-geist-mono)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {entry.model_selected}
          </div>
          <div style={{ fontSize: 10, color: "var(--text-3)" }}>{entry.provider}</div>
        </div>

        {/* Task type */}
        <span style={{ fontSize: 11, color: "var(--text-2)" }}>
          {entry.classification_snapshot?.task_type?.replace(/_/g, " ") || "—"}
        </span>

        {/* Risk */}
        <Badge label={entry.risk_level} color={riskColor} dim={riskDim} />

        {/* Tier */}
        <span style={{ fontSize: 11, color: TIER_COLORS[entry.model_tier] || "var(--text-2)", fontFamily: "var(--font-geist-mono)" }}>
          {entry.model_tier?.replace("_", " ")}
        </span>

        {/* Latency */}
        <span style={{ fontSize: 11, color: "var(--text-2)", fontFamily: "var(--font-geist-mono)" }}>
          {entry.latency_ms}ms
        </span>

        {/* Flags */}
        <div style={{ display: "flex", gap: 5, flexWrap: "wrap" }}>
          {entry.audit_required && <Badge label="AUDIT" color="var(--amber)" dim="var(--amber-dim)" />}
          {entry.fallback_used && <Badge label="FALLBACK" color="var(--red)" dim="var(--red-dim)" />}
          {entry.constraints_applied?.map((c, i) => (
            <Badge key={i} label={c.replace(/_/g, " ")} color="var(--accent)" dim="var(--accent-dim)" />
          ))}
          {entry.error && <Badge label="ERROR" color="var(--red)" dim="var(--red-dim)" />}
        </div>
      </div>

      {/* Expanded detail */}
      {expanded && (
        <div style={{ padding: "0 16px 16px 44px", display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12 }}>
          {/* Identity + policy */}
          <div style={{ padding: 12, borderRadius: 6, background: "var(--bg-2)", border: "1px solid var(--border)" }}>
            <div style={{ fontSize: 10, color: "var(--text-3)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 8 }}>Identity & Policy</div>
            <Row label="Request ID" value={entry.request_id} mono />
            <Row label="Tenant" value={entry.tenant_id} mono />
            <Row label="User" value={entry.user_id} mono />
            <Row label="Policy Version" value={entry.policy_version} mono />
            <Row label="Rule Matched" value={entry.rule_matched} mono />
          </div>

          {/* Classification snapshot */}
          <div style={{ padding: 12, borderRadius: 6, background: "var(--bg-2)", border: "1px solid var(--border)" }}>
            <div style={{ fontSize: 10, color: "var(--text-3)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 8 }}>Classification Snapshot</div>
            {entry.classification_snapshot ? (
              <>
                <Row label="Task Type" value={entry.classification_snapshot.task_type} />
                <Row label="Complexity" value={entry.classification_snapshot.complexity} />
                <Row label="Confidence" value={`${Math.round(entry.classification_snapshot.confidence * 100)}%`} />
                <Row label="Classified By" value={entry.classification_snapshot.classified_by === "meta_llm" ? "RoutingBrain" : "Heuristic"} />
                {entry.classification_snapshot.risk_signals?.length > 0 && (
                  <Row label="Risk Signals" value={entry.classification_snapshot.risk_signals.join(", ")} />
                )}
              </>
            ) : <span style={{ fontSize: 11, color: "var(--text-3)" }}>No snapshot</span>}
          </div>

          {/* Risk + data residency */}
          <div style={{ padding: 12, borderRadius: 6, background: "var(--bg-2)", border: "1px solid var(--border)" }}>
            <div style={{ fontSize: 10, color: "var(--text-3)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 8 }}>Risk & Governance</div>
            <Row label="Risk Level" value={entry.risk_level} valueColor={riskColor} />
            {entry.risk_rationale && <Row label="Rationale" value={entry.risk_rationale} />}
            {entry.data_residency_note && (
              <div style={{ marginTop: 6, fontSize: 11, color: "var(--amber)", lineHeight: 1.5 }}>
                {entry.data_residency_note}
              </div>
            )}
            <Row label="Cost (est.)" value={entry.estimated_cost_usd > 0 ? `$${entry.estimated_cost_usd.toFixed(5)}` : "—"} mono />
            <Row label="Tokens" value={`${entry.prompt_tokens} in / ${entry.completion_tokens} out`} mono />
          </div>
        </div>
      )}
    </div>
  );
}

function Row({ label, value, mono, valueColor }: { label: string; value: string; mono?: boolean; valueColor?: string }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", gap: 8, marginBottom: 4 }}>
      <span style={{ fontSize: 11, color: "var(--text-3)", flexShrink: 0 }}>{label}</span>
      <span style={{
        fontSize: 11,
        color: valueColor || "var(--text)",
        fontFamily: mono ? "var(--font-geist-mono)" : "inherit",
        textAlign: "right",
        wordBreak: "break-all",
      }}>
        {value}
      </span>
    </div>
  );
}

const COL_HEADERS = ["", "Timestamp", "Dept", "Model", "Task", "Risk", "Tier", "Latency", "Flags"];

export default function AuditPage() {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filterRisk, setFilterRisk] = useState("");
  const [filterDept, setFilterDept] = useState("");
  const [filterAuditOnly, setFilterAuditOnly] = useState(false);
  const [limit, setLimit] = useState(50);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchAuditLogs({
        limit,
        risk_level: filterRisk || undefined,
        department: filterDept || undefined,
        audit_required: filterAuditOnly ? true : undefined,
      });
      setEntries(res.entries);
      setTotal(res.total);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load audit logs");
    } finally {
      setLoading(false);
    }
  }, [limit, filterRisk, filterDept, filterAuditOnly]);

  useEffect(() => { load(); }, [load]);

  const selectStyle = {
    background: "var(--bg-3)", border: "1px solid var(--border-2)", borderRadius: 5,
    color: "var(--text)", fontSize: 12, padding: "4px 10px", cursor: "pointer", fontFamily: "inherit",
  };

  const auditOnlyCount = entries.filter(e => e.audit_required).length;

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", overflow: "hidden" }}>
      {/* Header */}
      <div style={{ padding: "20px 28px 16px", borderBottom: "1px solid var(--border)", background: "var(--bg-1)", flexShrink: 0 }}>
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between" }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4 }}>
              <ShieldCheck size={16} color="var(--accent)" strokeWidth={1.5} />
              <h1 style={{ fontSize: 18, fontWeight: 600, color: "var(--text)", letterSpacing: "-0.02em" }}>Audit Log</h1>
            </div>
            <p style={{ fontSize: 12, color: "var(--text-2)" }}>
              Immutable record of every routing decision · {total} total entries
              {auditOnlyCount > 0 && (
                <span style={{ marginLeft: 8, color: "var(--amber)", fontWeight: 500 }}>
                  {auditOnlyCount} requiring audit
                </span>
              )}
            </p>
          </div>
          <button
            onClick={load}
            disabled={loading}
            style={{ display: "flex", alignItems: "center", gap: 6, padding: "7px 14px", borderRadius: 6, border: "1px solid var(--border-2)", background: "var(--bg-2)", color: "var(--text-2)", fontSize: 12, cursor: "pointer" }}
          >
            <RefreshCw size={13} strokeWidth={1.5} style={{ animation: loading ? "spin 0.8s linear infinite" : "none" }} />
            Refresh
          </button>
        </div>

        {/* Filters */}
        <div style={{ display: "flex", gap: 10, marginTop: 14, alignItems: "center", flexWrap: "wrap" }}>
          <Filter size={13} color="var(--text-3)" />
          <select value={filterRisk} onChange={e => setFilterRisk(e.target.value)} style={selectStyle}>
            <option value="">All Risk Levels</option>
            {["low", "medium", "high", "regulated"].map(r => <option key={r} value={r}>{r}</option>)}
          </select>
          <select value={filterDept} onChange={e => setFilterDept(e.target.value)} style={selectStyle}>
            <option value="">All Departments</option>
            {["rd", "sales", "marketing", "hr", "finance", "general"].map(d => <option key={d} value={d}>{d.toUpperCase()}</option>)}
          </select>
          <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "var(--text-2)", cursor: "pointer" }}>
            <input
              type="checkbox"
              checked={filterAuditOnly}
              onChange={e => setFilterAuditOnly(e.target.checked)}
              style={{ accentColor: "var(--amber)" }}
            />
            Audit required only
          </label>
          <select value={limit} onChange={e => setLimit(Number(e.target.value))} style={{ ...selectStyle, marginLeft: "auto" }}>
            {[25, 50, 100, 200].map(n => <option key={n} value={n}>Last {n}</option>)}
          </select>
        </div>
      </div>

      {error && (
        <div style={{ padding: "10px 28px", background: "var(--red-dim)", borderBottom: "1px solid var(--border)", fontSize: 12, color: "var(--red)", display: "flex", alignItems: "center", gap: 8 }}>
          <AlertCircle size={13} />
          {error} — make sure the backend is running
        </div>
      )}

      {/* Column headers */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "16px 120px 80px 180px 80px 80px 80px 80px 1fr",
        gap: 12,
        padding: "6px 16px",
        borderBottom: "1px solid var(--border)",
        background: "var(--bg-1)",
        flexShrink: 0,
      }}>
        {COL_HEADERS.map((h, i) => (
          <span key={i} style={{ fontSize: 10, color: "var(--text-3)", textTransform: "uppercase", letterSpacing: "0.05em", fontWeight: 500 }}>{h}</span>
        ))}
      </div>

      {/* Entries */}
      <div style={{ flex: 1, overflow: "auto" }}>
        {entries.length === 0 && !loading && !error && (
          <div style={{ padding: 48, textAlign: "center", color: "var(--text-3)", fontSize: 13 }}>
            <ShieldCheck size={32} strokeWidth={1} style={{ margin: "0 auto 12px", display: "block" }} />
            No audit records yet — send a message from the Playground to generate entries.
          </div>
        )}
        {entries.map(entry => <EntryRow key={entry.request_id} entry={entry} />)}
      </div>

      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}
