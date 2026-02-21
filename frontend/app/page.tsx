"use client";

import { isValidElement, ReactNode, useState, useRef, useEffect } from "react";
import { sendMessage, RoutingDecision, ChatMessage } from "@/lib/api";
import { RoutingPanel } from "@/components/routing-panel";
import { Send, Square, RotateCcw, ChevronDown } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import "highlight.js/styles/github-dark.css";

const DEPARTMENTS = ["rd", "sales", "marketing", "hr", "finance", "general"];

interface Template {
  label: string;
  prompt: string;
  expectedTask: string;
  expectedComplexity: "simple" | "medium" | "complex";
  expectedTier: string;
  expectedRisk?: "low" | "medium" | "high" | "regulated";
}

const RISK_COLORS: Record<string, string> = {
  low: "var(--green)",
  medium: "var(--accent)",
  high: "var(--amber)",
  regulated: "var(--red)",
};

const RISK_DIM: Record<string, string> = {
  low: "var(--green-dim)",
  medium: "var(--accent-dim)",
  high: "var(--amber-dim)",
  regulated: "var(--red-dim)",
};

const TEMPLATES: { group: string; icon?: string; items: Template[] }[] = [
  {
    group: "Risk Classification",
    icon: "shield",
    items: [
      {
        label: "No Risk — public code",
        prompt: "Write a Python function to reverse a linked list",
        expectedTask: "code_generation", expectedComplexity: "simple", expectedTier: "fast_cheap",
        expectedRisk: "low",
      },
      {
        label: "Medium — business data",
        prompt: "Analyze our customer churn metrics and forecast Q3 revenue based on the current pipeline",
        expectedTask: "data_analysis", expectedComplexity: "medium", expectedTier: "fast_cheap",
        expectedRisk: "medium",
      },
      {
        label: "High — legal contract",
        prompt: "Review this NDA and indemnification clause. We need to assess our liability exposure before signing with the partner.",
        expectedTask: "requirement_analysis", expectedComplexity: "medium", expectedTier: "balanced",
        expectedRisk: "high",
      },
      {
        label: "High — executive + M&A",
        prompt: "Draft a confidential memo to the board of directors outlining the acquisition valuation and term sheet for the merger",
        expectedTask: "documentation", expectedComplexity: "complex", expectedTier: "powerful",
        expectedRisk: "high",
      },
      {
        label: "Regulated — PHI / HIPAA",
        prompt: "This patient has a medical record showing diagnosis of type 2 diabetes. Summarize the treatment plan and prescription history for the care team",
        expectedTask: "documentation", expectedComplexity: "medium", expectedTier: "balanced",
        expectedRisk: "regulated",
      },
      {
        label: "Regulated — PII / GDPR",
        prompt: "We have a GDPR data subject access request. Extract all PII and personal data records for user ID 12345 including email address, date of birth, and SSN",
        expectedTask: "data_analysis", expectedComplexity: "medium", expectedTier: "balanced",
        expectedRisk: "regulated",
      },
      {
        label: "Regulated — financial compliance",
        prompt: "Prepare the SOX compliance report and PCI-DSS audit documentation for Q4. Include all audited financial controls and regulatory filings",
        expectedTask: "documentation", expectedComplexity: "complex", expectedTier: "powerful",
        expectedRisk: "regulated",
      },
    ],
  },
  {
    group: "Code Generation",
    items: [
      { label: "Hello World", prompt: "Write a Python hello world script", expectedTask: "code_generation", expectedComplexity: "simple", expectedTier: "fast_cheap" },
      { label: "REST Endpoint", prompt: "Write a FastAPI endpoint that accepts a user registration form with email, password, and username, validates input, hashes the password with bcrypt, and saves to a PostgreSQL database using SQLAlchemy async", expectedTask: "code_generation", expectedComplexity: "medium", expectedTier: "balanced" },
      { label: "Distributed Rate Limiter", prompt: "Design and implement a distributed rate limiter in Go that uses Redis sliding window algorithm, supports per-user and per-IP limits, handles Redis failures gracefully with local fallback, and can handle 100k requests per second across 10 nodes", expectedTask: "code_generation", expectedComplexity: "complex", expectedTier: "powerful" },
    ],
  },
  {
    group: "Code Review",
    items: [
      { label: "Style Review", prompt: "Review this Python function for style issues:\ndef calc(x,y,z):\n  return x+y*z", expectedTask: "code_review", expectedComplexity: "simple", expectedTier: "fast_cheap" },
      { label: "Security Review", prompt: "Review this authentication middleware for security vulnerabilities. It handles JWT tokens, checks expiry, and sets user context. Look for issues with token validation, timing attacks, and privilege escalation.", expectedTask: "code_review", expectedComplexity: "medium", expectedTier: "balanced" },
      { label: "Architecture Review", prompt: "Perform a comprehensive review of our microservices architecture. We have 15 services communicating via REST and Kafka. Review for coupling issues, data consistency patterns, failure cascades, observability gaps, and scalability bottlenecks.", expectedTask: "code_review", expectedComplexity: "complex", expectedTier: "powerful" },
    ],
  },
  {
    group: "Test Generation",
    items: [
      { label: "Unit Test Scaffold", prompt: "Generate a pytest test file scaffold for a simple add(a, b) function", expectedTask: "test_generation", expectedComplexity: "simple", expectedTier: "fast_cheap" },
      { label: "API Tests", prompt: "Write comprehensive pytest tests for a FastAPI user authentication endpoint. Cover happy path, invalid credentials, expired tokens, rate limiting, and concurrent login scenarios.", expectedTask: "test_generation", expectedComplexity: "medium", expectedTier: "balanced" },
      { label: "E2E Playwright Suite", prompt: "Write a full Playwright end-to-end test suite for a multi-step checkout flow: product search, add to cart, apply coupon, fill shipping address, payment with Stripe, order confirmation, and email verification. Include error states and mobile viewport tests.", expectedTask: "test_generation", expectedComplexity: "complex", expectedTier: "powerful" },
    ],
  },
  {
    group: "Debugging",
    items: [
      { label: "Fix TypeError", prompt: "Fix this error: TypeError: cannot read properties of undefined reading 'map' in my React component", expectedTask: "debugging", expectedComplexity: "simple", expectedTier: "fast_cheap" },
      { label: "Memory Leak", prompt: "My Node.js API server memory grows by ~50MB per hour under normal load and eventually crashes. I'm using Express, Mongoose, and Redis. How do I diagnose and fix the memory leak?", expectedTask: "debugging", expectedComplexity: "medium", expectedTier: "balanced" },
      { label: "Race Condition", prompt: "We have a race condition in our distributed payment system. Sometimes customers are double-charged when two requests hit simultaneously. We use PostgreSQL with optimistic locking and Redis for idempotency keys. The issue only happens under high load (>500 rps). Walk through a systematic debugging approach.", expectedTask: "debugging", expectedComplexity: "complex", expectedTier: "powerful" },
    ],
  },
  {
    group: "Architecture Design",
    items: [
      { label: "Simple API Design", prompt: "Design a simple REST API for a todo list app with users, lists, and tasks", expectedTask: "architecture_design", expectedComplexity: "simple", expectedTier: "balanced" },
      { label: "Event-Driven System", prompt: "Design an event-driven order processing system for an e-commerce platform. It must handle order placement, inventory reservation, payment processing, and fulfillment with exactly-once delivery guarantees.", expectedTask: "architecture_design", expectedComplexity: "complex", expectedTier: "powerful" },
    ],
  },
  {
    group: "Documentation",
    items: [
      { label: "Docstring", prompt: "Write a docstring for this function: def calculate_discount(price, user_tier, coupon_code):", expectedTask: "documentation", expectedComplexity: "simple", expectedTier: "fast_cheap" },
      { label: "API Reference", prompt: "Write comprehensive API documentation for our authentication service. Include all endpoints, request/response schemas, error codes, rate limits, authentication flow, and code examples in Python, JavaScript, and curl.", expectedTask: "documentation", expectedComplexity: "medium", expectedTier: "balanced" },
    ],
  },
  {
    group: "Requirement Analysis",
    items: [
      { label: "Gap Analysis", prompt: "Evaluate these requirements for a login feature: 'Users should be able to log in with email and password'. Identify what's missing.", expectedTask: "requirement_analysis", expectedComplexity: "simple", expectedTier: "balanced" },
      { label: "Full PRD Review", prompt: "Evaluate this PRD for a real-time collaborative document editor. Identify ambiguities, missing edge cases, conflicting requirements, technical feasibility issues, and unstated assumptions. The system needs to support 10,000 concurrent editors on a single document with offline support and conflict resolution.", expectedTask: "requirement_analysis", expectedComplexity: "complex", expectedTier: "powerful" },
    ],
  },
  {
    group: "Q&A",
    items: [
      { label: "Quick Concept", prompt: "What is a Python decorator?", expectedTask: "question_answer", expectedComplexity: "simple", expectedTier: "fast_cheap" },
      { label: "Technical Deep Dive", prompt: "Explain how PostgreSQL MVCC (Multi-Version Concurrency Control) works, how it handles transaction isolation levels, and when you'd see phantom reads versus non-repeatable reads", expectedTask: "question_answer", expectedComplexity: "medium", expectedTier: "balanced" },
    ],
  },
  {
    group: "Math / Algorithms",
    items: [
      { label: "Algorithm Analysis", prompt: "What is the time and space complexity of merge sort?", expectedTask: "math_reasoning", expectedComplexity: "simple", expectedTier: "fast_cheap" },
      { label: "Hard Algorithm", prompt: "Design an optimal algorithm for the traveling salesman problem on a graph of 1000 cities with real-world road distances. Compare exact vs approximation approaches, prove the approximation ratio of the Christofides algorithm, and recommend a practical implementation strategy.", expectedTask: "math_reasoning", expectedComplexity: "complex", expectedTier: "powerful" },
    ],
  },
];

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  routing?: RoutingDecision;
  streaming?: boolean;
  error?: boolean;
  governanceBlocked?: boolean;
}

