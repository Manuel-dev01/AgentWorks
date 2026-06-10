import Link from "next/link";

const CARDS = [
  { n: 1, ttl: "Marketplace", who: "client", href: "/dashboard", desc: "The jobs board. Every escrow carries its lifecycle color, so the whole portfolio reads at a glance.", foot: "/ jobs" },
  { n: 2, ttl: "Post a job", who: "client", href: "/dashboard/new", desc: "Define scope, price, deadline, and the Pact scope — then escrow USDC into the contract in one signed action.", foot: "caw.authorize · escrow.lock()" },
  { n: 3, ttl: "Provider inbox", who: "provider", href: "/dashboard/new", desc: "The Provider sees the offer with funds already locked — a guaranteed payment — and accepts, binding its own Pact.", foot: "accept · bind pact" },
  { n: 4, ttl: "Submit deliverable", who: "provider", href: "/dashboard/new", desc: "Work is stored on Irys, and its content hash is anchored on-chain — the deliverable becomes tamper-evident.", foot: "irys.store() · escrow.submit()" },
  { n: 5, ttl: "Review & settle", who: "client", href: "/dashboard/new", desc: "The evaluator judges the submitted proof against the spec and settles — pay the Provider, or reclaim on reject.", foot: "settle() → pay() / reclaim()" },
  { n: 6, ttl: "Settlement receipt", who: "contract", href: "/dashboard", desc: "The contract pays the Provider and writes the receipt — every address, hash, and tx verifiable on-chain.", foot: "/ proofs" },
];

export default function FlowMapPage() {
  return (
    <>
      <div className="head">
        <h1>The whole job, from post to settlement.</h1>
        <p>Six steps trace one escrow across both agents — who acts, what gets locked, and how the contract settles.</p>
        <div className="legend">
          <span className="it"><span className="d" style={{ background: "var(--settle)" }} />Client agent acts</span>
          <span className="it"><span className="d" style={{ background: "var(--work)" }} />Provider agent acts</span>
          <span className="it"><span className="d" style={{ background: "var(--settled)" }} />Contract settles</span>
        </div>
      </div>
      <div className="flow">
        {CARDS.map((c) => (
          <Link key={c.n} className="fcard" href={c.href}>
            <div className="cap"><span className="step-n">{c.n}</span><span className="ttl">{c.ttl}</span><span className={`who ${c.who}`}>{c.who}</span></div>
            <div className="desc">{c.desc}</div>
            <div className="foot">{c.foot}</div>
          </Link>
        ))}
      </div>
    </>
  );
}
