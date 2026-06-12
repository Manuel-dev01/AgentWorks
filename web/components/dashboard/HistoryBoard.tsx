"use client";

/** The Marketplace tab, reframed as read-only PROOF HISTORY: every settled escrow on v2, newest first.
 *  Server seeds the verified autonomous runs (3/5/6) + any on-chain-only jobs; the client merges live
 *  backend /runs so cloud-triggered runs (#7/#8…) appear too. Each card opens its full on-chain receipt. */

import { useCallback, useEffect, useMemo, useState } from "react";
import { getRuns, type AgentRun } from "../../lib/agent";
import { RunCard, runBadge } from "./RunCard";
import { CFG, addrUrl, shortHex } from "../../lib/config";

type Filter = "all" | "settled" | "reclaim" | "work";
const FILTERS: { key: Filter; label: string; dot?: string }[] = [
  { key: "all", label: "All" },
  { key: "settled", label: "Paid out", dot: "var(--settled)" },
  { key: "reclaim", label: "Refunded", dot: "var(--reclaim)" },
  { key: "work", label: "In-flight / open", dot: "var(--work)" },
];

export function HistoryBoard({ seed }: { seed: AgentRun[] }) {
  const [runs, setRuns] = useState<AgentRun[]>(seed);
  const [live, setLive] = useState(false);
  const [f, setF] = useState<Filter>("all");

  const refresh = useCallback(async () => {
    const rs = await getRuns();
    if (!rs) return;
    setLive(true);
    const byId = new Map<number, AgentRun>();
    for (const r of seed) byId.set(r.job_id, r);
    for (const r of rs) byId.set(r.job_id, r); // live wins
    setRuns([...byId.values()].sort((a, b) => b.job_id - a.job_id));
  }, [seed]);

  useEffect(() => { refresh(); }, [refresh]);

  const shown = useMemo(() => {
    if (f === "all") return runs;
    if (f === "work") return runs.filter((r) => !["settled", "reclaim"].includes(runBadge(r).state));
    return runs.filter((r) => runBadge(r).state === f);
  }, [runs, f]);

  const paidOut = runs.filter((r) => runBadge(r).state === "settled").length;
  const refunded = runs.filter((r) => runBadge(r).state === "reclaim").length;
  const rate = paidOut + refunded > 0 ? Math.round((paidOut / (paidOut + refunded)) * 100) : 100;

  return (
    <div className="panel">
      <div className="toolbar">
        {FILTERS.map((x) => (
          <button key={x.key} className={`filter${f === x.key ? " on" : ""}`} onClick={() => setF(x.key)}>
            {x.dot && <span className="d" style={{ background: x.dot }} />}{x.label}
          </button>
        ))}
        <span className="count">
          {live ? <span style={{ color: "var(--settle-deep)" }}>● live</span> : "snapshot"} · {runs.length} runs
        </span>
      </div>

      {shown.length === 0 ? (
        <div className="empty">No runs in this state.</div>
      ) : (
        <div className="lj-runs" style={{ padding: 18 }}>
          {shown.map((r) => <RunCard key={r.job_id} r={r} href={`/dashboard/jobs/${r.job_id}`} />)}
        </div>
      )}

      <div className="stat">
        <div className="s"><div className="k">Settled runs</div><div className="v">{runs.length}</div></div>
        <div className="s"><div className="k">Paid out</div><div className="v" style={{ color: "var(--settled)" }}>{paidOut}</div></div>
        <div className="s"><div className="k">Refunded</div><div className="v" style={{ color: "var(--reclaim)" }}>{refunded}</div></div>
        <div className="s"><div className="k">Settlement rate</div><div className="v" style={{ color: "var(--settled)" }}>{rate}%</div></div>
        <div className="s" style={{ marginLeft: "auto", textAlign: "right" }}>
          <div className="k">Escrow v2</div>
          <div className="v"><a href={addrUrl(CFG.escrowV2)} target="_blank" rel="noreferrer">{shortHex(CFG.escrowV2)} ↗</a></div>
        </div>
      </div>
    </div>
  );
}
