import { loadJobs } from "../../lib/proofs";
import { liveJob } from "../../lib/chain";
import { Marketplace } from "../../components/dashboard/Marketplace";
import type { JobVM } from "../../lib/types";

export const dynamic = "force-dynamic";

export default async function MarketplacePage() {
  const jobs = loadJobs();
  // additive live enrichment (amount/status); falls back to the proof snapshot on RPC failure
  const live = await Promise.all(jobs.map((j) => liveJob(j.jobId)));
  const enriched: (JobVM & { idx: number })[] = jobs.map((j, i) => ({
    ...j,
    amountUsdc: live[i]?.amountUsdc || j.amountUsdc,
    idx: i,
  }));

  return (
    <>
      <div className="head">
        <h1>Marketplace</h1>
        <p>
          Every escrow carries its lifecycle color, so the whole portfolio reads at a glance. Each job ran
          end-to-end on Ethereum Sepolia through two Cobo Agentic Wallets — open one for the full proof trail,
          or post a new job to drive the live flow yourself.
        </p>
      </div>
      <Marketplace jobs={enriched} />
    </>
  );
}
