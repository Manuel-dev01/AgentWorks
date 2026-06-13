"""AgentWorks MCP server - the open agent socket.

Run locally by an operator with their OWN Cobo Agentic Wallet. Exposes the AgentWorks marketplace as MCP tools
so ANY MCP-capable agent (Claude Desktop / Claude Code / etc.) can be a client or a provider. The genuine
"agent" is the connecting LLM; this server just ships the socket.

Trustless by construction: calldata is built locally (escrow_v2), signed through the operator's OWN CAW wallet
(Pact-scoped), and only the shared off-chain board is read from the deployed service. The operator's api_key
never leaves this process, and the Pact is the hard boundary regardless of what the connecting LLM decides
(a provider Pact excludes USDC, so a provider can accept + deliver but can never move escrowed funds).

Config (env - the operator's own wallet):
  MCP_WALLET_ID, MCP_API_KEY, MCP_ADDRESS, MCP_ROLE=client|provider
  AGENT_API (marketplace board base url; defaults to the live Railway service)
  + reused from config.py / .env: RPC_URL, ESCROW_V2_CONTRACT_ADDRESS, USDC_TOKEN_ADDRESS, CAW_CHAIN_ID, IRYS_*

Run:  python agents/mcp_server.py            # stdio (for Claude Desktop / Code)
Signing tools need the operator's TSS node connected to the CAW relay; read tools do not.
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
from pathlib import Path
from uuid import uuid4
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))  # sibling imports regardless of cwd

import requests
from web3 import Web3
from mcp.server.fastmcp import FastMCP

import config
import escrow_v2 as esc
import irys_store
import pacts
from caw import CawWallet

MCP_WALLET_ID = os.environ.get("MCP_WALLET_ID", "")
MCP_API_KEY = os.environ.get("MCP_API_KEY", "")
MCP_ADDRESS = os.environ.get("MCP_ADDRESS", "")
MCP_ROLE = (os.environ.get("MCP_ROLE", "provider") or "provider").lower()
AGENT_API = (os.environ.get("AGENT_API") or os.environ.get("NEXT_PUBLIC_AGENT_API")
             or "https://insightful-wisdom-production-5c62.up.railway.app").rstrip("/")
EXPLORER = (os.environ.get("NEXT_PUBLIC_EXPLORER_BASE") or "https://sepolia.etherscan.io").rstrip("/")

mcp = FastMCP("agentworks")

# Cached operator wallet bound to an active Pact (lazy; created on first signing tool or onboard()).
_scoped: CawWallet | None = None
_pact: dict | None = None


# ── helpers ──────────────────────────────────────────────────────────────────

def _tx(h: str) -> dict:
    return {"hash": h, "url": f"{EXPLORER}/tx/{h}" if h else ""}


async def _get(path: str) -> Any:
    def _do():
        r = requests.get(f"{AGENT_API}{path}", timeout=30)
        r.raise_for_status()
        return r.json()
    return await asyncio.to_thread(_do)


async def _revoke_active(w: CawWallet) -> None:
    try:
        page = await w.list_pacts(status="active")
    except Exception:
        return
    items = page if isinstance(page, list) else (page.get("items", []) if isinstance(page, dict) else [])
    for p in items:
        if isinstance(p, dict) and p.get("id"):
            try:
                await w.revoke_pact(p["id"])
            except Exception:
                pass


async def _ensure_onboarded() -> CawWallet:
    """Submit the role's scoped Pact on the operator's OWN wallet and cache the pact-scoped client.
    Idempotent for the process lifetime (revokes stale active pacts first for a clean slate)."""
    global _scoped, _pact
    if _scoped is not None:
        return _scoped
    if not (MCP_WALLET_ID and MCP_API_KEY and MCP_ADDRESS):
        raise RuntimeError("set MCP_WALLET_ID / MCP_API_KEY / MCP_ADDRESS to your own CAW wallet")
    if MCP_ROLE not in ("client", "provider"):
        raise RuntimeError("MCP_ROLE must be 'client' or 'provider'")
    root = CawWallet(api_url=config.CAW_API_URL, api_key=MCP_API_KEY, wallet_uuid=MCP_WALLET_ID, name=f"mcp-{MCP_ROLE}")
    await _revoke_active(root)
    spec = (pacts.provider_pact(escrow=config.ESCROW_V2_ADDRESS) if MCP_ROLE == "provider"
            else pacts.client_escrow_pact(escrow=config.ESCROW_V2_ADDRESS, usdc=config.USDC_ADDRESS))
    sub = await root.submit_pact(intent=f"AgentWorks MCP {MCP_ROLE}", spec=spec,
                                 name=f"mcp-{MCP_ROLE}-{MCP_WALLET_ID[:8]}")
    _pact = await root.wait_pact_active(sub.get("pact_id"))
    _scoped = root.scoped(_pact)
    return _scoped


async def _sign(target: str, calldata: str, label: str) -> str:
    """contract_call through the operator's Pact-scoped wallet → wait for finality → return the tx hash."""
    w = await _ensure_onboarded()
    rid = f"mcp-{uuid4().hex[:10]}"
    resp = await w.contract_call(src_addr=MCP_ADDRESS, contract_addr=target, calldata=calldata,
                                 chain_id=config.CHAIN_ID, request_id=rid, description=label)
    rec = await w.wait_tx_final(rid, timeout=420.0)
    return (rec or {}).get("transaction_hash") or (resp or {}).get("transaction_hash") or ""


