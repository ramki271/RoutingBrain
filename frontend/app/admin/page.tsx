"use client";

import { useState } from "react";
import { Activity, KeyRound, ShieldCheck } from "lucide-react";
import { fetchAuthContext, fetchHealth, getSavedApiKey, setSavedApiKey } from "@/lib/api";

type HealthResponse = {
  status: string;
  providers?: Record<string, boolean>;
  redis?: boolean;
  database?: boolean;
};

export default function AdminPage() {
  const [apiKey, setApiKey] = useState(getSavedApiKey());
  const [tenantId, setTenantId] = useState("acme");
  const [userId, setUserId] = useState("user-1");
  const [department, setDepartment] = useState("rd");
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [authContext, setAuthContext] = useState<unknown>(null);
  const [error, setError] = useState("");

  const inputStyle: React.CSSProperties = {
    background: "var(--bg-3)",
    border: "1px solid var(--border-2)",
    borderRadius: 6,
    color: "var(--text)",
    fontSize: 12,
    padding: "7px 10px",
    width: "100%",
  };

  const runHealth = async () => {
    setError("");
    try {
      setHealth(await fetchHealth());
    } catch (e: unknown) {
      const err = e as Error;
      setError(err.message || "Health check failed");
    }
  };

  const runAuthContext = async () => {
    setError("");
    try {
      const ctx = await fetchAuthContext({
        api_key: apiKey,
        tenant_id: tenantId,
        user_id: userId,
        department,
      });
      setAuthContext(ctx);
    } catch (e: unknown) {
      const err = e as Error;
      setError(err.message || "Auth context failed");
    }
  };

  return (
    <div style={{ maxWidth: 980, margin: "0 auto", padding: "24px 28px" }}>
      <h1 style={{ fontSize: 18, margin: 0, display: "flex", alignItems: "center", gap: 8 }}>
        <ShieldCheck size={16} color="var(--accent)" />
        Admin Validation
      </h1>
      <div style={{ fontSize: 12, color: "var(--text-2)", marginTop: 6, marginBottom: 16 }}>
        Validate DB-backed API key auth and backend readiness from UI.
      </div>

      <div style={cardStyle}>
        <div style={cardHeaderStyle}>
          <KeyRound size={14} />
          API Key
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr auto", gap: 8 }}>
          <input
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder="API key"
            style={{ ...inputStyle, fontFamily: "var(--font-geist-mono)" }}
          />
          <button onClick={() => setSavedApiKey(apiKey)} style={btnStyle("var(--accent)")}>
            Save Key
          </button>
        </div>
      </div>

      <div style={{ ...cardStyle, marginTop: 12 }}>
        <div style={cardHeaderStyle}>
          <Activity size={14} />
          Backend Readiness
        </div>
        <button onClick={runHealth} style={btnStyle("var(--green)")}>Check /health</button>
        <pre style={preStyle}>{health ? JSON.stringify(health, null, 2) : "No health check run yet."}</pre>
      </div>

      <div style={{ ...cardStyle, marginTop: 12 }}>
        <div style={cardHeaderStyle}>
          <ShieldCheck size={14} />
          Auth Context (DB Key Test)
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 8, marginBottom: 8 }}>
          <input value={tenantId} onChange={(e) => setTenantId(e.target.value)} placeholder="tenant" style={inputStyle} />
          <input value={userId} onChange={(e) => setUserId(e.target.value)} placeholder="user" style={inputStyle} />
          <input value={department} onChange={(e) => setDepartment(e.target.value)} placeholder="department" style={inputStyle} />
        </div>
        <button onClick={runAuthContext} style={btnStyle("var(--amber)")}>Check /internal/auth/context</button>
        <pre style={preStyle}>{authContext ? JSON.stringify(authContext, null, 2) : "No auth context check run yet."}</pre>
      </div>

      {error && <div style={{ color: "var(--red)", fontSize: 12, marginTop: 10 }}>{error}</div>}
    </div>
  );
}

const cardStyle: React.CSSProperties = {
  border: "1px solid var(--border)",
  borderRadius: 8,
  background: "var(--bg-1)",
  padding: 12,
};

const cardHeaderStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: 6,
  fontSize: 12,
  color: "var(--text-2)",
  marginBottom: 8,
};

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
    marginBottom: 8,
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
  maxHeight: 260,
  overflow: "auto",
  whiteSpace: "pre-wrap",
  wordBreak: "break-word",
};
