"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { BrainCircuit, FlaskConical, GitBranch, BarChart2, ShieldCheck, TestTube2, SlidersHorizontal } from "lucide-react";

const NAV_ITEMS = [
  { href: "/", label: "Playground", icon: FlaskConical },
  { href: "/inspector", label: "Inspector", icon: GitBranch },
  { href: "/lab", label: "Lab", icon: TestTube2 },
  { href: "/admin", label: "Admin", icon: SlidersHorizontal },
  { href: "/analytics", label: "Analytics", icon: BarChart2 },
  { href: "/audit", label: "Audit Log", icon: ShieldCheck },
];

export function Nav() {
  const pathname = usePathname();

  return (
    <nav
      style={{
        width: 220,
        flexShrink: 0,
        borderRight: "1px solid var(--border)",
        background: "var(--bg-1)",
        display: "flex",
        flexDirection: "column",
        padding: "0",
      }}
    >
      {/* Logo */}
      <div
        style={{
          padding: "20px 20px 0",
          borderBottom: "1px solid var(--border)",
          paddingBottom: 20,
          marginBottom: 8,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div
            style={{
              width: 30,
              height: 30,
              borderRadius: 6,
              background: "var(--accent-dim)",
              border: "1px solid var(--accent-border)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              flexShrink: 0,
            }}
          >
            <BrainCircuit size={16} color="var(--accent)" strokeWidth={1.5} />
          </div>
          <div>
            <div style={{ fontWeight: 600, fontSize: 13, color: "var(--text)", letterSpacing: "-0.01em" }}>
              RoutingBrain
            </div>
            <div style={{ fontSize: 11, color: "var(--text-2)", marginTop: 1 }}>
              AI Governance Platform
            </div>
          </div>
        </div>
      </div>

      {/* Nav links */}
      <div style={{ padding: "8px 10px", flex: 1 }}>
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const active = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 10,
                padding: "8px 10px",
                borderRadius: 6,
                marginBottom: 2,
                color: active ? "var(--text)" : "var(--text-2)",
                background: active ? "var(--bg-3)" : "transparent",
                textDecoration: "none",
                fontSize: 13,
                fontWeight: active ? 500 : 400,
                transition: "background 0.1s, color 0.1s",
              }}
              onMouseEnter={(e) => {
                if (!active) {
                  (e.currentTarget as HTMLElement).style.background = "var(--bg-2)";
                  (e.currentTarget as HTMLElement).style.color = "var(--text)";
                }
              }}
              onMouseLeave={(e) => {
                if (!active) {
                  (e.currentTarget as HTMLElement).style.background = "transparent";
                  (e.currentTarget as HTMLElement).style.color = "var(--text-2)";
                }
              }}
            >
              <Icon size={15} strokeWidth={1.5} />
              {label}
            </Link>
          );
        })}
      </div>

      {/* Footer */}
      <div
        style={{
          padding: "16px 20px",
          borderTop: "1px solid var(--border)",
          fontSize: 11,
          color: "var(--text-3)",
          fontFamily: "var(--font-geist-mono)",
        }}
      >
        v0.1.0 · R&D
      </div>
    </nav>
  );
}