# ── discovery tools (no signing) ─────────────────────────────────────────────

@mcp.tool()
async def list_open_jobs() -> dict:
    """List funded, unclaimed jobs available to accept (chain-true), with their human-readable task text."""
    return await _get("/marketplace/jobs?status=open")


@mcp.tool()
async def list_all_jobs() -> dict:
    """List all recent marketplace jobs with on-chain status (open, accepted, submitted, settled)."""
    return await _get("/marketplace/jobs?status=all")


@mcp.tool()
async def get_job(job_id: int) -> dict:
    """Get one job's on-chain status + listing. Use after accept_job to confirm you won the race
    (provider == your address)."""
    return await _get(f"/marketplace/jobs/{job_id}")


@mcp.tool()
async def get_deliverable(job_id: int) -> dict:
    """Fetch the submitted deliverable from Irys for a job, so an evaluator agent can judge it against the spec."""
    w3 = esc.web3()
    job = await asyncio.to_thread(esc.get_job, w3, job_id)
    irys_id = job.get("irys_id") or ""
    if not irys_id:
        return {"job_id": job_id, "status": job.get("status"), "deliverable": None,
                "note": "no deliverable submitted yet"}
    content = (await asyncio.to_thread(irys_store.fetch, irys_id)).decode("utf-8", "replace")
    return {"job_id": job_id, "irys_id": irys_id, "status": job.get("status"),
            "content_hash_onchain": job.get("deliverable_hash"), "deliverable": content}


@mcp.tool()
async def marketplace_participants() -> dict:
    """List the seeded marketplace participants (public info - no keys)."""
    return await _get("/marketplace/participants")


@mcp.tool()
async def my_wallet() -> dict:
    """Show this operator's CAW wallet identity, role, native + USDC balances, and active-Pact status."""
    if not (MCP_WALLET_ID and MCP_API_KEY and MCP_ADDRESS):
        return {"configured": False, "note": "set MCP_WALLET_ID / MCP_API_KEY / MCP_ADDRESS to your CAW wallet"}
    out: dict = {"configured": True, "role": MCP_ROLE, "address": MCP_ADDRESS, "wallet_id": MCP_WALLET_ID,
                 "onboarded": _scoped is not None, "pact_id": (_pact or {}).get("id") if _pact else None,
                 "escrow_v2": config.ESCROW_V2_ADDRESS, "chain": "Ethereum Sepolia"}
    try:
        w3 = esc.web3()
        out["eth"] = w3.eth.get_balance(Web3.to_checksum_address(MCP_ADDRESS)) / 1e18
        out["usdc"] = (await asyncio.to_thread(esc.usdc_balance, w3, MCP_ADDRESS)) / 1_000_000
    except Exception as e:
        out["balance_note"] = f"balance read failed: {type(e).__name__}"
    return out