type RoutingApiError = Error & {
  governance_blocked?: boolean;
};

function complexityColor(c: string) {
  if (c === "simple") return "var(--green)";
  if (c === "complex") return "var(--amber)";
  return "var(--accent)";
}

function flattenText(node: ReactNode): string {
  if (typeof node === "string" || typeof node === "number") return String(node);
  if (Array.isArray(node)) return node.map(flattenText).join("");
  if (isValidElement(node)) return flattenText(node.props.children);
  return "";
}

function MarkdownCode({
  className,
  children,
  ...props
}: React.ComponentPropsWithoutRef<"code"> & { className?: string }) {
  const [copied, setCopied] = useState(false);
  const codeText = flattenText(children).replace(/\n$/, "");
  const languageMatch = className?.match(/language-([\w-]+)/);
  const language = languageMatch?.[1];
  const isBlock = Boolean(language) || codeText.includes("\n");

  const onCopy = async () => {
    try {
      await navigator.clipboard.writeText(codeText);
      setCopied(true);
      setTimeout(() => setCopied(false), 1200);
    } catch {
      setCopied(false);
    }
  };

  if (!isBlock) {
    return (
      <code
        {...props}
        className={className}
        style={{
          fontFamily: "var(--font-geist-mono)",
          background: "var(--bg-3)",
          border: "1px solid var(--border-2)",
          borderRadius: 4,
          padding: "1px 5px",
          fontSize: "0.92em",
        }}
      >
        {children}
      </code>
    );
  }

  return (
    <div style={{ margin: "10px 0", border: "1px solid var(--border-2)", borderRadius: 8, overflow: "hidden", background: "#0f0f0f" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "6px 10px", borderBottom: "1px solid var(--border)", background: "var(--bg-3)" }}>
        <span style={{ fontSize: 11, color: "var(--text-2)", fontFamily: "var(--font-geist-mono)" }}>{language || "code"}</span>
        <button
          onClick={onCopy}
          style={{
            border: "1px solid var(--border-2)",
            background: "var(--bg-2)",
            color: copied ? "var(--green)" : "var(--text-2)",
            borderRadius: 5,
            fontSize: 11,
            padding: "2px 8px",
            cursor: "pointer",
            fontFamily: "var(--font-geist-mono)",
          }}
        >
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <pre style={{ margin: 0, padding: "10px 12px", overflowX: "auto", fontSize: 12, lineHeight: 1.6 }}>
        <code {...props} className={className} style={{ fontFamily: "var(--font-geist-mono)" }}>
          {children}
        </code>
      </pre>
    </div>
  );
}

