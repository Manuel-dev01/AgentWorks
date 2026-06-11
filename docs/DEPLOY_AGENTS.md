# Deploying the autonomous agents (Phase 6.5.4)

The autonomous open-marketplace agents (`agents/autonomous.py`) run behind an HTTP control surface
(`agents/server.py`). This doc is how to run them **always-on**, and the **exact config you (human) must
provide**. The dashboard (`/web`, on Vercel) calls this service instead of spawning local processes.

## Architecture — two always-on pieces

CAW decouples *deciding/submitting* a transaction from *signing* it:

```
        ┌──────────────────────────┐        HTTPS         ┌─────────────────────┐
        │  Agent service (cloud)   │ ───────────────────▶ │   CAW cloud API     │
        │  FastAPI + autonomous    │  contract_call /     │ (pact enforcement,  │
        │  loops. NO key material. │  pact / status reads │  routes signing)    │
        └──────────────────────────┘                      └──────────┬──────────┘
                  ▲   ▲                                               │ websocket (relay)
       dashboard  │   │ reads on-chain (viem)                         ▼
       (Vercel) ──┘   │                                  ┌─────────────────────────┐
                      └───────────────────────────────── │  TSS signer (always-on) │
                          Ethereum Sepolia               │  holds the MPC key share │
                                                          └─────────────────────────┘
```

- **(a) Agent service** — `agents/Dockerfile`. Stateless w.r.t. keys; talks to the CAW cloud API and
  reads chain. **Deploy this to Railway/Fly** (or any container host). Verified locally end-to-end.
- **(b) TSS signer** — the CAW MPC node that co-signs. It must be **always-on and connected to the relay**,
  and it **holds your key share**. Two hosting options below.

> The local Windows `cobo-tss-node.exe` you already run IS this signer. It just isn't always-on.

## TSS signer hosting — pick one

| Option | What | Trade-off |
|---|---|---|
| **A. Self-controlled host (recommended)** | Keep the signer on a machine/VM **you** control, using the EXISTING funded key shares. A small always-on Linux VM, or your machine while demoing. | No key migration, no re-funding, key share stays on your hardware. Not "fully cloud," but the security-sensitive piece staying under your control is a feature, not a bug. |
| **B. Containerized signer** | `agents/tss/Dockerfile.tss` downloads the Linux CAW node and runs daemons from key shares **mounted** at `/keys`. Run it on a VM (Railway/Fly/GCP). | Fully cloud. Requires moving the key share (see caveat) and treating it as a secret/volume. |

**Caveat (both options):** only **one** node per wallet identity may be on the CAW relay at a time — a
second connection is refused ("duplicate node ID … register refused"). So **stop the local signer before
running another** for the same wallets.

**Key-share portability (Option B) is VERIFIED ✅ (2026-06-11):** the Linux `cobo-tss-node` in `agentworks-tss`
loaded the **Windows-generated** key shares (mounted at `/keys`) and connected to the relay with the *same*
node ids, then **co-signed a real tx** (`acceptJob` `0xdc60b338…`). So you can run the containerized signer
with your EXISTING funded wallets — no re-onboard, no re-fund.

### Option B — containerized signer: exact steps
1. **Mount Path = `/keys`** (the image hardcodes `PROFILES_DIR=/keys`). Inside it, one subdir per wallet, each
   holding that profile's `tss-node` contents — minimally `.password` + `db/secrets.db` + `configs/`:
   ```
   /keys/client/   ← from %USERPROFILE%\.cobo-agentic-wallet\profiles\profile_caw_agent_4bc15e6348db0514\tss-node\
   /keys/provider/ ← from …\profile_caw_agent_e6318ac84f123085\tss-node\
   ```
2. **Populate the volume.** A fresh Railway volume is empty. Proven/simplest options:
   - **Small always-on VM (recommended):** `git`-less copy your `keys/` dir to the VM and run
     `docker compose --profile tss up -d` (the compose mounts `./keys:/keys`). This is exactly the setup
     verified locally.
   - **Railway volume:** after attaching the volume at `/keys`, populate it once via `railway ssh` into the
     service and reconstruct from a base64 blob over **stdin** (no size limit):
     `bash agents/tss/make_keyshare_env.sh ./keys` emits `TSS_KEYSHARE_CLIENT_B64=…` / `…PROVIDER_B64=…`;
     pipe each blob's value: `echo '<blob>' | base64 -d | tar -xz -C /keys/client` (and `/provider`).
   - **Env-var auto-reconstruct (platform-dependent):** set `TSS_KEYSHARE_CLIENT_B64` / `TSS_KEYSHARE_PROVIDER_B64`
     as secrets and the entrypoint rebuilds `/keys` on first boot. NOTE: each blob is ~234 KB; docker's
     `--env-file` rejects that (64 KB line cap), and some platforms cap env-var size — use only if your host
     accepts large variables.
