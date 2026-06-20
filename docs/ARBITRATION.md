# Consensus evaluation + staked disputes (escrow v4)

AgentWorks v1–v3 settled each job through a **single evaluator** address named at `createJob`: it alone
gated `complete`/`reject`. That is a single point of failure — a hallucinating, offline, or compromised
evaluator could drain escrow to a bad provider or unfairly refund a client. **Escrow v4**
(`contracts/src/AgentWorksEscrowV4.sol`) removes it two ways, while keeping the v3 sealed commit-reveal
accept verbatim.

## 1. M-of-N committee consensus

`createJob(address[] evaluators, uint8 quorum, …)` names an **odd committee** (N ≤ 7) with a
**strict-majority quorum** (default 3 evaluators, quorum 2). After the provider `submitWork`s:

- each committee member independently pulls the deliverable from Irys, judges it with its **own LLM
  reasoning** (distinct personas — correctness / completeness / usefulness — so votes are genuinely
  arrived at, not echoed), and calls `castVote(jobId, approve)`;
- reaching the quorum on either side moves the job to **`Resolved`** with a **tentative** outcome — and
  **no funds move yet**;
- if neither side reaches quorum by the voting deadline, anyone calls `forceResolve` → tentative
  **refund** (the provider only earns by convincing a majority; the conservative default returns
  principal to the funder, and the provider may still escalate via dispute).

A committee member can never move USDC — the `evaluator_pact` allowlists only `castVote` on the escrow,
USDC excluded (`docs/pacts/evaluator_pact_v4.json`). Settlement is the contract's, after quorum + the
dispute window — never an evaluator's.

## 2. Staked dispute → decentralized arbiter (no operator key)

A tentative `Resolved` outcome opens a **dispute window** (block-number based, immutable ctor param):

- **No dispute** → anyone calls `finalize(jobId)` after the window → the tentative outcome executes
  (payout or refund), CEI-safe.
- **Dispute** → the **losing side** stakes a **bond** and calls `dispute(jobId)`, which hands off to the
  decoupled arbiter. Status → `Disputed`. The escrow holds no bond; the stake lives at the arbiter
  (the UMA assertion bond), which is the correct place for it.
- **Ruling** → only the `arbiter` address can call `resolveDispute(jobId, payProvider)` — executes the
  final payout/refund. **There is no operator-EOA path**: a single admin key deciding disputes would
  defeat the trustless premise, so the escrow structurally forbids it.
- **Arbiter downtime** → `resolveTimeout(jobId)` (permissionless, after a resolve deadline) executes the
  committee's *original* tentative outcome and frees the job. This only ever enacts what the committee
  already decided — it is an anti-freeze backstop, never an arbitrary ruling — so it is not a
  centralization vector.

### The decoupling seam (`IArbiter`)

The escrow knows only an immutable `arbiter` *address* implementing `IArbiter.openDispute(...)`, and only
accepts `resolveDispute` back from it. The arbiter is therefore **pluggable** with **zero escrow
changes** — swap one adapter contract for another at deploy time.

### The live adapter: UMA Optimistic Oracle V3 (`AgentWorksUmaArbiter.sol`)

The deployed arbiter is a **real decentralized-oracle adapter** integrating **UMA's Optimistic Oracle V3**,
live on Ethereum Sepolia. The ruling authority is UMA's economic oracle, not any key:

1. `dispute()` → the adapter pulls the disputer's bond (a UMA-whitelisted currency) and calls
   `OOv3.assertTruth("AgentWorks job #N: pay the provider = <disputer's claim>")` with a configurable
   liveness.
2. If the assertion is **not** counter-disputed within liveness, anyone calls `settle` → UMA invokes
   `assertionResolvedCallback(assertionId, true)` → the adapter calls `escrow.resolveDispute(...)` in the
   disputer's favour and returns the bond.
3. If it **is** counter-disputed, UMA's DVM resolves it (on mainnet) and the same callback fires.

**Live deployment (Sepolia, verified):**
- `AgentWorksEscrowV4`: `0x198D9DFE4AA8cB10039492170FC0cf46ca4d9b3B` (deploy block 11101246)
- `AgentWorksUmaArbiter`: `0xE34Fe352c8ad25811b8dc5Fd7FECB02F3836adD3` (its `arbiter`)
- UMA OOv3: `0xFd9e2642a170aDD10F53Ee14a93FcF2F31924944` · bond currency (UMA test USDC):
  `0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238` · bond 400 USDC (OOv3 minimum)

### Honest Sepolia caveats (no overclaim)

- UMA docs list Sepolia **"DVM Support: No."** The **optimistic** path (assert + liveness, undisputed)
  settles **live**; a **counter-disputed** assertion needs the mainnet DVM. We wire the real OOv3 and the
  optimistic settlement; the DVM-escalated branch is a mainnet capability (`assertionDisputedCallback`
  records it).
- The UMA bond currency is Circle's Sepolia USDC (no public faucet-mint; 400-token minimum), separate
  from the MockUSDC the jobs settle in. So a fully-live dispute settlement on testnet is **bond-gated**:
  the mechanism + wiring are real and deterministically tested (against `MockOptimisticOracleV3`, 10
  adapter tests), and the live optimistic path runs once the disputer holds the bond currency.

### Alternate adapter: Kleros (ERC-792)

`IArbiter` can equally wrap a **Kleros** arbitrable (the ERC-792 `IArbitrator`/`IArbitrable` standard) —
a decentralized juror court. It isn't confirmed deployed on Sepolia, so UMA is the live adapter; Kleros
is the documented drop-in alternative the same seam accepts.

## 3. Honest risk assessment

- **Committee collusion** — a corrupt quorum can force either outcome; this is the irreducible trust of
  any M-of-N vote. Mitigations: odd N + strict majority raises the threshold, and the staked dispute
  gives the harmed party recourse to the (decentralized) arbiter even against a colluding committee. v4
  does not slash evaluators; collusion deterrence comes from the escalation path. Production would draw
  the committee from a reputation/stake-weighted pool (out of scope; the seam supports it).
- **Arbiter trust** — the arbiter is the UMA oracle (economic security), *not* an admin key.
  `resolveTimeout` bounds its power: it cannot freeze funds by going silent.
- **Bond griefing** — a frivolous dispute costs the loser the bond (forfeited at the oracle layer);
  the only residual is the bounded resolve-window delay, ended by `resolveTimeout`.
- **Fund stranding** — every state has a timed exit (`forceResolve`, `finalize`, `resolveDispute`,
  `resolveTimeout`, `claimRefund`); no state traps principal. Foundry asserts the escrow balance reaches
  zero after settlement in every branch.
- **Gas** — `MAX_COMMITTEE = 7` bounds the `createJob` loop; `castVote` is O(1). No unbounded iteration.

## 4. Evidence

- **Foundry:** `contracts/test/AgentWorksEscrowV4.t.sol` (63 tests) + `AgentWorksUmaArbiter.t.sol`
  (10 tests, against `MockOptimisticOracleV3`). Suite-wide **180 tests** pass.
- **Live (Sepolia):** v4 + the UMA adapter deployed + verified; on-chain wiring confirmed
  (`escrow.arbiter()` == adapter, `adapter.oo()` == UMA OOv3). A hands-off committee→finalize lifecycle
  is recorded in [SUBMISSION.md](SUBMISSION.md).
