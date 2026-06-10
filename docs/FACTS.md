# FACTS.md — Verified Project Facts

> Progress snapshot + current addresses/ids: see **docs/STATUS.md**. As of 2026-06-09: Phases 0–5
> complete; chain = Ethereum Sepolia; escrow `0x812BcE…`, MockUSDC `0x4C4D12…`. Phase 6 (dashboard) next.

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
- Chosen chain: Base Sepolia (per CLAUDE.md §6) — fallback to Ethereum Sepolia NOT triggered (Base Sepolia CONFIRMED on CAW).
- ✅ Base Sepolia CAW chain_id string: `"TBASE_SETH"` — CONFIRMED LIVE 2026-06-08 — source: `caw meta chain-info --chain-id TBASE_SETH`
  → name "Base Sepolia Testnet", chain_type ETH (EVM), explorer https://sepolia.basescan.org. GO for Base Sepolia.
  - ⚠️ chain-info flags `enable_smart_contract_op` and `is_testnet` are BOTH `false` for EVERY chain (incl. ETH mainnet) —
    i.e. uniformly unreliable metadata, NOT a Base-specific limit. `contract_call` to be proven empirically in Phase 3.
- Base Sepolia native gas token_id: `"TBASE_SETH"` (18 decimals) — confirmed via meta.
- Ethereum Sepolia chain_id string (fallback): `"SETH"` — verified in examples/python/direct_sdk.py.
- Base Sepolia EVM numeric chain ID: `84532` — verified 2026-06-03 — source: docs.base.org/network-information (WebFetch) + corroborated by Circle/BaseScan results.
- Public RPC URL: `https://sepolia.base.org` — verified 2026-06-03 — source: docs.base.org/network-information.
  (A dedicated provider RPC — Alchemy/Infura — is recommended for deploy reliability; public RPC can rate-limit.)
- Block explorer (what judges open): `https://sepolia.basescan.org` — verified 2026-06-03 — source: search + token page load.
  - Verification API endpoint: `https://api-sepolia.basescan.org/api` (Etherscan-compatible; needs a BaseScan API key). Etherscan V2 unified `https://api.etherscan.io/v2/api?chainid=84532` is an alternative — confirm whichever forge uses in Phase 1.
- On-chain USDC ERC-20 (the token our escrow holds/transfers): `0x036CbD53842c5426634e7929541eC2318f3dCF7e`
  — verified 2026-06-03 — source: BaseScan token page (name "USDC", symbol "USDC", **6 decimals**, Circle FiatTokenProxy; impl 0xd74cc5d436923b8ba2c179b4bca2841d8a52c5b5).
  DECISION (user, 2026-06-03): attempt this real Base Sepolia USDC FIRST; fall back to MockUSDC only if faucet/CAW support proves unreliable.
- ✅ CAW `token_id` for Base Sepolia USDC: `"TBASE_USDC"` — CONFIRMED LIVE 2026-06-08 — source:
  `caw meta search-tokens --symbol USDC` → token_address `0x036cbd53842c5426634e7929541ec2318f3dcf7e`
  (the EXACT same Circle USDC our escrow is bound to). 6 decimals. (NOT "TBASE_SETH_USDC" — that guess was wrong.)
  - Eth Sepolia USDC = `"SETH_USDC"` (0x1c7d4b19...); these are different per chain.
- ⚠️ CAW FAUCET does NOT cover Base Sepolia. `caw faucet tokens` lists ONLY `SETH` (Eth Sepolia native) and
  `SOLDEV_SOL`/`SOLDEV_SOL_USDC` (Solana devnet). So CAW wallets must be funded on Base Sepolia by other means:
  (a) seed from our deployer EOA (has Base Sepolia ETH), (b) external Base Sepolia ETH faucet to the CAW EVM addr,
  (c) MockUSDC mint for USDC. Verified 2026-06-08 — source: `caw faucet tokens`.
- CAW wallet EVM addresses (same address across all EVM chains incl. Base Sepolia):
  Client `0x6dfbd0ac9feb5bb9a9ffeaf54df203c1633c1ddd` (wallet 0da4d5c3-…, agent caw_agent_4bc15e6348db0514);
  Provider `0xef9349b3273b1a54faaf701231f499fe0282e643` (wallet bdecbada-…, agent caw_agent_e6318ac84f123085).
  Both onboarded UNPAIRED + active 2026-06-08 via `caw onboard` (TWO separate profiles). caw CLI = v0.2.86, installed at ~/.cobo-agentic-wallet/bin/caw.exe.

