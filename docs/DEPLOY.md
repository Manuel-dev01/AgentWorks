# Deploying the AgentWorks dashboard to Vercel

The `/web` Next.js 15 app (landing `/`, brand `/brand`, dashboard `/dashboard`) is the demo surface.
It is built to run **hosted on Vercel** with live on-chain reads + the verified proof artifacts, while the
Python live-run stays a **localhost-only** capability.

## What runs where
| Capability | Local (`pnpm --filter web dev`) | Vercel (hosted) |
|---|---|---|
| Landing / brand / dashboard pages | ✅ | ✅ |
| Live USDC balances + job status (viem, read-only) | ✅ | ✅ |
| Verified proof artifacts (jobs, criticality beats, Pact JSON) | ✅ from `../agents` + `../docs` | ✅ from committed `web/data/` |
| Etherscan / Irys deep links | ✅ | ✅ |
| **Run-live** button (spawns the Python agents) | ✅ | ❌ hidden (serverless can't run the venv; `/api/run` is localhost-guarded) |

## Why `web/data/` exists
Next only bundles files under the project root, so the dashboard cannot `fs`-read the sibling
`../agents/scripts` / `../docs/pacts` from a serverless function. `web/scripts/snapshot-proofs.mjs`
copies the verified `*_proof.json` + Pact JSON into **`web/data/`** (committed to git, and refreshed by
`predev`/`prebuild`). `web/lib/proofs.ts` reads `web/data/` first and falls back to the sibling dirs for
local dev. Refresh after a new agent run with: `pnpm --filter web snapshot`.

## Vercel project settings
- **Framework preset:** Next.js
- **Root Directory:** repo root (leave default). Build runs `prebuild` (snapshot) → `next build`.
- **Install Command:** `pnpm install`
- **Build Command:** `pnpm --filter web build`
- **Output Directory:** `web/.next`
- **Environment Variables** — the public `NEXT_PUBLIC_*` block from `.env.example` (all non-secret testnet
  values; sensible defaults are also baked in, so the app works even if these are unset):
  `NEXT_PUBLIC_RPC_URL`, `NEXT_PUBLIC_ESCROW_ADDRESS`, `NEXT_PUBLIC_USDC_ADDRESS`,
  `NEXT_PUBLIC_CLIENT_CAW`, `NEXT_PUBLIC_PROVIDER_CAW`, `NEXT_PUBLIC_EXPLORER_BASE`,
  `NEXT_PUBLIC_IRYS_GATEWAY`. Do **not** set any `CAW_*` / `LLM_API_KEY` / `DEPLOYER_PRIVATE_KEY` on
  Vercel — those are agent-side secrets the hosted dashboard never uses.

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