3. **Free the relay first:** stop any other signer for these wallets (local `cobo-tss-node.exe`) — the relay
   refuses a duplicate node id.

If you ever DON'T want to move the key share, the fallback is `caw onboard` fresh wallets on the Linux host
(new wallet ids → re-fund + re-issue Pacts) — but portability is verified, so you shouldn't need this.

## What YOU need to provide (human checklist)

1. **A container host account** for the agent service — **Railway** or **Fly.io** (+ its CLI, logged in).
   I can't authenticate your account; you run the final `up`/`deploy`.
2. **Secrets/env** on that host (copy the values from your local `.env` — never commit them):
   - CAW: `CAW_CLIENT_WALLET_ID`, `CAW_CLIENT_API_KEY`, `CAW_CLIENT_ADDRESS`,
     `CAW_PROVIDER_WALLET_ID`, `CAW_PROVIDER_API_KEY`, `CAW_PROVIDER_ADDRESS`,
     `CAW_PROVIDER_ADDRESS_2=0x7ea0701d657e3427c2bb3bc195e943a81c5fc69e`, `AGENT_WALLET_API_URL`,
     `CAW_CHAIN_ID=SETH`.
   - Chain/contracts: `RPC_URL`, `ESCROW_V2_CONTRACT_ADDRESS=0xD6cB413c0E4a5839Fd4B02aFFeBF65e6868726b9`,
     `USDC_TOKEN_ADDRESS=0x4C4D1223BcC47E380CF4C37652EaDFe10A9Fd910`.
   - LLM: `LLM_API_KEY`, `LLM_MODEL`, `LLM_BASE_URL`.
   - Irys: `IRYS_PRIVATE_KEY` (the EVM key that funds the Irys devnet node; falls back to `DEPLOYER_PRIVATE_KEY`).
   - Service hardening (recommended for a public URL): `AGENT_TRIGGER_TOKEN=<random secret>` (protects
     `POST /trigger`), `AGENT_CORS_ORIGINS=https://<your-vercel-domain>` (lock CORS to the dashboard).
3. **TSS signer decision** (Option A or B) and, if **A**, an always-on host to keep it running (your machine
   during the demo is fine; a tiny VM is better). If **B**, the key-share volume + the portability test.
4. **Gas + USDC**: keep the Client and provider addresses funded on Sepolia (gas), and the Client holding
   MockUSDC (mint via the MockUSDC contract if needed).

## Deploy steps

### Agent service → Railway (example)
```bash
# from repo root, with the Railway CLI logged in
railway init                       # or link an existing project
railway up --dockerfile agents/Dockerfile   # build context = repo root
# set the env vars from the checklist (railway variables set KEY=VALUE …, or the dashboard)
# Railway gives you a public URL, e.g. https://agentworks-agent.up.railway.app
```

### Agent service → Fly.io (example)
```bash
fly launch --dockerfile agents/Dockerfile --no-deploy   # generates fly.toml
fly secrets set CAW_CLIENT_API_KEY=… LLM_API_KEY=… …    # all secrets from the checklist
fly deploy
```

### Local always-on (Docker, both pieces)
```bash
# agent only (TSS stays on your machine):
docker compose up agent
# agent + containerized signer (Option B; stop the local Windows signer first; put key shares in ./keys/<name>/):
docker compose --profile tss up
```

## Verify the deployment
```bash
curl https://<host>/health            # → {"status":"ok", escrow_v2, providers:2, …}
curl https://<host>/runs              # → past run artifacts
curl -X POST https://<host>/trigger \ # launches a real run (needs the signer up)
  -H "authorization: Bearer $AGENT_TRIGGER_TOKEN" -H "content-type: application/json" \
  -d '{"mode":"good","reward_usdc":5,"max_jobs":1}'
# then poll /runs and open the resulting tx hashes on https://sepolia.etherscan.io
```
**Proof gate (CLAUDE.md §4):** the deployment is only "always-on ✅" once a real signed tx originates
through it (a job lifecycle settles via the deployed `/trigger`). Until then it is WRITTEN-UNVERIFIED.

## Dashboard wiring (Phase 6.5.5)
The dashboard will call this service via a public base URL (e.g. `NEXT_PUBLIC_AGENT_API=https://<host>`),
keeping the deterministic verified-replay mode for the hosted judge demo. Wired in 6.5.5.
