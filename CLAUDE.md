# CLAUDE.md — AgentWorks Operating Manual

This file is the persistent contract for this project. Read it at the start of every
session and after every context compaction. It governs HOW you work here. When it
conflicts with a one-off instruction, follow this file and flag the conflict.

This file holds STABLE law (decisions, protocol, conventions). Volatile, discovered
facts — exact SDK signatures, deployed addresses, env var names — live in
`docs/FACTS.md` and are written there ONLY after they are verified. Never put an
unverified specific in this file.

═══════════════════════════════════════════════════════════════════════
## 1. THE PROJECT
═══════════════════════════════════════════════════════════════════════

### 1.1 What AgentWorks is
A trustless two-agent job-escrow marketplace for the Cobo "Agentic Economy × Cobo
Agentic Wallet" hackathon track.

A **Client Agent** posts a paid task and escrows USDC in our on-chain escrow contract.
A **Provider Agent** performs the task, stores the deliverable on Irys, and submits its
content hash on-chain. On acceptance the contract pays the Provider; on rejection or
expiry the Client reclaims funds. Each agent acts through its OWN Cobo Agentic Wallet
(CAW), governed by a scoped Pact. CAW is the load-bearing authority layer; our escrow
contract is the neutral settlement layer.

### 1.2 The lifecycle (mirrors ERC-8183 draft naming)
`createJob → fund → submitWork → complete (payout) | reject (refund) | claimRefund (expiry)`

### 1.3 The two actors and the third role
- **Client Agent** — owns Client CAW wallet. Decides a task is worth funding, creates
  and funds the job, evaluates the deliverable (or delegates to the evaluator).
- **Provider Agent** — owns Provider CAW wallet. Decides to accept the job, does REAL
  work, stores it on Irys, submits the content hash on-chain, receives payout.
- **Evaluator** — accept/reject decision. v1: Client-controlled rule-based or LLM judge
  (the ERC-8183 reference lets the client also be evaluator). Keep it a distinct,
  swappable component so we can later make it independent.

### 1.4 Definition of done (whole project)
A judge watches ONE continuous run where: the Client Agent reasons about and funds a job,
the Provider Agent does real work and submits a verifiable deliverable hash, the contract
pays out on acceptance (and refunds on a separately-shown rejected run), and CAW visibly
blocks an over-budget action and supports an emergency freeze — all with on-chain traces
the judge can open themselves.

═══════════════════════════════════════════════════════════════════════
## 2. THE FIVE JUDGING CRITERIA — optimize EVERY decision against these
═══════════════════════════════════════════════════════════════════════

This is a competition. The goal is first place. Every design choice is judged against:

1. **Scenario relevance** — clear Agentic Commerce; two autonomous economic actors.
   The agents must GENUINELY REASON at decision points (fund? accept? approve?), not be
   scripted timers. A cron job in an agent costume fails this. If you find yourself
   writing a hardcoded sequence with no decision, stop and tell me.
2. **CAW criticality** — CAW must be LOAD-BEARING, not a replaceable signer. Both agents
   are constrained by Pacts (budget cap + contract allowlist). The demo MUST show three
   beats: (a) successful job→escrow→payout, (b) a Pact DENIAL (over-budget or
   non-whitelisted contract), (c) an emergency FREEZE. These three beats are the proof of
   criticality — protect them above polish.
3. **Funds-flow completeness** — task trigger → escrow → settlement, on-chain, with BOTH
   the payout branch AND the refund-on-reject branch shown.
4. **Demonstrability** — runs LIVE and DETERMINISTICALLY on testnet. No market luck, no
   step that "usually works." If a step is flaky, we make it deterministic or we cut it.
5. **Risk-boundary description** — we ship the literal Pact policy JSON, a demonstrated
   blocked transaction, and the escrow expiry/refund logic as FIRST-CLASS deliverables.
   The track marks this "(if applicable)"; most entrants skip it; we treat it as core.

Where we are strongest: criteria 2 and 5 (most projects fail these). Protect that edge.

═══════════════════════════════════════════════════════════════════════
## 3. CLAIMS DISCIPLINE — what we may and may NOT say
═══════════════════════════════════════════════════════════════════════

Overclaiming loses technical judges instantly. Be precise.

TRUE, say freely:
- "CAW is the scoped-authority layer that makes autonomous agent spending safe; neither
  agent can exceed its Pact."
- "Our escrow contract is the neutral settlement layer between two distrustful agents."
- "We mirror the ERC-8183 draft lifecycle naming."

FALSE / FORBIDDEN claims:
- That CAW orchestrates the agent economy, performs the A2A coordination, or holds the
  escrow. It does NOT — our contract + our orchestration do. CAW enforces each agent's
  authority boundary, nothing more.
- That ERC-8183 is a finalized standard. It is a DRAFT EIP we mirror in naming. We do not
  depend on any external/Arc reference deployment.
- Any traction, volume, or market-size figure stated as current fact. (Public agentic-
  commerce figures are projections or test-inflated. If you reference one, mark it as a
  projection and cite it; otherwise omit.)

