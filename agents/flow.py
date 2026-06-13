"""Resumable, step-by-step escrow flow for the dashboard's live journey.

Refactors the Phase-5 one-shot lifecycle (agents/scripts/phase5_demo.py) into independently
invocable steps that share a small JSON state file, so the web UI can drive each action live:

    start  -> Client LLM fund decision + Client CAW pact active           (no on-chain tx)
    post   -> createJob + approve + fund                                  (Client, 3 txs)
    accept -> Provider CAW pact active (authority binding)                (no on-chain tx)
    submit -> Provider LLM does task -> Irys upload -> submitWork         (Provider, 1 tx)
    settle -> Evaluator LLM verdict -> complete | reject                  (Client, 1 tx)

Each step reads + rewrites agents/scripts/.flow/<run_id>.json. CAW auth is stateless per process
(the pact stays active server-side between calls), so each step can run in its own process - which is
exactly how the web /api/flow route invokes flow_step.py. Reuses the existing modules; invents no SDK.
"""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from uuid import uuid4

import config
import escrow as esc
import irys_store
import pacts
import reasoning
from caw import CawWallet
from web3 import Web3

STATE_DIR = Path(__file__).resolve().parent / "scripts" / ".flow"
AMOUNT = 10_000_000  # 10 USDC (6 decimals)
TASK = ("Write a clear 2-3 sentence explanation, for a non-expert, of how an on-chain escrow lets "
        "two agents who don't trust each other transact safely.")
BUDGET = 1000.0


def _state_path(run_id: str) -> Path:
    return STATE_DIR / f"{run_id}.json"


def load_state(run_id: str) -> dict:
    p = _state_path(run_id)
    if not p.exists():
        raise RuntimeError(f"no flow run '{run_id}' (state file missing)")
    return json.loads(p.read_text(encoding="utf-8"))


def save_state(state: dict) -> dict:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = int(time.time())
    _state_path(state["run_id"]).write_text(json.dumps(state, default=str, indent=2), encoding="utf-8")
    return state


def _spec(state: dict) -> str:
    """The full task spec the LLM works against (title + acceptance criteria)."""
    task = state.get("task") or TASK
    crit = (state.get("criteria") or "").strip()
    return f"{task}\n\nAcceptance criteria: {crit}" if crit else task


def _client():
    return config.client_agent()


def _provider():
    return config.provider_agent()


async def _revoke_all(w: CawWallet) -> None:
    try:
        page = await w.list_pacts(status="active")
    except Exception:
        return
    items = page if isinstance(page, list) else (page.get("items", []) if isinstance(page, dict) else [])
    for p in items:
        if isinstance(p, dict) and p.get("status") == "active" and p.get("id"):
            try:
                await w.revoke_pact(p["id"])
            except Exception:
                pass


async def _call(agent: CawWallet, src: str, target: str, calldata: str, label: str, run_id: str, n: int) -> str:
    rid = f"flow-{run_id}-{n}-{uuid4().hex[:6]}"
    resp = await agent.contract_call(src_addr=src, contract_addr=target, calldata=calldata,
                                     chain_id=config.CHAIN_ID, request_id=rid, description=label)
    rec = await agent.wait_tx_final(rid)
    return (rec or {}).get("transaction_hash") or (resp or {}).get("transaction_hash") or ""


# ── steps ──────────────────────────────────────────────────────────────────

async def start(mode: str = "good", task: str | None = None, criteria: str | None = None,
                amount_usdc: float | None = None) -> dict:
    assert mode in ("good", "bad")
    run_id = uuid4().hex[:10]
    cc = _client()
    amt = float(amount_usdc) if amount_usdc else AMOUNT / 1e6
    amt_base = int(round(amt * 1_000_000))
    state = {
        "run_id": run_id, "mode": mode, "status": "started",
        "task": (task or TASK).strip(), "criteria": (criteria or "").strip(),
        "amount_usdc": amt, "amount_base": amt_base, "created_at": int(time.time()),
        "client": cc.address, "provider": _provider().address,
        "txs": {}, "irys": None, "deliverable": None, "verdict": None, "branch": None,
        "client_pact_id": None, "provider_pact_id": None,
    }
    # Client genuinely decides whether to fund (criterion 1).
    fund = reasoning.client_decide_fund(_spec(state), amt, BUDGET)
    state["fund_decision"] = fund
    if not fund.get("fund"):
        state["status"] = "declined"
        return save_state(state)

    async with CawWallet(api_url=config.CAW_API_URL, api_key=cc.api_key, wallet_uuid=cc.wallet_id, name="Client") as cw:
        await _revoke_all(cw)
        sub = await cw.submit_pact(intent="Client funds + evaluates escrow jobs",
                                   spec=pacts.client_escrow_pact(), name=f"flow-client-{run_id}")
        pact = await cw.wait_pact_active(sub.get("pact_id"))
        state["client_pact_id"] = pact.get("id") or sub.get("pact_id")
    return save_state(state)


