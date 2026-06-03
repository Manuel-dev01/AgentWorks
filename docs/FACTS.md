# FACTS.md — Verified Project Facts

THE RULES FOR THIS FILE:
- Every entry MUST have a verification date and a source (command run, file/URL read,
  tx hash). No source → it does not belong here.
- A blank or `UNKNOWN — not yet verified` means exactly that: unknown. It does NOT mean
  "use a sensible default." Code must not assume a value that isn't confirmed here.
- If a fact changes, update it AND note what changed and why. Never silently overwrite.
- If something here is later found wrong, mark it `CORRECTED (was: ...)` — don't delete history.

Format per entry:  `value`  — verified YYYY-MM-DD — source: <how it was confirmed>

═══════════════════════════════════════════════════════════════════════
## Toolchain (Phase 0)
═══════════════════════════════════════════════════════════════════════
- Foundry / forge version: UNKNOWN — not yet verified
- Python version: UNKNOWN — not yet verified
- Node version: UNKNOWN — not yet verified
- pnpm version: UNKNOWN — not yet verified

═══════════════════════════════════════════════════════════════════════
## CAW SDK — confirmed surface (Phase 0)  [top fabrication risk — source everything]
═══════════════════════════════════════════════════════════════════════
- Install command: UNKNOWN — not yet verified
- Onboarding command(s): UNKNOWN — not yet verified
- Python client class + import path: UNKNOWN — not yet verified
- Method — create/onboard wallet: UNKNOWN (signature + params + return) — not yet verified
- Method — submit Pact: UNKNOWN — not yet verified
- Method — transfer_tokens: UNKNOWN — not yet verified
- Method — contract_call: UNKNOWN (how calldata/ABI is passed) — not yet verified
- Method — read balance: UNKNOWN — not yet verified
- Method — read audit logs: UNKNOWN — not yet verified
- Method — emergency freeze: UNKNOWN — not yet verified
- Pact `spec` JSON shape (policies + completion_conditions): UNKNOWN — not yet verified
  (paste a REAL confirmed example here once verified)

═══════════════════════════════════════════════════════════════════════
## Chain & network (Phase 0 / Phase 2)
═══════════════════════════════════════════════════════════════════════
- Chosen chain: Base Sepolia (per CLAUDE.md §6) — fallback decision: not yet triggered
- Chain ID: UNKNOWN — not yet verified
- CAW chain identifier string (e.g. for Pact `chain_in`): UNKNOWN — not yet verified
- RPC URL in use: UNKNOWN — not yet verified
- Block explorer base URL: UNKNOWN — not yet verified
- Faucet URL + reliability note: UNKNOWN — not yet verified
- USDC testnet token address / decimals: UNKNOWN — not yet verified
- (If MockUSDC deployed instead) address + decimals: not yet deployed

═══════════════════════════════════════════════════════════════════════
## Deployed artifacts (Phase 1+)
═══════════════════════════════════════════════════════════════════════
- Escrow contract address: not yet deployed
- Escrow deploy tx hash + explorer URL: not yet deployed
- Escrow ABI location (path in repo): not yet generated
- Client CAW wallet address: not yet created
- Provider CAW wallet address: not yet created
- Client Pact id: not yet created
- Provider Pact id: not yet created

═══════════════════════════════════════════════════════════════════════
## Env vars (names only — values live in .env, never here)
═══════════════════════════════════════════════════════════════════════
- (list each env var name as it is introduced, with one line on what it's for)