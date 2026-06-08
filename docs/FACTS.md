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
- Foundry / forge version: `forge 1.7.1` (commit 4072e487, build 2026-05-08) — verified 2026-06-03 — source: `forge --version`
  - NOTE: forge/cast/anvil/chisel/foundryup live in `%USERPROFILE%\.foundry\bin` but that dir is NOT on PATH. Invoke by full path or add to PATH before Phase 1.
- Python version: `3.12.10` — verified 2026-06-03 — source: `python --version`
  - NOTE: CAW SDK requires Python >= 3.11 (PyPI metadata). 3.12.10 satisfies this.
- Node version: `v24.12.0` — verified 2026-06-03 — source: `node --version`
- pnpm version: `11.1.2` — verified 2026-06-03 — source: `pnpm --version`
- git version: `2.52.0.windows.1` — verified 2026-06-03 — source: `git --version`

═══════════════════════════════════════════════════════════════════════
## CAW SDK — confirmed surface (Phase 0)  [top fabrication risk — source everything]
═══════════════════════════════════════════════════════════════════════
All facts below verified 2026-06-03 by reading the ACTUAL installed source of
`cobo-agentic-wallet` **version 0.1.40** (py3-none-any wheel, downloaded via
`pip download cobo-agentic-wallet --no-deps`) plus the repo reference docs at
github.com/CoboGlobal/cobo-agentic-wallet (master). Exact source files cited per line.

- Package + version: `cobo-agentic-wallet` `0.1.40` — source: PyPI page + downloaded wheel filename
- Install command: `pip install cobo-agentic-wallet` — source: PyPI / repo README
- TypeScript counterpart (not used by us): `npm install @cobo/agentic-wallet`
- Python import path + client class: `from cobo_agentic_wallet.client import WalletAPIClient`
  (also re-exported as `from cobo_agentic_wallet import WalletAPIClient`)
  — source: `cobo_agentic_wallet/client.py`, examples/python/direct_sdk.py
- ALL client methods are `async`. Client is an async context manager:
  `async with WalletAPIClient(base_url=..., api_key=...) as client:` — source: client.py:128, direct_sdk.py
- Client constructor (client.py:71): `WalletAPIClient(*, base_url: str, api_key: str | None = None,`
  `allow_unauthenticated: bool = False, timeout: float = 30.0, service_auth_key: str | None = None)`

### Confirmed method signatures (verbatim from `_mixins/*.py`, all `async`)
- create/onboard wallet — `_mixins/wallet.py:28`:
  `create_wallet(wallet_type=None, name=None, group_type=None, main_node_id=None, metadata=None, for_owner=False)`
  (NOTE: real onboarding is done via the `caw` CLI, not this method — see Onboarding below.)
  Related: `get_wallet(wallet_uuid, include_spend_summary=None)`, `list_wallets(...)`,
  `list_wallet_addresses(wallet_uuid)`, `create_wallet_address(wallet_uuid, *, chain_id=None, chain_type=None)`,
  pairing: `initiate_wallet_pair(...)`, `confirm_wallet_pair(...)`, `get_pair_info(token)`.
- submit Pact — `_mixins/pact.py:83`:
  `submit_pact(wallet_id=None, intent=None, original_intent=None, spec=None, name=None, recipe_slugs=None)`
  → returns dict with `pact_id` (and once active, an `api_key`). Source: direct_sdk.py uses `pact_resp["pact_id"]` and `pact["api_key"]`.
- get Pact — `get_pact(pact_id)` → dict with `status`, and when active `api_key`. — pact.py:24
- revoke Pact — `revoke_pact(pact_id)` — pact.py:78.  withdraw pending — `withdraw_pact(pact_id)` — pact.py:124.
- update policies / completion mid-pact: `update_policies(pact_id, *, policies=[...])`, `update_completion_conditions(pact_id, *, completion_conditions=[...])`
- list pacts / events / stats: `list_pacts(...)`, `list_pact_events(pact_id,...)`, `get_wallet_pact_stats(...)`
- transfer_tokens — `_mixins/transaction.py:222`:
  `transfer_tokens(wallet_uuid, *, dst_addr=None, amount=None, token_id="SETH", chain_id=None,`
  `request_id=None, fee=None, src_addr=None, sponsor=None, gas_provider=None, description=None)`
  (NOTE default token_id is "SETH"; `amount` is a decimal STRING e.g. "0.001", not base units. wallet_uuid is positional.)