═══════════════════════════════════════════════════════════════════════
## Deployed artifacts (Phase 1+)
═══════════════════════════════════════════════════════════════════════
- Escrow contract: IMPLEMENTED + tested locally (Phase 1). `contracts/src/AgentWorksEscrow.sol`,
  solc 0.8.28, self-contained (inline IERC20, no external imports → trivial BaseScan verify).
  ✅ 25/25 forge tests pass — verified 2026-06-08 — source: `forge test` (full lifecycle, both
  payout+refund branches, expiry refund, access control, status guards, CEI/reentrancy test).
- ✅ CURRENT stack (Ethereum Sepolia, chainId 11155111), both VERIFIED on Etherscan:
  - **MockUSDC** `0x4C4D1223BcC47E380CF4C37652EaDFe10A9Fd910` (our 6-decimal USDC, mintable). `Pass - Verified`.
  - **Escrow** `0x812BcEEc2De8C8aC71C7af7A8E2d4467E65Fdf18` (Phase 5: `submitWork(jobId, bytes32 deliverableHash, string irysId)`
    + `Job.irysId` + `WorkSubmitted(...,string irysId)`), bound to MockUSDC. Deploy tx `0x2249eeb6601255b7c2eaf9087bc34971544d9bbaac702d7d380a40dd15a374b2`. `Pass - Verified`.
    Explorer: https://sepolia.etherscan.io/address/0x812bceec2de8c8ac71c7af7a8e2d4467e65fdf18
  - ⚠️ getJob now returns 9 fields: (client, provider, evaluator, amount, specHash, deliverableHash, **irysId**, deadline, status).
  - Client holds MockUSDC (minted 1000; ~960 after Phase 3/4 demo jobs). 25/25 forge tests pass with the change.
  - RETIRED Phase 3 escrow `0xe8eB3a0233D8E227636f91f45Cd17583Be6A1008` (no irysId) — superseded by the Phase 5 escrow.
- RETIRED: escrow `0x19Ea8a44…` on Eth Sepolia (bound to real SETH_USDC, deploy tx `0xc92b258f…`) — superseded by the
  MockUSDC stack for determinism. Earlier Base Sepolia escrow `0x19Ea8a44…` (tx `0x630490a5…`) retired by the chain switch. Kept for history.
- Escrow ABI location (path in repo): `contracts/out/AgentWorksEscrow.sol/AgentWorksEscrow.json` (generated by `forge build`)
- Settlement token bound at deploy: real Base Sepolia USDC `0x036CbD53842c5426634e7929541eC2318f3dCF7e`.
- Deployer EOA address (testnet, throwaway): `0xBCA6f82e240C6AC36B23b4f7D21adF17e03966Fe` — verified 2026-06-08 — source: `cast wallet address`.
- Client CAW wallet: id `0da4d5c3-5fc4-4a50-878a-0e8ee1a1787d`, EVM addr `0x6dfbd0ac9feb5bb9a9ffeaf54df203c1633c1ddd`, agent `caw_agent_4bc15e6348db0514` — onboarded active 2026-06-08.
- Provider CAW wallet: id `bdecbada-3e1d-41d8-9e04-c12202cc9c17`, EVM addr `0xef9349b3273b1a54faaf701231f499fe0282e643`, agent `caw_agent_e6318ac84f123085` — onboarded active 2026-06-08.
- Client Pact id (Phase 2 hello-world, SETH transfer): `74b89e03-e9e5-47a5-862c-69b92feeaef5` (status active; auto-approved unpaired).
- Provider Pact id: not yet created (Phase 3+).

═══════════════════════════════════════════════════════════════════════
## CAW runtime — VERIFIED LIVE (Phase 2, 2026-06-08)
═══════════════════════════════════════════════════════════════════════
- ✅ Two wallets onboarded (UNPAIRED, two separate `caw onboard` profiles). caw CLI v0.2.86 at
  `~/.cobo-agentic-wallet/bin/caw.exe`. Local `cobo-tss-node.exe` processes co-sign (MPC).
