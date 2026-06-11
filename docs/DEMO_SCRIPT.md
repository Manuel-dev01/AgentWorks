# AgentWorks — demo video storyboard (3–5 min)

One continuous run a judge can follow, hitting all five judging criteria + CAW's value. **Before recording:**
start both CAW TSS signer nodes (see [`FACTS.md`](FACTS.md)), then `pnpm --filter web dev`; open
`http://localhost:3000`. Keep an Etherscan tab ready. Total ≈ 4 min.

---

### 0 · Hook (0:00–0:25)
**Say:** "Two AI agents can act on-chain — but they can't trust each other with money. A Provider won't
work without a guarantee of payment; a Client won't pay before seeing the work. AgentWorks resolves that with
neutral on-chain escrow, where each agent acts through its **own Cobo Agentic Wallet** under a scoped Pact."
**Show:** the landing page (`/`) hero, then click **Launch app**.

### 1 · Marketplace — state at a glance (0:25–0:45)
**Say:** "This board is read **live from Ethereum Sepolia** — every escrow, lifecycle-colored." 
**Show:** `/dashboard` — the jobs, the "● live" indicator, the in-escrow / settled / reclaimed stats.
*(Criterion 3: funds-flow completeness.)*

### 2 · Post a job — real escrow (0:45–1:45)
**Say:** "I'll author a job. The Client agent **reasons** about whether to fund it, then escrows USDC — each
step a real CAW `contract_call`." 
**Show:** `/dashboard/new` → type a task + acceptance criteria + reward → **Escrow & post job**. Point out the
**LLM fund decision** card, then the createJob / approve / **fund** tx hashes. **Click one → Etherscan**, show
it confirmed from the Client CAW wallet. *(Criteria 1 + 3; real fund execution through CAW.)*

### 3 · Provider delivers + proves (1:45–2:30)
**Say:** "The Provider binds its own Pact — it can only `submitWork`, it can't move the escrowed funds. It does
the work, stores it on **Irys**, and anchors the content hash on-chain." 
**Show:** **Accept job** → **Submit** → the **Irys** deliverable link (open it) + the **submitWork** tx.
*(Criterion 2: each agent's authority is scoped; criterion 4: verifiable deliverable.)*

### 4 · Settle — payout (2:30–3:00)
**Say:** "The evaluator agent judges the Irys deliverable against the spec and the contract settles —
the Provider is paid. And we verify `keccak256(Irys) == the on-chain hash`." 
**Show:** **Run evaluation & settle** → the receipt: **Paid to provider**, the **settle() tx** (open it), the
**content-verified** badge. Mention: the **refund** branch (reject → reclaim) is the same flow with a
sabotaged deliverable — visible on the Marketplace as a Reclaimed job. *(Criterion 3: both branches.)*

### 5 · CAW criticality — the money shot (3:00–3:45)
**Say:** "This is what makes autonomous spending **safe**. A Pact is enforced server-side by CAW — the agent
can't exceed it no matter what its LLM decides." 
**Show:** the **Proofs** tab —
- **Pact denial:** real codes `TRANSFER_LIMIT_EXCEEDED` + `CONTRACT_NOT_WHITELISTED` (403).
- **Emergency freeze:** `revoke_pact` → the next call is denied.
- **Human review:** `review_if` → PendingApproval → approved → executed.
- The **literal Pact JSON** (allowlist + caps).
*(Criteria 2 + 5 — our strongest edge: permission control, security isolation, risk boundary.)*

### 6 · Close (3:45–4:00)
**Say:** "Real USDC settlement between two distrustful agents, every fund operation through Cobo Agentic
Wallet, with permission control and an emergency freeze — running live on testnet, not a mockup. Every
address and transaction is in the README." 
**Show:** the Marketplace with the new settled job; cut to the README's on-chain facts.

---

**Criteria coverage:** 1 (genuine reasoning at fund/accept/settle) · 2 (CAW load-bearing: scoped Pacts +
denial + freeze) · 3 (escrow → settlement, both branches, on-chain) · 4 (live + deterministic on testnet) ·
5 (risk boundary: shipped Pact JSON + blocked tx + refund logic).
