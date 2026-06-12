# AgentWorks — Project Status (as of 2026-06-12)

Fast-recall snapshot of where the build is. Stable law → `CLAUDE.md`; verified specifics
(every tx hash, signature, address) → `docs/FACTS.md`. This file is the bridge.

## TL;DR
**Phases 0–6 complete. Phase 6.5 (autonomous open marketplace) sub-phases 6.5.0–6.5.5 done; live e2e +
cloud-triggered run verified 2026-06-12. NEXT: Phase 7 (demo/docs) + commit.**
Everything runs on **Ethereum Sepolia** (chainId 11155111). Escrow **v2** (open `createJob` + `acceptJob`
race) `0xD6cB413c0E4a5839Fd4B02aFFeBF65e6868726b9` is live + Etherscan-verified.
**2026-06-12 live e2e on v2, BOTH branches (genuine LLM decisions, every tx Success, re-read on-chain):**
job **#5 → Completed** (payout) and job **#6 → Rejected** (refund). **Then the autonomy headline: a `POST /trigger`
to the DEPLOYED Railway agent service ran the full lifecycle autonomously → job #7 → Completed, with a real
2-provider accept-race IN THE CLOUD** (Provider + ProviderB both reasoned accept; Provider won). All tx hashes in
FACTS.md ("Live end-to-end re-verification" + "CLOUD-TRIGGERED autonomous run").
**Dashboard reshaped (6.5.5):** `/dashboard` is now a LIVE WINDOW onto the deployed agents — `components/dashboard/
LiveMarketplace.tsx` + `lib/agent.ts` (browser client for the Railway `/health`,`/runs`,`/board`,`/trigger`).
"Post job → trigger agents" fires the cloud service and the board polls it settling; verified runs (3/5/6) seed the
board (snapshotted to `web/data/market/`). `NEXT_PUBLIC_AGENT_API` defaults to the Railway URL. `pnpm --filter web
build` PASSES; `/dashboard` renders 200. Nothing is committed to git yet (user commits).

