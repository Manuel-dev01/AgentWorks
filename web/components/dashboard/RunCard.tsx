/** A single autonomous run, rendered as a ledger receipt: the agents' decisions (fund → accept-race →
 *  verdict) and the on-chain trail (createJob → … → settle) + the Irys deliverable. Shared by the live
 *  "New job" tab and the read-only "Marketplace" history. Pure presentational - data is an AgentRun. */

import Link from "next/link";
import { Badge, type BadgeState } from "../Badge";
import { txUrl, irysUrl } from "../../lib/config";
import type { AgentRun } from "../../lib/agent";

const TX_ORDER = ["createJob", "approve", "fund", "acceptJob", "submitWork", "complete", "reject"];

// LLM-generated run text (task / reasons) can contain em/en-dashes; normalize to hyphens for display.
const clean = (s?: string | null) => (s ? s.replace(/[—–]/g, "-") : s);

// v2 on-chain status label → lifecycle badge (for chain-only jobs with no run artifact).
const CHAIN_BADGE: Record<string, { state: BadgeState; label: string }> = {
  Completed: { state: "settled", label: "Paid out" },
  Rejected: { state: "reclaim", label: "Refunded" },
  Refunded: { state: "reclaim", label: "Refunded" },
  Submitted: { state: "work", label: "Submitted" },
  Accepted: { state: "work", label: "Accepted" },
  Funded: { state: "escrow", label: "Funded" },
  Open: { state: "open", label: "Open" },
};

export function runBadge(r: AgentRun): { state: BadgeState; label: string } {
  if (r.final_status === "Completed" || r.branch === "payout") return { state: "settled", label: "Paid out" };
  if (r.final_status === "Rejected" || r.branch === "refund") return { state: "reclaim", label: "Refunded" };
  if (r.txs?.submitWork) return { state: "work", label: "Submitted" };
  if (r.txs?.acceptJob) return { state: "work", label: "Accepted" };
  if (r.txs?.fund) return { state: "escrow", label: "Funded" };
  // no txs (chain-only row) - fall back to the on-chain status label if present
  if (r.final_status && CHAIN_BADGE[r.final_status]) return CHAIN_BADGE[r.final_status];
  return { state: "open", label: "Open" };
}

export function RunCard({ r, href }: { r: AgentRun; href?: string }) {
  const b = runBadge(r);
  const accepts = Object.entries(r.accept_decisions || {});
  const raced = accepts.length > 1;
  const txs = TX_ORDER.filter((k) => r.txs?.[k]).map((k) => [k, r.txs[k]] as const);

  const head = (
    <div className="rc-h">
      <div className="rc-ttl">
        <h3>{clean(r.task) ?? `Escrow job #${r.job_id}`}</h3>
        <div className="rc-m">
          JOB #{r.job_id} · {(r.amount_usdc ?? 5).toFixed(2)} USDC
          {r.winner ? ` · provider ${r.winner}` : ""}
          {r.content_verified ? " · content_verified ✓" : ""}
        </div>
      </div>
      <Badge state={b.state} label={b.label} />
    </div>
  );

  return (
    <div className="rc">
      {href ? <Link href={href} className="rc-link">{head}</Link> : head}

      <div className="rc-dec">
        {r.fund_decision && (
          <Decision who="Client · fund" yes={r.fund_decision.fund} y="FUND" n="SKIP" reason={clean(r.fund_decision.reason)!} />
        )}
        {accepts.map(([who, d]) => (
          <Decision
            key={who}
            who={`${who} · accept`}
            yes={d.accept}
            y="ACCEPT"
            n="PASS"
            reason={
              (raced ? (who === r.winner ? "won the on-chain race · " : "lost the race (acceptJob reverted) · ") : "") +
              clean(d.reason)
            }
          />
        ))}
        {r.verdict && (
          <Decision who="Evaluator" yes={r.verdict.accept} y="ACCEPT" n="REJECT" reason={clean(r.verdict.reason)!} />
        )}
      </div>

      <div className="rc-tx">
        {txs.map(([k, h]) => (
          <a key={k} href={txUrl(h)} target="_blank" rel="noreferrer" className="rc-chip" title={h}>
            {k} ↗
          </a>
        ))}
        {r.irys && (
          <a href={irysUrl(r.irys.id)} target="_blank" rel="noreferrer" className="rc-chip irys" title={r.irys.id}>
            Irys deliverable ↗
          </a>
        )}
      </div>
    </div>
  );
}

function Decision({ who, yes, y, n, reason }: { who: string; yes: boolean; y: string; n: string; reason: string }) {
  return (
    <div className="rc-d">
      <span className="rc-who">{who}</span>
      <span className={`rc-v ${yes ? "y" : "n"}`}>{yes ? y : n}</span>
      <span className="rc-rz">{reason}</span>
    </div>
  );
}
