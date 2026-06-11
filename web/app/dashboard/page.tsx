import { loadJobs } from "../../lib/proofs";
import { listJobs } from "../../lib/chain";
import { Marketplace } from "../../components/dashboard/Marketplace";
import type { BoardJob, JobVM } from "../../lib/types";

export const dynamic = "force-dynamic";

export default async function MarketplacePage() {
  const artifacts = loadJobs();
  const byId = new Map<number, JobVM>();
  for (const j of artifacts) if (!byId.has(j.jobId)) byId.set(j.jobId, j);

  // Live on-chain state is the source of truth for the board so every escrow appears; we join the
  // artifact/flow record by job id for the human title + branch. Falls back to artifacts if RPC is down.
  const chain = await listJobs();
  let board: BoardJob[];
  if (chain && chain.length) {
    board = chain.map((cj) => {
      const a = byId.get(cj.jobId);
      return {
        jobId: cj.jobId,
        title: a?.title ?? `Escrow job #${cj.jobId}`,
        amountUsdc: cj.amountUsdc || a?.amountUsdc || 0,
        badge: cj.badge,
        statusLabel: cj.statusLabel,
        branch: a?.branch ?? null,
        phase: a?.phase ?? "On-chain",
        live: true,
      };
    });
  } else {
    board = artifacts.map((a) => ({
      jobId: a.jobId, title: a.title, amountUsdc: a.amountUsdc, badge: a.badge,
      statusLabel: a.statusLabel, branch: a.branch, phase: a.phase, live: false,
    }));
  }

  return (
    <>
      <div className="head">
        <h1>Marketplace</h1>
        <p>
          Every escrow on the contract, lifecycle-colored so the whole board reads at a glance — read live from
          Ethereum Sepolia, so jobs you post in the live journey appear here. Open one for its full on-chain proof
          trail, or post a new job to drive the flow yourself.
        </p>
      </div>
      <Marketplace jobs={board} live={!!(chain && chain.length)} />
    </>
  );
}
