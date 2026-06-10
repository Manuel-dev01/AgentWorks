"use client";

import { useState } from "react";
import Link from "next/link";
import { runStep, type FlowState } from "../../lib/flow";
import { CFG, txUrl, irysUrl, addrUrl, shortHex } from "../../lib/config";
import { Badge } from "../Badge";

const STEP_LABELS = ["Post", "Accept", "Submit", "Review", "Settle"];
// status → step index
const STATUS_STEP: Record<string, number> = {
  started: 0, declined: 0, posted: 1, accepted: 2, submitted: 3, settled: 4,
};

const check = (
  <svg width="11" height="11" viewBox="0 0 12 12"><path d="M3 6.5l2 2 4-5" fill="none" stroke="var(--settled)" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" /></svg>
);

export function Journey({ enabled }: { enabled: boolean }) {
  const [mode, setMode] = useState<"good" | "bad">("good");
  const [flow, setFlow] = useState<FlowState | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const step = flow ? (STATUS_STEP[flow.status] ?? 0) : 0;

  async function go(label: string, fn: () => Promise<FlowState>) {
    setBusy(label);
    setErr(null);
    try {
      const s = await fn();
      if (s.error) setErr(s.error);
      else setFlow(s);
    } catch (e) {
      setErr(String(e));
    } finally {
      setBusy(null);
    }
  }

  const postJob = () =>
    go("Posting (createJob + escrow)…", async () => {
      const started = await runStep("start", { mode });
      if (started.error || started.status === "declined") return started;
      setFlow(started); // surface fund decision immediately
      return runStep("post", { runId: started.run_id });
    });
  const accept = () => flow && go("Provider binding Pact…", () => runStep("accept", { runId: flow.run_id }));
  const submit = () => flow && go("Working → Irys → submitWork…", () => runStep("submit", { runId: flow.run_id }));
  const settle = () => flow && go("Evaluator deciding → settle…", () => runStep("settle", { runId: flow.run_id }));

  if (!enabled) {
    return (
      <div className="panel" style={{ padding: 24 }}>
        <p className="muted mono" style={{ fontSize: 12, lineHeight: 1.7 }}>
          The live journey drives the real Python agents on Ethereum Sepolia and is available only when running
          locally (<span className="mono">pnpm --filter web dev</span>). Browse the <Link className="lnk" href="/dashboard">Marketplace</Link>{" "}
          for the verified runs, or the <Link className="lnk" href="/dashboard/proofs">Proofs</Link> tab for the CAW criticality beats.
        </p>
      </div>
    );
  }

  return (
    <div>
      {/* step rail */}
      <div className="stepnav">
        {STEP_LABELS.map((l, i) => (
          <span key={l} className={`sx${i < step ? " done" : ""}${i === step ? " on" : ""}`}>
            <span className="n">{i < step ? "✓" : i + 1}</span>{l}
          </span>
        ))}
      </div>
      <p className="runline">
        Mode:{" "}
        <button className={`filter${mode === "good" ? " on" : ""}`} disabled={!!flow || !!busy} onClick={() => setMode("good")} style={{ marginRight: 6 }}>good → payout</button>
        <button className={`filter${mode === "bad" ? " on" : ""}`} disabled={!!flow || !!busy} onClick={() => setMode("bad")}>bad → refund</button>
        {flow?.run_id && <span> · run {flow.run_id}</span>}
      </p>

      {busy && <p className="running"><span className="spin" />{busy}</p>}
      {err && <div className="err">⚠ {err}<br />The verified runs in the Marketplace remain intact.</div>}

      {flow?.status === "declined" && (
        <div className="panel sc-body">
          <h3>Client declined to fund</h3>
          <p className="muted" style={{ marginTop: 8 }}>{flow.fund_decision?.reason}</p>
          <button className="btn" style={{ marginTop: 14 }} onClick={() => setFlow(null)}>Start over</button>
        </div>
      )}

      {/* screen by step */}
      {step === 0 && flow?.status !== "declined" && <PostScreen mode={mode} flow={flow} busy={!!busy} onPost={postJob} />}
      {step === 1 && flow && <InboxScreen flow={flow} busy={!!busy} onAccept={accept} />}
      {step === 2 && flow && <SubmitScreen flow={flow} busy={!!busy} onSubmit={submit} />}
      {step === 3 && flow && <ReviewScreen flow={flow} busy={!!busy} onSettle={settle} />}
      {step === 4 && flow && <ReceiptScreen flow={flow} />}
    </div>
  );
}

