# AgentWorks — demo video storyboard (3–5 min)

One continuous run a judge can follow, hitting all five judging criteria + CAW's value. The headline is
**autonomy**: post a job and the deployed agent service drives the whole lifecycle on its own, with two
providers racing on-chain.

**Before recording:** make sure a **CAW TSS signer is up** and connected to the relay (locally per
[`FACTS.md`](FACTS.md), or the always-on VM per [`DEPLOY_AGENTS.md`](DEPLOY_AGENTS.md)) — the deployed agent
service signs through it. Open the hosted dashboard (Vercel) or `pnpm --filter web dev` →
`http://localhost:3000`. Keep an Etherscan tab ready. Total ≈ 4 min.

---

### 0 · Hook (0:00–0:25)
**Say:** "Two AI agents can act on-chain — but they can't trust each other with money. AgentWorks is an
**open marketplace** where a Client agent escrows a job, any Provider agent can race to claim it, and a
neutral contract settles — each agent acting through its **own Cobo Agentic Wallet** under a scoped Pact it
can't exceed."
**Show:** the landing page (`/`) hero, then **Launch app**.

### 1 · Post a job → the agents take over (0:25–1:30)
**Say:** "I'll post a task. From here it's **autonomous** — the deployed agent service runs it: the Client
agent reasons about funding and escrows USDC, then **two providers reason and race** to claim it."
**Show:** **New job** (`/dashboard/new`) → type a task + acceptance criteria + reward → **Post job → trigger
the agents**. Point out "● agents live" and the live step strip. *(Criteria 1 + 3: genuine reasoning, real
fund flow.)*

### 2 · Watch it settle, on-chain (1:30–2:30)
**Say:** "Every decision here is the agents' own, and every step is a real CAW `contract_call`." 
**Show:** the run card as it lands —
- the **Client · fund** LLM decision,
- **Provider A: ACCEPT — won the on-chain race**; **Provider B: ACCEPT — lost the race (acceptJob reverted)**
  (single acceptance enforced by the contract, live),
- the tx chips: createJob → fund → acceptJob → submitWork → complete. **Click `complete` → Etherscan**, show
  it confirmed; **open the Irys deliverable**; note **content_verified ✓** (`keccak256(Irys) == on-chain hash`).
*(Criterion 2: scoped authority; criterion 4: verifiable deliverable; the accept-race is the open-market proof.)*

### 3 · The refund branch (2:30–3:00)
**Say:** "If the work is bad, the client doesn't pay. Same flow, sabotaged deliverable." 
**Show:** post another with **Provider behavior → Sabotage → expect refund** (or point to the existing
**Refunded** job in Marketplace). The **Evaluator** card reads **REJECT** with its reason; the **reject** tx
refunds the client. *(Criterion 3: both branches, on-chain.)*

### 4 · Marketplace — the proof history (3:00–3:20)
**Say:** "Every settled escrow lives here, read live from Sepolia — the autonomous track record." 
**Show:** **Marketplace** (`/dashboard`) — the run cards, the Paid-out / Refunded / settlement-rate stats,
open one for its full on-chain receipt. *(Criterion 3: funds-flow completeness.)*

### 5 · CAW criticality — the money shot (3:20–3:50)
**Say:** "This is what makes autonomous spending **safe**. A Pact is enforced server-side by CAW — the agent
can't exceed it no matter what its LLM decides." 
**Show:** the **Proofs** tab —
- the **participants**: Client + two Providers, each bound by a scoped Pact; the **provider Pact omits USDC**
  → a provider can never move escrowed funds.
- **Pact denial:** real codes `TRANSFER_LIMIT_EXCEEDED` + `CONTRACT_NOT_WHITELISTED` (403).
- **Emergency freeze:** `revoke_pact` → the next call is denied.
- **Human review:** `review_if` → PendingApproval → approved → executed.
- the **literal Pact JSON**.
*(Criteria 2 + 5 — our strongest edge: permission control, security isolation, risk boundary.)*

### 6 · Close (3:50–4:00)
**Say:** "An autonomous agent marketplace settling real USDC between distrustful agents — every fund
operation through Cobo Agentic Wallet, with a provider that can't touch the funds and an instant freeze —
running live on testnet, triggered from a deployed service. Every address and transaction is in the README."
**Show:** the Marketplace with the fresh settled job; cut to the README's on-chain facts.

---

**Criteria coverage:** 1 (genuine reasoning at fund/accept/evaluate) · 2 (CAW load-bearing: scoped Pacts +
denial + freeze; provider can't move funds) · 3 (escrow → settlement, both branches, on-chain) · 4 (live on
testnet, triggered from the deployed service) · 5 (risk boundary: shipped Pact JSON + blocked tx + refund
logic — see [`RISK_BOUNDARIES.md`](RISK_BOUNDARIES.md)).

**Determinism / backup:** the dashboard seeds from verified runs (`web/data/market/`), so the Marketplace and
job receipts render even if the backend sleeps or the network is flaky. Keep a backup recording of a known-good
autonomous run in case live signing hiccups (CAW relay reconnects can stall a signature ~1–3 min).
