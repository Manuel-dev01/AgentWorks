/** Client-side helper + type for the live per-step flow (POST /api/flow). Mirrors agents/flow.py state. */

export interface FlowState {
  run_id: string;
  mode: string;
  status: string; // started | declined | posted | accepted | submitted | settled
  task: string;
  amount_usdc: number;
  client: string;
  provider: string;
  txs: Record<string, string>;
  irys: { id: string; url: string; bytes?: number } | null;
  deliverable: string | null;
  verdict: { accept: boolean; reason: string } | null;
  branch: "payout" | "refund" | null;
  client_pact_id?: string | null;
  provider_pact_id?: string | null;
  fund_decision?: { fund: boolean; reason: string };
  job_id?: number;
  final_status?: string;
  content_verified?: boolean;
  error?: string;
}

export async function runStep(
  step: "start" | "post" | "accept" | "submit" | "settle",
  opts: { runId?: string; mode?: "good" | "bad" } = {},
): Promise<FlowState> {
  const res = await fetch("/api/flow", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ step, runId: opts.runId, mode: opts.mode }),
  });
  const data = await res.json();
  if (!res.ok && !data?.error) throw new Error(`flow ${step} failed (${res.status})`);
  return data as FlowState;
}
