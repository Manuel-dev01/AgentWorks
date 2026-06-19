"use client";

/** The LIVE autonomous experience (the "New job" tab). Post a task → POST /trigger on the deployed agent
 *  service → the Client agent reasons + funds, Providers race to acceptJob, the winner delivers to Irys,
 *  the evaluator settles. We poll /health + /runs and render the agents' run as it lands. The service runs
 *  the orchestration + LLM reasoning in the cloud; signing is via the operator-controlled relay TSS node. */

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { CFG, addrUrl, shortHex } from "../../lib/config";
import { agentEnabled, getHealth, getRuns, trigger, type AgentHealth, type AgentRun } from "../../lib/agent";
import { RunCard } from "./RunCard";

const STEPS = ["Reason & fund", "Open + escrowed", "Sealed commit → reveal", "Deliver to Irys", "Evaluate & settle"];

/** How many of STEPS are complete, derived from the live run artifact (autonomous.py rewrites it at each
 *  milestone, so /runs reflects progress). null/early = 0 (the Client is still reasoning + funding).
 *  The accept step covers the v3 sealed race (commitAccept → revealAccept); t.acceptJob is legacy v2. */
function stepsDone(r?: AgentRun | null): number {
  if (!r) return 0;
  const t = r.txs || {};
  if (r.status === "settled" || r.branch || t.complete || t.reject) return 5;
  if (t.submitWork || r.irys) return 4;
  if (t.revealAccept || t.acceptJob || r.winner) return 3;
  if (t.fund) return 2;
  if (t.createJob || r.fund_decision) return 1;
  return 0;
}

