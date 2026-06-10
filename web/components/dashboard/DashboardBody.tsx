"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import type { JobVM, Balances } from "../../lib/types";
import { Badge } from "../Badge";
import { txUrl, addrUrl, irysUrl, shortHex, CFG } from "../../lib/config";

const STEP_DEFS: { key: string; ti: string; term?: "payout" | "reject" }[] = [
  { key: "createJob", ti: "Job created" },
  { key: "approve", ti: "USDC approved" },
  { key: "fund", ti: "USDC escrowed" },
  { key: "submitWork", ti: "Work submitted + Irys id" },
  { key: "complete", ti: "Accepted → Provider paid", term: "payout" },
  { key: "reject", ti: "Rejected → Client refunded", term: "reject" },
];

export function DashboardBody({
  jobs,
  balances,
  enableLiveRun,
}: {
  jobs: JobVM[];
  balances: Balances;
  enableLiveRun: boolean;
}) {
  const router = useRouter();
  const [selId, setSelId] = useState<string>(jobs[0] ? key(jobs[0]) : "");
  const [running, setRunning] = useState(false);
  const [log, setLog] = useState<string>("");

  const sel = jobs.find((j) => key(j) === selId) ?? jobs[0];

  async function runLive(mode: "good" | "bad") {
    if (running) return;
    setRunning(true);
    setLog(`$ python agents/scripts/phase5_demo.py ${mode}\n`);
    try {
      const res = await fetch("/api/run", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ mode }),
      });
      if (!res.ok || !res.body) {
        const t = await res.text().catch(() => "");
        setLog((l) => l + `\n[error] run not available (${res.status}). ${t}\nVerified artifacts below remain the source of truth.`);
        setRunning(false);
        return;
      }
      const reader = res.body.getReader();
      const dec = new TextDecoder();
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        setLog((l) => l + dec.decode(value, { stream: true }));
      }
      setLog((l) => l + "\n[done] refreshing from the new proof artifact…");
      router.refresh();
    } catch (e) {
      setLog((l) => l + `\n[error] ${String(e)}\nVerified artifacts below remain the source of truth.`);
    } finally {
      setRunning(false);
    }
  }

  return (
    <>
      {/* live-run trigger (additive; artifacts stay the source of truth) */}
      {enableLiveRun && (
        <>
          <div className="runbar">
            <span className="lbl">Run a live lifecycle</span>
            <button className="btn accent" disabled={running} onClick={() => runLive("good")}>
              {running ? "Running…" : "Run · payout"} <span className="arr">→</span>
            </button>
            <button className="btn" disabled={running} onClick={() => runLive("bad")}>
              Run · refund
            </button>
            <span className="grow" />
            <span className="lbl">drives the real Python agents on Ethereum Sepolia</span>
          </div>
          {log && <pre className="runlog">{log}</pre>}
        </>
      )}

      {/* jobs board + escrow detail */}
      <div className="grid2">
        <div className="panelcard joblist">
          {jobs.map((j) => (
            <button key={key(j)} className={`job${key(j) === selId ? " sel" : ""}`} onClick={() => setSelId(key(j))}>
              <div>
                <div className="jt">{j.title.length > 64 ? j.title.slice(0, 64) + "…" : j.title}</div>
                <div className="jm">
                  JOB #{j.jobId} · {j.phase}
                  {j.branch ? ` · ${j.branch.toUpperCase()}` : ""}
                </div>
              </div>
              <div>
                <div className="amt">
                  {j.amountUsdc.toFixed(2)}
                  <span className="u"> USDC</span>
                </div>
                <div className="bwrap">
                  <Badge state={j.badge} label={j.statusLabel} />
                </div>
              </div>
            </button>
          ))}
        </div>

        {sel && (
          <div className="panelcard detail">
            <div className="dh">
              <div>
                <h3>Escrow · Job #{sel.jobId}</h3>
                <div className="dsub">{sel.title}</div>
              </div>
              <Badge state={sel.badge} label={sel.statusLabel} />
            </div>

            {/* two agents + scoped pacts */}
            <div className="agents">
              <div className="agent">
                <div className="role">Client · A</div>
                <div className="addr">
                  <span style={{ width: 7, height: 7, borderRadius: "50%", background: "var(--ink)" }} />
                  <a href={addrUrl(CFG.clientCaw)} target="_blank" rel="noreferrer">{shortHex(CFG.clientCaw)}</a>
                </div>
                <div className="pact">Pact · escrow + USDC allowlist</div>
              </div>
              <div className="link" />
              <div className="agent">
                <div className="role">Provider · W</div>
                <div className="addr">
                  <span style={{ width: 7, height: 7, borderRadius: "50%", background: "var(--ink)" }} />
                  <a href={addrUrl(CFG.providerCaw)} target="_blank" rel="noreferrer">{shortHex(CFG.providerCaw)}</a>
                </div>
                <div className="pact">Pact · escrow allowlist</div>
              </div>
            </div>

            {/* lifecycle timeline — each step links to its real tx on Etherscan */}
            <div className="timeline">
              {STEP_DEFS.filter((s) => sel.txs[s.key]).map((s, i, arr) => (
                <div key={s.key} className={`tstep done${s.term === "reject" ? " term-reject" : ""}`}>
                  <div className="mk">
                    <span className="o" />
                    {i < arr.length - 1 && <span className="ln" />}
                  </div>
                  <div>
                    <div className="ti">{s.ti}</div>
                    <div className="tx">
                      <a href={txUrl(sel.txs[s.key])} target="_blank" rel="noreferrer">
                        {shortHex(sel.txs[s.key], 10)}
                      </a>
                      <span className="muted"> · {s.key}()</span>
                    </div>
                  </div>
                  <div className="tx muted" />
                </div>
              ))}
            </div>

            {/* genuine LLM reasoning at the decision points */}
            {(sel.reasoning.client_fund || sel.reasoning.evaluate) && (
              <div className="reason">
                {sel.reasoning.client_fund && (
                  <div className="rcard">
                    <div className="rk">Client · fund decision (LLM)</div>
                    <div className={`verdict ${sel.reasoning.client_fund.fund ? "y" : "n"}`}>
                      {sel.reasoning.client_fund.fund ? "FUND ✓" : "DECLINE ✕"}
                    </div>
                    <div className="why">{sel.reasoning.client_fund.reason}</div>
                  </div>
                )}
                {sel.reasoning.evaluate && (
                  <div className="rcard">
                    <div className="rk">Evaluator · verdict (LLM)</div>
                    <div className={`verdict ${sel.reasoning.evaluate.accept ? "y" : "n"}`}>
                      {sel.reasoning.evaluate.accept ? "ACCEPT ✓ → payout" : "REJECT ✕ → refund"}
                    </div>
                    <div className="why">{sel.reasoning.evaluate.reason}</div>
                  </div>
                )}
              </div>
            )}

            {/* Irys deliverable + on-chain content-hash verification */}
            {(sel.irys || sel.deliverable) && (
              <div className="proofbox">
                {sel.irys && (
                  <div className="prow">
                    <span className="pk">Deliverable · Irys</span>
                    <a href={irysUrl(sel.irys.id)} target="_blank" rel="noreferrer">
                      {sel.irys.id}
                    </a>
                    {sel.contentVerified && (
                      <span className="verified">
                        <svg width="12" height="12" viewBox="0 0 12 12">
                          <path d="M3 6.5l2 2 4-5" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
                        </svg>
                        keccak256(Irys) == on-chain hash
                      </span>
                    )}
                  </div>
                )}
                {sel.deliverable && <div className="deliverable">{sel.deliverable}</div>}
              </div>
            )}

            {/* settlement receipt for terminal jobs */}
            {(sel.badge === "settled" || sel.badge === "reclaim") && (
              <div className="receipt" style={{ marginTop: 18 }}>
                <RCell k="Outcome" v={sel.branch === "payout" ? "Provider paid" : "Client refunded"} />
                <RCell k="Amount" v={`${sel.amountUsdc.toFixed(2)} USDC`} />
                <RCell k="Final status" v={sel.statusLabel} />
                <RCell
                  k="Settle tx"
                  v={sel.txs.complete || sel.txs.reject ? shortHex(sel.txs.complete || sel.txs.reject, 10) : "—"}
                  href={sel.txs.complete || sel.txs.reject ? txUrl(sel.txs.complete || sel.txs.reject) : undefined}
                />
                <RCell k="Provider CAW" v={shortHex(CFG.providerCaw)} href={addrUrl(CFG.providerCaw)} />
                <RCell k="Deliverable" v={sel.irys ? shortHex(sel.irys.id, 8) : "—"} href={sel.irys ? irysUrl(sel.irys.id) : undefined} />
              </div>
            )}
          </div>
        )}
      </div>

      {balances && (balances.client !== null || balances.provider !== null) && (
        <p className="mono" style={{ fontSize: 11, color: "var(--ink-3)", marginTop: 16, letterSpacing: "0.04em" }}>
          Live MockUSDC balances · Client {fmt(balances.client)} · Provider {fmt(balances.provider)} (read from chain)
        </p>
      )}
    </>
  );
}

function RCell({ k, v, href }: { k: string; v: string; href?: string }) {
  return (
    <div className="rcell">
      <div className="rk2">{k}</div>
      <div className="rv2">{href ? <a href={href} target="_blank" rel="noreferrer">{v}</a> : v}</div>
    </div>
  );
}

const fmt = (n: number | null) => (n === null ? "—" : `${n.toFixed(2)} USDC`);
const key = (j: JobVM) => `${j.source}#${j.jobId}`;