@mcp.tool()
async def workflow_guide() -> dict:
    """How to participate. Returns the provider and client step sequences (which tools to call, in order)."""
    return {
        "your_role": MCP_ROLE,
        "provider": ["onboard()", "list_open_jobs()", "(decide which job is worth the reward)",
                     "accept_job(job_id)  # on-chain race; check 'won'", "(do the work)",
                     "deliver_work(job_id, deliverable)"],
        "client": ["onboard()", "post_job(task, criteria, reward_usdc)",
                   "(wait; poll get_job(job_id) until status == 'Submitted')",
                   "get_deliverable(job_id)  # judge it against the spec",
                   "evaluate_and_settle(job_id, accept=True|False)"],
        "note": "Authority is your Pact, not this server. A provider Pact excludes USDC, so you can accept + "
                "deliver but can never move escrowed funds; only the escrow contract settles.",
    }


# ── onboarding (self-Pact, trustless) ────────────────────────────────────────

@mcp.tool()
async def onboard() -> dict:
    """Bind this wallet's scoped Pact (the authority boundary) on YOUR OWN CAW wallet. Trustless: your api_key
    never leaves this process. Provider Pact = escrow-only (no USDC); client Pact = escrow + USDC, tx-capped."""
    await _ensure_onboarded()
    return {"onboarded": True, "role": MCP_ROLE, "address": MCP_ADDRESS,
            "pact_id": (_pact or {}).get("id"), "pact_status": (_pact or {}).get("status"),
            "policy": "provider: escrow-only, USDC excluded" if MCP_ROLE == "provider"
                      else "client: escrow + USDC allowlist, tx-capped"}


# ── client tools (sign via the operator's wallet) ────────────────────────────

@mcp.tool()
async def post_job(task: str, criteria: str = "", reward_usdc: float = 5.0, deadline_days: int = 7) -> dict:
    """[client] Open + fund a job through YOUR OWN wallet (createJob → approve → fund), then publish the listing
    so providers can discover the task. You become the job's evaluator. Returns the job_id + tx hashes."""
    if MCP_ROLE != "client":
        return {"error": "MCP_ROLE must be 'client' to post jobs"}
    w3 = esc.web3()
    job_id = await asyncio.to_thread(esc.next_job_id, w3)
    spec = f"{task}\n\nAcceptance criteria: {criteria}".strip() if criteria else task
    spec_hash = Web3.keccak(text=f"{spec}#{job_id}")
    amt = int(round(reward_usdc * 1_000_000))
    deadline = int(time.time()) + max(1, deadline_days) * 24 * 3600
    tx_create = await _sign(config.ESCROW_V2_ADDRESS, esc.create_job(MCP_ADDRESS, amt, spec_hash, deadline), "createJob")
    tx_approve = await _sign(config.USDC_ADDRESS, esc.approve(config.ESCROW_V2_ADDRESS, amt), "approve")
    tx_fund = await _sign(config.ESCROW_V2_ADDRESS, esc.fund(job_id), "fund")
    listing: Any = None
    try:
        def _pub():
            r = requests.post(f"{AGENT_API}/marketplace/jobs",
                              json={"job_id": job_id, "task": task, "criteria": criteria, "reward_usdc": reward_usdc},
                              timeout=30)
            return r.json() if r.status_code < 400 else {"warn": f"HTTP {r.status_code}: {r.text[:200]}"}
        listing = await asyncio.to_thread(_pub)
    except Exception as e:
        listing = {"warn": f"listing publish failed: {type(e).__name__}: {e}"}
    return {"job_id": job_id, "evaluator": MCP_ADDRESS, "reward_usdc": reward_usdc,
            "txs": {"createJob": _tx(tx_create), "approve": _tx(tx_approve), "fund": _tx(tx_fund)},
            "listing_published": listing, "next": "providers can now accept_job(%d); poll get_job(%d)" % (job_id, job_id)}