- ✅ CAW pact→transfer→audit loop PROVEN on Ethereum Sepolia (SETH):
  - pact submitted → `"status":"active"`, `"Pact submitted and auto-approved for unpaired agent"` (instant; no app approval).
  - For an unpaired self-provisioned wallet, the pact's operator==owner and there is NO separate pact-scoped api_key;
    the wallet's own api_key is used for the constrained call. (Differs from direct_sdk.py's paired pattern.)
  - transfer 0.001 SETH Client→Provider, tx `0x30c32c33c89b154a9d2a614f5a1bc1efbc89d294da64b2a74aabf05d352ea2fd`
    (also earlier `0xd42976a1e92e66ae604855eede1760d0361a8a1220143413fa4313af1ab29ff6`). Verified on Eth Sepolia
    (from 0x6dFB → 0xEf93, value 1e15 wei). Explorer: https://sepolia.etherscan.io/tx/0x30c32c33c89b154a9d2a614f5a1bc1efbc89d294da64b2a74aabf05d352ea2fd
  - audit log shows `transfer.initiate` + `transfer.allowed` (result=allowed) at the transfer time.
- TRANSACTION STATUS CODE LEGEND (numeric `status` + `status_display`): 400=Processing, 500=Pending, 900=Success.
  Poll `get_user_transaction_by_request_id(wallet_uuid, request_id)`; match on status_display/900.
- ✅ CAW `contract_call` on Eth Sepolia VERIFIED (Phase 3 smoke, 2026-06-08): Client did a
  contract_call SETH_USDC.approve(escrow,1) via a contract_call-type pact → tx
  `0x48b069049756709539bd1c04bc4bff9c59bb12f9d6b6031baee94037684e5d42`; on-chain
  allowance(client→escrow) went 0→1 (RPC-confirmed). contract_call needs `src_addr`; calldata is
  our own ABI-encoded hex (eth_abi); no token_id needed for contract_call.

### ✅ Phase 3 — full lifecycle headless via CAW contract_call (2026-06-08), BOTH branches
Stack: escrow `0xe8eB3a02…` + MockUSDC `0x4C4D1223…`. Client agent (also v1 evaluator) + Provider agent,
each constrained by a contract_call-type pact (Client→[USDC,escrow]; Provider→[escrow]). Every step is an
on-chain CAW contract_call; transitions verified by reading `escrow.getJob` + USDC balances over RPC.
- PAYOUT (job 2 → Completed): createJob `0x0f2b6c93…`, approve `0x64a3226b…`, fund `0xc20cc8d9…`,
  submitWork `0x0919e53b…`, complete `0x058025a6…`. Balances: client 1000→990, provider 0→10, escrow 0.
- REFUND (job 3 → Rejected): createJob `0x8216bb4c…`, approve `0x4ea3d57e…`, fund `0x4d945951…`,
  submitWork `0x64e5b8ca…`, reject `0x0c983411…`. Client funded 10 then refunded 10 (net 0); escrow 0.
- (job 1 = orphaned Created/unfunded from an aborted first run — harmless.)
- Code: `agents/escrow.py` (calldata + RPC reads), `agents/scripts/phase3_lifecycle.py` (orchestration).
  Proofs: `agents/scripts/phase3_{complete,reject}_proof.json`.
- RPC note: public `ethereum-sepolia-rpc.publicnode.com` timed out on reads; switched read RPC to
  `https://sepolia.drpc.org` + added retry. (CAW contract_call WRITES use CAW infra, not our RPC.)

### ✅ Phase 4 — CAW criticality ENFORCEMENT verified live (2026-06-08), unpaired wallets
Pacts are enforced server-side (security.md confirmed in practice). Smoke `phase4_criticality_smoke.py`:
- NO active pact → `contract_call` DENIED: `PolicyDeniedError` code `INSUFFICIENT_PERMISSION`,
  reason `permission_check_failed`, HTTP 403.
- Whitelisted target (USDC, in pact `target_in`) → ALLOWED.
- NON-whitelisted target (0x…dEaD) → DENIED: code `CONTRACT_NOT_WHITELISTED`,
  reason `no_pact_contract_call_allow_policy_matched`, HTTP 403. ← the contract-allowlist beat.
- After `revoke_pact(id)` → next call DENIED (403 Forbidden). ← the emergency-FREEZE beat (freeze = revoke).
- `revoke_pact` returns the full pact object; `list_pacts(status="active")` used to clean slate.
- ⚠️ Multiple active pacts stack as allow-lists — must revoke ALL stale pacts before a denial is observable.
- Pact spending caps proven enforceable: `deny_if.usage_limits.rolling_24h.tx_count_gt` (count) and
  (transfer) `deny_if.amount_gt` (amount). USDC-amount-in-calldata is NOT pact-visible (use allowlist + tx-count).