- contract_call — `_mixins/transaction.py:29`:
  `contract_call(wallet_uuid, *, chain_id=None, contract_addr=None, value="0", calldata=None,`
  `instructions=None, address_lookup_table_accounts=None, request_id=None, fee=None, src_addr=None,`
  `sponsor=None, gas_provider=None, description=None)`
  → KEY: we pass our OWN pre-encoded `calldata` (hex string) + `contract_addr`. No ABI is passed to CAW;
  CAW does NOT validate custom-contract semantics (matches CLAUDE.md §9 risk). `instructions`/`address_lookup_table_accounts` are Solana-only.
- fee estimation: `estimate_transfer_fee(...)`, `estimate_contract_call_fee(...)` (same shapes minus request_id).
- read balance — `_mixins/balance.py:18`:  `list_balances(wallet_uuid=None, chain_id=None, address=None, token_id=None, force_refresh=None, limit=None, after=None, before=None, offset=None)`
  ⚠️ CORRECTION: method is `list_balances`, NOT `get_balance` (the PyPI/README prose said "get_balance" — WRONG; confirmed against source).
- read audit logs — `_mixins/audit.py:19`:  `list_audit_logs(wallet_id=None, principal_id=None, action=None, result=None, start_time=None, end_time=None, after=None, before=None, cursor=None, limit=None)`
  ⚠️ CORRECTION: method is `list_audit_logs`, NOT `get_audit_logs`.
- faucet — `_mixins/faucet.py`: `deposit(address=None, token_id=None)`, `list_tokens()`
- transaction records: `list_transaction_records(...)`, `get_transaction_record_by_request_id(...)` (transaction_record mixin)
- message signing: `message_sign(wallet_uuid, *, chain_id, eip712_typed_data=..., ...)`
- x402 / agent payment protocol: `payment(wallet_uuid, *, protocol, x402_payment_required=..., ...)` (transaction.py:183)

### EMERGENCY FREEZE — important honesty note
There is NO native `freeze` / `pause` / `suspend` / `emergency_stop` wallet method in the SDK
(grepped the entire extracted package, 2026-06-03). The authority-kill primitive is
`revoke_pact(pact_id)` — revoking an active Pact strips the agent's scoped authority (its
pact-scoped API key stops working). Our demo "emergency freeze" beat = `revoke_pact`.
MUST verify behaviorally in Phase 4 that a revoked pact's api_key is immediately rejected.
Do NOT claim a dedicated freeze API exists.

### Policy denial behavior
A blocked operation raises `PolicyDeniedError` (import: `from cobo_agentic_wallet.errors import PolicyDeniedError`).
It exposes `.denial` (structured: code, reason, details, suggestions) and `.status_code`. — source: direct_sdk.py, errors.py

### Pact `spec` JSON shape — VERIFIED (transfer example verbatim from examples/python/direct_sdk.py)
```json
{
  "policies": [
    {
      "name": "max-tx-limit",
      "type": "transfer",
      "rules": {
        "effect": "allow",
        "when": {
          "chain_in": ["SETH"],
          "token_in": [{"chain_id": "SETH", "token_id": "SETH"}]
        },
        "deny_if": {"amount_gt": "0.002"}
      }
    }
  ],
  "completion_conditions": [{"type": "time_elapsed", "threshold": "86400"}]
}
```
Spec schema rules (verbatim from `cobo_agentic_wallet/tool_specs.py` lines 128-660):
- `spec` requires >=1 `policies` and >=1 `completion_conditions`.
- policy `type` ∈ `["transfer", "contract_call", "message_sign"]`.
- `rules.effect` only accepts `"allow"` (pact policies are always allow-lists).
  To BLOCK: set `deny_if: {}` (unconditional deny) or populate `deny_if` with thresholds;
  `review_if` = soft review (owner approval); `always_review: true` = approve every match.
