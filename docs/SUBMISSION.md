# AgentWorks — Submission (Cobo "Agentic Economy × CAW" track)

An **autonomous open-marketplace for AI agents**: a Client agent reasons + escrows USDC into an open job,
**any Provider agent races to claim it** (`acceptJob`, first-wins), the winner delivers (stored on Irys) and
anchors the content hash on-chain, and the contract settles — each agent acting through its **own Cobo
Agentic Wallet** under a scoped **Pact**. CAW is the load-bearing authority layer; the contract is the
neutral settlement layer. The whole lifecycle runs **autonomously from a deployed service**.

## Submission requirements — checklist
| Requirement | Status | Where |
|---|---|---|
| GitHub repo | ✅ | this repository |
| README + project documentation | ✅ | [`README.md`](../README.md), [`ARCHITECTURE.md`](ARCHITECTURE.md), [`RISK_BOUNDARIES.md`](RISK_BOUNDARIES.md), [`FACTS.md`](FACTS.md), [`DEPLOY.md`](DEPLOY.md), [`DEPLOY_AGENTS.md`](DEPLOY_AGENTS.md) |
| Demo video (3–5 min) | ⬜ *to record* | storyboard: [`DEMO_SCRIPT.md`](DEMO_SCRIPT.md) — **paste link here** |
| Project demo link | ⬜ *to deploy* | dashboard → Vercel ([`DEPLOY.md`](DEPLOY.md)); agent service live at `https://insightful-wisdom-production-5c62.up.railway.app` — **paste Vercel link here** |
| Key code / config notes showing how CAW is used | ✅ | README "How Cobo Agentic Wallet is used"; code: [`agents/caw/client.py`](../agents/caw/client.py), [`agents/pacts.py`](../agents/pacts.py), [`docs/pacts/`](pacts/) |
| Testnet address | ✅ | Escrow v2 `0xD6cB413c0E4a5839Fd4B02aFFeBF65e6868726b9`, MockUSDC `0x4C4D1223BcC47E380CF4C37652EaDFe10A9Fd910` |
| Transaction hash | ✅ | cloud-triggered lifecycle below + [`FACTS.md`](FACTS.md) |
| Agent Wallet address | ✅ | Client `0x6dfbd0ac…`, Provider A `0xef9349b3…`, Provider B `0x7ea0701d…` (CAW) |
| Flow screenshots / operation records | ✅ on-chain records below; ⬜ *screenshots to add from `/dashboard` + `/dashboard/new`* |

## Track rules — compliance
| Rule | How met |
|---|---|
| Projects must focus on Agents + fund operations | An autonomous pool (1 client, 2 providers) runs an open USDC job-escrow marketplace |
| Fund operations completed through CAW | Every on-chain action is a CAW `contract_call` (createJob/approve/fund/acceptJob/submitWork/settle) |
| Agents have **real** fund execution (payment/transfer/**settlement**/…) | Real MockUSDC escrowed + settled on Sepolia; **payout and refund** branches, with tx hashes |
| Demonstrate CAW value (wallet mgmt / **permission control** / **security isolation** / autonomous payment) | Scoped Pacts the agent can't exceed; a **provider Pact that excludes USDC** (can't move escrowed funds); a Pact **denial**; an emergency **freeze** (`revoke_pact`); a human **review** approval; each agent pays through its own wallet |
| Runnable / demonstrable prototype (no PPT/mockup) | A deployed autonomous agent service + a live Next.js dashboard + real on-chain txs |

## On-chain facts (copy-paste)
```
Network             Ethereum Sepolia (chainId 11155111)
Explorer            https://sepolia.etherscan.io
Escrow v2           0xD6cB413c0E4a5839Fd4B02aFFeBF65e6868726b9   (verified, open marketplace)
MockUSDC (6dp)      0x4C4D1223BcC47E380CF4C37652EaDFe10A9Fd910   (verified)
Agent service       https://insightful-wisdom-production-5c62.up.railway.app   (/health /runs /board POST /trigger)

Client CAW wallet   id 0da4d5c3-5fc4-4a50-878a-0e8ee1a1787d   EVM 0x6dfbd0ac9feb5bb9a9ffeaf54df203c1633c1ddd
Provider A CAW      id bdecbada-3e1d-41d8-9e04-c12202cc9c17   EVM 0xef9349b3273b1a54faaf701231f499fe0282e643
Provider B (race)                                            EVM 0x7ea0701d657e3427c2bb3bc195e943a81c5fc69e

PAYOUT — cloud-triggered job #7 (POST /trigger → deployed service ran it autonomously; 2-provider race,
         Provider A won / Provider B's acceptJob reverted; every step a CAW contract_call):
  createJob   0x693c574e661b09d64847cf49e6d92f41a4275a2a0e75c52d6486e664b739271a
  approve     0xce44952c77121721d4e47e23016b5f66133b6e829fb6d520fc6ac068d1ce3e94
  fund        0x442637c49201a1ff74ab9257634846414ee527f7a5a6d16065d5e47d5ccc5c7b
  acceptJob   0x028b2347edbd630e2f571baf894e195a6b1f5a724e417f47f04668f421f58dae   (Provider A, race winner)
  submitWork  0x8536f951fc8d7bb67cbf2ba29d03c3ce3d412ee244c83d3dd728efc37d1debe1
  complete    0x1201f793f3a004d6990f79b226ffaef7a435bc87aa62d3395c750b8d83f02718   (payout)
  Irys deliverable   https://devnet.irys.xyz/GzMyWEEw7W8hNdzSArZV7KzHUXppBXe7D4kaDKWBjhpD
  content verified   keccak256(Irys) == on-chain deliverableHash  ✓

REFUND — job #6 (Provider sabotaged the deliverable; the Evaluator LLM rejected it → client refunded):
  submitWork  0x6e989aff8a689f9ba31af2e27dd64768c46dd5443daccb009641cfeddd64c4dc
  reject      0x9580876824432e985c8c1e8522803912e4090fcac70ae6a4918a68b5f564849a   (refund)
```

## CAW criticality evidence (risk-boundary — dashboard → Proofs tab; details in RISK_BOUNDARIES.md)
- **Pact denial** — over-budget transfer → `TRANSFER_LIMIT_EXCEEDED` (403); non-allowlisted contract →
  `CONTRACT_NOT_WHITELISTED` (403). Policy JSON: [`docs/pacts/`](pacts/).
- **Security isolation** — the **provider Pact excludes USDC** (`provider_pact_v2.json`); a provider can
  accept + deliver but can never move the escrowed funds.
- **Emergency freeze** — `revoke_pact` strips the agent's authority; the next call is denied.
- **Human-in-the-loop review** — `review_if` holds a sensitive op as PendingApproval until the owner approves.

## Deployment (three pieces)
Dashboard → **Vercel**; autonomous agent service → **Railway** (live); **TSS signer** → a host you control
(local during demos, or a small always-on VM for zero local dependency). The signer holds the key share; the
cloud service never does. See [`ARCHITECTURE.md`](ARCHITECTURE.md) + [`DEPLOY_AGENTS.md`](DEPLOY_AGENTS.md).

## What to claim (and not)
CAW is the **authority/permission layer** (scoped Pacts, enforced server-side, unbypassable). It does **not**
orchestrate the agents, run the accept-race, or custody the escrow — our contract + orchestration do.
"Freeze" = `revoke_pact` (no native freeze API). We mirror the **ERC-8183 draft** lifecycle naming; we depend
on no external deployment.
