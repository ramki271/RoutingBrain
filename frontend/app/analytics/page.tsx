"use client";

import { BarChart2, TrendingDown, Zap, DollarSign, Activity } from "lucide-react";

// Static data based on savings.md — will be replaced with live API data in Phase 3
const ROUTING_DISTRIBUTION = [
  { tier: "Fast / Cheap", pct: 40, color: "var(--green)", models: "Haiku · GPT-4o-mini · Gemini Flash", cost: "$0.50/MTok" },
  { tier: "Balanced", pct: 45, color: "var(--accent)", models: "Sonnet · GPT-4o · Gemini Pro", cost: "$3.00/MTok" },
  { tier: "Powerful", pct: 15, color: "var(--amber)", models: "Opus · o1", cost: "$20.00/MTok" },
];

const TASK_BREAKDOWN = [
  { type: "Code Generation", pct: 28, color: "var(--accent)" },
  { type: "Code Review", pct: 18, color: "var(--green)" },
  { type: "Test Generation", pct: 14, color: "var(--blue)" },
  { type: "Debugging", pct: 16, color: "var(--amber)" },
  { type: "Architecture", pct: 8, color: "var(--red)" },
  { type: "Documentation", pct: 7, color: "var(--text-2)" },
  { type: "Q&A", pct: 9, color: "var(--text-3)" },
];

const SAVINGS_SCENARIOS = [
  {
    label: "Scenario A",
    subtitle: "Commercial only",
    savings_pct: "11–14%",
    annual_5k: "$65,000",
    annual_50k: "$178,100",
    color: "var(--accent)",
  },
  {
    label: "Scenario B",
    subtitle: "Commercial + OSS",
    savings_pct: "44–50%",
    annual_5k: "$225,800",
    annual_50k: "$618,700",
    color: "var(--green)",
    recommended: true,
  },
  {
    label: "Scenario C",
    subtitle: "OSS-first",
    savings_pct: "57–61%",
    annual_5k: "$274,500",
    annual_50k: "$752,300",
    color: "var(--amber)",
  },
];

function StatCard({ label, value, sub, icon: Icon, color }: { label: string; value: string; sub?: string; icon: React.ElementType; color: string }) {
  return (
    <div
      style={{
        padding: "18px 20px",
        borderRadius: 8,
        border: "1px solid var(--border)",
        background: "var(--bg-1)",
        display: "flex",
        flexDirection: "column",
        gap: 10,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <span style={{ fontSize: 12, color: "var(--text-2)" }}>{label}</span>
        <Icon size={14} color={color} strokeWidth={1.5} />
      </div>
      <div style={{ fontSize: 24, fontWeight: 600, color: "var(--text)", letterSpacing: "-0.03em", fontFamily: "var(--font-geist-mono)" }}>
        {value}
      </div>
      {sub && <div style={{ fontSize: 11, color: "var(--text-3)" }}>{sub}</div>}
    </div>
  );
}

function BarRow({ label, pct, color, sub }: { label: string; pct: number; color: string; sub?: string }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={{ fontSize: 12, color: "var(--text)" }}>{label}</span>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          {sub && <span style={{ fontSize: 11, color: "var(--text-3)", fontFamily: "var(--font-geist-mono)" }}>{sub}</span>}
          <span style={{ fontSize: 12, fontFamily: "var(--font-geist-mono)", color: "var(--text-2)", minWidth: 32, textAlign: "right" }}>{pct}%</span>
        </div>
      </div>
      <div style={{ height: 5, background: "var(--border-2)", borderRadius: 3, overflow: "hidden" }}>
        <div style={{ height: "100%", width: `${pct}%`, background: color, borderRadius: 3, transition: "width 0.6s ease" }} />
      </div>
    </div>
  );
}

function SavingsCard({ scenario }: { scenario: typeof SAVINGS_SCENARIOS[0] }) {
  return (
    <div
      style={{
        padding: "18px 20px",
        borderRadius: 8,
        border: `1px solid ${scenario.recommended ? scenario.color + "44" : "var(--border)"}`,
        background: scenario.recommended ? `${scenario.color}08` : "var(--bg-1)",
        position: "relative",
        flex: 1,
      }}
    >
      {scenario.recommended && (
        <div
          style={{
            position: "absolute",
            top: -10,
            left: 16,
            fontSize: 10,
            fontWeight: 600,
            color: scenario.color,
            background: "var(--bg)",
            padding: "2px 8px",
            borderRadius: 4,
            border: `1px solid ${scenario.color}44`,
            letterSpacing: "0.06em",
            textTransform: "uppercase",
          }}
        >
          Recommended
        </div>
      )}
      <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text)", marginBottom: 4 }}>{scenario.label}</div>
      <div style={{ fontSize: 11, color: "var(--text-2)", marginBottom: 16 }}>{scenario.subtitle}</div>
      <div style={{ fontSize: 26, fontWeight: 700, color: scenario.color, fontFamily: "var(--font-geist-mono)", letterSpacing: "-0.03em", marginBottom: 4 }}>
        {scenario.savings_pct}
      </div>
      <div style={{ fontSize: 11, color: "var(--text-3)", marginBottom: 16 }}>cost savings vs always-Sonnet</div>
      <div style={{ display: "flex", flexDirection: "column", gap: 6, paddingTop: 12, borderTop: "1px solid var(--border)" }}>
        <div style={{ display: "flex", justifyContent: "space-between" }}>
          <span style={{ fontSize: 11, color: "var(--text-2)" }}>5K–50K calls/day</span>
          <span style={{ fontSize: 12, fontFamily: "var(--font-geist-mono)", color: "var(--text)" }}>{scenario.annual_5k}/yr</span>
        </div>
        <div style={{ display: "flex", justifyContent: "space-between" }}>
          <span style={{ fontSize: 11, color: "var(--text-2)" }}>&gt;50K calls/day</span>
          <span style={{ fontSize: 12, fontFamily: "var(--font-geist-mono)", color: "var(--text)" }}>{scenario.annual_50k}/yr</span>
        </div>
      </div>
    </div>
  );
}