function AssistantFormattedContent({ content }: { content: string }) {
  return (
    <div className="assistant-markdown">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeHighlight]}
        components={{
          code: MarkdownCode,
          a: ({ href, children }) => (
            <a href={href} target="_blank" rel="noreferrer">
              {children}
            </a>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}

function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";
  const bgColor = message.governanceBlocked
    ? "var(--amber-dim)"
    : message.error
    ? "var(--red-dim)"
    : isUser
    ? "var(--accent-dim)"
    : "var(--bg-2)";
  const borderColor = message.governanceBlocked
    ? "var(--amber)"
    : message.error
    ? "var(--red)"
    : isUser
    ? "var(--accent-border)"
    : "var(--border)";

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: isUser ? "flex-end" : "flex-start", gap: 6 }}>
      {message.governanceBlocked && (
        <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: "var(--amber)", fontWeight: 600 }}>
          <span>⚠️</span> Governance policy blocked this request
        </div>
      )}
      <div
        style={{
          maxWidth: "85%",
          padding: "10px 14px",
          borderRadius: isUser ? "10px 10px 2px 10px" : "10px 10px 10px 2px",
          background: bgColor,
          border: `1px solid ${borderColor}44`,
          fontSize: 13,
          lineHeight: 1.7,
          color: "var(--text)",
          wordBreak: "break-word",
        }}
      >
        {isUser ? (
          <span style={{ whiteSpace: "pre-wrap" }}>{message.content}</span>
        ) : (
          <AssistantFormattedContent content={message.content} />
        )}
        {message.streaming && (
          <span
            style={{
              display: "inline-block",
              width: 2,
              height: 14,
              background: "var(--accent)",
              marginLeft: 2,
              verticalAlign: "text-bottom",
              animation: "blink 0.8s ease-in-out infinite",
            }}
          />
        )}
      </div>
      {!isUser && message.routing?.model_selected && (
        <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: "var(--text-3)", fontFamily: "var(--font-geist-mono)" }}>
          <span style={{ color: "var(--text-2)" }}>{message.routing.model_selected}</span>
          <span>·</span>
          <span>{message.routing.task_type?.replace(/_/g, " ")}</span>
          <span>·</span>
          <span style={{ color: complexityColor(message.routing.complexity) }}>{message.routing.complexity}</span>
        </div>
      )}
    </div>
  );
}

