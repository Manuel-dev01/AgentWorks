"""Autonomous agents — continuous loops over the open marketplace (Phase 6.5.3).

Two long-running roles, each acting through its own CAW wallet under a scoped Pact, coordinating
via an off-chain job board (the marketplace listing) + the on-chain v2 escrow (the source of truth):

  Client loop   — for each task it deems worth funding: createJob (OPEN) → approve → fund, and posts
                  the task text to the board. Then watches its jobs; when one is Submitted it fetches
                  the deliverable from Irys, evaluates it, and complete()s (payout) or reject()s (refund).
  Provider pool — N provider identities. Each scans the board + chain for funded, unclaimed jobs,
                  genuinely decides whether to accept, and races to acceptJob() on-chain (first wins;
                  losers revert/skip). The winner does the work, stores it on Irys, and submitWork()s.

Genuine LLM reasoning at every decision (criterion 1); the Pact is the hard boundary regardless
(criterion 2). Every CAW call + decision is logged; a proof artifact is written per settled job.
Reuses escrow_v2 / pacts / reasoning / registry / irys_store — invents no SDK surface.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import time
from pathlib import Path
from uuid import uuid4

import config
import escrow_v2 as esc
import irys_store
import pacts
import reasoning
import registry
from caw import CawWallet
from web3 import Web3

log = logging.getLogger("auto")

# Off-chain marketplace state (board + run artifacts). On a host with ephemeral storage (e.g. Railway),
# set AGENT_DATA_DIR to a mounted volume so listings + registrations survive restarts; default is the
# in-repo path for local dev.
_DATA_DIR = Path(os.environ["AGENT_DATA_DIR"]) if os.environ.get("AGENT_DATA_DIR") else (Path(__file__).resolve().parent / "scripts")
MARKET_DIR = _DATA_DIR / ".market"
BOARD_FILE = MARKET_DIR / "board.json"
RUNS_DIR = MARKET_DIR / "runs"
BUDGET_USDC = 1000.0
POLL = 4.0  # seconds between scans


# ── off-chain job board (the marketplace listing) ───────────────────────────

def _read_board() -> dict:
    if BOARD_FILE.exists():
        try:
            return json.loads(BOARD_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _write_board(board: dict) -> None:
    MARKET_DIR.mkdir(parents=True, exist_ok=True)
    BOARD_FILE.write_text(json.dumps(board, indent=2), encoding="utf-8")


def _post_listing(job_id: int, *, task: str, criteria: str, reward_usdc: float,
                  spec_hash: str, client: str, deadline: int) -> None:
    board = _read_board()
    board[str(job_id)] = {
        "job_id": job_id, "task": task, "criteria": criteria, "reward_usdc": reward_usdc,
        "spec_hash": spec_hash, "client": client, "deadline": deadline, "posted_at": int(time.time()),
    }
    _write_board(board)


def _listing(job_id: int) -> dict | None:
    return _read_board().get(str(job_id))


def _spec_text(listing: dict) -> str:
    crit = (listing.get("criteria") or "").strip()
    return f"{listing['task']}\n\nAcceptance criteria: {crit}" if crit else listing["task"]


# ── shared run state ────────────────────────────────────────────────────────

class Run:
    def __init__(self, *, mode: str, target: int) -> None:
        self.mode = mode                      # 'good' | 'bad'
        self.target = target                  # stop after this many jobs settle
        self.run_id = uuid4().hex[:10]
        self.jobs: dict[int, dict] = {}       # job_id -> record
        self.settled = 0
        self.stop = asyncio.Event()

    def record(self, job_id: int) -> dict:
        return self.jobs.setdefault(job_id, {
            "run_id": self.run_id, "job_id": job_id, "txs": {}, "accept_decisions": {},
            "winner": None, "winner_addr": None, "irys": None, "deliverable": None,
            "verdict": None, "branch": None, "status": "open",
        })

    def write_artifact(self, job_id: int) -> None:
        RUNS_DIR.mkdir(parents=True, exist_ok=True)
        rec = self.jobs[job_id]
        (RUNS_DIR / f"{job_id}.json").write_text(json.dumps(rec, default=str, indent=2), encoding="utf-8")


async def _revoke_active(w: CawWallet) -> None:
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


async def _call(agent: CawWallet, src: str, target: str, calldata: str, label: str) -> str:
    rid = f"auto-{uuid4().hex[:10]}"
    resp = await agent.contract_call(src_addr=src, contract_addr=target, calldata=calldata,
                                     chain_id=config.CHAIN_ID, request_id=rid, description=label)
    # Generous timeout: CAW's TSS relay can drop + re-register over a ~3-min window, during which a
    # signature stalls at status 400 "signing" before completing. 420s outlasts that reconnect window.
    rec = await agent.wait_tx_final(rid, timeout=420.0)
    return (rec or {}).get("transaction_hash") or (resp or {}).get("transaction_hash") or ""


# ── client loop ─────────────────────────────────────────────────────────────

async def client_loop(run: Run, tasks: list[dict], reward_usdc: float) -> None:
    cc = config.client_agent()
    w3 = esc.web3()
    async with CawWallet(api_url=config.CAW_API_URL, api_key=cc.api_key,
                         wallet_uuid=cc.wallet_id, name="Client") as cw:
        await _revoke_active(cw)
        sub = await cw.submit_pact(intent="Client funds + evaluates open marketplace jobs",
                                   spec=pacts.client_escrow_pact(escrow=config.ESCROW_V2_ADDRESS,
                                                                 usdc=config.USDC_ADDRESS),
                                   name=f"auto-client-{run.run_id}")
        pact = await cw.wait_pact_active(sub.get("pact_id"))
        async with cw.scoped(pact) as client:
            amt_base = int(round(reward_usdc * 1_000_000))

            # 1) post every task the client decides to fund
            for t in tasks:
                spec = _spec_text(t)
                decision = await asyncio.to_thread(reasoning.client_decide_fund, spec, reward_usdc, BUDGET_USDC)
                if not decision.get("fund"):
                    log.info("[client] declined task %r: %s", t["task"][:40], decision.get("reason"))
                    continue
                job_id = esc.next_job_id(w3)
                spec_hash = Web3.keccak(text=f"{spec}#{job_id}")
                deadline = int(time.time()) + 7 * 24 * 3600
                rec = run.record(job_id)
                rec.update({"task": t["task"], "criteria": t.get("criteria", ""),
                            "amount_usdc": reward_usdc, "client": cc.address,
                            "fund_decision": decision, "spec_hash": Web3.to_hex(spec_hash)})
                rec["txs"]["createJob"] = await _call(client, cc.address, config.ESCROW_V2_ADDRESS,
                    esc.create_job(cc.address, amt_base, spec_hash, deadline), "createJob")
                rec["txs"]["approve"] = await _call(client, cc.address, config.USDC_ADDRESS,
                    esc.approve(config.ESCROW_V2_ADDRESS, amt_base), "approve")
                rec["txs"]["fund"] = await _call(client, cc.address, config.ESCROW_V2_ADDRESS,
                    esc.fund(job_id), "fund")
                rec["status"] = "funded"
                _post_listing(job_id, task=t["task"], criteria=t.get("criteria", ""),
                              reward_usdc=reward_usdc, spec_hash=Web3.to_hex(spec_hash),
                              client=cc.address, deadline=deadline)
                run.write_artifact(job_id)
                log.info("[client] posted + funded open job #%s (%s USDC)", job_id, reward_usdc)

            # 2) evaluate + settle submitted jobs until target reached
            rounds = 0
            while not run.stop.is_set():
                for job_id, rec in list(run.jobs.items()):
                    if rec.get("branch"):
                        continue
                    job = await asyncio.to_thread(esc.get_job, w3, job_id)
                    if job["status"] != "Submitted":
                        continue
                    fetched = (await asyncio.to_thread(irys_store.fetch, rec["irys"]["id"])).decode("utf-8", "replace")
                    verdict = await asyncio.to_thread(reasoning.evaluate, _spec_text(_listing(job_id) or rec), fetched)
                    rec["verdict"] = verdict
                    if verdict.get("accept"):
                        rec["txs"]["complete"] = await _call(client, cc.address, config.ESCROW_V2_ADDRESS,
                            esc.complete(job_id), "complete")
                        rec["branch"] = "payout"
                    else:
                        rec["txs"]["reject"] = await _call(client, cc.address, config.ESCROW_V2_ADDRESS,
                            esc.reject(job_id), "reject")
                        rec["branch"] = "refund"
                    final = await asyncio.to_thread(esc.get_job, w3, job_id)
                    rec["final_status"] = final["status"]
                    _content = await asyncio.to_thread(irys_store.fetch, rec["irys"]["id"])
                    rec["content_verified"] = (irys_store.keccak(_content) == final["deliverable_hash"])
                    rec["status"] = "settled"
                    run.settled += 1
                    run.write_artifact(job_id)
                    log.info("[client] settled job #%s -> %s (content_verified=%s)",
                             job_id, rec["branch"], rec["content_verified"])
                    if run.settled >= run.target:
                        run.stop.set()
                        return
                rounds += 1
                if rounds > 180:  # ~12 min safety (provider signing can stall on relay reconnects)
                    log.warning("[client] giving up after %d rounds", rounds)
                    run.stop.set()
                    return
                await asyncio.sleep(POLL)


# ── provider worker (one per provider identity; share the provider wallet's pact) ──

async def provider_worker(run: Run, name: str, addr: str, pact: dict, reward_usdc: float) -> None:
    pp = config.provider_agent()
    w3 = esc.web3()
    attempted: set[int] = set()
    async with CawWallet(api_url=config.CAW_API_URL, api_key=pp.api_key,
                         wallet_uuid=pp.wallet_id, name=name) as pw_root:
        async with pw_root.scoped(pact, name_suffix="") as pw:
            while not run.stop.is_set():
                # Discover via the off-chain board (only written AFTER a job is funded), so we never
                # read a job that isn't on-chain yet. Guard getJob in case it's momentarily not visible.
                for job_id_s in list(_read_board().keys()):
                    job_id = int(job_id_s)
                    if job_id in attempted:
                        continue
                    rec = run.jobs.get(job_id)
                    if rec is None or rec.get("winner"):
                        continue
                    try:
                        job = await asyncio.to_thread(esc.get_job, w3, job_id)
                    except Exception:
                        continue  # not yet visible on-chain (createJob still confirming)
                    if job["status"] != "Funded" or int(job["provider"], 16) != 0:
                        continue
                    listing = _listing(job_id)
                    if not listing:
                        continue
                    spec = _spec_text(listing)
                    decision = await asyncio.to_thread(reasoning.provider_decide_accept, spec, reward_usdc,
                                                       provider_name=name)
                    rec["accept_decisions"][name] = decision
                    if not decision.get("accept"):
                        attempted.add(job_id)
                        continue
                    attempted.add(job_id)
                    try:
                        tx = await _call(pw, addr, config.ESCROW_V2_ADDRESS, esc.accept_job(job_id), f"acceptJob[{name}]")
                    except Exception as e:
                        log.info("[%s] lost the race for job #%s (%s)", name, job_id, type(e).__name__)
                        rec.setdefault("race_losers", []).append({"name": name, "addr": addr, "error": type(e).__name__})
                        run.write_artifact(job_id)
                        continue
                    # double-check we actually hold it (race-safe)
                    job = await asyncio.to_thread(esc.get_job, w3, job_id)
                    if int(job["provider"], 16) != int(addr, 16):
                        log.info("[%s] acceptJob for #%s did not stick; winner=%s", name, job_id, job["provider"])
                        continue
                    rec["winner"], rec["winner_addr"] = name, addr
                    rec["txs"]["acceptJob"] = tx
                    rec["provider"] = addr
                    run.write_artifact(job_id)
                    log.info("[%s] WON job #%s -> acceptJob %s", name, job_id, tx)

                    # do the work, store on Irys, submit
                    deliverable = await asyncio.to_thread(reasoning.provider_do_task, spec,
                                                          sabotage=(run.mode == "bad"))
                    rec["deliverable"] = deliverable
                    dhash = Web3.keccak(text=deliverable)
                    irys = await asyncio.to_thread(irys_store.upload, deliverable,
                        {"app": "AgentWorks", "job-id": str(job_id), "content-keccak": Web3.to_hex(dhash)})
                    rec["irys"] = irys
                    rec["txs"]["submitWork"] = await _call(pw, addr, config.ESCROW_V2_ADDRESS,
                        esc.submit_work(job_id, dhash, irys["id"]), f"submitWork[{name}]")
                    rec["status"] = "submitted"
                    run.write_artifact(job_id)
                    log.info("[%s] submitted work for job #%s (Irys %s)", name, job_id, irys["id"])
                await asyncio.sleep(POLL)


# ── orchestrator ─────────────────────────────────────────────────────────────

async def run_market(tasks: list[dict], *, mode: str = "good", reward_usdc: float = 5.0,
                     max_jobs: int = 1) -> dict:
    run = Run(mode=mode, target=max_jobs)
    pp = config.provider_agent()

    # provider identities (addresses) from the registry — share ONE provider wallet + pact
    pool = registry.providers()
    provider_ids = [(p.name, p.address) for p in pool if p.wallet_id == pp.wallet_id] or [("Provider", pp.address)]
    log.info("[market] providers: %s", provider_ids)

    # onboard the provider wallet's pact ONCE; all worker addresses bind to it
    async with CawWallet(api_url=config.CAW_API_URL, api_key=pp.api_key,
                         wallet_uuid=pp.wallet_id, name="Provider") as pw_root:
        await _revoke_active(pw_root)
        psub = await pw_root.submit_pact(intent="Providers accept + deliver marketplace jobs",
                                         spec=pacts.provider_pact(escrow=config.ESCROW_V2_ADDRESS),
                                         name=f"auto-provider-{run.run_id}")
        ppact = await pw_root.wait_pact_active(psub.get("pact_id"))

    await asyncio.gather(
        client_loop(run, tasks, reward_usdc),
        *[provider_worker(run, name, addr, ppact, reward_usdc) for name, addr in provider_ids],
    )
    return {"run_id": run.run_id, "settled": run.settled,
            "jobs": {jid: r for jid, r in run.jobs.items()}}


def _default_tasks() -> list[dict]:
    return [{
        "task": "Write a clear 2-3 sentence explanation, for a non-expert, of how an on-chain escrow "
                "lets two agents who don't trust each other transact safely.",
        "criteria": "Plain language, 2-3 sentences, mentions the neutral escrow holding funds.",
    }]


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    ap = argparse.ArgumentParser(description="AgentWorks autonomous open-marketplace agents")
    ap.add_argument("--mode", choices=["good", "bad"], default="good")
    ap.add_argument("--reward", type=float, default=5.0, help="reward per job in USDC")
    ap.add_argument("--max-jobs", type=int, default=1, help="stop after this many jobs settle")
    ap.add_argument("--task", default=None, help="single task text (else a default task)")
    ap.add_argument("--criteria", default="", help="acceptance criteria for --task")
    args = ap.parse_args()

    tasks = ([{"task": args.task, "criteria": args.criteria}] if args.task else _default_tasks())
    out = asyncio.run(run_market(tasks, mode=args.mode, reward_usdc=args.reward, max_jobs=args.max_jobs))
    print("\n=== RUN SUMMARY ===")
    print(json.dumps(out, default=str, indent=2))


if __name__ == "__main__":
    main()
