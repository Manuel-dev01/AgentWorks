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

## Status — working, on-chain, demonstrable
A runnable prototype on **Ethereum Sepolia**, not a mockup. What works end-to-end today:
- **Real USDC settlement through CAW** — two agents drive `createJob → fund → submitWork → settle`, every
  on-chain action a Cobo Agentic Wallet `contract_call`; both the **payout** and **refund** branches.
- **CAW as the load-bearing trust layer** — scoped Pacts (allowlist + caps) that the agent cannot exceed,
  a Pact **denial**, an emergency **freeze** (`revoke_pact`), and a human-in-the-loop **review** approval.
- **Genuine agent reasoning** (DeepSeek) at fund / accept / reject, bounded by the Pact.
- **Verifiable deliverables** — stored on Irys, with `keccak256(content)` anchored on-chain and checked.
- **A live dashboard** — author a job and watch each step settle on Sepolia (localhost), with a hosted
  deterministic replay + live on-chain Marketplace.

Submission checklist + track-rule mapping: **[docs/SUBMISSION.md](docs/SUBMISSION.md)** · demo storyboard:
**[docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md)** · every verified address/signature/tx: **[docs/FACTS.md](docs/FACTS.md)**.

## Stack
Foundry (escrow) · Python agents (CAW SDK `cobo-agentic-wallet` + web3) · DeepSeek reasoning
(OpenAI-compatible) · Irys devnet (deliverable storage) · **Next.js 15** dashboard (landing + brand +
demo surface, viem live reads) · **Ethereum Sepolia** testnet (chainId 11155111).

