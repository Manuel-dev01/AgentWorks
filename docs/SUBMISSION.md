# AgentWorks — Submission (Cobo "Agentic Economy × CAW" track)

A trustless **two-agent job-escrow marketplace**: a Client agent escrows USDC for a task, a Provider agent
delivers (stored on Irys) and submits the content hash on-chain, and the escrow contract settles — each agent
acting through its **own Cobo Agentic Wallet** under a scoped **Pact**. CAW is the load-bearing authority layer;
the contract is the neutral settlement layer.

## Submission requirements — checklist
| Requirement | Status | Where |
|---|---|---|
| GitHub repo | ✅ | this repository |
| README + project documentation | ✅ | [`README.md`](../README.md), [`docs/FACTS.md`](FACTS.md), [`docs/DEPLOY.md`](DEPLOY.md), this file |
| Demo video (3–5 min) | ⬜ *to record* | storyboard: [`docs/DEMO_SCRIPT.md`](DEMO_SCRIPT.md) — **paste link here** |
| Project demo link | ⬜ *to deploy* | Vercel (see [`docs/DEPLOY.md`](DEPLOY.md)) — **paste link here** |
| Key code / config notes showing how CAW is used | ✅ | README "How Cobo Agentic Wallet is used"; code: [`agents/caw/client.py`](../agents/caw/client.py), [`agents/pacts.py`](../agents/pacts.py), [`docs/pacts/`](pacts/) |
| Testnet address | ✅ | Escrow `0x812BcEEc2De8C8aC71C7af7A8E2d4467E65Fdf18`, MockUSDC `0x4C4D1223BcC47E380CF4C37652EaDFe10A9Fd910` |
| Transaction hash | ✅ | full lifecycle below + [`docs/FACTS.md`](FACTS.md) |
| Agent Wallet address | ✅ | Client `0x6dfbd0ac…`, Provider `0xef9349b3…` (CAW) |
| Flow screenshots / operation records | ✅ on-chain records below; ⬜ *screenshots to add from `/dashboard/new`* |

## Track rules — compliance
| Rule | How met |
|---|---|
| Projects must focus on Agents + fund operations | Two autonomous agents run a USDC job-escrow marketplace |
| Fund operations completed through CAW | Every on-chain action is a CAW `contract_call` (createJob/approve/fund/submitWork/settle) |
| Agents have **real** fund execution (payment/transfer/**settlement**/…) | Real MockUSDC escrowed + settled on Sepolia; **payout and refund** branches, with tx hashes |
| Demonstrate CAW value (wallet mgmt / **permission control** / **security isolation** / autonomous payment) | Scoped Pacts (allowlist + caps) the agent can't exceed; a Pact **denial**; an emergency **freeze** (`revoke_pact`); a human **review** approval; each agent pays through its own wallet |
| Runnable / demonstrable prototype (no PPT/mockup) | Live Next.js dashboard + real on-chain txs + local live agents |

## On-chain facts (copy-paste)
```
Network            Ethereum Sepolia (chainId 11155111)
Explorer           https://sepolia.etherscan.io
Escrow contract    0x812BcEEc2De8C8aC71C7af7A8E2d4467E65Fdf18   (verified)
MockUSDC (6dp)     0x4C4D1223BcC47E380CF4C37652EaDFe10A9Fd910   (verified)

Client CAW wallet  id 0da4d5c3-5fc4-4a50-878a-0e8ee1a1787d   EVM 0x6dfbd0ac9feb5bb9a9ffeaf54df203c1633c1ddd
Provider CAW wallet id bdecbada-3e1d-41d8-9e04-c12202cc9c17   EVM 0xef9349b3273b1a54faaf701231f499fe0282e643

Full lifecycle (job #8, settled via the dashboard, every step a CAW contract_call):
  createJob   0x7a9b6f195455a7368e289a071e28b8a3e4a0d984bd680a65016f9a5e682f41f3
  approve     0xa5318c68b95d6f560a15adf9930de6fb1b421a70fd7510e4886c325d533fdca6
  fund        0x1ce7030502d807b220037dee5a7e7b94c231b6c18c1fe0ab2df8381bcdd31dd0
  submitWork  0x9b5731f947e7fc90ff2750875057fc7f040d8ee38452cb9716e21d3f8046c20d
  complete    0xabcb748af22c77dc31cba6abb460a843338beba1a758f4b88e30c1f3548bc040   (payout)

Second run (job #4, headless):
  createJob   0x01e07e2666c9cbfc75ca7aa9c1f73894b56ebb6d5b2d0364efbfb25c5cd8eac9
  fund        0x56c48a27acd287202294ff52926c17998b6bec2c232995c3a996eaaf453b13e9
  submitWork  0xd2677326763daf02ed15bbbc0f1e47e9d6946166333a450dd8eb6b1aa84d4265
  complete    0x77f93630943e367d490886cb7469cc1b056660a854d7ba5cda3f7d159dc01323
  Irys deliverable   https://devnet.irys.xyz/3GZU7do1TGEseoFJRRRc7E4ywQjMKgpnbTkGmrMo8m4B
  content verified   keccak256(Irys) == on-chain deliverableHash  ✓
```

## CAW criticality evidence (risk-boundary, dashboard → Proofs tab)
- **Pact denial** — over-budget transfer → `TRANSFER_LIMIT_EXCEEDED` (403); non-allowlisted contract →
  `CONTRACT_NOT_WHITELISTED` (403). Policy JSON: [`docs/pacts/`](pacts/).
- **Emergency freeze** — `revoke_pact` strips the agent's authority; the next call is denied.
- **Human-in-the-loop review** — `review_if` holds a sensitive op as PendingApproval until the owner approves.

## What to claim (and not)
CAW is the **authority/permission layer** (scoped Pacts, enforced server-side, unbypassable). It does **not**
orchestrate the two agents or custody the escrow — our contract + orchestration do. "Freeze" = `revoke_pact`
(no native freeze API). We mirror the **ERC-8183 draft** lifecycle naming; we depend on no external deployment.
