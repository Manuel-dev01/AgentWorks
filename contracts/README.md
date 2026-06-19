# contracts - AgentWorks escrow (Foundry)

The neutral settlement layer for the autonomous open marketplace. Funds are held by neither agent; only the
contract moves them, and only along the lifecycle (with a deadline refund as the backstop). Lifecycle mirrors
the ERC-8183 draft naming, with a **sealed commit-reveal** accept race that resists mempool frontrunning:
`createJob → fund → commitAccept → revealAccept → submitWork → complete | reject | claimRefund`.

- [`src/AgentWorksEscrowV3.sol`](src/AgentWorksEscrowV3.sol) - **the live escrow (open marketplace, MEV-hardened).**
  `createJob(evaluator, amount, specHash, deadline)` names **no** provider. Claiming a funded job is sealed:
  `commitAccept(commitment)` where `commitment = keccak256(abi.encode(jobId, msg.sender, salt))` publishes an
  opaque hash (the jobId stays off the public mempool), then after `revealDelayBlocks` `revealAccept(jobId, salt)`
  claims it - **first valid reveal wins**, a second reveal reverts, and a *copied* commitment is useless (it
  binds to the committer's address). Defeats frontrunning of the accept race (see [../docs/MEV.md](../docs/MEV.md)).
  Settlement (`complete`/`reject`) is gated to the per-job evaluator; unclaimed-past-deadline funds return via
  `claimRefund`. Self-contained (inline minimal `IERC20` + safe-transfer; no external imports → trivial explorer
  verification). An event on every transition; custom errors over `require` strings.
- [`src/MockUSDC.sol`](src/MockUSDC.sol) - 6-decimal mintable ERC-20, the deterministic settlement token.
- [`src/AgentWorksEscrowV2.sol`](src/AgentWorksEscrowV2.sol) - the prior v2 (raw `acceptJob` race), kept for history.
- [`src/AgentWorksEscrow.sol`](src/AgentWorksEscrow.sol) - the prior v1 (closed 1:1) escrow, kept for history.
- [`test/AgentWorksEscrowV3.t.sol`](test/AgentWorksEscrowV3.t.sol) (+ V2/V1 test files for history)
  - **70 tests total** (52 for v3): full lifecycle, both settlement branches, the **sealed commit-reveal race**
  (commit/reveal timing, address-binding anti-theft, replay, first-reveal-wins), expiry refund, access control,
  status guards, and a CEI/reentrancy-safety test.
- [`script/DeployV3.s.sol`](script/DeployV3.s.sol) - deploys escrow v3 bound to `USDC_TOKEN_ADDRESS` with
  `REVEAL_DELAY_BLOCKS`/`REVEAL_WINDOW_BLOCKS` (defaults 1 / 256). [`script/DeployV2.s.sol`] + 
  [`script/DeployMockUSDC.s.sol`](script/DeployMockUSDC.s.sol) remain.

## Live addresses (Ethereum Sepolia, chainId 11155111, all verified on Etherscan)
- Escrow v3 (live, commit-reveal): `0xFAab4d6ff5CBEcD72a4e1B9315662e7846166D69` (deploy block 11087195; delay=1, window=256)
- Escrow v2 (legacy, raw acceptJob): `0xD6cB413c0E4a5839Fd4B02aFFeBF65e6868726b9`
- MockUSDC:  `0x4C4D1223BcC47E380CF4C37652EaDFe10A9Fd910`

## Usage

Foundry lives at `~/.foundry/bin` (not on PATH on this machine). Env vars come from the repo-root `.env`.

```bash
forge build
forge test -vv                       # 70 tests
forge test --gas-report

# Deploy escrow v3 to Ethereum Sepolia (DEPLOYER_PRIVATE_KEY funded with Sepolia ETH):
set -a; . ../.env; set +a
forge script script/DeployV3.s.sol \
  --rpc-url "$RPC_URL" --broadcast \
  --verify --verifier etherscan --etherscan-api-key "$EXPLORER_API_KEY" --chain 11155111
```

> `lib/` (forge-std) is gitignored; run `git clone --depth 1 https://github.com/foundry-rs/forge-std lib/forge-std`
> on a fresh checkout.