## On-chain & agent wallets (Ethereum Sepolia, chainId 11155111)
**Contracts (testnet addresses, verified on Etherscan):**
- Escrow `AgentWorksEscrow`: [`0x812BcEEc2De8C8aC71C7af7A8E2d4467E65Fdf18`](https://sepolia.etherscan.io/address/0x812bceec2de8c8ac71c7af7a8e2d4467e65fdf18)
- MockUSDC (6-decimal, mintable): [`0x4C4D1223BcC47E380CF4C37652EaDFe10A9Fd910`](https://sepolia.etherscan.io/address/0x4c4d1223bcc47e380cf4c37652eadfe10a9fd910)

**Cobo Agentic Wallet addresses (the two agents):**
- Client agent CAW — wallet id `0da4d5c3-5fc4-4a50-878a-0e8ee1a1787d` · EVM [`0x6dfbd0ac9feb5bb9a9ffeaf54df203c1633c1ddd`](https://sepolia.etherscan.io/address/0x6dfbd0ac9feb5bb9a9ffeaf54df203c1633c1ddd)
- Provider agent CAW — wallet id `bdecbada-3e1d-41d8-9e04-c12202cc9c17` · EVM [`0xef9349b3273b1a54faaf701231f499fe0282e643`](https://sepolia.etherscan.io/address/0xef9349b3273b1a54faaf701231f499fe0282e643)

**Verified transactions** — one full live lifecycle (job #8, driven step-by-step through the dashboard's
`/api/flow`), every action a CAW `contract_call`:
| Step | Agent | Transaction |
|---|---|---|
| createJob | Client CAW | [`0x7a9b6f19…`](https://sepolia.etherscan.io/tx/0x7a9b6f195455a7368e289a071e28b8a3e4a0d984bd680a65016f9a5e682f41f3) |
| approve (USDC) | Client CAW | [`0xa5318c68…`](https://sepolia.etherscan.io/tx/0xa5318c68b95d6f560a15adf9930de6fb1b421a70fd7510e4886c325d533fdca6) |
| fund (escrow) | Client CAW | [`0x1ce70305…`](https://sepolia.etherscan.io/tx/0x1ce7030502d807b220037dee5a7e7b94c231b6c18c1fe0ab2df8381bcdd31dd0) |
| submitWork | Provider CAW | [`0x9b5731f9…`](https://sepolia.etherscan.io/tx/0x9b5731f947e7fc90ff2750875057fc7f040d8ee38452cb9716e21d3f8046c20d) |
| complete (payout) | Client CAW | [`0xabcb748a…`](https://sepolia.etherscan.io/tx/0xabcb748af22c77dc31cba6abb460a843338beba1a758f4b88e30c1f3548bc040) |

A second verified run (job #4, headless) + the Irys deliverable id and the denial/freeze/review beats are in
**[docs/FACTS.md](docs/FACTS.md)**.

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

## How Cobo Agentic Wallet is used (key code & config)
CAW is the **load-bearing authority layer** — the agents have no other way to move funds. The integration
is isolated to one place so a judge can read it quickly:

- **`agents/caw/client.py`** — the single CAW SDK wrapper. Every fund operation goes through
  `contract_call(src_addr, contract_addr, calldata, …)` (createJob / approve / fund / submitWork / settle),
  with `submit_pact` / `wait_pact_active` for authorization, `revoke_pact` for the freeze, and
  `approve_pending_operation` for review.
- **`agents/pacts.py` + the shipped `docs/pacts/*.json`** — the literal **Pact policies** = permission control
  + security isolation: a contract **allowlist** (`target_in` = only the escrow + USDC), a per-24h **tx cap**,
  a **budget cap** (`deny_if.amount_gt`), and a **review threshold** (`review_if`). The agent cannot exceed these
  regardless of what its LLM decides — enforced server-side by CAW.
- **The three CAW value beats** (live in the dashboard's **Proofs** tab + reproducible from `agents/scripts/`):
  - *Permission/isolation* → a **Pact denial** (`TRANSFER_LIMIT_EXCEEDED`, `CONTRACT_NOT_WHITELISTED`, HTTP 403).
  - *Wallet management/safety* → an emergency **freeze** via `revoke_pact` (the next call is denied).
  - *Human-in-the-loop* → a **review** approval (`require_approval` → `approve_pending_operation`).
- **Autonomous payment** → the Client and Provider agents each act through **their own** CAW wallet; signing is
  MPC via the local TSS nodes; settlement is the neutral escrow contract.

Live signing requires the local CAW TSS signer nodes — restart procedure in **[docs/FACTS.md](docs/FACTS.md)**.

## Submission & track-rules compliance
| Track rule | How AgentWorks meets it |
|---|---|
| Agents + fund operations | Two autonomous agents (Client, Provider) run a USDC job-escrow marketplace |
| Fund operations via CAW | Every on-chain action is a CAW `contract_call` (see verified txs above) |
| Real fund execution (payment / transfer / **settlement**) | Real MockUSDC is escrowed and **settled** on Sepolia — payout *and* refund branches, with tx hashes |
| Demonstrate CAW value (wallet mgmt · **permission control** · **security isolation** · autonomous payment) | Scoped Pacts (`agents/pacts.py`), the denial + freeze + review beats, agents paying autonomously through their own wallets |
| Runnable / demonstrable prototype | Live Next.js dashboard + real on-chain txs + local live agents — not a PPT or mockup |

Full submission checklist (repo · README · video · demo link · CAW code notes · testnet address · tx hash ·
agent wallet address · flow records) with every value filled in: **[docs/SUBMISSION.md](docs/SUBMISSION.md)**.

## Local Replication & Architecture
The hosted dashboard is a **deterministic demo** (it replays verified runs + reads live chain state). To
drive the **real agents** — author a job and watch each step settle on-chain — run it locally.

### Architecture (local)
```
        reads (viem, also works hosted)
  ┌──────────────────────────────┐
  │                              ▼
┌─────────────────┐        ┌──────────────────────────────┐
│  Next.js /web   │        │  Ethereum Sepolia            │
│  dashboard      │        │  AgentWorksEscrow + MockUSDC │
│  /dashboard/new │        └──────────────────────────────┘
└───────┬─────────┘                      ▲ broadcast
        │ POST /api/flow (localhost only)│
        ▼                                │
┌──────────────────────┐  CAW SDK  ┌─────────────────┐  co-sign  ┌────────────────────┐
│ Python agents        │──────────▶│ Cobo Agentic    │◀─────────▶│ local cobo-tss-node│
│ flow.py + reasoning  │   REST    │ Wallet API      │   relay   │ (MPC signer ×2)    │
│ (Client / Provider)  │           └─────────────────┘           └────────────────────┘
└───────┬──────────────┘
        │ store deliverable
        ▼
   ┌─────────────┐     DeepSeek (OpenAI-compatible) drives fund / accept / reject decisions
   │ Irys devnet │
   └─────────────┘
```
CAW enforces each agent's Pact server-side; signing happens via the **local MPC TSS nodes**; settlement is
the neutral escrow contract. The frontend never holds keys.

### Prerequisites (`.env`, see `.env.example`)
- `CAW_CLIENT_*` / `CAW_PROVIDER_*` — wallet ids, api keys, addresses from `caw onboard` (two agents)
- `DEPLOYER_PRIVATE_KEY` (throwaway, funded Sepolia ETH) · `EXPLORER_API_KEY` (Etherscan) · `RPC_URL`
- `LLM_API_KEY` (DeepSeek) + `LLM_MODEL` + `LLM_BASE_URL`
- `ESCROW_CONTRACT_ADDRESS` / `USDC_TOKEN_ADDRESS` (deployed values are prefilled in `.env.example`)

### Run it locally
```bash
git clone <repo> && cd AgentWorks
cp .env.example .env            # fill the secrets above

# 1. contracts (already deployed; redeploy only if you want your own)
cd contracts && ~/.foundry/bin/forge.exe test
#   forge script script/Deploy.s.sol --rpc-url $RPC_URL --broadcast --verify   # optional redeploy

# 2. agents: onboard two CAW wallets (writes CAW_* into .env), fund them with MockUSDC + Sepolia ETH
caw onboard   # ×2 (Client, Provider)  — see docs/FACTS.md

# 3. start the MPC signers (one terminal each, leave open) — see docs/FACTS.md for the exact command
#    ~/.cobo-agentic-wallet/profiles/<profile>/tss-node/cobo-tss-node(.exe) start --caw --prod --key-file .password

# 4. the dashboard (live journey enabled on localhost)
pnpm install && pnpm --filter web dev    # http://localhost:3000/dashboard/new
```
With the signers up, `/dashboard/new` authors a job and signs every step (createJob → fund → submitWork →
settle) on Sepolia; the Marketplace then shows the new escrow live. Deploy notes (Vercel): `docs/DEPLOY.md`.