If you are about to write a claim into a README, demo script, or comment and you cannot
back it from a verified source, flag it instead of writing it.

═══════════════════════════════════════════════════════════════════════
## 4. VERIFICATION PROTOCOL — non-negotiable, overrides optimism
═══════════════════════════════════════════════════════════════════════

I have caught AI coding agents fabricating "done" status before. This is the single worst
failure mode on this project. The following overrides any instinct to report progress
favorably.

### 4.1 The three states — label EVERY deliverable
- ✅ **VERIFIED** — I ran it; the output/proof is in this message.
- 🔧 **WRITTEN-UNVERIFIED** — code exists, not yet run or tested.
- ❌ **NOT STARTED / BLOCKED** — with the reason.

### 4.2 Proof requirements
- Never say "done / working / deployed / passing / it works" without proof IN THE SAME
  MESSAGE. Proof = command output, test result, tx hash + explorer URL, file diff, or a
  screenshot path. No proof → the word is "UNVERIFIED."
- On-chain "verified" REQUIRES a real tx hash openable on BaseScan Sepolia. Paste the hash
  and the full explorer URL.
- CAW-call "verified" REQUIRES the actual SDK response object or audit-log entry, pasted
  verbatim — never a paraphrase or a "should return."
- "Tests pass" REQUIRES the test runner output showing the count and the green result.

### 4.3 Anti-fabrication rules
- NEVER invent SDK method names, function signatures, parameters, return shapes, env var
  names, or contract addresses. If you are not certain something exists, STOP and read the
  real source. Inventing an API surface is a critical failure, worse than saying "I don't
  know."
- When a test or command fails, report it plainly. NEVER make it pass by deleting the
  assertion, mocking the unit under test, weakening the check, adding `try/except: pass`,
  or hardcoding the expected value. A red test reported honestly is worth more than a
  green lie. If you are tempted to do any of these, surface it to me instead.
- Do not summarize multiple unverified steps as one "done." Each step gets its own state.
- If you guessed at something, say "I GUESSED:" and explain what needs confirming.

### 4.4 Phase Verification Block (end of every phase)
Output a table: each phase deliverable | state (✅/🔧/❌) | proof artifact (path, hash,
URL, or output snippet). No block, no phase boundary.

═══════════════════════════════════════════════════════════════════════
## 5. HOW WE WORK
═══════════════════════════════════════════════════════════════════════

### 5.1 Phased execution
- Build in PHASES (section 8). Complete ONE phase, produce its Verification Block, then
  STOP for my confirmation. Do not start the next phase unprompted.
- Within a phase, prefer the smallest thing that PROVES the loop over the most impressive
  thing. A complete small loop beats an incomplete big one — that is the lesson from every
  prior winner in this space.

### 5.2 Before touching CAW
Read the real docs/source and confirm method names, parameters, and the Pact `spec` shape
from the ACTUAL source — not memory, not this file. Sources:
- PyPI: `cobo-agentic-wallet`
- GitHub: github.com/CoboGlobal/cobo-agentic-wallet
- API base: https://api.agenticwallet.cobo.com
Write what you confirm into `docs/FACTS.md` with the date and source.

### 5.3 Research before guessing
If a CAW capability, chain detail, or library API is uncertain, check the source before
writing code against it. A five-minute read beats an hour debugging a hallucinated method.

### 5.4 Secrets & safety
- All secrets in `.env`; commit only `.env.example` with placeholder keys.
- Never echo my private keys, mnemonics, or invitation codes back to me or into logs.
- Never commit a `.env`, a keystore, or anything with a real key. Check before every commit.
- Testnet only. If any instruction would touch mainnet or real funds, STOP and confirm.

### 5.5 Asking vs proceeding
- Locked decisions (section 6): do not relitigate; if you think one is wrong, raise it
  once, briefly, then defer to me.
- Genuinely ambiguous forks not covered here: ask one crisp question rather than guessing.
- Everything else: proceed and report.

═══════════════════════════════════════════════════════════════════════
## 6. LOCKED TECHNICAL DECISIONS (do not relitigate without asking)
═══════════════════════════════════════════════════════════════════════

- **Chain:** Base Sepolia. Fallback: Ethereum Sepolia IF Phase 0/2 shows weak CAW Base
  support. Decide the fallback only with verified evidence, not assumption.
- **Token:** USDC testnet on Base Sepolia. ATTEMPT REAL Base Sepolia USDC FIRST (decided
  2026-06-03); verified on-chain address + decimals are in FACTS.md. Fall back to our own
  test ERC-20 (`MockUSDC`) only if the faucet/CAW support is unreliable — acceptable and
  keeps the demo deterministic.
- **Escrow:** self-deployed Solidity contract via Foundry, invoked through CAW's generic
  `contract_call` (we pass our own ABI-encoded calldata; CAW does NOT validate custom-contract
  semantics — safety rests on the Pact `target_in` allowlist + our Foundry tests). No
  dependence on external/Arc deployments. We own and verify it.
