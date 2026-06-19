/** Read-only on-chain enrichment via viem (server-side). Additive: every call is wrapped so a
 *  flaky RPC degrades gracefully to the proof snapshots - the dashboard never goes blank. */

import { createPublicClient, http, formatUnits } from "viem";
import { sepolia } from "viem/chains";
import { CFG } from "./config";
import { escrowAbi, erc20Abi, STATUS_LABELS, STATUS_LABELS_V2, ESCROW_V3_FROM_BLOCK } from "./abi";

const client = createPublicClient({
  chain: sepolia,
  transport: http(CFG.rpc, { timeout: 6000 }),
});

async function safe<T>(p: Promise<T>): Promise<T | null> {
  try {
    return await p;
  } catch {
    return null;
  }
}

/** USDC (6-decimal MockUSDC) balance as a display number, or null if unreachable. */
export async function usdcBalance(address: `0x${string}`): Promise<number | null> {
  const raw = await safe(
    client.readContract({ address: CFG.usdc, abi: erc20Abi, functionName: "balanceOf", args: [address] }),
  );
  return raw === null ? null : Number(formatUnits(raw as bigint, 6));
}

export interface LiveJob {
  amountUsdc: number;
  statusLabel: string;
  irysId: string;
}

/** Live getJob() for a job id, or null if unreachable / not found. */
export async function liveJob(jobId: number): Promise<LiveJob | null> {
  const j = await safe(
    client.readContract({ address: CFG.escrow, abi: escrowAbi, functionName: "getJob", args: [BigInt(jobId)] }),
  );
  if (!j) return null;
  const job = j as { amount: bigint; irysId: string; status: number };
  return {
    amountUsdc: Number(formatUnits(job.amount, 6)),
    statusLabel: STATUS_LABELS[job.status] ?? "Unknown",
    irysId: job.irysId,
  };
}

/** Current job counter (first id is 1), or null if unreachable. */
export async function nextJobId(): Promise<number | null> {
  const n = await safe(client.readContract({ address: CFG.escrow, abi: escrowAbi, functionName: "nextJobId" }));
  return n === null ? null : Number(n as bigint);
}

import type { BadgeState } from "../components/Badge";
// Solidity Status enum index → lifecycle badge.
const STATUS_BADGE: BadgeState[] = ["open", "open", "escrow", "work", "settled", "reclaim", "reclaim"];

export interface ChainJob {
  jobId: number;
  amountUsdc: number;
  statusLabel: string;
  badge: BadgeState;
  irysId: string;
  client: string;
  provider: string;
}

/** Every job currently on-chain (newest first), so the Marketplace reflects live escrow state.
 *  Returns null if the RPC is unreachable (caller falls back to the artifact snapshot). */
export async function listJobs(max = 40): Promise<ChainJob[] | null> {
  const n = await nextJobId();
  if (n === null) return null;
  const ids: number[] = [];
  for (let i = Math.max(1, n - max); i < n; i++) ids.push(i);
  const rows = await Promise.all(
    ids.map(async (id) => {
      const j = await safe(
        client.readContract({ address: CFG.escrow, abi: escrowAbi, functionName: "getJob", args: [BigInt(id)] }),
      );
      if (!j) return null;
      const job = j as { client: string; provider: string; amount: bigint; irysId: string; status: number };
      return {
        jobId: id,
        amountUsdc: Number(formatUnits(job.amount, 6)),
        statusLabel: STATUS_LABELS[job.status] ?? "Unknown",
        badge: STATUS_BADGE[job.status] ?? "open",
        irysId: job.irysId,
        client: job.client,
        provider: job.provider,
      } as ChainJob;
    }),
  );
  return rows.filter((r): r is ChainJob => r !== null).reverse();
}