export function LiveJob() {
  const enabled = agentEnabled();
  const [health, setHealth] = useState<AgentHealth | null>(null);
  const [runs, setRuns] = useState<AgentRun[]>([]);
  const [reachable, setReachable] = useState<boolean | null>(null);

  const [task, setTask] = useState("");
  const [criteria, setCriteria] = useState("");
  const [mode, setMode] = useState<"good" | "bad">("good");
  const [reward, setReward] = useState("5"); // string so the field can be cleared / set below 5
  const [posting, setPosting] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const baseline = useRef<Set<number> | null>(null);

  const refresh = useCallback(async () => {
    if (!enabled) return;
    const [h, rs] = await Promise.all([getHealth(), getRuns()]);
    setReachable(h !== null || rs !== null);
    if (h) setHealth(h);
    if (rs) {
      const sorted = [...rs].sort((a, b) => b.job_id - a.job_id);
      setRuns(sorted);
      if (baseline.current === null) baseline.current = new Set(sorted.map((r) => r.job_id));
    }
  }, [enabled]);

  useEffect(() => { refresh(); }, [refresh]);

  const active = health?.run.active ?? false;
  useEffect(() => {
    if (!enabled) return;
    const t = setInterval(refresh, active || posting ? 4000 : 20000);
    return () => clearInterval(t);
  }, [enabled, active, posting, refresh]);

  // when a brand-new run settles, surface it and stop the busy state
  const fresh = runs.find((r) => baseline.current && !baseline.current.has(r.job_id));
  useEffect(() => {
    if (posting && fresh && !active) {
      setMsg(`Settled live - job #${fresh.job_id} ${fresh.branch === "refund" ? "refunded to client" : "paid out to the provider"}.`);
      setPosting(false);
    }
  }, [posting, fresh, active]);

  async function onPost() {
    setErr(null); setMsg(null); setPosting(true);
    baseline.current = new Set(runs.map((r) => r.job_id));
    const r = Number(reward);
    const reward_usdc = Number.isFinite(r) && r > 0 ? r : 5; // fall back to 5 only if blank/invalid
    const res = await trigger({ task: task.trim() || undefined, criteria: criteria.trim(), mode, reward_usdc });
    if (!res.ok) { setErr(res.error ?? "trigger failed"); setPosting(false); return; }
    setMsg("Agents triggered - the Client is reasoning about funding…");
    refresh();
  }

  const recent = runs.slice(0, 4);

  return (
    <div className="panel">
      {/* status strip */}
      <div className="lj-status">
        {!enabled ? (
          <span className="off">Agent service not configured</span>
        ) : reachable === false ? (
          <span className="off">● backend asleep - it wakes on the first request (~10s)</span>
        ) : active ? (
          <span className="on"><span className="spin" />agents live{health?.run.mode ? ` · ${health.run.mode} run` : ""}</span>
        ) : (
          <span className="on">● {health?.providers ?? 0} providers ready · cloud backend live</span>
        )}
        <Link className="lj-explorer" href="/dashboard">View proof history →</Link>
      </div>

      {/* post form (brand form vocabulary) */}
      <div className="lj-form">
        <div className="field">
          <div className="lab">Task</div>
          <input className="inp big" placeholder="Leave blank to use the default task"
            value={task} onChange={(e) => setTask(e.target.value)} />
        </div>
        <div className="field">
          <div className="lab">Acceptance criteria</div>
          <textarea className="inp area" placeholder="What the evaluator agent checks for"
            value={criteria} onChange={(e) => setCriteria(e.target.value)} />
        </div>
        <div className="row2">
          <div className="field">
            <div className="lab">Provider behavior</div>
            <select className="inp" value={mode} onChange={(e) => setMode(e.target.value as "good" | "bad")}>
              <option value="good">Honest → expect payout</option>
              <option value="bad">Sabotage → expect refund</option>
            </select>
          </div>
          <div className="field">
            <div className="lab">Reward (USDC)</div>
            <div className="amtin">
              <input className="v" inputMode="decimal" value={reward}
                onChange={(e) => setReward(e.target.value.replace(/[^0-9.]/g, ""))}
                style={{ width: 90, border: 0, background: "transparent", fontFamily: "var(--mono)", fontWeight: 600, fontSize: 18, color: "var(--ink)" }} />
              <span className="u">USDC</span>
            </div>
          </div>
        </div>
        <button className="btn accent lj-go" onClick={onPost} disabled={!enabled || posting || active}>
          {posting || active ? "Agents working…" : "Post job → trigger the agents"}
        </button>
        {msg && <p className="lj-msg">{msg}</p>}
        {err && <div className="err">⚠ {err}<br />The verified runs in the Marketplace remain intact.</div>}
      </div>

      {/* live progress while a run is active - driven by the live run artifact */}
      {(active || posting) && (
        <div className="lj-steps">
          {STEPS.map((s, i) => {
            const dc = stepsDone(fresh);
            const state = i < dc ? "done" : i === dc ? "current" : "pending";
            return (
              <span key={s} className={`lj-step ${state}`}>
                <span className="n">{state === "done" ? "✓" : i + 1}</span>{s}
              </span>
            );
          })}
        </div>
      )}

      {/* the resulting / recent runs */}
      <div className="lj-section">
        <div className="lj-sh">{posting || active ? "This run" : "Recent autonomous runs"}</div>
        {recent.length === 0 ? (
          <div className="empty">No runs yet - post a job to trigger the agents.</div>
        ) : (
          <div className="lj-runs">{recent.map((r) => <RunCard key={r.job_id} r={r} href={`/dashboard/jobs/${r.job_id}`} />)}</div>
        )}
      </div>

      {/* participants - the scoped-authority boundary */}
      {health?.participants?.length ? (
        <div className="lj-section">
          <div className="lj-sh">Participants · each bound by a scoped Pact in its Cobo Agentic Wallet</div>
          <div className="lj-parts">
            {health.participants.map((p) => (
              <a key={p.address} href={addrUrl(p.address)} target="_blank" rel="noreferrer" className="lj-part">
                <span className={`lj-role ${p.role}`}>{p.role}</span>
                <span className="lj-pn">{p.name}</span>
                <span className="lj-pa">{shortHex(p.address)}</span>
              </a>
            ))}
          </div>
          <p className="lj-note">
            The provider Pact omits USDC entirely - a provider can accept and deliver but can never move escrowed
            funds; only the escrow contract settles. Authority is the Pact, not the code.
          </p>
        </div>
      ) : null}

      <div className="stat">
        <div className="s"><div className="k">Escrow v2</div><div className="v"><a href={addrUrl(CFG.escrowV2)} target="_blank" rel="noreferrer">{shortHex(CFG.escrowV2)} ↗</a></div></div>
        <div className="s" style={{ marginLeft: "auto", textAlign: "right" }}>
          <div className="k">Settles on</div><div className="v">Ethereum Sepolia</div>
        </div>
      </div>
    </div>
  );
}