- Shipped policy artifacts (criterion 5): `docs/pacts/*.json` (client_escrow, provider, client_budget_transfer, review).
- DENIAL demo (`phase4_denial.py`): budget-cap → `TRANSFER_LIMIT_EXCEEDED`/`matched_pact_transfer_deny_if`;
  allowlist → `CONTRACT_NOT_WHITELISTED`/`no_pact_contract_call_allow_policy_matched`. Audit: `transfer.denied`, `contract_call.denied`.
- FREEZE demo (`phase4_freeze.py`): allowed contract_call `0x249aeb95…` then `revoke_pact` → next call DENIED (403).

### ✅ Phase 4 — genuine LLM reasoning + reasoned lifecycle (DeepSeek deepseek-v4-flash, 2026-06-08)
- LLM via OpenAI-compatible API at `https://api.deepseek.com`; `deepseek-v4-flash` is a REASONING model
  (chain-of-thought in `reasoning_content`; needs generous max_tokens or `content` is empty). Layer: `agents/reasoning.py`.
- `phase4_demo.py good` → Client LLM funds; Provider LLM writes a real explanation; Evaluator LLM **ACCEPTS**
  → `complete` → job 4 Completed, provider 10→20 USDC. txs createJob `0xb53b6f27…` approve `0x73c84e82…`
  fund `0xc15aa686…` submitWork `0xb5953bda…` complete `0x192cb842…`.