// ── open marketplace (the LIVE v3 commit-reveal escrow) ──
// The Job tuple + Status enum are identical to v2, so these readers keep the V2 names/shape but now
// target the v3 escrow (CFG.escrowV3). The only lifecycle difference is the accept path (commit→reveal),
// which produces the same JobAccepted event + Accepted status the badge already maps.
// Status enum index → badge: None, Open, Funded, Accepted, Submitted, Completed, Rejected, Refunded.
const STATUS_BADGE_V2: BadgeState[] = ["open", "open", "escrow", "work", "work", "settled", "reclaim", "reclaim"];

/** Current marketplace (v3) job counter, or null if unreachable. */
export async function nextJobIdV2(): Promise<number | null> {
  const n = await safe(client.readContract({ address: CFG.escrowV3, abi: escrowAbi, functionName: "nextJobId" }));
  return n === null ? null : Number(n as bigint);
}

export interface LiveJobV2 {
  amountUsdc: number;
  statusLabel: string;
  irysId: string;
  client: string;
  provider: string;
}

export interface SettlementV2 {
  outcome: "payout" | "refund";
  txHash: `0x${string}`;
}

/** Recover a job's settlement (which tx settled it + the outcome) from chain events, for jobs that have no
 *  run artifact. Best-effort: returns null if unreachable, unsupported, or unsettled. */
export async function settlementV2(jobId: number): Promise<SettlementV2 | null> {
  const scan = (eventName: "JobCompleted" | "JobRejected" | "RefundClaimed") =>
    safe(
      client.getContractEvents({
        address: CFG.escrowV3,
        abi: escrowAbi,
        eventName,
        args: { jobId: BigInt(jobId) },
        fromBlock: ESCROW_V3_FROM_BLOCK,
        toBlock: "latest",
      }),
    );
  const [completed, rejected, refunded] = await Promise.all([scan("JobCompleted"), scan("JobRejected"), scan("RefundClaimed")]);
  const hit = completed?.[0]
    ? { outcome: "payout" as const, log: completed[0] }
    : rejected?.[0]
      ? { outcome: "refund" as const, log: rejected[0] }
      : refunded?.[0]
        ? { outcome: "refund" as const, log: refunded[0] }
        : null;
  if (!hit?.log?.transactionHash) return null;
  return { outcome: hit.outcome, txHash: hit.log.transactionHash };
}

/** Live getJob() on the marketplace (v3) escrow, or null if unreachable / not found. */
export async function liveJobV2(jobId: number): Promise<LiveJobV2 | null> {
  const j = await safe(
    client.readContract({ address: CFG.escrowV3, abi: escrowAbi, functionName: "getJob", args: [BigInt(jobId)] }),
  );
  if (!j) return null;
  const job = j as { client: string; provider: string; amount: bigint; irysId: string; status: number };
  return {
    amountUsdc: Number(formatUnits(job.amount, 6)),
    statusLabel: STATUS_LABELS_V2[job.status] ?? "Unknown",
    irysId: job.irysId,
    client: job.client,
    provider: job.provider,
  };
}

/** Every job on the marketplace (v3) escrow (newest first). The Job tuple is identical to v1/v2, so
 *  the same ABI reads it; only the status enum (8 states) differs. Null if the RPC is unreachable. */
export async function listJobsV2(max = 40): Promise<ChainJob[] | null> {
  const n = await nextJobIdV2();
  if (n === null) return null;
  const ids: number[] = [];
  for (let i = Math.max(1, n - max); i < n; i++) ids.push(i);
  const rows = await Promise.all(
    ids.map(async (id) => {
      const j = await safe(
        client.readContract({ address: CFG.escrowV3, abi: escrowAbi, functionName: "getJob", args: [BigInt(id)] }),
      );
      if (!j) return null;
      const job = j as { client: string; provider: string; amount: bigint; irysId: string; status: number };
      return {
        jobId: id,
        amountUsdc: Number(formatUnits(job.amount, 6)),
        statusLabel: STATUS_LABELS_V2[job.status] ?? "Unknown",
        badge: STATUS_BADGE_V2[job.status] ?? "open",
        irysId: job.irysId,
        client: job.client,
        provider: job.provider,
      } as ChainJob;
    }),
  );
  return rows.filter((r): r is ChainJob => r !== null).reverse();
}
