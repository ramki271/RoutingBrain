"use client";

import { RoutingDecision } from "@/lib/api";
import { Brain, ShieldAlert } from "lucide-react";

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

const RISK_CONFIG: Record<string, { color: string; dim: string; label: string; icon: string }> = {
  low:        { color: "var(--green)",  dim: "var(--green-dim)",  label: "Low",       icon: "●" },
  medium:     { color: "var(--accent)", dim: "var(--accent-dim)", label: "Medium",    icon: "▲" },
  high:       { color: "var(--amber)",  dim: "var(--amber-dim)",  label: "High",      icon: "▲" },
  regulated:  { color: "var(--red)",    dim: "var(--red-dim)",    label: "Regulated", icon: "■" },
};

const COMPLEXITY_COLORS: Record<string, string> = {
  simple: "var(--green)",
  medium: "var(--accent)",
  complex: "var(--amber)",
};

const TASK_TYPE_LABELS: Record<string, string> = {
  code_generation: "Code Generation",
  code_review: "Code Review",
  test_generation: "Test Generation",
  debugging: "Debugging",
  architecture_design: "Architecture Design",
  documentation: "Documentation",
  requirement_analysis: "Requirement Analysis",
  question_answer: "Q&A",
  data_analysis: "Data Analysis",
  math_reasoning: "Math / Algorithms",
  general: "General",
};

interface Props {
  decision: RoutingDecision | null;
  loading: boolean;
}

function Chip({
  label,
  color,
  dim,
}: {
  label: string;
  color: string;
  dim: string;
}) {
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        padding: "2px 8px",
        borderRadius: 4,
        fontSize: 11,
        fontWeight: 500,
        color,
        background: dim,
        border: `1px solid ${color}22`,
        fontFamily: "var(--font-geist-mono)",
        letterSpacing: "0.02em",
      }}
    >
      {label}
    </span>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        padding: "8px 0",
        borderBottom: "1px solid var(--border)",
        gap: 12,
      }}
    >
      <span style={{ color: "var(--text-2)", fontSize: 12, flexShrink: 0 }}>{label}</span>
      <div style={{ textAlign: "right" }}>{children}</div>
    </div>
  );
}

function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color = value >= 0.8 ? "var(--green)" : value >= 0.6 ? "var(--accent)" : "var(--amber)";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, justifyContent: "flex-end" }}>
      <div
        style={{
          width: 80,
          height: 4,
          background: "var(--border-2)",
          borderRadius: 2,
          overflow: "hidden",
        }}
      >
        <div
          style={{
            height: "100%",
            width: `${pct}%`,
            background: color,
            borderRadius: 2,
            transition: "width 0.4s ease",
          }}
        />
      </div>
      <span
        style={{
          fontSize: 12,
          color,
          fontFamily: "var(--font-geist-mono)",
          minWidth: 32,
          textAlign: "right",
        }}
      >
        {pct}%
      </span>
    </div>
  );
}