- `phase4_demo.py bad` → Provider LLM sabotages (describes a bank); Evaluator LLM **REJECTS** ("not an on-chain
  escrow… without a trusted third party") → `reject` → job 5 Rejected, client refunded. reject tx `0x02e0d6ce…`.
  → The on-chain branch is chosen by the LLM's genuine verdict (criterion 1), bounded by the scoped pact.
- ✅ review_if (`phase4_review.py`) CONFIRMED LIVE: transfer > review threshold → `status_display=PendingApproval`
  (status 200) + `pending_operation_id`; `get_pending_operation` shows `policy_decision.effect="require_approval"`,
  reason `operation_matched_approval_conditions`; `approve_pending_operation` → `status="executed"` → tx `0x275117e4…`.
  Pending op also exposes a `delegation_id`. (Unpaired owner approves in-conversation; SDK methods per `_mixins/pending_operation.py`.)

═══════════════════════════════════════════════════════════════════════
## Irys deliverable storage (Phase 5) — VERIFIED LIVE 2026-06-09
═══════════════════════════════════════════════════════════════════════
- SDK (Node): `@irys/upload` (^0.0.15, default export = `Uploader`/`Builder`) + `@irys/upload-ethereum`
  (^0.0.16, default export = `Ethereum`). Pattern: `await Uploader(Ethereum).withWallet(pk).withRpc(rpc).devnet()`;
  methods `getPrice(bytes)`, `getLoadedBalance()`, `fund(amt)`, `upload(data, {tags})` → `receipt.id`.
- Agents are Python → Node helper `agents/irys/upload.mjs` (reads deliverable on stdin, prints `{id,url,...}`);
  Python wrapper `agents/irys_store.py` (`upload`, `fetch`, `keccak`).
- DEVNET: `.devnet()`; uploads auto-funded from the EVM key's Sepolia ETH (tiny, ~1.3e-6 ETH/upload — `fund()` runs a Sepolia tx).
  Uses `IRYS_PRIVATE_KEY` or falls back to `DEPLOYER_PRIVATE_KEY`. Data-item id = 43-char base64url.
- ⚠️ RETRIEVAL: devnet data is served at `https://devnet.irys.xyz/<id>` (NOT prod `gateway.irys.xyz` → 403 for devnet ids).
- ⚠️ The Irys gateway 403s the default `Python-urllib` User-Agent — `fetch()` MUST send a normal `User-Agent` header.
- Roundtrip verified: upload → fetch → byte/keccak match.
- ✅ Phase 5 full loop (`phase5_demo.py`, escrow `0x812BcE…`): Provider stores deliverable on Irys →
  `submitWork(jobId, keccak256(content), irysId)` → Evaluator FETCHES from Irys by the on-chain irysId → judges →
  settle → VERIFY `keccak256(Irys-fetched) == on-chain deliverableHash` (True both branches).
  - good (job 1 → Completed/payout): irys `BycfUyokk95HxwswpA3uiBVBfX7hSzumTrJLmJSQvU92`; submitWork `0x09a576d4…`, complete `0x20109ead…`.
  - bad  (job 2 → Rejected/refund): irys `BAJk8iWc5yoFG3uTMyopmTHvzDxd9DPaRK5ubroDKKCU`; submitWork `0xc0dce63b…`, reject `0x310c6900…`.
    (Evaluator rejected the Irys-fetched sabotaged deliverable: "a poem, not a clear explanation".)
- `transfer_tokens` REQUIRES `src_addr` on this backend (SDK marks it optional — 422 without it).
- `create_wallet_address(chain_id=...)` MINTS A NEW derived address each call; the onboarding default EVM
  address already lists all EVM chains (incl. TBASE_SETH) in `compatible_chains`. Use the default; don't mint.
- ⚠️⚠️ KEY ISSUE — CAW does NOT surface externally-deposited BASE SEPOLIA native balance:
  funded Client 0x6dFB with 0.00005 Base Sepolia ETH (167+ confs, on-chain confirmed), yet
  `list_balances(chain_id=TBASE_SETH, force_refresh=True)` returns `[]` and a TBASE_SETH transfer is rejected
  `INSUFFICIENT_BALANCE` (available 0). By contrast, a CAW-faucet SETH deposit (0.01) WAS indexed and spendable.
  → CAW reliably funds/indexes its faucet chains (SETH, SOLDEV) but not external Base Sepolia deposits (in our window).
  → OPEN DECISION for Phase 3: how to fund the CAW agents on Base Sepolia (our escrow's chain). Options: gas
    sponsorship (`sponsor`/`gas_provider` on contract_call), longer indexer wait, or move escrow to Eth Sepolia.

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

═══════════════════════════════════════════════════════════════════════
## Phase 6 — Web dashboard (Next.js 15, the demo surface) — verified 2026-06-09
═══════════════════════════════════════════════════════════════════════
- App in `/web`: Next 15.1.6 + React 19 + viem 2.x, App Router, TypeScript. Bespoke CSS porting the
  AgentWorks brand tokens (oklch paper/ink + Settle Blue; Space Grotesk + IBM Plex Mono via CDN link).
  `pnpm --filter web build` → PASS, 5 routes (`/` static, `/brand` static, `/dashboard` ƒ, `/api/run` ƒ,
  `/_not-found`). Only warnings are cosmetic autoprefixer `align-items: start` notes.
- Routes: `/` landing, `/brand` brand board, `/dashboard` demo surface. CSS scoped per route (`.lp`/`.bp`/`.dp`)
  so component classnames don't collide; shared primitives + tokens in `app/globals.css`.
- Data model: verified proof artifacts are the source of truth. `web/scripts/snapshot-proofs.mjs`
  (predev/prebuild) copies `agents/scripts/*_proof.json` → `web/data/proofs/` and `docs/pacts/*.json` →
  `web/data/pacts/` (committed). `lib/proofs.ts` reads `web/data/` first, falls back to sibling dirs in dev.
  Live additive reads via `lib/chain.ts` (viem): `usdcBalance()`, `getJob()` — wrapped, degrade to snapshots.
- `app/api/run/route.ts`: POST `{mode:"good"|"bad"}` spawns `agents/.venv/Scripts/python.exe
  agents/scripts/phase5_demo.py <mode>` and streams stdout. Localhost-guarded; the dashboard hides the
  Run-live button when `NODE_ENV==="production"` (Vercel serverless can't run the venv).
- Public dashboard config (`lib/config.ts`, `NEXT_PUBLIC_*`, verified defaults baked in): RPC
  `https://sepolia.drpc.org`, escrow/MockUSDC/Client+Provider CAW addresses, explorer
  `https://sepolia.etherscan.io`, Irys `https://devnet.irys.xyz`. No secrets in the web app.
- pnpm: repo pins `pnpm@11.1.2`, which gates native install scripts. `pnpm-workspace.yaml` uses
  `allowBuilds: { sharp: true }` to clear `ERR_PNPM_IGNORED_BUILDS` (sharp = Next's optional image
  optimizer, prebuilt binary). `web/node_modules/.bin/next dev` bypasses the dep-status gate.
- Env-key clarification (confirmed from source): agents read `CAW_CLIENT_*`/`CAW_PROVIDER_*` + only
  `AGENT_WALLET_API_URL`; `AGENT_WALLET_API_KEY`/`_WALLET_ID` are unused legacy names. Irys uploader
  (`agents/irys/upload.mjs`) uses `IRYS_PRIVATE_KEY` or falls back to `DEPLOYER_PRIVATE_KEY`; `IRYS_NODE_URL`
  is never read. So blank `AGENT_WALLET_*` / `IRYS_*` are expected — nothing missing.
- Deploy: see `docs/DEPLOY.md` (Vercel: build `pnpm --filter web build`, output `web/.next`, NEXT_PUBLIC_* envs).