const PROVIDER = () => shortHex(CFG.providerCaw);
const CLIENT = () => shortHex(CFG.clientCaw);

function PostScreen({ mode, flow, busy, onPost }: { mode: string; flow: FlowState | null; busy: boolean; onPost: () => void }) {
  return (
    <div className="panel">
      <div className="sc-head"><div><h3>Post a job — Client escrows USDC</h3><div className="sc-sub">Client CAW {CLIENT()} signs createJob + escrow in one flow</div></div><span className="badge b-open"><span className="bd" />New</span></div>
      <div className="post">
        <div className="form">
          <div className="field"><div className="lab">Task</div><div className="inp big">Explain on-chain escrow for a non-expert</div></div>
          <div className="field"><div className="lab">Scope / acceptance criteria</div><div className="inp area">A clear 2–3 sentence explanation. Acceptance is judged by the evaluator against the Irys-stored deliverable.</div></div>
          <div className="row2">
            <div className="field"><div className="lab">Reward</div><div className="amtin"><span className="v">10.00</span><span className="u">USDC</span></div></div>
            <div className="field"><div className="lab">Deadline</div><div className="inp">7 days from escrow</div></div>
          </div>
          <div className="field"><div className="lab">Provider agent</div><div className="inp mono" style={{ fontSize: 13 }}>{CFG.providerCaw} · Provider CAW</div></div>
          <div className="field">
            <div className="lab">Pact scope · granted to this job</div>
            <div className="pactbox">
              <div className="ph">Authority bound in the Client's Cobo Agentic Wallet</div>
              <Scope on label="contract_call → escrow + USDC" desc="createJob, approve, fund" />
              <Scope on label="accept / reject" desc="on proof submitted" />
              <Scope label="transfer escrow funds" desc="not granted — only the contract moves funds" off />
            </div>
          </div>
        </div>
        <div className="summary">
          <h4>Escrow summary</h4>
          <div className="sline"><span className="k">Reward</span><span className="v">10.00 USDC</span></div>
          <div className="sline"><span className="k">Held by</span><span className="v">Escrow contract</span></div>
          <div className="sline"><span className="k">Released on</span><span className="v">accepted proof</span></div>
          <div className="stotal"><span className="k">Total to escrow</span><span className="v">10.00<span className="u"> USDC</span></span></div>
          {flow?.fund_decision && (
            <div className="rcard" style={{ margin: "4px 0 14px" }}>
              <div className="rk">Client · fund decision (LLM)</div>
              <div className={`verdict ${flow.fund_decision.fund ? "y" : "n"}`}>{flow.fund_decision.fund ? "FUND ✓" : "DECLINE ✕"}</div>
              <div className="why">{flow.fund_decision.reason}</div>
            </div>
          )}
          <p className="enote">Funds move into the escrow contract — held by neither party. The Provider gains a payment guarantee; the Client reclaims on rejection or expiry.</p>
          <button className="btn accept" style={{ justifyContent: "center", padding: 13 }} disabled={busy} onClick={onPost}>
            Escrow &amp; post job ({mode}) <span className="k" style={{ opacity: 0.7 }}>⏎</span>
          </button>
          <p className="enote" style={{ textAlign: "center", margin: "12px 0 0" }}>SIGNS WITH CLIENT CAW · {CLIENT()}</p>
        </div>
      </div>
    </div>
  );
}

