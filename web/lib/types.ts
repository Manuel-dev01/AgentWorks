/** Dashboard view-model types. Pure types (no node deps) so both server loaders and
 *  client components can import them safely. */
import type { BadgeState } from "../components/Badge";

export interface JobVM {
  jobId: number;
  source: string;
  phase: string;
  title: string;
  amountUsdc: number;
  badge: BadgeState;
  statusLabel: string;
  branch: "payout" | "refund" | null;
  txs: Record<string, string>;
  irys: { id: string; url: string; bytes?: number } | null;
  deliverable: string | null;
  reasoning: { client_fund?: { fund: boolean; reason: string }; evaluate?: { accept: boolean; reason: string } };
  contentVerified: boolean | null;
}

export interface DenialVM {
  code: string;
  statusCode: number;
  type: string;
  reason: string;
  detail: string;
}
export interface AuditEntry {
  action: string;
  result: string;
  createdAt?: string;
}
export interface Beats {
  denials: DenialVM[];
  auditDenied: AuditEntry[];
  freeze: { pactId: string; allowedTx: string; afterFreezeDenied: boolean; recentDenied: AuditEntry[] } | null;
  review: { pendingId: string; approvalId: string; effect: string; status: string; txHash: string } | null;
}
export interface PactVM {
  name: string;
  json: string;
}
export interface Balances {
  client: number | null;
  provider: number | null;
}

/** A row on the Marketplace board — live on-chain state joined with artifact/flow detail. */
export interface BoardJob {
  jobId: number;
  title: string;
  amountUsdc: number;
  badge: BadgeState;
  statusLabel: string;
  branch: "payout" | "refund" | null;
  phase: string;
  live: boolean; // true when the row reflects a live on-chain read
}