async def post(run_id: str) -> dict:
    state = load_state(run_id)
    cc = _client()
    w3 = esc.web3()
    job_id = esc.next_job_id(w3)
    amt = int(state["amount_base"])
    spec_hash = Web3.keccak(text=f"{_spec(state)}#{job_id}")
    deadline = int(time.time()) + 7 * 24 * 3600
    state["job_id"] = job_id
    async with CawWallet(api_url=config.CAW_API_URL, api_key=cc.api_key, wallet_uuid=cc.wallet_id, name="Client") as cw:
        client = cw.scoped(await cw.get_pact(state["client_pact_id"]))
        state["txs"]["createJob"] = await _call(client, cc.address, config.ESCROW_ADDRESS,
            esc.create_job(_provider().address, cc.address, amt, spec_hash, deadline), "createJob", run_id, 1)
        state["txs"]["approve"] = await _call(client, cc.address, config.USDC_ADDRESS,
            esc.approve(config.ESCROW_ADDRESS, amt), "approve", run_id, 2)
        state["txs"]["fund"] = await _call(client, cc.address, config.ESCROW_ADDRESS,
            esc.fund(job_id), "fund", run_id, 3)
    state["status"] = "posted"
    return save_state(state)


async def accept(run_id: str) -> dict:
    state = load_state(run_id)
    pp = _provider()
    async with CawWallet(api_url=config.CAW_API_URL, api_key=pp.api_key, wallet_uuid=pp.wallet_id, name="Provider") as pw:
        await _revoke_all(pw)
        sub = await pw.submit_pact(intent="Provider submits deliverables",
                                   spec=pacts.provider_pact(), name=f"flow-provider-{run_id}")
        pact = await pw.wait_pact_active(sub.get("pact_id"))
        state["provider_pact_id"] = pact.get("id") or sub.get("pact_id")
    state["status"] = "accepted"
    return save_state(state)


async def submit(run_id: str) -> dict:
    state = load_state(run_id)
    pp = _provider()
    deliverable = reasoning.provider_do_task(_spec(state), sabotage=(state["mode"] == "bad"))
    state["deliverable"] = deliverable
    dhash = Web3.keccak(text=deliverable)
    irys = irys_store.upload(deliverable, tags={"app": "AgentWorks", "job-id": str(state["job_id"]),
                                                "content-keccak": Web3.to_hex(dhash)})
    state["irys"] = irys
    async with CawWallet(api_url=config.CAW_API_URL, api_key=pp.api_key, wallet_uuid=pp.wallet_id, name="Provider") as pw:
        provider = pw.scoped(await pw.get_pact(state["provider_pact_id"]))
        state["txs"]["submitWork"] = await _call(provider, pp.address, config.ESCROW_ADDRESS,
            esc.submit_work(state["job_id"], dhash, irys["id"]), "submitWork", run_id, 4)
    state["status"] = "submitted"
    return save_state(state)


async def settle(run_id: str) -> dict:
    state = load_state(run_id)
    cc = _client()
    # Evaluator fetches the deliverable FROM Irys (by the on-chain id) and judges it.
    fetched = irys_store.fetch(state["irys"]["id"]).decode("utf-8", "replace")
    verdict = reasoning.evaluate(_spec(state), fetched)
    state["verdict"] = verdict
    async with CawWallet(api_url=config.CAW_API_URL, api_key=cc.api_key, wallet_uuid=cc.wallet_id, name="Client") as cw:
        client = cw.scoped(await cw.get_pact(state["client_pact_id"]))
        if verdict.get("accept"):
            state["txs"]["complete"] = await _call(client, cc.address, config.ESCROW_ADDRESS,
                esc.complete(state["job_id"]), "complete", run_id, 5)
            state["branch"] = "payout"
        else:
            state["txs"]["reject"] = await _call(client, cc.address, config.ESCROW_ADDRESS,
                esc.reject(state["job_id"]), "reject", run_id, 5)
            state["branch"] = "refund"
    # content verification against the on-chain hash
    final = esc.get_job(esc.web3(), state["job_id"])
    state["final_status"] = final["status"]
    state["content_verified"] = (irys_store.keccak(irys_store.fetch(state["irys"]["id"])) == final["deliverable_hash"])
    state["status"] = "settled"
    return save_state(state)


# ── dispatch ─────────────────────────────────────────────────────────────────

def run_step(step: str, run_id: str | None = None, mode: str = "good", task: str | None = None,
             criteria: str | None = None, amount_usdc: float | None = None) -> dict:
    if step == "start":
        return asyncio.run(start(mode, task, criteria, amount_usdc))
    if run_id is None:
        raise RuntimeError(f"step '{step}' requires a run_id")
    fn = {"post": post, "accept": accept, "submit": submit, "settle": settle}.get(step)
    if fn is None:
        raise RuntimeError(f"unknown step '{step}'")
    return asyncio.run(fn(run_id))