## Current addresses / identities (Ethereum Sepolia)
| What | Value |
|---|---|
| Escrow (Phase 5, carries irysId) | `0x812BcEEc2De8C8aC71C7af7A8E2d4467E65Fdf18` (verified on Etherscan) |
| MockUSDC (6-decimal, mintable) | `0x4C4D1223BcC47E380CF4C37652EaDFe10A9Fd910` (verified) |
| Client CAW wallet | id `0da4d5c3-5fc4-4a50-878a-0e8ee1a1787d` · EVM `0x6dfbd0ac9feb5bb9a9ffeaf54df203c1633c1ddd` |
| Provider CAW wallet | id `bdecbada-3e1d-41d8-9e04-c12202cc9c17` · EVM `0xef9349b3273b1a54faaf701231f499fe0282e643` |
| Deployer EOA (throwaway) | `0xBCA6f82e240C6AC36B23b4f7D21adF17e03966Fe` |
| CAW chain id / native / USDC token_id | `SETH` / `SETH` / `SETH_USDC` (we use MockUSDC via contract_call, not CAW's USDC) |
| Read RPC | `https://sepolia.drpc.org` (public node was flaky; + retry in `agents/escrow.py`) |
| Explorer | `https://sepolia.etherscan.io` · Irys (devnet) `https://devnet.irys.xyz/<id>` |

## Stack
Foundry escrow · Python agents (CAW SDK `cobo-agentic-wallet` 0.1.40 + web3) · DeepSeek
`deepseek-v4-flash` reasoning (OpenAI-compatible) · Irys devnet storage · Next.js 15 dashboard (pending).
`caw` CLI v0.2.86 at `~/.cobo-agentic-wallet/bin`; two unpaired MPC wallets onboarded.

## Phase-by-phase
- **Phase 0 — Recon & scaffold ✅** Toolchain verified; CAW SDK reality-checked from source; monorepo skeleton.
- **Phase 1 — Escrow (Foundry) ✅** Full lifecycle + 25 tests; self-contained (inline IERC20). Deployed + verified.
  (Originally Base Sepolia; later moved to Eth Sepolia + extended in Phase 5.)
- **Phase 2 — CAW hello-world ✅** Two wallets onboarded (unpaired); pact → transfer → audit-log read.
  **Finding:** CAW can't fund/index Base Sepolia → **switched the whole project to Ethereum Sepolia** (user-approved).
- **Phase 3 — Agents drive escrow via contract_call ✅** Full lifecycle headless, both branches (payout + refund).
  Adopted **MockUSDC** (CAW dispenses no USDC). escrow.py = calldata builders + RPC reads.
- **Phase 4 — Pacts + criticality + genuine LLM reasoning ✅** (our strongest phase, criteria 1/2/5)
  - DENIAL: budget-cap (`TRANSFER_LIMIT_EXCEEDED`) + contract-allowlist (`CONTRACT_NOT_WHITELISTED`).
  - FREEZE: `revoke_pact` → next call denied (no native freeze API; freeze = revocation).
  - review_if human-in-the-loop: PendingApproval → `approve_pending_operation` → executed (live-verified).
  - LLM agents genuinely decide fund/accept/reject; the **branch is the LLM's verdict**, bounded by the Pact.
  - Literal Pact JSON shipped at `docs/pacts/*.json`.
- **Phase 5 — Irys storage + on-chain content verification ✅** Escrow extended:
  `submitWork(jobId, keccak256(content), irysId)` + `Job.irysId` + `WorkSubmitted(…,irysId)` (redeployed + reverified).
  Full loop: Provider stores on Irys → submits hash+id → Evaluator **fetches from Irys** to judge → settle →
  `keccak256(Irys-fetched) == on-chain deliverableHash` (True, both branches).

- **Phase 6 — Next.js 15 app on the AgentWorks brand ✅** (paper/ink + Settle Blue, Space Grotesk + IBM Plex
  Mono, the AW escrow-chip mark). Rebuilt around the **app FLOW** (2nd Claude Design handoff, `screens/`),
  replacing the earlier monolithic dashboard. Routes: landing `/`, brand `/brand`, and the dashboard shell:
  - `/dashboard` **Marketplace** — jobs board (filters + stats) from verified artifacts + live viem reads.
  - `/dashboard/new` **live journey** — Post → Accept → Submit → Review → Settle, each step a **real action
    on Sepolia** via a resumable orchestrator (`agents/flow.py` + `flow_step.py` → `/api/flow`, localhost-only,
    hidden in prod). Verified e2e: a full run produced real createJob/fund/submitWork/complete txs +
    Irys id + `content_verified=true` (job #4, run f99a959257).
  - `/dashboard/proofs` — CAW denial/freeze beats + literal Pact JSON (relocated here, off the main flow).
  - `/dashboard/flow` — the 6-step flow map; `/dashboard/jobs/[idx]` — read-only receipt for a past run.
  `pnpm --filter web build` passes; all routes 200 in dev. Vercel-ready (artifacts snapshotted to `web/data/`).
  **Live signing depends on the local CAW TSS nodes running** — restart procedure in FACTS.md.

## What's NEXT
- **Phase 7 docs — DONE this session:** README rewritten (v2 + autonomy + 3-part deploy), new
  `docs/ARCHITECTURE.md` + `docs/RISK_BOUNDARIES.md`, `DEMO_SCRIPT.md`/`SUBMISSION.md`/`DEPLOY*.md` refreshed.
- **Dashboard 6.5.5 — DONE:** `/dashboard/new` = the live autonomous trigger (→ deployed Railway service,
  watches the agents settle); `/dashboard` = read-only proof history; `/dashboard/proofs` on v2 + the Pact
  participants boundary; flow map on the v2 open lifecycle. Demo-journey UI (`Journey.tsx`, `/api/flow`,
  `/api/run`, replay loaders) deleted. `pnpm --filter web build` passes.
- **Remaining for fully hands-off:** an always-on TSS signer on a VM (Option A, `docker compose --profile tss`).
  Railway Option B is provisioned but the node won't stay up there (FACTS) — the local signer is the working
  default; the VM is the proven zero-local route and needs the user's VM. Record the demo video; user does the Vercel deploy.

## Key gotchas to remember (full detail in FACTS.md)
- CAW: every tx needs an active pact; non-matching → DENIED server-side; tx status 400→500→900 (Success);
  `transfer_tokens`/`contract_call` need `src_addr`; unpaired pacts auto-activate (no app approval).
- Irys devnet: retrieve at `devnet.irys.xyz/<id>` (prod gateway 403s devnet); the gateway 403s the default
  Python-urllib UA (send a normal User-Agent). Uploads auto-fund from the EVM key's Sepolia ETH.
- Foundry reads `$CHAIN` as `--chain` → keep `CHAIN=sepolia` in `.env`.
- Windows console is cp1252 → force UTF-8 stdout in scripts; avoid non-ASCII in prints.
- **Web/pnpm:** repo pins `pnpm@11.1.2`, which gates native build scripts — `pnpm-workspace.yaml` has
  `allowBuilds: { sharp: true }` (else `ERR_PNPM_IGNORED_BUILDS`). `web/node_modules/.bin/next dev` bypasses
  the gate. Dashboard reads proofs from `web/data/` first (snapshot for Vercel), sibling dirs as dev fallback.
- **Env keys clarification:** the agents read `CAW_CLIENT_*`/`CAW_PROVIDER_*` (set) — `AGENT_WALLET_API_KEY`/
  `_WALLET_ID` are unused legacy names. `IRYS_PRIVATE_KEY` falls back to `DEPLOYER_PRIVATE_KEY`; `IRYS_NODE_URL`
  is never read (`.devnet()` sets the node). So blank `AGENT_WALLET_*`/`IRYS_*` are fine — nothing missing.
- **CAW signing needs the local TSS nodes RUNNING** (one `cobo-tss-node.exe` per wallet profile). They don't
  auto-restart on reboot; when down, every tx stalls at `Processing/"signing"` (no tx hash, nonce frozen).
  Restart both before any live run — exact command + profiles in FACTS.md ("CAW TSS signer — restart procedure").

## Run cheatsheet (from repo root)
- Contracts: `cd contracts && ~/.foundry/bin/forge.exe test`
- Agents (venv): `agents/.venv/Scripts/python.exe agents/scripts/<phaseN_*>.py`
- Phase 4 beats: `phase4_criticality_smoke.py`, `phase4_denial.py`, `phase4_freeze.py`, `phase4_demo.py {good|bad}`, `phase4_review.py`
- Phase 5: `phase5_irys_smoke.py`, `phase5_demo.py {good|bad}`
- Dashboard: `pnpm install` then `pnpm --filter web dev` → http://localhost:3000 (`/`, `/brand`, `/dashboard`,
  `/dashboard/new`, `/dashboard/proofs`, `/dashboard/flow`); refresh artifacts with `pnpm --filter web snapshot`;
  build with `pnpm --filter web build`. For the **live journey** (`/dashboard/new`), first start both CAW TSS
  nodes (FACTS.md) so signing works.

## Secrets/keys in `.env` (gitignored) — what's set
CAW client/provider wallet ids + api keys; DEPLOYER_PRIVATE_KEY (funded Sepolia ETH); EXPLORER_API_KEY
(Etherscan); RPC_URL (drpc); LLM_API_KEY (DeepSeek) + LLM_MODEL/LLM_BASE_URL; CDP_* (Base faucet, now unused).
IRYS_PRIVATE_KEY optional (falls back to DEPLOYER_PRIVATE_KEY for devnet funding).