- `when` scope filters depend on `type`:
  - transfer → `chain_in`, `token_in` ([{chain_id, token_id}]), `destination_address_in` ([{chain_id, address}])
  - contract_call (EVM) → `chain_in`, `target_in` ([{chain_id, contract_addr}]), `params_match`
  - contract_call (Solana) → `chain_in`, `program_in`, `program_all_in`
  - message_sign → `chain_in`, `primary_type_in`, `source_address_in`, `domain_match`, `message_match`
- Canonical field names: `contract_addr` (NOT contract_address), `function_id` (NOT function_signature).
- `deny_if.usage_limits.rolling_24h.tx_count_gt` = rolling-window count cap (source: skills/.../pact.md contract_call example).

### contract_call policy example (verbatim from skills/cobo-agentic-wallet/references/pact.md)
```json
[
  {
    "name": "usdc-eth-swap",
    "type": "contract_call",
    "rules": {
      "effect": "allow",
      "when": {
        "chain_in": ["BASE_ETH"],
        "target_in": [{"chain_id": "BASE_ETH", "contract_addr": "0x2626664c2603336E57B271c5C0b26F421741e481"}]
      },
      "deny_if": {"usage_limits": {"rolling_24h": {"tx_count_gt": 3}}}
    }
  }
]
```
(NOTE: `BASE_ETH` here is Base MAINNET. Our chain is Base Sepolia — see chain section.)

### ARCHITECTURE-CRITICAL: how authority is scoped (verified pattern from direct_sdk.py)
1. Submit a pact (with the wallet-level api key) → get `pact_id`.
2. Poll `get_pact(pact_id)` until `status == "active"` (unpaired wallet: auto-activates; paired wallet: owner approves in app).
3. The active pact dict contains its OWN `api_key`. Open a NEW `WalletAPIClient` with that pact-scoped key and make all constrained calls (transfer/contract_call) through it.
4. Terminal pact statuses: `rejected`, `expired`, `revoked`, `completed`.
→ This is why CAW is load-bearing: the agent literally holds a pact-scoped API key whose
authority is the policy. Over-budget / non-whitelisted calls raise PolicyDeniedError.

═══════════════════════════════════════════════════════════════════════
## CAW Onboarding (CLI) — Phase 2 will run these
═══════════════════════════════════════════════════════════════════════
- The `caw` CLI is installed separately from the Python SDK. Install (Unix):
  `curl -fsSL https://raw.githubusercontent.com/CoboGlobal/cobo-agentic-wallet/master/install.sh | bash`
  then `export PATH="$HOME/.cobo-agentic-wallet/bin:$PATH"`. (Windows: `install.ps1` exists in repo — not yet tested on this machine.)
- Onboard: `caw onboard --agent-name <NAME>` returns a `session_id`. EVERY subsequent call MUST
  pass `--session-id <SESSION_ID>` (and `--answers '{"prompt_id":"value"}'` when prompted).
  Done when `wallet_status == active` and `phase == wallet_active`.
- Pairing (transfer ownership to the Cobo app): `caw wallet pair`; status: `caw wallet pair-status` / `caw status`.
- SDK env vars the examples expect: `AGENT_WALLET_API_URL`, `AGENT_WALLET_API_KEY`, `AGENT_WALLET_WALLET_ID`.
  (Our .env mirrors these; see Env vars section.)
- UNKNOWN — not yet verified: exact command that prints the api key, and faucet CLI syntax
  (a doc referenced `caw faucet deposit --token-id SETH --address <addr>` and SDK has `deposit(address, token_id)`,
  but neither has been run on this machine yet). Confirm live in Phase 2.