@mcp.tool()
async def evaluate_and_settle(job_id: int, accept: bool) -> dict:
    """[client / evaluator] Settle a submitted job: accept → complete (payout to provider), reject → reject
    (refund to client). Only the job's recorded evaluator can do this on-chain. Read get_deliverable(job_id) first."""
    w3 = esc.web3()
    job = await asyncio.to_thread(esc.get_job, w3, job_id)
    if job["status"] != "Submitted":
        return {"error": f"job {job_id} is not Submitted (status: {job['status']})"}
    if accept:
        tx = await _sign(config.ESCROW_V2_ADDRESS, esc.complete(job_id), "complete")
        branch = "payout"
    else:
        tx = await _sign(config.ESCROW_V2_ADDRESS, esc.reject(job_id), "reject")
        branch = "refund"
    final = await asyncio.to_thread(esc.get_job, w3, job_id)
    return {"job_id": job_id, "branch": branch, "tx": _tx(tx), "final_status": final["status"]}


# ── provider tools (sign via the operator's wallet) ──────────────────────────

@mcp.tool()
async def accept_job(job_id: int) -> dict:
    """[provider] Claim a funded job on-chain (acceptJob). First claimer wins the race; a late claim reverts.
    Re-reads the job afterward to report whether you won."""
    w3 = esc.web3()
    job = await asyncio.to_thread(esc.get_job, w3, job_id)
    if job["status"] != "Funded":
        return {"error": f"job {job_id} is not available (status: {job['status']})"}
    try:
        tx = await _sign(config.ESCROW_V2_ADDRESS, esc.accept_job(job_id), "acceptJob")
    except Exception as e:
        return {"won": False, "error": f"acceptJob reverted - likely lost the race: {type(e).__name__}: {e}"}
    after = await asyncio.to_thread(esc.get_job, w3, job_id)
    won = int(after["provider"], 16) == int(MCP_ADDRESS, 16)
    return {"job_id": job_id, "won": won, "tx": _tx(tx), "provider_now": after["provider"],
            "next": "deliver_work(%d, <your work>)" % job_id if won else "another provider won; pick another job"}


@mcp.tool()
async def deliver_work(job_id: int, deliverable: str) -> dict:
    """[provider] Store your work on Irys and submit its keccak256 hash on-chain (submitWork). You must be the
    job's accepted provider. The client/evaluator then judges it and settles."""
    w3 = esc.web3()
    job = await asyncio.to_thread(esc.get_job, w3, job_id)
    if job["status"] != "Accepted":
        return {"error": f"job {job_id} is not Accepted (status: {job['status']})"}
    if not deliverable.strip():
        return {"error": "deliverable is empty"}
    dhash = Web3.keccak(text=deliverable)
    try:
        irys = await asyncio.to_thread(
            irys_store.upload, deliverable,
            {"app": "AgentWorks", "job-id": str(job_id), "content-keccak": Web3.to_hex(dhash)})
    except Exception as e:
        return {"error": f"Irys upload failed: {type(e).__name__}: {e}"}
    tx = await _sign(config.ESCROW_V2_ADDRESS, esc.submit_work(job_id, dhash, irys.get("id")), "submitWork")
    return {"job_id": job_id, "irys_id": irys.get("id"), "irys_url": irys.get("url"),
            "deliverable_hash": Web3.to_hex(dhash), "tx": _tx(tx),
            "next": "the job's evaluator now settles via evaluate_and_settle(%d, accept=...)" % job_id}


def main() -> None:
    mcp.run()  # stdio transport (Claude Desktop / Code). For HTTP: mcp.run(transport="streamable-http").


if __name__ == "__main__":
    main()
