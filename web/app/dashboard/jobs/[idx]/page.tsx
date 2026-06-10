import Link from "next/link";
import { notFound } from "next/navigation";
import { loadJobs } from "../../../../lib/proofs";
import { CFG, txUrl, irysUrl, addrUrl, shortHex } from "../../../../lib/config";
import { Badge } from "../../../../components/Badge";

export const dynamic = "force-dynamic";

const STEP_DEFS: { key: string; ti: string }[] = [
  { key: "createJob", ti: "Job created" },
  { key: "approve", ti: "USDC approved" },
  { key: "fund", ti: "USDC escrowed" },
  { key: "submitWork", ti: "Work submitted + Irys id" },
  { key: "complete", ti: "Accepted → Provider paid" },
  { key: "reject", ti: "Rejected → Client refunded" },
];

const check = (
  <svg width="11" height="11" viewBox="0 0 12 12"><path d="M3 6.5l2 2 4-5" fill="none" stroke="var(--settled)" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" /></svg>
);

export default async function JobDetailPage({ params }: { params: Promise<{ idx: string }> }) {
  const { idx } = await params;
  const jobs = loadJobs();
  const job = jobs[Number(idx)];
  if (!job) notFound();
  const payout = job.branch === "payout";
  const settleTx = job.txs.complete || job.txs.reject || "";
  const steps = STEP_DEFS.filter((s) => job.txs[s.key]);

  return (
    <>
      <div className="head">
        <h1 style={{ fontSize: 26 }}>Escrow · Job #{job.jobId}</h1>
        <p style={{ maxWidth: "70ch" }}>{job.title}</p>
      </div>

      <div className="panel sc-body">
        <div className="sc-head" style={{ padding: 0 }}>
          <div><h3>Settlement detail</h3><div className="sc-sub">{job.phase} · {job.source}</div></div>
          <Badge state={job.badge} label={job.statusLabel} />
        </div>

        {/* agents */}
        <div className="agents">
          <div className="agent">
            <div className="role">Client · A</div>
            <div className="addr"><span style={{ width: 7, height: 7, borderRadius: "50%", background: "var(--ink)" }} /><a href={addrUrl(CFG.clientCaw)} target="_blank" rel="noreferrer">{shortHex(CFG.clientCaw)}</a></div>
            <div className="pact">Pact · escrow + USDC allowlist</div>
          </div>
          <div className="seam" />
          <div className="agent">
            <div className="role">Provider · W</div>
            <div className="addr"><span style={{ width: 7, height: 7, borderRadius: "50%", background: "var(--ink)" }} /><a href={addrUrl(CFG.providerCaw)} target="_blank" rel="noreferrer">{shortHex(CFG.providerCaw)}</a></div>
            <div className="pact">Pact · escrow allowlist</div>
          </div>
        </div>

        {/* reasoning */}
        {(job.reasoning.client_fund || job.reasoning.evaluate) && (
          <div className="reason">
            {job.reasoning.client_fund && (
              <div className="rcard"><div className="rk">Client · fund decision (LLM)</div>
                <div className={`verdict ${job.reasoning.client_fund.fund ? "y" : "n"}`}>{job.reasoning.client_fund.fund ? "FUND ✓" : "DECLINE ✕"}</div>
                <div className="why">{job.reasoning.client_fund.reason}</div></div>
            )}
            {job.reasoning.evaluate && (
              <div className="rcard"><div className="rk">Evaluator · verdict (LLM)</div>
                <div className={`verdict ${job.reasoning.evaluate.accept ? "y" : "n"}`}>{job.reasoning.evaluate.accept ? "ACCEPT ✓ → payout" : "REJECT ✕ → refund"}</div>
                <div className="why">{job.reasoning.evaluate.reason}</div></div>
            )}
          </div>
        )}

        {/* timeline */}
        <div className="timeline">
          {steps.map((s, i) => (
            <div key={s.key} className={`tstep done${s.key === "reject" ? "" : ""}`}>
              <div className="mk"><span className="o" />{i < steps.length - 1 && <span className="ln" />}</div>
              <div><div className="ti">{s.ti}</div><div className="td">{check}{s.key}() · <a className="lnk" href={txUrl(job.txs[s.key])} target="_blank" rel="noreferrer">{shortHex(job.txs[s.key], 10)}</a></div></div>
              <div className="tt" />
            </div>
          ))}
        </div>

        {/* irys + verification */}
        {job.irys && (
          <div className="proof" style={{ marginTop: 18 }}>
            <div className="ph"><span className="t">Deliverable · Irys</span><span className="when"><a className="lnk" href={irysUrl(job.irys.id)} target="_blank" rel="noreferrer">{shortHex(job.irys.id, 10)}</a></span></div>
            <div className="pb">
              <div className="ic"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M4 7h16M4 12h16M4 17h10" /></svg></div>
              <div><div className="fn">deliverable.txt</div>{job.deliverable && <div className="fh" style={{ color: "var(--ink-3)" }}>{job.deliverable.slice(0, 90)}…</div>}</div>
              {job.contentVerified && <span className="verified" style={{ marginLeft: "auto" }}>{check} hash verified</span>}
            </div>
          </div>
        )}

        {/* receipt */}
        <div className="receipt" style={{ marginTop: 18 }}>
          <div className="rcell"><div className="rk">Outcome</div><div className="rv">{job.branch === "payout" ? "Provider paid" : job.branch === "refund" ? "Client refunded" : "—"}</div></div>
          <div className="rcell"><div className="rk">Amount</div><div className="rv">{job.amountUsdc.toFixed(2)} USDC</div></div>
          <div className="rcell"><div className="rk">settle() tx</div><div className="rv">{settleTx ? <a href={txUrl(settleTx)} target="_blank" rel="noreferrer">{shortHex(settleTx, 10)}</a> : "—"}</div></div>
          <div className="rcell"><div className="rk">Final status</div><div className="rv">{job.statusLabel}</div></div>
        </div>

        <div className="sc-actions" style={{ padding: "18px 0 0", background: "none", border: 0 }}>
          <Link className="btn" href="/dashboard">← Back to Marketplace</Link>
          {settleTx && <a className="btn primary" href={txUrl(settleTx)} target="_blank" rel="noreferrer">View on explorer</a>}
        </div>
      </div>
    </>
  );
}
