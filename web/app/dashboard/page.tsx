import Link from "next/link";
import "../dashboard.css";
import { AwMark } from "../../components/AwMark";
import { DashboardBody } from "../../components/dashboard/DashboardBody";
import { loadJobs, loadBeats, loadPacts } from "../../lib/proofs";
import { usdcBalance, liveJob } from "../../lib/chain";
import { CFG, addrUrl, txUrl, shortHex } from "../../lib/config";
import type { JobVM } from "../../lib/types";

// Reads proof artifacts (fs) + chain state at request time; never statically prerendered.
export const dynamic = "force-dynamic";

export default async function DashboardPage() {
  const jobs = loadJobs();
  const beats = loadBeats();
  const pacts = loadPacts();

  // Additive live enrichment — degrades gracefully to the proof snapshots on RPC failure.
  const [clientBal, providerBal, ...live] = await Promise.all([
    usdcBalance(CFG.clientCaw),
    usdcBalance(CFG.providerCaw),
    ...jobs.map((j) => liveJob(j.jobId)),
  ]);
  const enriched: JobVM[] = jobs.map((j, i) => {
    const lj = live[i];
    return lj ? { ...j, amountUsdc: lj.amountUsdc || j.amountUsdc } : j;
  });

  // The Python live-run only works locally (Vercel serverless can't run the agents' venv);
  // hide it in production. The /api/run route is additionally localhost-guarded.
  const enableLiveRun = CFG.enableLiveRun && process.env.NODE_ENV !== "production";

  return (
    <div className="dp">
      {/* top bar */}
      <div className="bar">
        <div className="wrap">
          <AwMark size={28} style={{ color: "var(--ink)" }} />
          <span className="nm">AgentWorks</span>
          <span className="links">
            <Link href="/">Landing</Link>
            <Link href="/brand">Brand</Link>
          </span>
          <span className="wallets">
            <span className="wchip">
              <span className="dot" style={{ background: "var(--settle)" }} />
              <b>Client CAW</b> {shortHex(CFG.clientCaw)} · {fmtBal(clientBal)}
            </span>
            <span className="wchip">
              <span className="dot" style={{ background: "var(--work)" }} />
              <b>Provider CAW</b> {shortHex(CFG.providerCaw)} · {fmtBal(providerBal)}
            </span>
          </span>
        </div>
      </div>

      <div className="wrap">
        {/* head */}
        <div className="head">
          <h1>Escrow lifecycle, on-chain and verifiable.</h1>
          <p>
            Every job below ran end-to-end on Ethereum Sepolia through two Cobo Agentic Wallets — each transition is a
            real transaction you can open, each deliverable is stored on Irys and verified against its on-chain hash.
            Source of truth is the verified run artifacts; balances and job status are read live from chain.
          </p>
        </div>

        {/* jobs + detail + live-run (client) */}
        <section>
          <div className="sec-tag"><span className="num">01</span> · <b>Jobs &amp; settlement</b></div>
          <DashboardBody jobs={enriched} balances={{ client: clientBal, provider: providerBal }} enableLiveRun={enableLiveRun} />
        </section>

        {/* CAW criticality beats */}
        <section>
          <div className="sec-tag"><span className="num">02</span> · <b>CAW criticality</b> — the load-bearing trust layer</div>
          <p style={{ color: "var(--ink-2)", fontSize: 15, lineHeight: 1.55, maxWidth: "64ch", marginBottom: 18 }}>
            A Pact is enforced server-side by Cobo Agentic Wallet — the agent cannot exceed it regardless of what its LLM
            decides. These three beats are pulled from the verified Phase 4 runs.
          </p>
          <div className="beats">
            {/* DENIAL */}
            <div className="beat">
              <div className="bh">
                <span className="bnum">BEAT 01</span>
                <h3>Pact denial</h3>
                <span className="denied-pill">403 DENIED</span>
              </div>
              <p>An over-budget transfer and a call to a non-allowlisted contract are both refused before they ever reach the chain.</p>
              {beats.denials.map((d) => (
                <div className="codeline" key={d.code}>
                  <span className="c">{d.code}</span> · {d.statusCode}
                  <br />
                  {d.detail}
                </div>
              ))}
              {beats.auditDenied.length > 0 && (
                <div className="audit">
                  {beats.auditDenied.slice(0, 4).map((e, i) => (
                    <div className="ae" key={i}>
                      <span className="x">✕</span> {e.action} · {e.result}
                      {e.createdAt ? ` · ${e.createdAt.slice(0, 19).replace("T", " ")}Z` : ""}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* FREEZE */}
            <div className="beat">
              <div className="bh">
                <span className="bnum">BEAT 02</span>
                <h3>Emergency freeze</h3>
                {beats.freeze?.afterFreezeDenied && <span className="denied-pill">403 AFTER</span>}
              </div>
              <p>
                CAW has no native freeze API, so freeze = <b style={{ color: "var(--ink)", fontWeight: 600 }}>revoke_pact</b>.
                A call succeeds, the Pact is revoked, and the very next call is denied — authority stripped instantly.
              </p>
              {beats.freeze && (
                <>
                  <div className="codeline">
                    allowed before · <a href={txUrl(beats.freeze.allowedTx)} target="_blank" rel="noreferrer" style={{ color: "var(--settle-deep)", textDecoration: "none" }}>{shortHex(beats.freeze.allowedTx, 10)}</a>
                    <br />
                    revoke_pact · {shortHex(beats.freeze.pactId, 8)}
                  </div>
                  <div className="audit">
                    {beats.freeze.recentDenied.slice(0, 3).map((e, i) => (
                      <div className="ae" key={i}><span className="x">✕</span> {e.action} · {e.result}</div>
                    ))}
                  </div>
                </>
              )}
            </div>

            {/* REVIEW */}
            <div className="beat">
              <div className="bh">
                <span className="bnum">BEAT 03</span>
                <h3>Human-in-the-loop review</h3>
                {beats.review && <span className="denied-pill ok-pill">APPROVED</span>}
              </div>
              <p>
                A <code>review_if</code> Pact holds a sensitive transfer as a <b style={{ color: "var(--ink)", fontWeight: 600 }}>PendingApproval</b> until
                the owner approves — then it executes on-chain.
              </p>
              {beats.review && (
                <>
                  <div className="codeline">
                    decision · <span className="c" style={{ color: "var(--work)" }}>{beats.review.effect}</span>
                    <br />
                    pending · {shortHex(beats.review.pendingId, 8)} → {beats.review.status}
                  </div>
                  {beats.review.txHash && (
                    <div className="audit">
                      <div className="ae">
                        <span style={{ color: "var(--settled)" }}>✓</span> executed ·{" "}
                        <a href={txUrl(beats.review.txHash)} target="_blank" rel="noreferrer" style={{ color: "var(--settle-deep)", textDecoration: "none" }}>{shortHex(beats.review.txHash, 10)}</a>
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        </section>

        {/* literal Pact policies */}
        <section>
          <div className="sec-tag"><span className="num">03</span> · <b>Pact policies</b> — the literal risk boundary</div>
          <p style={{ color: "var(--ink-2)", fontSize: 15, lineHeight: 1.55, maxWidth: "64ch", marginBottom: 18 }}>
            The exact JSON each agent operates within, shipped as a first-class deliverable. The allowlist binds the live
            escrow ({shortHex(CFG.escrow)}) + MockUSDC; caps and review thresholds are enforced by CAW, not by our code.
          </p>
          <div className="pacts">
            {pacts.map((p) => (
              <div className="pact" key={p.name}>
                <div className="ph">
                  <span className="pn">{p.name}</span>
                  <span className="pt">Pact spec</span>
                </div>
                <pre>{p.json}</pre>
              </div>
            ))}
          </div>
        </section>

        {/* footer */}
        <div className="foot">
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <AwMark size={26} style={{ color: "var(--ink)" }} />
            <div className="mono">
              Escrow <a href={addrUrl(CFG.escrow)} target="_blank" rel="noreferrer" style={{ color: "var(--settle-deep)", textDecoration: "none" }}>{shortHex(CFG.escrow)}</a> ·
              MockUSDC <a href={addrUrl(CFG.usdc)} target="_blank" rel="noreferrer" style={{ color: "var(--settle-deep)", textDecoration: "none" }}>{shortHex(CFG.usdc)}</a> · Ethereum Sepolia
            </div>
          </div>
          <div className="mono">ESCROW · PROOF · SETTLEMENT — COBO AGENTIC ECONOMY TRACK</div>
        </div>
      </div>
    </div>
  );
}

const fmtBal = (n: number | null) => (n === null ? "— USDC" : `${n.toFixed(2)} USDC`);
