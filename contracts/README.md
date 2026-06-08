# contracts — AgentWorks escrow (Foundry)

Neutral settlement layer for the two-agent job marketplace. Lifecycle mirrors the
ERC-8183 draft naming: `createJob → fund → submitWork → complete | reject | claimRefund`.

- [`src/AgentWorksEscrow.sol`](src/AgentWorksEscrow.sol) — the escrow. Self-contained
  (inline minimal `IERC20` + safe-transfer; no external imports → trivial explorer verification).
  Evaluator is a distinct per-job address (v1: client-controlled, swappable).
- [`src/MockUSDC.sol`](src/MockUSDC.sol) — 6-decimal ERC-20 for deterministic tests and as a
  fallback settlement token.
- [`test/AgentWorksEscrow.t.sol`](test/AgentWorksEscrow.t.sol) — full lifecycle, both settlement
  branches, expiry refund, access control, status guards, and a CEI/reentrancy-safety test.
- [`script/Deploy.s.sol`](script/Deploy.s.sol) — deploys the escrow bound to `USDC_TOKEN_ADDRESS`.
- [`script/DeployMockUSDC.s.sol`](script/DeployMockUSDC.s.sol) — fallback: deploy our own USDC.

## Usage

Foundry lives at `~/.foundry/bin` (not on PATH on this machine). Env vars come from the
repo-root `.env` — source it before deploy/verify.

```bash
forge build
forge test -vv                       # 25 tests
forge test --gas-report

# Deploy to Base Sepolia (needs DEPLOYER_PRIVATE_KEY funded with Base Sepolia ETH):
set -a; . ../.env; set +a
forge script script/Deploy.s.sol:Deploy \
  --rpc-url "$RPC_URL" --broadcast \
  --verify --verifier etherscan --etherscan-api-key "$EXPLORER_API_KEY" --chain 84532
```

Settlement token defaults to real Base Sepolia USDC
(`0x036CbD53842c5426634e7929541eC2318f3dCF7e`, 6 decimals). See repo `docs/FACTS.md`.

> `lib/` (forge-std) is gitignored; run `git clone --depth 1 https://github.com/foundry-rs/forge-std lib/forge-std` on a fresh checkout.
