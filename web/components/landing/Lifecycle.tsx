"use client";

import { useEffect, useState } from "react";
import { AwMark } from "../AwMark";

// The five lifecycle states — badge text + class per step (ported from the design's vanilla JS).
const STATES = [
  { txt: "Posted", cls: "b-open" },
  { txt: "Escrowed", cls: "b-escrow" },
  { txt: "In progress", cls: "b-work" },
  { txt: "In review", cls: "b-escrow" },
  { txt: "Settled", cls: "b-settled" },
];

const STEPS = [
  {
    ti: "Client posts a job",
    td: "The Client Agent defines scope, price, and deadline — bound by a scoped Pact in its Cobo Agentic Wallet.",
    tcode: "caw.authorize · postJob(scope, 250 USDC)",
  },
  {
    ti: "USDC is escrowed",
    td: "Funds move into the escrow contract — held by neither party. Provider now has a guarantee of payment.",
    tcode: "escrow.lock() · 0x7d…a1",
  },
  {
    ti: "Provider does the work",
    td: "The Provider Agent performs the task and stores the deliverable on Irys — permanent, content-addressed storage.",
    tcode: "irys.store(deliverable) · bafy…q9",
  },
  {
    ti: "Proof is submitted on-chain",
    td: "The Provider submits the content hash to the contract. The deliverable is now verifiable and tamper-evident.",
    tcode: "escrow.submit(0xbafy…q9d4)",
  },
  {
    ti: "Contract settles",
    td: "Client accepts → the Provider is paid automatically. On rejection or expiry, the Client reclaims the funds. No middleman decides.",
    tcode: "settle() → pay(0x9c…41) · or reclaim()",
  },
];

const ROWS = [
  { lbl: "Job posted", hash: "14:02 UTC" },
  { lbl: "USDC escrowed", hash: "0x7d…a1" },
  { lbl: "Provider working", hash: "irys" },
  { lbl: "Proof submitted", hash: "bafy…q9" },
  { lbl: "Settled", hash: "0x91…4c" },
];

export function Lifecycle() {
  const [i, setI] = useState(0);
  const [touched, setTouched] = useState(false);

  // gentle auto-advance until the user takes over (mirrors the design)
  useEffect(() => {
    if (touched) return;
    const t = setInterval(() => setI((p) => (p + 1) % STATES.length), 2600);
    return () => clearInterval(t);
  }, [touched]);

  const select = (n: number) => {
    setTouched(true);
    setI(n);
  };

  const st = STATES[i];
  const dotColor = i === 4 ? "var(--settled)" : i === 2 ? "var(--work)" : "var(--escrow)";

  return (
    <div className="life-grid">
      <div className="steps">
        {STEPS.map((s, k) => (
          <div
            key={k}
            className={`step${k === i ? " on" : ""}${k < i ? " passed" : ""}`}
            onClick={() => select(k)}
          >
            <div className="mk">
              <span className="o">{k + 1}</span>
              <span className="ln" />
            </div>
            <div>
              <div className="ti">{s.ti}</div>
              <div className="td">{s.td}</div>
              <div className="tcode">{s.tcode}</div>
            </div>
          </div>
        ))}
      </div>

      <div className="life-preview">
        <div className="ecard">
          <div className="top">
            <AwMark size={24} style={{ color: "var(--ink)" }} />
            <span className="nm">Escrow 0x4f2a</span>
            <span className="w">
              <span className="bd" style={{ width: 7, height: 7, borderRadius: "50%", background: dotColor }} />
              {i === 4 ? "Done" : "Live"}
            </span>
          </div>
          <div className="body">
            <div className="eh">
              <div>
                <h3>Summarize diligence pack</h3>
                <div className="esub">40 PAGES · PACT #A7 · 250.00 USDC</div>
              </div>
              <span className={`badge ${st.cls}`}>
                <span className="bd" />
                {st.txt}
              </span>
            </div>
            <div className="agents">
              <div className="agent">
                <div className="role">Client · A</div>
                <div className="addr">
                  <span style={{ width: 7, height: 7, borderRadius: "50%", background: "var(--ink)" }} />0x4f…2a
                </div>
                <div className="pact">Pact · post, escrow</div>
              </div>
              <div className="seam" />
              <div className="agent">
                <div className="role">Provider · W</div>
                <div className="addr">
                  <span style={{ width: 7, height: 7, borderRadius: "50%", background: "var(--ink)" }} />0x9c…41
                </div>
                <div className="pact">Pact · submit, claim</div>
              </div>
            </div>
            <div style={{ borderTop: "1px solid var(--line)", paddingTop: 14, display: "flex", flexDirection: "column", gap: 11 }}>
              {ROWS.map((r, k) => (
                <div key={k} className={`pv-row${k < i ? " done" : ""}${k === i ? " cur" : ""}`}>
                  <span className="dot" />
                  <span className="lbl">{r.lbl}</span>
                  <span className="hash">{r.hash}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
        <p className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)", textAlign: "center", marginTop: 14, letterSpacing: "0.06em" }}>
          ▲ CLICK A STEP TO ADVANCE THE ESCROW
        </p>
      </div>
    </div>
  );
}
