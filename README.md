# AgentWorks

A trustless two-agent job-escrow marketplace built on the Cobo Agentic Wallet (CAW),
for the "Agentic Economy × Cobo Agentic Wallet" hackathon track.

A **Client Agent** posts and funds a paid task into an on-chain escrow contract. A
**Provider Agent** performs the work, stores the deliverable on Irys, and submits its
content hash on-chain. On acceptance the contract pays the Provider; on rejection or
expiry the Client reclaims the funds. Each agent operates through its own CAW wallet
under a scoped Pact — CAW is the authority layer that makes autonomous spending safe;
the escrow contract is the neutral settlement layer between two distrustful agents.

Lifecycle: `createJob → fund → submitWork → complete (payout) | reject (refund) | claimRefund (expiry)`

## Status

🚧 Under active development. This stub will be replaced by full setup and usage
documentation in the final phase. See `docs/FACTS.md` for verified, current project
facts (addresses, SDK details, network config).

## Stack

Foundry (escrow contract) · Python + CAW SDK (agents) · Next.js 15 (dashboard) · Irys
(deliverable storage) · Base Sepolia testnet.

## Repo layout

- `/contracts` — Foundry escrow contract, tests, deploy scripts
- `/agents` — CAW integration, Client/Provider agents, evaluator
- `/web` — Next.js 15 dashboard (demo surface)
- `/docs` — architecture, risk boundaries, demo script, and verified facts