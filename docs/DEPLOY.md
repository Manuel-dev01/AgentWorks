# Deploying the AgentWorks dashboard to Vercel

The `/web` Next.js 15 app (landing `/`, brand `/brand`, dashboard `/dashboard`) is the demo surface — one
of **three** deployments (Vercel web + Railway agent service + a TSS signer host; see
[ARCHITECTURE.md](ARCHITECTURE.md) and [DEPLOY_AGENTS.md](DEPLOY_AGENTS.md)). The dashboard itself holds no
keys: it reads chain via viem and **triggers the deployed agent service** over HTTPS.

## What runs where
| Capability | Local (`pnpm --filter web dev`) | Vercel (hosted) |
|---|---|---|
| Landing / brand / dashboard pages | ✅ | ✅ |
| Live USDC balances + job/run status (viem + agent `/runs`, read-only) | ✅ | ✅ |
| Verified proof artifacts (autonomous runs, criticality beats, Pact JSON) | ✅ from `../agents` + `../docs` | ✅ from committed `web/data/` |
| Etherscan / Irys deep links | ✅ | ✅ |
| **New job → trigger** the autonomous agents (`POST /trigger` to the agent service) | ✅ | ✅ (calls the Railway service; needs a TSS signer up — see DEPLOY_AGENTS.md) |

## Why `web/data/` exists
Next only bundles files under the project root, so the dashboard cannot `fs`-read the sibling
`../agents/scripts` / `../docs/pacts` from a serverless function. `web/scripts/snapshot-proofs.mjs`
copies the verified `*_proof.json` + Pact JSON into **`web/data/`** (committed to git, and refreshed by
`predev`/`prebuild`). `web/lib/proofs.ts` reads `web/data/` first and falls back to the sibling dirs for
local dev. Refresh after a new agent run with: `pnpm --filter web snapshot`.

## Vercel project settings
- **Root Directory:** **`web`** (recommended). Vercel auto-detects Next.js, and for a pnpm workspace it
  walks up to the repo-root `pnpm-workspace.yaml` (so `allowBuilds: sharp` + the lockfile apply) and installs
  from there. Turn ON **"Include source files outside of the Root Directory"** so `prebuild` can snapshot
  from `../agents` / `../docs` — though `web/data/` is committed, so the dashboard works even without it.
- **Framework preset:** Next.js (auto-detected)
- **Install Command:** default (`pnpm install`)
- **Build Command:** default (`pnpm run build` → runs `prebuild` snapshot, then `next build`)
- **Output Directory:** default (`.next`)
- *(Alternative — Root Directory = repo root: set Build Command `pnpm --filter web build`, Output `web/.next`.)*
- **Environment Variables** — the public `NEXT_PUBLIC_*` block from `.env.example` (all non-secret testnet
  values; sensible defaults are also baked in, so the app works even if these are unset):
  `NEXT_PUBLIC_RPC_URL`, `NEXT_PUBLIC_ESCROW_V2_ADDRESS`, `NEXT_PUBLIC_USDC_ADDRESS`,
  `NEXT_PUBLIC_CLIENT_CAW`, `NEXT_PUBLIC_PROVIDER_CAW`, `NEXT_PUBLIC_EXPLORER_BASE`,
  `NEXT_PUBLIC_IRYS_GATEWAY`, and **`NEXT_PUBLIC_AGENT_API`** (the deployed agent service base URL — defaults
  to the live Railway URL, so the New-job trigger works even if unset). Do **not** set any `CAW_*` /
  `LLM_API_KEY` / `DEPLOYER_PRIVATE_KEY` on Vercel — those are agent-side secrets the hosted dashboard never uses.

## pnpm build-script note (`sharp`)
This repo pins `pnpm@11.1.2`, which gates native install scripts. `pnpm-workspace.yaml` approves the one
we hit: `allowBuilds: { sharp: true }` (sharp is Next's optional image optimizer; prebuilt binary, fast).
If a Vercel build ever errors with `ERR_PNPM_IGNORED_BUILDS`, set the Install Command to
`pnpm install --no-frozen-lockfile` or add the package under `onlyBuiltDependencies` for the pnpm version
Vercel resolves. Locally, `web/node_modules/.bin/next dev` bypasses the dep-status gate entirely.

## Local dev quickstart
```bash
pnpm install                 # approves sharp build; links web deps
pnpm --filter web dev        # http://localhost:3000  (/, /brand, /dashboard)
# Run-live buttons shell out to: agents/.venv/Scripts/python.exe agents/scripts/phase5_demo.py {good|bad}
```
