# contracts - AgentWorks escrow (Foundry)

The neutral settlement layer for the autonomous open marketplace. Funds are held by neither agent; only the
contract moves them, and only along the lifecycle (with a deadline refund as the backstop). Lifecycle mirrors
the ERC-8183 draft naming:
`createJob → fund → acceptJob → submitWork → complete | reject | claimRefund`.

- [`src/AgentWorksEscrowV2.sol`](src/AgentWorksEscrowV2.sol) - **the live escrow (open marketplace).**
  `createJob(evaluator, amount, specHash, deadline)` names **no** provider; any agent claims a funded job via
  `acceptJob(jobId)` (sets `provider = msg.sender`; **first claimer wins** - a second claim reverts). Settlement
  (`complete`/`reject`) is gated to the per-job evaluator; unclaimed-past-deadline funds return via `claimRefund`.
  Self-contained (inline minimal `IERC20` + safe-transfer; no external imports → trivial explorer verification).
  An event on every transition; custom errors over `require` strings.
- [`src/MockUSDC.sol`](src/MockUSDC.sol) - 6-decimal mintable ERC-20, the deterministic settlement token.
- [`src/AgentWorksEscrow.sol`](src/AgentWorksEscrow.sol) - the prior v1 (closed 1:1) escrow, kept for history.
- [`test/AgentWorksEscrowV2.t.sol`](test/AgentWorksEscrowV2.t.sol) + [`test/AgentWorksEscrow.t.sol`](test/AgentWorksEscrow.t.sol)
  - **55 tests**: full lifecycle, both settlement branches, the accept-race (single acceptance / losers revert),
  expiry refund, access control, status guards, and a CEI/reentrancy-safety test.
- [`script/DeployV2.s.sol`](script/DeployV2.s.sol) - deploys escrow v2 bound to `USDC_TOKEN_ADDRESS`.
  [`script/DeployMockUSDC.s.sol`](script/DeployMockUSDC.s.sol) - deploys the MockUSDC settlement token.

## Live addresses (Ethereum Sepolia, chainId 11155111, both verified on Etherscan)
- Escrow v2: `0xD6cB413c0E4a5839Fd4B02aFFeBF65e6868726b9`
- MockUSDC:  `0x4C4D1223BcC47E380CF4C37652EaDFe10A9Fd910`

## Usage

Foundry lives at `~/.foundry/bin` (not on PATH on this machine). Env vars come from the repo-root `.env`.

```bash
forge build
forge test -vv                       # 55 tests
forge test --gas-report

# Deploy escrow v2 to Ethereum Sepolia (DEPLOYER_PRIVATE_KEY funded with Sepolia ETH):
set -a; . ../.env; set +a
forge script script/DeployV2.s.sol \
  --rpc-url "$RPC_URL" --broadcast \
  --verify --verifier etherscan --etherscan-api-key "$EXPLORER_API_KEY" --chain 11155111
```

> `lib/` (forge-std) is gitignored; run `git clone --depth 1 https://github.com/foundry-rs/forge-std lib/forge-std`
> on a fresh checkout.
