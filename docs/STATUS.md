# AgentWorks — Project Status (as of 2026-06-09)

Fast-recall snapshot of where the build is. Stable law → `CLAUDE.md`; verified specifics
(every tx hash, signature, address) → `docs/FACTS.md`. This file is the bridge.

## TL;DR
**Phases 0–5 complete and verified. Phase 6 (Next.js dashboard) is NEXT.** Phase 7 = demo/docs.
Everything runs on **Ethereum Sepolia** (chainId 11155111) — we switched off Base Sepolia in Phase 2
because CAW can't fund/index agents on Base. Nothing is committed to git yet (user commits).

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

## What's NEXT — Phase 6 (Next.js 15 dashboard, the demo surface)
Surface the verified flows for a live judge: wallet/USDC balances, the job state machine
(Created→Funded→Submitted→Completed|Rejected), deliverable hash + clickable Irys link, CAW audit-log
allowed/denied entries, the literal Pact JSON, and Etherscan/Irys links. Build in `/web`.
(Phase 7 = demo script/video, README, architecture diagram, risk-boundary doc.)

## Key gotchas to remember (full detail in FACTS.md)
- CAW: every tx needs an active pact; non-matching → DENIED server-side; tx status 400→500→900 (Success);
  `transfer_tokens`/`contract_call` need `src_addr`; unpaired pacts auto-activate (no app approval).
- Irys devnet: retrieve at `devnet.irys.xyz/<id>` (prod gateway 403s devnet); the gateway 403s the default
  Python-urllib UA (send a normal User-Agent). Uploads auto-fund from the EVM key's Sepolia ETH.
- Foundry reads `$CHAIN` as `--chain` → keep `CHAIN=sepolia` in `.env`.
- Windows console is cp1252 → force UTF-8 stdout in scripts; avoid non-ASCII in prints.

## Run cheatsheet (from repo root)
- Contracts: `cd contracts && ~/.foundry/bin/forge.exe test`
- Agents (venv): `agents/.venv/Scripts/python.exe agents/scripts/<phaseN_*>.py`
- Phase 4 beats: `phase4_criticality_smoke.py`, `phase4_denial.py`, `phase4_freeze.py`, `phase4_demo.py {good|bad}`, `phase4_review.py`
- Phase 5: `phase5_irys_smoke.py`, `phase5_demo.py {good|bad}`

## Secrets/keys in `.env` (gitignored) — what's set
CAW client/provider wallet ids + api keys; DEPLOYER_PRIVATE_KEY (funded Sepolia ETH); EXPLORER_API_KEY
(Etherscan); RPC_URL (drpc); LLM_API_KEY (DeepSeek) + LLM_MODEL/LLM_BASE_URL; CDP_* (Base faucet, now unused).
IRYS_PRIVATE_KEY optional (falls back to DEPLOYER_PRIVATE_KEY for devnet funding).