function Scope({ on, off, label, desc }: { on?: boolean; off?: boolean; label: string; desc: string }) {
  return (
    <div className={`scope${off ? " off" : ""}`}>
      <span className="ck">{!off && <svg width="9" height="9" viewBox="0 0 12 12"><path d="M3 6.5l2 2 4-5" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" /></svg>}</span>
      {label}<span className="desc">{desc}</span>
    </div>
  );
}

function InboxScreen({ flow, busy, onAccept }: { flow: FlowState; busy: boolean; onAccept: () => void }) {
  return (
    <div className="panel sc-body">
      <div className="offer">
        <div className="oh">
          <div><h3>New job offer · Job #{flow.job_id}</h3><div className="osub">FROM CLIENT {CLIENT()} · ESCROWED ON-CHAIN</div></div>
          <span className="locked"><svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="5" y="11" width="14" height="9" rx="2" /><path d="M8 11V8a4 4 0 0 1 8 0v3" /></svg>Funds locked</span>
        </div>
        <div className="reward">
          <span className="v">{flow.amount_usdc.toFixed(2)}</span><span className="u">USDC</span>
          <span className="gua">Already in escrow<br /><b><a className="lnk" href={txUrl(flow.txs.fund)} target="_blank" rel="noreferrer">fund() · {shortHex(flow.txs.fund || "", 8)}</a></b></span>
        </div>
        <div className="scopebox"><div className="sk">On-chain so far</div>
          <p className="mono" style={{ fontSize: 12, lineHeight: 1.9 }}>
            createJob · <a className="lnk" href={txUrl(flow.txs.createJob)} target="_blank" rel="noreferrer">{shortHex(flow.txs.createJob || "", 10)}</a><br />
            approve · <a className="lnk" href={txUrl(flow.txs.approve)} target="_blank" rel="noreferrer">{shortHex(flow.txs.approve || "", 10)}</a><br />
            fund · <a className="lnk" href={txUrl(flow.txs.fund)} target="_blank" rel="noreferrer">{shortHex(flow.txs.fund || "", 10)}</a>
          </p>
        </div>
        <p className="myscope">Accepting binds the Provider CAW Pact to <b style={{ color: "var(--ink)", fontWeight: 500 }}>submitWork</b> on the escrow only. The Provider cannot move the escrowed funds — only the contract can.</p>
        <div className="sc-actions" style={{ padding: "16px 0 0", background: "none", border: 0 }}>
          <button className="btn accept" disabled={busy} onClick={onAccept}>Accept job — bind Pact <span className="k" style={{ opacity: 0.7 }}>⏎</span></button>
        </div>
      </div>
    </div>
  );
}

function SubmitScreen({ flow, busy, onSubmit }: { flow: FlowState; busy: boolean; onSubmit: () => void }) {
  return (
    <div className="panel">
      <div className="sc-head"><div><h3>Submit deliverable · Job #{flow.job_id}</h3><div className="sc-sub">Provider CAW {PROVIDER()} · stores to Irys, anchors the content hash on-chain</div></div><span className="badge b-work"><span className="bd" />In progress</span></div>
      <div className="sc-body">
        <p className="muted" style={{ fontSize: 14, marginBottom: 16 }}>
          The Provider agent performs the task, uploads the deliverable to Irys (permanent, content-addressed),
          and submits <span className="mono">submitWork(jobId, keccak256(content), irysId)</span> on-chain.
        </p>
        <div className="sc-actions" style={{ padding: 0, background: "none", border: 0 }}>
          <button className="btn accept" disabled={busy} onClick={onSubmit}>Do work → store on Irys → submit proof <span className="k" style={{ opacity: 0.7 }}>⏎</span></button>
          <span className="signs">SIGNS submitWork() WITH PROVIDER CAW · {PROVIDER()}</span>
        </div>
      </div>
    </div>
  );
}

function ReviewScreen({ flow, busy, onSettle }: { flow: FlowState; busy: boolean; onSettle: () => void }) {
  return (
    <div className="panel">
      <div className="sc-head"><div><h3>Review &amp; settle · Job #{flow.job_id}</h3><div className="sc-sub">The evaluator judges the Irys deliverable against the spec, then the contract settles</div></div><span className="badge b-escrow"><span className="bd" />In review</span></div>
      <div className="sc-body">
        <div className="detail-amt">{flow.amount_usdc.toFixed(2)}<span className="u"> USDC</span></div>
        {flow.deliverable && (
          <div className="proof">
            <div className="ph"><span className="t">Deliverable submitted · proof on-chain</span>
              {flow.irys && <span className="when"><a className="lnk" href={irysUrl(flow.irys.id)} target="_blank" rel="noreferrer">irys · {shortHex(flow.irys.id, 8)}</a></span>}</div>
            <div className="pb">
              <div className="ic"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M14 3v5h5" /><path d="M14 3H6v18h12V8z" /></svg></div>
              <div><div className="fn">deliverable.txt</div><div className="fh">submitWork() · <a className="lnk" href={txUrl(flow.txs.submitWork)} target="_blank" rel="noreferrer">{shortHex(flow.txs.submitWork || "", 10)}</a></div></div>
              {flow.irys && <a className="view" href={irysUrl(flow.irys.id)} target="_blank" rel="noreferrer">Open</a>}
            </div>
          </div>
        )}
        <div className="timeline">
          <TStep done ti="USDC escrowed" td={<>{check}fund() · <a className="lnk" href={txUrl(flow.txs.fund)} target="_blank" rel="noreferrer">{shortHex(flow.txs.fund || "", 8)}</a></>} tt="step 2" />
          <TStep done ti="Proof submitted" td={<>{check}{flow.irys ? `Irys ${shortHex(flow.irys.id, 8)} anchored` : "submitWork"}</>} tt="step 4" />
          <TStep active ti="Evaluator decision" td="Evaluator LLM judges → contract settles (pay or reclaim)" tt="now" />
        </div>
        <p className="muted" style={{ fontSize: 13, margin: "14px 0 0" }}>
          The evaluator agent (not a human) decides — acceptance is matched to the deliverable, then{" "}
          <span className="mono">settle()</span> pays the Provider, or reclaims to the Client on reject.
        </p>
      </div>
      <div className="sc-actions">
        <button className="btn accept" disabled={busy} onClick={onSettle}>Run evaluation &amp; settle <span className="k" style={{ opacity: 0.7 }}>⏎</span></button>
        <span className="signs">SIGNS complete()/reject() WITH CLIENT CAW · {CLIENT()}</span>
      </div>
    </div>
  );
}

function ReceiptScreen({ flow }: { flow: FlowState }) {
  const payout = flow.branch === "payout";
  const settleTx = flow.txs.complete || flow.txs.reject || "";
  return (
    <div className="panel sc-body">
      <div className="rtop">
        <span className={`seal${payout ? "" : " refund"}`}>
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.4"><path d={payout ? "M5 13l4 4 10-11" : "M6 6l12 12M18 6L6 18"} strokeLinecap="round" strokeLinejoin="round" /></svg>
        </span>
        <div><h3>{payout ? "Settlement complete" : "Reclaimed to client"}</h3><div className="rsub">JOB #{flow.job_id} · ESCROW SETTLED ON-CHAIN</div></div>
        <div className="paid">{flow.amount_usdc.toFixed(2)}<span className="u"> USDC</span></div>
        <Badge state={payout ? "settled" : "reclaim"} label={payout ? "Paid to provider" : "Refunded to client"} />
        {flow.verdict && <p className="muted" style={{ fontSize: 13, maxWidth: "46ch" }}>Evaluator: {flow.verdict.reason}</p>}
      </div>
      <div className="receipt">
        <div className="rcell"><div className="rk">Outcome</div><div className="rv">{payout ? "Provider paid" : "Client refunded"}</div></div>
        <div className="rcell"><div className="rk">Amount</div><div className="rv">{flow.amount_usdc.toFixed(2)} USDC</div></div>
        <div className="rcell"><div className="rk">Provider CAW</div><div className="rv"><a href={addrUrl(CFG.providerCaw)} target="_blank" rel="noreferrer">{shortHex(CFG.providerCaw)}</a></div></div>
        <div className="rcell"><div className="rk">Deliverable · Irys</div><div className="rv">{flow.irys ? <a href={irysUrl(flow.irys.id)} target="_blank" rel="noreferrer">{shortHex(flow.irys.id, 8)}</a> : "—"}</div></div>
        <div className="rcell"><div className="rk">settle() tx</div><div className="rv">{settleTx ? <a href={txUrl(settleTx)} target="_blank" rel="noreferrer">{shortHex(settleTx, 10)}</a> : "—"}</div></div>
        <div className="rcell"><div className="rk">Final status</div><div className="rv">{flow.final_status ?? "—"}</div></div>
        <div className="rcell full"><div className="rk">Content verification</div><div className="rv">
          {flow.content_verified ? <span className="verified">{check} keccak256(Irys) == on-chain deliverableHash</span> : "—"}
        </div></div>
      </div>
      <div className="sc-actions" style={{ padding: "18px 0 0", background: "none", border: 0 }}>
        {settleTx && <a className="btn primary" href={txUrl(settleTx)} target="_blank" rel="noreferrer">View settle() on explorer</a>}
        <Link className="btn" href="/dashboard">Back to Marketplace</Link>
      </div>
      <p className="footnote">SETTLED BY CONTRACT · HELD BY NEITHER PARTY · VERIFIABLE ON-CHAIN</p>
    </div>
  );
}

function TStep({ done, active, ti, td, tt }: { done?: boolean; active?: boolean; ti: string; td: React.ReactNode; tt: string }) {
  return (
    <div className={`tstep${done ? " done" : ""}${active ? " active" : ""}`}>
      <div className="mk"><span className="o" /><span className="ln" /></div>
      <div><div className="ti">{ti}</div><div className="td">{td}</div></div>
      <div className="tt">{tt}</div>
    </div>
  );
}