export function RoutingPanel({ decision, loading }: Props) {
  return (
    <div
      style={{
        width: 300,
        flexShrink: 0,
        borderLeft: "1px solid var(--border)",
        background: "var(--bg-1)",
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: "16px 20px",
          borderBottom: "1px solid var(--border)",
          display: "flex",
          alignItems: "center",
          gap: 8,
        }}
      >
        <Brain size={14} color="var(--accent)" strokeWidth={1.5} />
        <span style={{ fontSize: 12, fontWeight: 500, color: "var(--text-2)", letterSpacing: "0.04em", textTransform: "uppercase" }}>
          Routing Decision
        </span>
      </div>

      <div style={{ flex: 1, overflow: "auto", padding: "0 20px 20px" }}>
        {loading && !decision && (
          <div
            style={{
              paddingTop: 32,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: 12,
              color: "var(--text-3)",
            }}
          >
            <div className="pulse-dot" />
            <span style={{ fontSize: 12 }}>Classifying request…</span>
          </div>
        )}

        {!loading && !decision && (
          <div
            style={{
              paddingTop: 48,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: 8,
              color: "var(--text-3)",
            }}
          >
            <Brain size={28} strokeWidth={1} />
            <span style={{ fontSize: 12, textAlign: "center" }}>
              Send a message to see<br />the routing decision
            </span>
          </div>
        )}

        {decision && (
          <>
            {/* Model badge */}
            <div
              style={{
                margin: "16px 0 4px",
                padding: "12px 14px",
                borderRadius: 8,
                background: "var(--bg-3)",
                border: "1px solid var(--border-2)",
              }}
            >
              <div style={{ fontSize: 11, color: "var(--text-2)", marginBottom: 4 }}>Selected Model</div>
              <div
                style={{
                  fontFamily: "var(--font-geist-mono)",
                  fontSize: 13,
                  color: "var(--text)",
                  fontWeight: 500,
                  wordBreak: "break-all",
                }}
              >
                {decision.model_selected}
              </div>
              <div style={{ fontSize: 11, color: "var(--text-2)", marginTop: 2 }}>
                via{" "}
                <span style={{ color: "var(--text)" }}>{decision.provider}</span>
              </div>
              {decision.model_tier && (
                <div style={{ marginTop: 8 }}>
                  <Chip
                    label={TIER_LABELS[decision.model_tier] || decision.model_tier}
                    color={TIER_COLORS[decision.model_tier] || "var(--text-2)"}
                    dim={`${TIER_COLORS[decision.model_tier]}1a` || "var(--bg-2)"}
                  />
                  {decision.fallback_used && (
                    <Chip
                      label="Fallback"
                      color="var(--amber)"
                      dim="var(--amber-dim)"
                    />
                  )}
                </div>
              )}
            </div>

            {/* Classification details */}
            <div style={{ marginTop: 4 }}>
              <Row label="Task Type">
                <span
                  style={{
                    fontSize: 12,
                    color: "var(--text)",
                    fontFamily: "var(--font-geist-mono)",
                  }}
                >
                  {TASK_TYPE_LABELS[decision.task_type] || decision.task_type}
                </span>
              </Row>

              <Row label="Complexity">
                <Chip
                  label={decision.complexity}
                  color={COMPLEXITY_COLORS[decision.complexity] || "var(--text-2)"}
                  dim={`${COMPLEXITY_COLORS[decision.complexity]}18` || "var(--bg-2)"}
                />
              </Row>

              <Row label="Confidence">
                <ConfidenceBar value={decision.confidence} />
              </Row>

              <Row label="Classified By">
                <span
                  style={{
                    fontSize: 11,
                    color:
                      decision.classified_by === "meta_llm"
                        ? "var(--green)"
                        : "var(--amber)",
                    fontFamily: "var(--font-geist-mono)",
                  }}
                >
                  {decision.classified_by === "meta_llm"
                    ? "RoutingBrain"
                    : "Heuristic"}
                </span>
              </Row>

              {decision.latency_ms > 0 && (
                <Row label="Routing Latency">
                  <span
                    style={{
                      fontSize: 12,
                      color: "var(--text-2)",
                      fontFamily: "var(--font-geist-mono)",
                    }}
                  >
                    {decision.latency_ms}ms
                  </span>
                </Row>
              )}

              {decision.rule_matched && (
                <Row label="Rule Matched">
                  <span style={{ fontSize: 11, color: "var(--text-2)", fontFamily: "var(--font-geist-mono)" }}>
                    {decision.rule_matched}
                  </span>
                </Row>
              )}

              <Row label="Risk Level">
                {(() => {
                  const rc = RISK_CONFIG[decision.risk_level] || RISK_CONFIG.low;
                  return (
                    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                      <ShieldAlert size={12} color={rc.color} strokeWidth={2} />
                      <span style={{ fontSize: 11, fontWeight: 600, color: rc.color, fontFamily: "var(--font-geist-mono)", letterSpacing: "0.04em" }}>
                        {rc.label.toUpperCase()}
                      </span>
                      {decision.audit_required && (
                        <span style={{ fontSize: 10, color: "var(--amber)", background: "var(--amber-dim)", border: "1px solid var(--amber)22", borderRadius: 3, padding: "1px 5px", fontFamily: "var(--font-geist-mono)" }}>
                          AUDIT
                        </span>
                      )}
                    </div>
                  );
                })()}
              </Row>
            </div>

            {/* Risk rationale — shown when risk > low */}
            {decision.risk_level && decision.risk_level !== "low" && decision.risk_rationale && (
              <div
                style={{
                  marginTop: 8,
                  padding: "9px 12px",
                  borderRadius: 6,
                  background: RISK_CONFIG[decision.risk_level]?.dim || "var(--bg-2)",
                  border: `1px solid ${RISK_CONFIG[decision.risk_level]?.color || "var(--border)"}22`,
                  fontSize: 11,
                  color: "var(--text-2)",
                  lineHeight: 1.6,
                  display: "flex",
                  gap: 8,
                  alignItems: "flex-start",
                }}
              >
                <ShieldAlert size={12} color={RISK_CONFIG[decision.risk_level]?.color} strokeWidth={2} style={{ flexShrink: 0, marginTop: 1 }} />
                <span>{decision.risk_rationale}</span>
              </div>
            )}

            {/* Routing rationale */}
            {decision.routing_rationale && (
              <div
                style={{
                  marginTop: 8,
                  padding: "10px 12px",
                  borderRadius: 6,
                  background: "var(--accent-dim)",
                  border: "1px solid var(--accent-border)",
                  fontSize: 12,
                  color: "var(--text-2)",
                  lineHeight: 1.6,
                  fontStyle: "italic",
                }}
              >
                &ldquo;{decision.routing_rationale}&rdquo;
              </div>
            )}
          </>
        )}
      </div>

      <style>{`
        .pulse-dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background: var(--accent);
          animation: pulse 1.2s ease-in-out infinite;
        }
        @keyframes pulse {
          0%, 100% { opacity: 0.3; transform: scale(0.8); }
          50% { opacity: 1; transform: scale(1.1); }
        }
      `}</style>
    </div>
  );
}
