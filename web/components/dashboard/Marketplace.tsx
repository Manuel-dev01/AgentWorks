"use client";

import { useState } from "react";
import Link from "next/link";
import type { JobVM } from "../../lib/types";
import type { BadgeState } from "../Badge";
import { Badge } from "../Badge";

const PROG: Record<BadgeState, { w: string; c: string }> = {
  open: { w: "15%", c: "var(--ink-3)" },
  escrow: { w: "40%", c: "var(--escrow)" },
  work: { w: "68%", c: "var(--work)" },
  settled: { w: "100%", c: "var(--settled)" },
  reclaim: { w: "100%", c: "var(--reclaim)" },
};

const FILTERS: { key: BadgeState | "all"; label: string; dot?: string }[] = [
  { key: "all", label: "All" },
  { key: "escrow", label: "Escrowed", dot: "var(--escrow)" },
  { key: "work", label: "In progress", dot: "var(--work)" },
  { key: "settled", label: "Settled", dot: "var(--settled)" },
  { key: "reclaim", label: "Reclaimed", dot: "var(--reclaim)" },
];

export function Marketplace({ jobs }: { jobs: (JobVM & { idx: number })[] }) {
  const [f, setF] = useState<BadgeState | "all">("all");
  const shown = f === "all" ? jobs : jobs.filter((j) => j.badge === f);

  const sum = (pred: (j: JobVM) => boolean) => jobs.filter(pred).reduce((a, j) => a + j.amountUsdc, 0);
  const inEscrow = sum((j) => j.badge === "escrow" || j.badge === "work" || j.badge === "open");
  const settledAmt = sum((j) => j.badge === "settled");
  const reclaimedAmt = sum((j) => j.badge === "reclaim");
  const settledN = jobs.filter((j) => j.badge === "settled").length;
  const reclaimN = jobs.filter((j) => j.badge === "reclaim").length;
  const rate = settledN + reclaimN > 0 ? Math.round((settledN / (settledN + reclaimN)) * 100) : 100;

  return (
    <div className="panel">
      <div className="toolbar">
        {FILTERS.map((x) => (
          <button key={x.key} className={`filter${f === x.key ? " on" : ""}`} onClick={() => setF(x.key)}>
            {x.dot && <span className="d" style={{ background: x.dot }} />}
            {x.label}
          </button>
        ))}
        <span className="count">
          {jobs.length} jobs · {inEscrow.toFixed(2)} USDC in escrow
        </span>
        <Link className="new" href="/dashboard/new">+ Post job</Link>
      </div>

      {shown.length === 0 ? (
        <div className="empty">No jobs in this state.</div>
      ) : (
        <div className="joblist">
          {shown.map((j) => (
            <Link key={j.idx} className="job" href={`/dashboard/jobs/${j.idx}`}>
              <div>
                <div className="jt">{j.title.length > 60 ? j.title.slice(0, 60) + "…" : j.title}</div>
                <div className="jm">
                  JOB #{j.jobId} · {j.phase}
                  {j.branch ? ` · ${j.branch.toUpperCase()}` : ""}
                </div>
              </div>
              <div>
                <div className="amt">{j.amountUsdc.toFixed(2)}<span className="u"> USDC</span></div>
                <div className="bwrap"><Badge state={j.badge} label={j.statusLabel} /></div>
              </div>
              <div className="prog"><i style={{ width: PROG[j.badge].w, background: PROG[j.badge].c }} /></div>
            </Link>
          ))}
        </div>
      )}

      <div className="stat">
        <div className="s"><div className="k">In escrow</div><div className="v">{inEscrow.toFixed(2)} USDC</div></div>
        <div className="s"><div className="k">Settled</div><div className="v">{settledAmt.toFixed(2)} USDC</div></div>
        <div className="s"><div className="k">Reclaimed</div><div className="v">{reclaimedAmt.toFixed(2)} USDC</div></div>
        <div className="s" style={{ marginLeft: "auto", textAlign: "right" }}>
          <div className="k">Settlement rate</div><div className="v" style={{ color: "var(--settled)" }}>{rate}%</div>
        </div>
      </div>
    </div>
  );
}