═══════════════════════════════════════════════════════════════════════
## Chain & network (Phase 0 / Phase 2)
═══════════════════════════════════════════════════════════════════════
- Chosen chain: Base Sepolia (per CLAUDE.md §6) — fallback to Ethereum Sepolia not yet triggered.
- ⚠️ Base Sepolia CAW chain_id string: documented as `"TBASE_SETH"` — source: skills/cobo-agentic-wallet/references/chains-and-tokens.md (read 2026-06-03).
  NOT independently confirmed: this string does NOT appear in SDK source (chain_id is a free-form
  string passed to the server). MUST confirm live in Phase 2 via `list_tokens()` / metadata API
  before relying on it. The shipped SDK example uses `"SETH"` (Ethereum Sepolia), NOT Base Sepolia.
- Ethereum Sepolia chain_id string (fallback): `"SETH"` — verified in examples/python/direct_sdk.py.
- Base Sepolia EVM numeric chain ID: `84532` — verified 2026-06-03 — source: docs.base.org/network-information (WebFetch) + corroborated by Circle/BaseScan results.
- Public RPC URL: `https://sepolia.base.org` — verified 2026-06-03 — source: docs.base.org/network-information.
  (A dedicated provider RPC — Alchemy/Infura — is recommended for deploy reliability; public RPC can rate-limit.)
- Block explorer (what judges open): `https://sepolia.basescan.org` — verified 2026-06-03 — source: search + token page load.
  - Verification API endpoint: `https://api-sepolia.basescan.org/api` (Etherscan-compatible; needs a BaseScan API key). Etherscan V2 unified `https://api.etherscan.io/v2/api?chainid=84532` is an alternative — confirm whichever forge uses in Phase 1.
- On-chain USDC ERC-20 (the token our escrow holds/transfers): `0x036CbD53842c5426634e7929541eC2318f3dCF7e`
  — verified 2026-06-03 — source: BaseScan token page (name "USDC", symbol "USDC", **6 decimals**, Circle FiatTokenProxy; impl 0xd74cc5d436923b8ba2c179b4bca2841d8a52c5b5).
  DECISION (user, 2026-06-03): attempt this real Base Sepolia USDC FIRST; fall back to MockUSDC only if faucet/CAW support proves unreliable.
- ⚠️ CAW `token_id` STRING for Base Sepolia USDC: UNKNOWN — not yet verified. This is the Cobo
  symbolic id (e.g. like "SETH_USDC" for Eth Sepolia), DISTINCT from the on-chain ERC-20 address above.
  Do NOT guess "TBASE_SETH_USDC". Confirm via `list_tokens()` / metadata in Phase 2.
  - Ethereum Sepolia USDC token_id documented as `"SETH_USDC"` — source: chains-and-tokens.md.
- Faucet: SDK `deposit(address, token_id)` + `list_tokens()` exist; reliability UNKNOWN — test in Phase 2.
  Circle also has a public USDC testnet faucet (faucet.circle.com) for the on-chain token; Base Sepolia ETH
  gas faucet needed for the deployer key. Note (decimals trap, from chains-and-tokens.md): BSC_USDC/BSC_USDT use 18 decimals; standard USDC uses 6.

═══════════════════════════════════════════════════════════════════════
## Deployed artifacts (Phase 1+)
═══════════════════════════════════════════════════════════════════════
- Escrow contract: IMPLEMENTED + tested locally (Phase 1). `contracts/src/AgentWorksEscrow.sol`,
  solc 0.8.28, self-contained (inline IERC20, no external imports → trivial BaseScan verify).
  ✅ 25/25 forge tests pass — verified 2026-06-08 — source: `forge test` (full lifecycle, both
  payout+refund branches, expiry refund, access control, status guards, CEI/reentrancy test).