export default function AnalyticsPage() {
  return (
    <div style={{ padding: "28px 32px", maxWidth: 1000, margin: "0 auto" }}>
      {/* Header */}
      <div style={{ marginBottom: 28 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
          <BarChart2 size={16} color="var(--accent)" strokeWidth={1.5} />
          <h1 style={{ fontSize: 18, fontWeight: 600, color: "var(--text)", letterSpacing: "-0.02em" }}>Analytics</h1>
        </div>
        <p style={{ fontSize: 12, color: "var(--text-2)" }}>
          Routing distribution, cost projections, and savings estimates.{" "}
          <span style={{ color: "var(--text-3)" }}>Live metrics available in Phase 3 (PostgreSQL + Prometheus).</span>
        </p>
      </div>

      {/* Stat cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginBottom: 28 }}>
        <StatCard label="RoutingBrain Overhead" value="~$0.001" sub="per request (Haiku classification)" icon={Zap} color="var(--green)" />
        <StatCard label="Routing Latency" value="<3s" sub="classifier timeout threshold" icon={Activity} color="var(--accent)" />
        <StatCard label="Baseline (all Sonnet)" value="$3.00" sub="per MTok input" icon={DollarSign} color="var(--text-2)" />
        <StatCard label="Max Savings (OSS-first)" value="57–61%" sub="large requests at scale" icon={TrendingDown} color="var(--amber)" />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, marginBottom: 28 }}>
        {/* Tier distribution */}
        <div style={{ padding: "20px", borderRadius: 8, border: "1px solid var(--border)", background: "var(--bg-1)" }}>
          <div style={{ fontSize: 12, fontWeight: 500, color: "var(--text)", marginBottom: 4 }}>Routing Tier Distribution</div>
          <div style={{ fontSize: 11, color: "var(--text-3)", marginBottom: 20 }}>Expected split for a typical R&D team</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            {ROUTING_DISTRIBUTION.map((tier) => (
              <BarRow key={tier.tier} label={tier.tier} pct={tier.pct} color={tier.color} sub={tier.cost} />
            ))}
          </div>
        </div>

        {/* Task type breakdown */}
        <div style={{ padding: "20px", borderRadius: 8, border: "1px solid var(--border)", background: "var(--bg-1)" }}>
          <div style={{ fontSize: 12, fontWeight: 500, color: "var(--text)", marginBottom: 4 }}>Task Type Breakdown</div>
          <div style={{ fontSize: 11, color: "var(--text-3)", marginBottom: 20 }}>R&D department request classification</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {TASK_BREAKDOWN.map((t) => (
              <BarRow key={t.type} label={t.type} pct={t.pct} color={t.color} />
            ))}
          </div>
        </div>
      </div>

      {/* Savings scenarios */}
      <div style={{ marginBottom: 8 }}>
        <div style={{ fontSize: 11, color: "var(--text-3)", letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: 14 }}>
          Cost Savings Scenarios (from savings.md)
        </div>
        <div style={{ display: "flex", gap: 14 }}>
          {SAVINGS_SCENARIOS.map((s) => <SavingsCard key={s.label} scenario={s} />)}
        </div>
      </div>

      {/* Strategy timeline */}
      <div style={{ marginTop: 28, padding: "20px", borderRadius: 8, border: "1px solid var(--border)", background: "var(--bg-1)" }}>
        <div style={{ fontSize: 12, fontWeight: 500, color: "var(--text)", marginBottom: 16 }}>Recommended Rollout Strategy</div>
        <div style={{ display: "flex", gap: 0 }}>
          {[
            { month: "Month 1", label: "Commercial Router", desc: "Deploy Scenario A. Route across Haiku / Sonnet / Opus based on R&D policy.", savings: "11–14%" },
            { month: "Month 2–3", label: "Add OSS Models", desc: "Self-host Llama 3.1 70B + CodeLlama 34B. Route simple tasks to local OSS.", savings: "44–50%" },
            { month: "Month 4+", label: "Expand Departments", desc: "Add Sales, Marketing, HR YAML policies. Tune OSS for medium complexity.", savings: "57–61%" },
          ].map((step, i) => (
            <div key={i} style={{ flex: 1, position: "relative", paddingLeft: i === 0 ? 0 : 24 }}>
              {i > 0 && (
                <div style={{ position: "absolute", left: 0, top: 8, width: 24, height: 1, background: "var(--border-2)" }} />
              )}
              <div style={{ fontSize: 10, color: "var(--text-3)", letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: 4 }}>{step.month}</div>
              <div style={{ fontSize: 12, fontWeight: 600, color: "var(--text)", marginBottom: 4 }}>{step.label}</div>
              <div style={{ fontSize: 11, color: "var(--text-2)", lineHeight: 1.6, marginBottom: 8 }}>{step.desc}</div>
              <div style={{ fontSize: 11, color: "var(--green)", fontFamily: "var(--font-geist-mono)" }}>{step.savings} savings</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
