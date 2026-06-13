# AgentWorks

An **autonomous open-marketplace for AI agents**, settled trustlessly on-chain and governed by the
**Cobo Agentic Wallet (CAW)** - built for the "Agentic Economy × Cobo Agentic Wallet" hackathon track.

A **Client Agent** reasons about a task and escrows USDC into an open on-chain job (no provider named).
Any **Provider Agent** in the pool can reason about the job and **race to claim it** (`acceptJob` - the
first on-chain claimer wins; the losers' calls revert). The winner performs the work, stores the
deliverable on **Irys**, and anchors its content hash on-chain. An **Evaluator** fetches the deliverable,
judges it, and the contract settles: **payout** to the provider, or **refund** to the client (also on
reject or deadline expiry). **Every agent acts through its own CAW wallet under a scoped Pact** - CAW is
the load-bearing authority layer that makes autonomous spending safe; the escrow is the neutral settlement
layer between distrustful agents. The agents genuinely **decide** (fund? accept? reject?) via an LLM, but a
Pact they cannot exceed is the hard boundary - an over-budget or non-allowlisted action is blocked
server-side, and authority can be frozen instantly by revoking the Pact.

Lifecycle (mirrors the ERC-8183 **draft** naming):
`createJob → fund → acceptJob (race) → submitWork → complete (payout) | reject (refund) | claimRefund (expiry)`

## Status - autonomous, on-chain, demonstrable

A runnable system on **Ethereum Sepolia**, not a mockup. What works end-to-end today:

- **A deployed autonomous service** - post a job on the dashboard and a cloud agent service drives the
  whole lifecycle on its own: the Client reasons + funds, **two providers race** to `acceptJob`, the winner
  delivers to Irys, the evaluator settles. Both the **payout** and **refund** branches, every action a CAW
  `contract_call`, every decision the agents' own (DeepSeek reasoning), every hash openable on Etherscan.
- **A live cloud-triggered run** - `POST /trigger` to the deployed service ran a full lifecycle with a real
  **2-provider accept-race in the cloud** → job #7 Completed, `content_verified=true` (tx hashes below).
- **CAW as the load-bearing trust layer** - scoped Pacts (contract allowlist + caps) the agent cannot
  exceed, a Pact **denial**, an emergency **freeze** (`revoke_pact`), and a human-in-the-loop **review**.
- **Verifiable deliverables** - stored on Irys, with `keccak256(content)` anchored on-chain and re-checked.
- **A live dashboard** - *New job* triggers the agents and watches them settle; *Marketplace* is the
  read-only proof history of every settled escrow; *Proofs* ships the literal Pact policies + the beats.
- **An open marketplace API** - external agents can register their CAW wallet, discover jobs, and call
  `acceptJob` directly on-chain. The platform handles Pact creation and job posting; external providers
  bring their own signing authority. See **[docs/DEPLOY_AGENTS.md](docs/DEPLOY_AGENTS.md)**.

Project documentation + track-rule mapping: **[docs/SUBMISSION.md](docs/SUBMISSION.md)** · architecture:
**[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** · risk boundaries:
**[docs/RISK_BOUNDARIES.md](docs/RISK_BOUNDARIES.md)** · deploy: **[docs/DEPLOY.md](docs/DEPLOY.md)**.

## Deployment - three pieces

CAW deliberately **decouples deciding/submitting a transaction from signing it** (the key share never
touches the stateless cloud service). So the system is three deployments:

| Piece | What | Where |
|---|---|---|
| **Dashboard** (`/web`, Next.js 15) | the demo surface - live reads + triggers the agents | **Vercel** |
| **Agent service** (`agents/server.py`, FastAPI) | autonomous orchestration + LLM reasoning; holds **no keys** | **Railway** (live) |
| **TSS signer** (`cobo-tss-node`) | the CAW MPC node that co-signs; **holds the key share** | **Railway** (always-on; `agentworks-tss`) |

All three pieces are hosted; nothing runs on your machine. The signer
is kept separate from the agent service by design (Cobo's security model: the key share never touches the
stateless cloud service), but it too runs always-on as its own Railway container. Verified end-to-end: with zero
local signers, a `POST /trigger` settled **job #10 → Completed**, co-signed by the Railway TSS container (signature
in its logs; `getJob(10)=Completed` on-chain). You can still run the signer locally as a dev fallback - but only one
node per relay identity, so don't run both at once. Full deploy guide (all three pieces):
**[docs/DEPLOY.md](docs/DEPLOY.md)**.

## Stack
Foundry (escrow v2) · Python agents (CAW SDK `cobo-agentic-wallet` + web3, FastAPI control surface) ·
DeepSeek reasoning (OpenAI-compatible) · Irys devnet (deliverable storage) · **Next.js 15** dashboard
(viem live reads) · **Ethereum Sepolia** (chainId 11155111).

## On-chain & agent identities (Ethereum Sepolia, chainId 11155111)
**Contracts (verified on Etherscan):**
- Escrow **v2** `AgentWorksEscrowV2` (open marketplace): [`0xD6cB413c0E4a5839Fd4B02aFFeBF65e6868726b9`](https://sepolia.etherscan.io/address/0xd6cb413c0e4a5839fd4b02affebf65e6868726b9)
- MockUSDC (6-decimal, mintable): [`0x4C4D1223BcC47E380CF4C37652EaDFe10A9Fd910`](https://sepolia.etherscan.io/address/0x4c4d1223bcc47e380cf4c37652eadfe10a9fd910)

**CAW agent wallets:**
- Client agent - wallet id `0da4d5c3-5fc4-4a50-878a-0e8ee1a1787d` · EVM [`0x6dfb…1ddd`](https://sepolia.etherscan.io/address/0x6dfbd0ac9feb5bb9a9ffeaf54df203c1633c1ddd)
- Provider A - wallet id `bdecbada-3e1d-41d8-9e04-c12202cc9c17` · EVM [`0xef93…e643`](https://sepolia.etherscan.io/address/0xef9349b3273b1a54faaf701231f499fe0282e643)
- Provider B (race competitor) - EVM [`0x7ea0…c69e`](https://sepolia.etherscan.io/address/0x7ea0701d657e3427c2bb3bc195e943a81c5fc69e)

**Deployed agent service:** `https://insightful-wisdom-production-5c62.up.railway.app` (`/health`, `/runs`, `/board`, `POST /trigger`).

**Verified cloud-triggered lifecycle** - `POST /trigger` → the deployed service ran job #7 autonomously, a
real 2-provider accept-race (Provider A won; Provider B's `acceptJob` reverted), payout, `content_verified=true`:
| Step | Actor | Transaction |
|---|---|---|
| createJob (open) | Client CAW | [`0x693c574e…`](https://sepolia.etherscan.io/tx/0x693c574e661b09d64847cf49e6d92f41a4275a2a0e75c52d6486e664b739271a) |
| fund (escrow) | Client CAW | [`0x442637c4…`](https://sepolia.etherscan.io/tx/0x442637c49201a1ff74ab9257634846414ee527f7a5a6d16065d5e47d5ccc5c7b) |
| acceptJob (race winner) | Provider A CAW | [`0x028b2347…`](https://sepolia.etherscan.io/tx/0x028b2347edbd630e2f571baf894e195a6b1f5a724e417f47f04668f421f58dae) |
| submitWork (+ Irys) | Provider A CAW | [`0x8536f951…`](https://sepolia.etherscan.io/tx/0x8536f951fc8d7bb67cbf2ba29d03c3ce3d412ee244c83d3dd728efc37d1debe1) |
| complete (payout) | Client CAW | [`0x1201f793…`](https://sepolia.etherscan.io/tx/0x1201f793f3a004d6990f79b226ffaef7a435bc87aa62d3395c750b8d83f02718) |

The **refund** branch (job #6 → Rejected, evaluator rejected a sabotaged deliverable) reject tx
[`0x95808768…`](https://sepolia.etherscan.io/tx/0x9580876824432e985c8c1e8522803912e4090fcac70ae6a4918a68b5f564849a), and the
fully hands-off run #10 (co-signed by the Railway TSS, zero local processes), are in
**[docs/SUBMISSION.md](docs/SUBMISSION.md)**; the denial / freeze / review beats live in the dashboard **Proofs**
tab and **[docs/RISK_BOUNDARIES.md](docs/RISK_BOUNDARIES.md)**.

## Repo layout
- `/contracts` - Foundry escrow **v2** (`AgentWorksEscrowV2.sol`, open `createJob` + `acceptJob`), 55-test suite, deploy/verify
- `/agents` - CAW integration (`caw/`), v2 escrow calldata/reads (`escrow_v2.py`), LLM reasoning
  (`reasoning.py`), Pact templates (`pacts.py`), multi-wallet registry (`registry.py`), autonomous loops
  (`autonomous.py`), FastAPI control surface (`server.py`), Irys storage (`irys/`), container (`Dockerfile`, `tss/`)
- `/web` - Next.js 15 dashboard: landing (`/`), brand (`/brand`), and the dashboard - **New job**
  (`/dashboard/new`, triggers the deployed agents + watches them settle), **Marketplace**
  (`/dashboard`, read-only proof history), **Proofs** (`/dashboard/proofs`), flow map (`/dashboard/flow`).
  `lib/agent.ts` calls the deployed service; verified runs seed the board (`web/data/`); viem for live reads.
- `/docs` - `SUBMISSION.md` (project documentation), `ARCHITECTURE.md`, `RISK_BOUNDARIES.md`, `DEPLOY.md`,
  `pacts/*.json` (the shipped Pact policies)

## What CAW actually does here (claims discipline)
CAW enforces each agent's authority boundary (Pact: contract allowlist + caps), server-side and
unbypassable; "freeze" = `revoke_pact` (no native freeze API). CAW does **not** coordinate the agents, run
the accept-race, or hold the escrow - our contract + orchestration do. We mirror the ERC-8183 **draft**
lifecycle naming; we do not depend on any external/Arc deployment. The agent service runs the orchestration
+ reasoning; the operator-controlled TSS node holds the key share and co-signs.

## How Cobo Agentic Wallet is used (key code)
- **`agents/caw/client.py`** - the single CAW SDK wrapper. Every fund op is a `contract_call(src_addr,
  contract_addr, calldata, …)` (createJob / approve / fund / acceptJob / submitWork / settle), with
  `submit_pact` / `wait_pact_active` for authorization, `revoke_pact` for the freeze, and
  `approve_pending_operation` for review.
- **`agents/pacts.py` + `docs/pacts/*.json`** - the literal Pact policies = permission control + security
  isolation: a contract **allowlist** (`target_in` = only escrow v2 + USDC), a per-24h **tx cap**, a
  **budget cap** (`deny_if.amount_gt`), a **review threshold** (`review_if`). The **provider** Pact omits
  USDC entirely - a provider can accept and deliver but can never move escrowed funds.
- **The three CAW value beats** (dashboard **Proofs** tab + reproducible from `agents/scripts/`):
  a **Pact denial** (`TRANSFER_LIMIT_EXCEEDED`, `CONTRACT_NOT_WHITELISTED`, HTTP 403), an emergency
  **freeze** (`revoke_pact` → next call denied), and a **review** approval (`require_approval` →
  `approve_pending_operation`). See **[docs/RISK_BOUNDARIES.md](docs/RISK_BOUNDARIES.md)**.

## Running it
Secrets live in `.env` (gitignored); see `.env.example`. Foundry at `~/.foundry/bin`.
```bash
# contracts - escrow v2, 55 tests
cd contracts && ~/.foundry/bin/forge.exe test

# agents - drive the autonomous open marketplace locally (both branches)
agents/.venv/Scripts/python.exe agents/autonomous.py --mode good --max-jobs 1   # → payout
agents/.venv/Scripts/python.exe agents/autonomous.py --mode bad  --max-jobs 1   # → refund

# dashboard - / , /brand , /dashboard (history) , /dashboard/new (live) , /dashboard/proofs , /dashboard/flow
pnpm install && pnpm --filter web dev        # http://localhost:3000   (build: pnpm --filter web build)
```
Running the agents (locally or via the deployed service) signs real txs, so a **CAW TSS signer** must be up
and connected to the relay. The hosted setup runs it always-on on Railway (`agentworks-tss`); to drive runs
locally instead, run `cobo-tss-node` per wallet profile - one node per relay identity, so don't run the local
and Railway signers at the same time. Setup + the VM/Railway signer guide: **[docs/DEPLOY.md](docs/DEPLOY.md)**.
If `pnpm --filter web dev` errors on an ignored `sharp` build, run `web/node_modules/.bin/next dev` directly.

## Track-rules compliance
| Track rule | How AgentWorks meets it |
|---|---|
| Agents + fund operations | An autonomous pool (1 client, 2 providers) runs an open USDC job-escrow marketplace |
| Fund operations via CAW | Every on-chain action is a CAW `contract_call` (verified txs above) |
| Real fund execution (payment / **settlement**) | Real MockUSDC escrowed and **settled** on Sepolia - payout *and* refund, with tx hashes |
| Demonstrate CAW value (wallet mgmt · **permission control** · **security isolation** · autonomous payment) | Scoped Pacts (`agents/pacts.py`), the denial + freeze + review beats, a provider Pact that can't touch funds, agents paying autonomously through their own wallets |
| Runnable / demonstrable prototype | A deployed autonomous service + a live dashboard + real on-chain txs - not a slide deck |

Full submission checklist with every value filled in: **[docs/SUBMISSION.md](docs/SUBMISSION.md)**.
