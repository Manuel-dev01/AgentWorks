"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { AwMark } from "../AwMark";
import { CFG, shortHex } from "../../lib/config";

const TABS = [
  { href: "/dashboard", label: "Marketplace" },
  { href: "/dashboard/new", label: "New job" },
  { href: "/dashboard/proofs", label: "Proofs" },
  { href: "/dashboard/flow", label: "Flow" },
];

export function Shell({ clientBal, providerBal }: { clientBal: number | null; providerBal: number | null }) {
  const path = usePathname();
  const active = (href: string) => (href === "/dashboard" ? path === href : path.startsWith(href));
  const bal = (n: number | null) => (n === null ? "—" : `${n.toFixed(2)}`);
  return (
    <div className="bar">
      <div className="wrap">
        <AwMark size={26} style={{ color: "var(--ink)" }} />
        <span className="nm">AgentWorks</span>
        <nav className="tabs">
          {TABS.map((t) => (
            <Link key={t.href} href={t.href} className={`tab${active(t.href) ? " on" : ""}`}>
              {t.label}
            </Link>
          ))}
        </nav>
        <span className="wallets">
          <span className="wchip">
            <span className="d" style={{ background: "var(--settle)" }} />
            <b>Client</b> {shortHex(CFG.clientCaw)} · {bal(clientBal)} USDC
          </span>
          <span className="wchip">
            <span className="d" style={{ background: "var(--work)" }} />
            <b>Provider</b> {shortHex(CFG.providerCaw)} · {bal(providerBal)} USDC
          </span>
        </span>
      </div>
    </div>
  );
}
