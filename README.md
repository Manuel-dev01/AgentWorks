# AgentWorks

A trustless **two-agent job-escrow marketplace** built on the **Cobo Agentic Wallet (CAW)**,
for the "Agentic Economy × Cobo Agentic Wallet" hackathon track.

A **Client Agent** reasons about a task, funds it into an on-chain escrow, and (v1) evaluates the
result. A **Provider Agent** performs the work, stores the deliverable on **Irys**, and submits its
content hash + Irys id on-chain. On acceptance the escrow pays the Provider; on rejection (or expiry)
the Client is refunded. **Each agent acts through its own CAW wallet under a scoped Pact** — CAW is the
load-bearing authority layer that makes autonomous spending safe; the escrow is the neutral settlement
layer between two distrustful agents. The agents genuinely **decide** (fund? accept? reject?) via an LLM,
but a Pact they cannot exceed is the hard boundary — even an over-budget or non-whitelisted action is
blocked server-side, and authority can be frozen instantly by revoking the Pact.

Lifecycle: `createJob → fund → submitWork → complete (payout) | reject (refund) | claimRefund (expiry)`

## Status — Phases 0–6 complete & verified; demo polish (Phase 7) next
Full lifecycle works headless on **Ethereum Sepolia** with both settlement branches, the CAW
criticality beats (Pact **denial** + emergency **freeze** + human-in-the-loop **review**), genuine LLM
reasoning, and Irys-stored deliverables verified against the on-chain content hash. The **Next.js
dashboard** (the demo surface) is built on the AgentWorks brand and surfaces every verified run with live
on-chain reads — production build passes and it's Vercel-deployable (see **[docs/DEPLOY.md](docs/DEPLOY.md)**).
See **[docs/STATUS.md](docs/STATUS.md)** for the phase-by-phase state and **[docs/FACTS.md](docs/FACTS.md)**
for every verified address, signature, and tx hash. Demo script + architecture/risk docs are the remaining work.

## Stack
Foundry (escrow) · Python agents (CAW SDK `cobo-agentic-wallet` + web3) · DeepSeek reasoning
(OpenAI-compatible) · Irys devnet (deliverable storage) · **Next.js 15** dashboard (landing + brand +
demo surface, viem live reads) · **Ethereum Sepolia** testnet (chainId 11155111).

## Deployed (Ethereum Sepolia)
- Escrow: [`0x812BcEEc2De8C8aC71C7af7A8E2d4467E65Fdf18`](https://sepolia.etherscan.io/address/0x812bceec2de8c8ac71c7af7a8e2d4467e65fdf18) (verified)
- MockUSDC: [`0x4C4D1223BcC47E380CF4C37652EaDFe10A9Fd910`](https://sepolia.etherscan.io/address/0x4c4d1223bcc47e380cf4c37652eadfe10a9fd910) (verified)

## Repo layout
- `/contracts` — Foundry escrow (`AgentWorksEscrow.sol`), 25-test suite, deploy/verify scripts
- `/agents` — CAW integration (`caw/`), escrow calldata/reads (`escrow.py`), LLM reasoning
  (`reasoning.py`), Pact specs (`pacts.py`), Irys storage (`irys/`, `irys_store.py`), runnable `scripts/`
- `/web` — Next.js 15 app on the flow IA: landing (`/`), brand (`/brand`), and the dashboard —
  Marketplace (`/dashboard`), **live journey** (`/dashboard/new`, drives the agents step-by-step via
  `/api/flow`), Proofs (`/dashboard/proofs`), flow map (`/dashboard/flow`). Reads verified artifacts from
  `web/data/` (snapshotted) + live chain via viem; the live journey is localhost-only.
- `/docs` — `STATUS.md`, `FACTS.md` (verified facts), `DEPLOY.md` (Vercel), `pacts/*.json` (shipped Pact policies)

## Running it (testnet)
Secrets live in `.env` (gitignored); see `.env.example`. Foundry is at `~/.foundry/bin`.
```bash
# contracts
cd contracts && ~/.foundry/bin/forge.exe test            # 25 tests

# agents (Python venv already set up in agents/.venv)
agents/.venv/Scripts/python.exe agents/scripts/phase4_demo.py good     # reasoned payout
agents/.venv/Scripts/python.exe agents/scripts/phase4_denial.py        # Pact denial beats
agents/.venv/Scripts/python.exe agents/scripts/phase4_freeze.py        # emergency freeze
agents/.venv/Scripts/python.exe agents/scripts/phase5_demo.py good     # Irys store + on-chain verify

# dashboard — landing /, brand /brand, Marketplace /dashboard, live journey /dashboard/new
pnpm install
pnpm --filter web dev          # http://localhost:3000   (build: pnpm --filter web build)
```
The **live journey** (`/dashboard/new`) signs real txs, so both local CAW TSS nodes must be running
(they don't auto-restart on reboot) — see the restart procedure in [docs/FACTS.md](docs/FACTS.md).
If `pnpm --filter web dev` ever errors on an ignored `sharp` build, run `web/node_modules/.bin/next dev`
directly. Deploy notes: **[docs/DEPLOY.md](docs/DEPLOY.md)**.

## What CAW actually does here (claims discipline)
CAW enforces each agent's authority boundary (Pact: contract allowlist + caps), server-side and
unbypassable; "freeze" = `revoke_pact` (no native freeze API). CAW does **not** coordinate the two
agents or hold the escrow — our contract + orchestration do. We mirror the ERC-8183 **draft** lifecycle
naming; we do not depend on any external/Arc deployment.