- Escrow contract address: `0x19Ea8a442802065a61c69cbc03bE97724Ad8cd9b` — verified 2026-06-08 — source: `forge script Deploy --broadcast` (Base Sepolia, chainId 84532).
- Escrow deploy tx hash: `0x630490a5df5c36d71b540fb5618cc060063e481a8cf822748924e896fe3c8de9` (block 42582092, status 0x1, gasUsed 841468).
- Escrow explorer URL: https://sepolia.basescan.org/address/0x19ea8a442802065a61c69cbc03be97724ad8cd9b
- Escrow source VERIFIED on BaseScan: ✅ `Pass - Verified` — 2026-06-08 — source: `forge verify-contract` via Etherscan V2 (`https://api.etherscan.io/v2/api?chainid=84532`). Constructor arg = USDC 0x036C...
- Escrow ABI location (path in repo): `contracts/out/AgentWorksEscrow.sol/AgentWorksEscrow.json` (generated by `forge build`)
- Settlement token bound at deploy: real Base Sepolia USDC `0x036CbD53842c5426634e7929541eC2318f3dCF7e`.
- Deployer EOA address (testnet, throwaway): `0xBCA6f82e240C6AC36B23b4f7D21adF17e03966Fe` — verified 2026-06-08 — source: `cast wallet address`.
- Client CAW wallet address / id: not yet created
- Provider CAW wallet address / id: not yet created
- Client Pact id: not yet created
- Provider Pact id: not yet created

═══════════════════════════════════════════════════════════════════════
## Env vars (names only — values live in .env, never here)
═══════════════════════════════════════════════════════════════════════
- `AGENT_WALLET_API_URL` — CAW API base (https://api.agenticwallet.cobo.com). Read by SDK examples.
- `AGENT_WALLET_API_KEY` — wallet- or pact-scoped API key passed to WalletAPIClient(api_key=...).
- `AGENT_WALLET_WALLET_ID` — wallet UUID used as `wallet_id`/`wallet_uuid` arg.
- (project-local, provisional) CAW_CLIENT_WALLET_ID / CAW_PROVIDER_WALLET_ID, RPC_URL,
  DEPLOYER_PRIVATE_KEY, EXPLORER_API_KEY, ESCROW_CONTRACT_ADDRESS, USDC_TOKEN_ADDRESS,
  IRYS_PRIVATE_KEY, IRYS_NODE_URL, LLM_API_KEY, LLM_MODEL — see .env.example.
- CDP faucet creds (for funding the deployer with Base Sepolia ETH): CDP_API_KEY_ID,
  CDP_API_KEY_SECRET, CDP_WALLET_SECRET (wallet secret may be optional for faucet-to-external).

═══════════════════════════════════════════════════════════════════════
## References (official CAW docs — user-provided 2026-06-08)
═══════════════════════════════════════════════════════════════════════
- Website: https://www.cobo.com/agentic-wallet
- Recipes: https://agenticwallet.cobo.com/agentic-wallet/recipes
- Manual / intro: https://www.cobo.com/products/agentic-wallet/manual/start-here/introduction
- SDK quickstart: https://www.cobo.com/products/agentic-wallet/manual/developer/quickstart-overview
- What is Agentic Wallet: https://www.cobo.com/products/agentic-wallet/manual/learn/what-is-agentic-wallet
- Agentic Economy blog: https://www.cobo.com/blog-new-page?tag=Cobo+Agentic+Economy
- SDK source (read in Phase 0): github.com/CoboGlobal/cobo-agentic-wallet + python-sdk repo.

═══════════════════════════════════════════════════════════════════════
## CDP faucet — environment note (Phase 1)
═══════════════════════════════════════════════════════════════════════
- `@coinbase/cdp-sdk` v1.51.0 faucet call: `cdp.evm.requestFaucet({ address, network: "base-sepolia", token: "eth" })`
  — can fund an arbitrary external address; 0.0001 ETH/claim, 1000 claims/24h. — verified 2026-06-08 (docs + npm).
- ⚠️ From inside the agent's sandboxed Bash, the CDP API call returns `NetworkError status=0`
  (connection blocked). See whether running with sandbox disabled / on the user's own machine succeeds.