export default function PlaygroundPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [department, setDepartment] = useState("rd");
  const [loading, setLoading] = useState(false);
  const [latestRouting, setLatestRouting] = useState<RoutingDecision | null>(null);
  const [streamingContent, setStreamingContent] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const abortRef = useRef(false);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingContent]);

  const autoResize = () => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 200) + "px";
  };

  const handleSend = async () => {
    const text = input.trim();
    if (!text || loading) return;

    const userMsg: Message = { id: Date.now().toString(), role: "user", content: text };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";
    setLoading(true);
    setStreamingContent("");
    abortRef.current = false;

    const history: ChatMessage[] = [
      ...messages.map((m) => ({ role: m.role as "user" | "assistant", content: m.content })),
      { role: "user", content: text },
    ];

    try {
      let routingDecision: RoutingDecision | null = null;
      let accumulated = "";

      await sendMessage({
        messages: history,
        department,
        stream: true,
        onToken: (token) => {
          if (abortRef.current) return;
          accumulated += token;
          setStreamingContent(accumulated);
        },
        onRoutingDecision: (rd) => {
          routingDecision = rd;
          setLatestRouting(rd);
        },
      });

      if (!abortRef.current) {
        setMessages((prev) => [
          ...prev,
          { id: (Date.now() + 1).toString(), role: "assistant", content: accumulated, routing: routingDecision ?? undefined },
        ]);
        setStreamingContent("");
      }
    } catch (err: unknown) {
      const routingErr = err as RoutingApiError;
      const isGovernanceBlocked = routingErr?.governance_blocked === true;
      const errMessage = err instanceof Error ? err.message : "Request failed";
      const content = isGovernanceBlocked
        ? errMessage  // backend already formats a clear governance message
        : `All providers failed for this request.\n\n${errMessage}\n\nCheck that API keys are configured in backend/.env and the provider is online.`;
      setMessages((prev) => [
        ...prev,
        { id: (Date.now() + 1).toString(), role: "assistant", content, error: true, governanceBlocked: isGovernanceBlocked },
      ]);
      setStreamingContent("");
    } finally {
      setLoading(false);
    }
  };

  const handleStop = () => {
    abortRef.current = true;
    setLoading(false);
    if (streamingContent) {
      setMessages((prev) => [...prev, { id: (Date.now() + 1).toString(), role: "assistant", content: streamingContent }]);
      setStreamingContent("");
    }
  };

  const handleReset = () => {
    setMessages([]);
    setLatestRouting(null);
    setStreamingContent("");
    setLoading(false);
    abortRef.current = true;
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div style={{ display: "flex", height: "100%", overflow: "hidden" }}>
      {/* Chat area */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
        {/* Toolbar */}
        <div style={{ padding: "12px 20px", borderBottom: "1px solid var(--border)", display: "flex", alignItems: "center", justifyContent: "space-between", background: "var(--bg-1)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ fontSize: 12, color: "var(--text-2)" }}>Department</span>
            <div style={{ position: "relative" }}>
              <select
                value={department}
                onChange={(e) => setDepartment(e.target.value)}
                style={{ background: "var(--bg-3)", border: "1px solid var(--border-2)", borderRadius: 5, color: "var(--text)", fontSize: 12, padding: "4px 28px 4px 10px", appearance: "none", cursor: "pointer", fontFamily: "inherit" }}
              >
                {DEPARTMENTS.map((d) => <option key={d} value={d}>{d.toUpperCase()}</option>)}
              </select>
              <ChevronDown size={12} style={{ position: "absolute", right: 8, top: "50%", transform: "translateY(-50%)", pointerEvents: "none", color: "var(--text-2)" }} />
            </div>
          </div>
          <button
            onClick={handleReset}
            disabled={messages.length === 0 && !loading}
            style={{ display: "flex", alignItems: "center", gap: 5, padding: "5px 10px", borderRadius: 5, border: "1px solid var(--border-2)", background: "transparent", color: "var(--text-2)", fontSize: 12, cursor: "pointer", opacity: messages.length === 0 && !loading ? 0.4 : 1 }}
          >
            <RotateCcw size={12} strokeWidth={1.5} />
            Clear
          </button>
        </div>

        {/* Messages */}
        <div style={{ flex: 1, overflow: "auto", padding: "24px 0" }}>
          {messages.length === 0 && !loading && (
            <div style={{ maxWidth: 720, margin: "0 auto", padding: "0 24px" }}>
              <div style={{ marginBottom: 28, textAlign: "center" }}>
                <div style={{ fontSize: 22, fontWeight: 600, color: "var(--text)", marginBottom: 8, letterSpacing: "-0.02em" }}>
                  RoutingBrain Playground
                </div>
                <div style={{ fontSize: 13, color: "var(--text-2)", lineHeight: 1.7 }}>
                  Send any message. RoutingBrain classifies the request and routes it to the most appropriate model automatically.
                </div>
              </div>

              <div style={{ fontSize: 11, color: "var(--text-3)", marginBottom: 12, letterSpacing: "0.06em", textTransform: "uppercase" }}>
                Test templates — verify routing classification
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                {TEMPLATES.map((group) => (
                  <div key={group.group}>
                    <div style={{ fontSize: 11, fontWeight: 500, color: "var(--text-2)", marginBottom: 6, letterSpacing: "0.02em" }}>
                      {group.group}
                    </div>
                    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                      {group.items.map((t, i) => (
                        <button
                          key={i}
                          onClick={() => { setInput(t.prompt); textareaRef.current?.focus(); }}
                          style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, textAlign: "left", padding: "8px 12px", borderRadius: 6, border: "1px solid var(--border)", background: "var(--bg-1)", cursor: "pointer", lineHeight: 1.5, transition: "border-color 0.1s, background 0.1s" }}
                          onMouseEnter={(e) => { e.currentTarget.style.borderColor = "var(--border-2)"; e.currentTarget.style.background = "var(--bg-2)"; }}
                          onMouseLeave={(e) => { e.currentTarget.style.borderColor = "var(--border)"; e.currentTarget.style.background = "var(--bg-1)"; }}
                        >
                          <span style={{ fontSize: 12, color: "var(--text)", flexShrink: 0, minWidth: 140 }}>{t.label}</span>
                          <span style={{ fontSize: 11, color: "var(--text-3)", flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                            {t.prompt.length > 80 ? t.prompt.slice(0, 80) + "…" : t.prompt}
                          </span>
                          <div style={{ display: "flex", gap: 5, flexShrink: 0 }}>
                            {t.expectedRisk && (
                              <span style={{
                                fontSize: 10, padding: "1px 6px", borderRadius: 3, fontFamily: "var(--font-geist-mono)", fontWeight: 600,
                                color: RISK_COLORS[t.expectedRisk],
                                background: RISK_DIM[t.expectedRisk],
                                border: `1px solid ${RISK_COLORS[t.expectedRisk]}33`,
                              }}>
                                {t.expectedRisk}
                              </span>
                            )}
                            <span style={{
                              fontSize: 10, padding: "1px 6px", borderRadius: 3, fontFamily: "var(--font-geist-mono)", fontWeight: 500,
                              color: t.expectedComplexity === "simple" ? "var(--green)" : t.expectedComplexity === "complex" ? "var(--amber)" : "var(--accent)",
                              background: t.expectedComplexity === "simple" ? "var(--green-dim)" : t.expectedComplexity === "complex" ? "var(--amber-dim)" : "var(--accent-dim)",
                            }}>
                              {t.expectedComplexity}
                            </span>
                            <span style={{
                              fontSize: 10, padding: "1px 6px", borderRadius: 3, fontFamily: "var(--font-geist-mono)",
                              color: t.expectedTier === "fast_cheap" ? "var(--green)" : t.expectedTier === "powerful" ? "var(--amber)" : "var(--accent)",
                              background: t.expectedTier === "fast_cheap" ? "var(--green-dim)" : t.expectedTier === "powerful" ? "var(--amber-dim)" : "var(--accent-dim)",
                            }}>
                              {t.expectedTier === "fast_cheap" ? "cheap" : t.expectedTier}
                            </span>
                          </div>
                        </button>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div style={{ maxWidth: 760, margin: "0 auto", padding: "0 24px", display: "flex", flexDirection: "column", gap: 24 }}>
            {messages.map((msg) => <MessageBubble key={msg.id} message={msg} />)}
            {loading && streamingContent && <MessageBubble message={{ id: "streaming", role: "assistant", content: streamingContent, streaming: true }} />}
            {loading && !streamingContent && (
              <div style={{ display: "flex", gap: 4, paddingLeft: 4 }}>
                {[0, 1, 2].map((i) => (
                  <div key={i} style={{ width: 5, height: 5, borderRadius: "50%", background: "var(--text-3)", animation: `bounce 1s ease-in-out ${i * 0.15}s infinite` }} />
                ))}
              </div>
            )}
          </div>
          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <div style={{ padding: "16px 24px", borderTop: "1px solid var(--border)", background: "var(--bg-1)" }}>
          <div
            style={{ maxWidth: 760, margin: "0 auto", display: "flex", gap: 10, alignItems: "flex-end", padding: "10px 14px", borderRadius: 8, border: "1px solid var(--border-2)", background: "var(--bg-3)", transition: "border-color 0.1s" }}
            onFocusCapture={(e) => { (e.currentTarget as HTMLElement).style.borderColor = "var(--accent-border)"; }}
            onBlurCapture={(e) => { (e.currentTarget as HTMLElement).style.borderColor = "var(--border-2)"; }}
          >
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => { setInput(e.target.value); autoResize(); }}
              onKeyDown={handleKeyDown}
              placeholder="Message RoutingBrain… (Enter to send, Shift+Enter for newline)"
              rows={1}
              style={{ flex: 1, background: "transparent", border: "none", outline: "none", color: "var(--text)", fontSize: 13, lineHeight: 1.6, resize: "none", fontFamily: "inherit", maxHeight: 200, overflow: "auto" }}
            />
            <button
              onClick={loading ? handleStop : handleSend}
              disabled={!loading && !input.trim()}
              style={{ flexShrink: 0, width: 32, height: 32, borderRadius: 6, border: "none", background: loading ? "var(--red-dim)" : input.trim() ? "var(--accent)" : "var(--border-2)", color: loading ? "var(--red)" : "white", cursor: (!loading && !input.trim()) ? "not-allowed" : "pointer", display: "flex", alignItems: "center", justifyContent: "center", transition: "background 0.1s" }}
            >
              {loading ? <Square size={13} fill="currentColor" strokeWidth={0} /> : <Send size={13} strokeWidth={2} />}
            </button>
          </div>
          <div style={{ maxWidth: 760, margin: "6px auto 0", textAlign: "right", fontSize: 11, color: "var(--text-3)" }}>
            Model: <span style={{ fontFamily: "var(--font-geist-mono)" }}>auto</span> · RoutingBrain selects automatically
          </div>
        </div>
      </div>

      <RoutingPanel decision={latestRouting} loading={loading} />

      <style>{`
        @keyframes bounce { 0%, 100% { transform: translateY(0); opacity: 0.4; } 50% { transform: translateY(-4px); opacity: 1; } }
        @keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }
      `}</style>
    </div>
  );
}