- **Evaluator:** a distinct `evaluator` address recorded PER-JOB at `createJob`; `complete`
  and `reject` are gated to that address. v1: the Client controls it (client-as-evaluator),
  but it stays a separate, swappable component so it can later be made independent. (Decided 2026-06-03.)
- **Emergency freeze:** there is NO native CAW freeze/pause method (verified — see FACTS.md).
  The criticality-beat "freeze" is implemented as `revoke_pact(pact_id)`, which strips the
  agent's scoped authority. Use accurate language in demo/README — never claim a freeze API.
- **CAW SDK:** Python (`cobo-agentic-wallet`, v0.1.40 confirmed). Two wallets (Client,
  Provider), two Pacts. All client methods are `async`; authority flows through a
  PACT-SCOPED api key (see FACTS.md "how authority is scoped").
- **Agent runtime:** Python. Direct SDK calls FIRST. Add an agent framework (LangChain /
  OpenAI Agents SDK) only where it demonstrably earns its place — not by default.
- **Deliverable storage:** Irys.
- **Frontend:** Next.js 15 dashboard. It is the DEMO SURFACE and is built LAST.
- **Repo:** pnpm monorepo.

═══════════════════════════════════════════════════════════════════════
## 7. REPO LAYOUT & CONVENTIONS
═══════════════════════════════════════════════════════════════════════

### 7.1 Layout
- `/contracts` — Foundry: escrow contract, tests, deploy/verify scripts.
- `/agents`    — Python: CAW integration layer, Client Agent, Provider Agent, evaluator,
                 shared config.
- `/web`       — Next.js 15 dashboard (demo surface).
- `/docs`      — README, ARCHITECTURE (diagram), RISK_BOUNDARIES, DEMO_SCRIPT, FACTS.md.
- root         — pnpm workspace config, `.gitignore`, `.env.example`, this file.

### 7.2 docs/FACTS.md — the living truth file
Every verified specific goes here with date + source: confirmed SDK signatures, the real
Pact `spec` JSON, deployed contract addresses, wallet addresses, env var names, faucet
URLs, chain IDs. This file is how we avoid re-deriving facts and avoid trusting guesses.
If a fact isn't in FACTS.md and isn't verified live, treat it as unknown.

### 7.3 Conventions
- Solidity: clear events on every state transition (judges read events on the explorer).
  Name events to mirror the lifecycle (`JobCreated`, `JobFunded`, `WorkSubmitted`,
  `JobCompleted`, `JobRejected`, `RefundClaimed`). Custom errors over `require` strings.
- Python: typed, small modules; the CAW integration is one isolated layer the agents call,
  so a CAW SDK change touches one file.
- Commits: small, present-tense, one logical change each. Never commit secrets.
- Logging: agents log their REASONING and every CAW call + response, so the audit trail is
  legible in the demo.

═══════════════════════════════════════════════════════════════════════
## 8. PHASE MAP
═══════════════════════════════════════════════════════════════════════

Detailed per-phase prompts are delivered separately, one at a time. High level:

- **Phase 0** — Recon & scaffold: toolchain versions, CAW SDK reality-check (write findings
  to FACTS.md), propose escrow interface, init empty monorepo skeleton, list risks.
- **Phase 1** — Escrow contract in Foundry: full lifecycle, both branches, complete test
  suite, deploy + verify on BaseScan (paste address + tx hashes).
- **Phase 2** — CAW hello-world: two wallets created, a transfer, audit-log read, on the
  chosen testnet (paste SDK responses + tx hashes).
- **Phase 3** — Agents drive the contract via `contract_call`: full lifecycle headless,
  both payout and refund branches.
- **Phase 4** — Pacts: budget cap + contract allowlist; the DENIAL demo; the FREEZE demo;
  the refund-on-reject run.
- **Phase 5** — Irys deliverable storage + on-chain content-hash verification.
- **Phase 6** — Next.js dashboard: balances, job state machine, deliverable hash, audit-log
  denials, explorer links. The demo surface.
- **Phase 7** — Demo script + video, README, architecture diagram, risk-boundary doc.

Phase boundaries are hard stops. Do not cross one without my confirmation.

═══════════════════════════════════════════════════════════════════════
## 9. RISKS TO STAY AHEAD OF (from prior research)
═══════════════════════════════════════════════════════════════════════

- **CAW SDK method shapes** are the top fabrication risk — the docs site is partly client-
  rendered and some specifics couldn't be confirmed remotely. Always read source first;
  record in FACTS.md.
- **CAW is single-wallet-scoped** — there is NO native multi-wallet/A2A coordination
  primitive. The A2A logic lives in OUR contract + orchestration. Do not design as if CAW
  coordinates the agents; it enforces each one's boundary.
- **Custom contracts get no Recipe-level validation** — we supply correct ABI/calldata and
  lean on the Pact contract-allowlist for safety. Test exhaustively in Foundry first.
- **Pact approval latency** could make a live demo flaky — develop in pre-pairing mode,
  enable Pact enforcement only for the criticality beats, and keep a backup recording.
- **Faucet reliability** — if testnet USDC is flaky, switch to our own MockUSDC to keep the
  demo deterministic (criterion 4 outranks "uses real USDC").