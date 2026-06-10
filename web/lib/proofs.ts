/** Server-only loader for the VERIFIED proof artifacts (the dashboard's source of truth).
 *  Reads the committed JSON the agent runs wrote in Phase 3–5 + the literal Pact policies.
 *  Uses node:fs, so it must only be imported from server components / route handlers. */

import { readFileSync, existsSync } from "node:fs";
import path from "node:path";
import type { BadgeState } from "../components/Badge";
import type { JobVM, Beats, DenialVM, AuditEntry, PactVM } from "./types";

export type { JobVM, Beats, DenialVM, AuditEntry, PactVM } from "./types";

// Source resolution: prefer the committed/snapshotted web/data (works inside a Vercel serverless
// bundle, where sibling dirs aren't traced); fall back to the sibling repo dirs for local dev even
// without a snapshot. cwd is the /web dir under `next dev`/`next build`.
const WEB = process.cwd();
const REPO_ROOT = path.resolve(WEB, "..");
const DATA = path.join(WEB, "data");

const resolveDir = (snapshot: string, sibling: string) => (existsSync(snapshot) ? snapshot : sibling);
const SCRIPTS = resolveDir(path.join(DATA, "proofs"), path.join(REPO_ROOT, "agents", "scripts"));
const PACTS = resolveDir(path.join(DATA, "pacts"), path.join(REPO_ROOT, "docs", "pacts"));

function readJson<T>(p: string): T | null {
  try {
    return JSON.parse(readFileSync(p, "utf-8")) as T;
  } catch {
    return null;
  }
}

const STATUS_TO_BADGE: Record<string, BadgeState> = {
  Created: "open",
  Funded: "escrow",
  Submitted: "work",
  Completed: "settled",
  Rejected: "reclaim",
  Refunded: "reclaim",
};

interface RawDemo {
  mode: string;
  task: string;
  reasoning: JobVM["reasoning"];
  txs: Record<string, string>;
  balances_pre?: { client: number; provider: number };
  balances_post?: { client: number; provider: number };
  job_id: number;
  deliverable?: string;
  irys?: { id: string; url: string; bytes?: number };
  branch?: "payout" | "refund";
  content_verified?: boolean;
  final_status: string;
}

function demoToJob(raw: RawDemo | null, file: string, phase: string): JobVM | null {
  if (!raw) return null;
  // amount: provider delta on payout; else the run's fixed 10 USDC (chain read can override live).
  let amount = 10;
  if (raw.branch === "payout" && raw.balances_post && raw.balances_pre) {
    amount = (raw.balances_post.provider - raw.balances_pre.provider) / 1e6 || 10;
  }
  return {
    jobId: raw.job_id,
    source: file,
    phase,
    title: raw.task,
    amountUsdc: amount,
    badge: STATUS_TO_BADGE[raw.final_status] ?? "open",
    statusLabel: raw.final_status,
    branch: raw.branch ?? null,
    txs: raw.txs ?? {},
    irys: raw.irys ?? null,
    deliverable: raw.deliverable ?? null,
    reasoning: raw.reasoning ?? {},
    contentVerified: raw.content_verified ?? null,
  };
}

export function loadJobs(): JobVM[] {
  const specs: [string, string][] = [
    ["phase5_demo_good_proof.json", "Phase 5 · Irys"],
    ["phase5_demo_bad_proof.json", "Phase 5 · Irys"],
    ["phase4_demo_good_proof.json", "Phase 4 · reasoned"],
    ["phase4_demo_bad_proof.json", "Phase 4 · reasoned"],
  ];
  // Phase-5 entries (with Irys + verification) come first so they read as the richest jobs.
  return specs
    .map(([f, phase]) => demoToJob(readJson<RawDemo>(path.join(SCRIPTS, f)), f, phase))
    .filter((j): j is JobVM => j !== null);
}

export function loadBeats(): Beats {
  const denial = readJson<any>(path.join(SCRIPTS, "phase4_denial_proof.json"));
  const freeze = readJson<any>(path.join(SCRIPTS, "phase4_freeze_proof.json"));
  const review = readJson<any>(path.join(SCRIPTS, "phase4_review_proof.json"));

  const denials: DenialVM[] = [];
  if (denial?.budget_cap) {
    const d = denial.budget_cap;
    denials.push({
      code: d.code,
      statusCode: d.status_code,
      type: d.type,
      reason: d.reason,
      detail: `transfer → ${d.details?.dst_addr ?? ""} exceeded the Pact amount cap`,
    });
  }
  if (denial?.allowlist) {
    const d = denial.allowlist;
    denials.push({
      code: d.code,
      statusCode: d.status_code,
      type: d.type,
      reason: d.reason,
      detail: `contract_call → ${d.details?.contract_addr ?? ""} not in the Pact allowlist`,
    });
  }

  return {
    denials,
    auditDenied: (denial?.audit_denied_entries ?? []).map((e: any) => ({
      action: e.action,
      result: e.result,
      createdAt: e.created_at,
    })),
    freeze: freeze
      ? {
          pactId: freeze.pact_id,
          allowedTx: freeze.allowed_tx,
          afterFreezeDenied: freeze.after_freeze?.result === "denied",
          recentDenied: (freeze.recent_denied ?? []).map((e: any) => ({ action: e.action, result: e.result })),
        }
      : null,
    review: review
      ? {
          pendingId: review.transfer_response?.pending_operation_id,
          approvalId: review.transfer_response?.approval_id,
          effect: review.pending_before?.policy_decision?.effect ?? "require_approval",
          status: review.approve_result?.status ?? "executed",
          txHash: review.tx_hash,
        }
      : null,
  };
}

export function loadPacts(): PactVM[] {
  const files = [
    ["client_escrow_pact.json", "Client · escrow + USDC allowlist"],
    ["provider_pact.json", "Provider · escrow allowlist"],
    ["client_budget_transfer_pact.json", "Client · budget cap (deny_if)"],
    ["review_pact.json", "Client · review threshold (review_if)"],
  ];
  return files
    .map(([f, name]) => {
      const raw = readJson<unknown>(path.join(PACTS, f));
      return raw ? { name, json: JSON.stringify(raw, null, 2) } : null;
    })
    .filter((p): p is PactVM => p !== null);
}
