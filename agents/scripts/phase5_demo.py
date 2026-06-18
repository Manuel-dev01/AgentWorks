"""Phase 5 - reasoned lifecycle with REAL Irys storage + on-chain content-hash verification.

Closes the loop:
  Provider LLM writes the deliverable -> stores it on Irys (devnet) -> submits
  submitWork(jobId, keccak256(content), irysId) on-chain via CAW contract_call.
  Evaluator FETCHES the deliverable back FROM Irys (by the on-chain irysId) -> judges accept/reject.
  Finally we VERIFY: keccak256(fetched-from-Irys) == on-chain deliverableHash.

Modes: good -> evaluator likely accepts -> payout ; bad -> sabotaged -> reject -> refund.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
import time
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import config
import escrow as esc
import irys_store
import pacts
import reasoning
from caw import CawWallet
from web3 import Web3

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

AMOUNT = 10_000_000  # 10 USDC
TASK = ("Write a clear 2-3 sentence explanation, for a non-expert, of how an on-chain escrow lets "
        "two agents who don't trust each other transact safely.")


def usd(x: int) -> str:
    return f"{x/1e6:.6f} USDC"


async def revoke_all(w: CawWallet) -> None:
    page = await w.list_pacts(status="active")
    items = page if isinstance(page, list) else (page.get("items", []) if isinstance(page, dict) else [])
    for p in items:
        if isinstance(p, dict) and p.get("status") == "active" and p.get("id"):
            try:
                await w.revoke_pact(p["id"])
            except Exception:
                pass


async def call(agent: CawWallet, src: str, target: str, calldata: str, label: str) -> str:
    rid = f"p5-{uuid4().hex[:10]}"
    resp = await agent.contract_call(src_addr=src, contract_addr=target, calldata=calldata,
                                     chain_id=config.CHAIN_ID, request_id=rid, description=label)
    rec = await agent.wait_tx_final(rid)
    txh = (rec or {}).get("transaction_hash") or (resp or {}).get("transaction_hash")
    print(f"   [ok] {label}: {txh}")
    return txh


async def main(mode: str) -> None:
    assert mode in ("good", "bad")
    w3 = esc.web3()
    cc, pp = config.client_agent(), config.provider_agent()
    proof: dict = {"mode": mode, "task": TASK, "reasoning": {}, "txs": {}}
    print(f"\n=== Phase 5 reasoned lifecycle + Irys: mode={mode} ===")

    fund_decision = reasoning.client_decide_fund(TASK, 10.0, 1000.0)
    proof["reasoning"]["client_fund"] = fund_decision
    print(f"[reason] Client.fund? {fund_decision}")
    if not fund_decision.get("fund"):
        proof["stopped"] = "client_declined"; print("Client declined - stop."); return

    bal0 = {"client": esc.usdc_balance(w3, cc.address), "provider": esc.usdc_balance(w3, pp.address)}
    proof["balances_pre"] = bal0

    async with CawWallet(api_url=config.CAW_API_URL, api_key=cc.api_key, wallet_uuid=cc.wallet_id, name="Client") as cw, \
               CawWallet(api_url=config.CAW_API_URL, api_key=pp.api_key, wallet_uuid=pp.wallet_id, name="Provider") as pw:
        await revoke_all(cw); await revoke_all(pw)
        client = cw.scoped(await cw.wait_pact_active((await cw.submit_pact(
            intent="Client funds + evaluates escrow jobs", spec=pacts.client_escrow_pact(), name="p5-client")).get("pact_id")))
        provider = pw.scoped(await pw.wait_pact_active((await pw.submit_pact(
            intent="Provider submits deliverables", spec=pacts.provider_pact(), name="p5-provider")).get("pact_id")))

        job_id = esc.next_job_id(w3)
        proof["job_id"] = job_id
        spec_hash = Web3.keccak(text=f"{TASK}#{job_id}")
        deadline = int(time.time()) + 7 * 24 * 3600

        print(f"[1] createJob({job_id}) + approve + fund ({usd(AMOUNT)})")
        proof["txs"]["createJob"] = await call(client, cc.address, config.ESCROW_ADDRESS,
            esc.create_job(pp.address, cc.address, AMOUNT, spec_hash, deadline), "createJob")
        proof["txs"]["approve"] = await call(client, cc.address, config.USDC_ADDRESS, esc.approve(config.ESCROW_ADDRESS, AMOUNT), "approve")
        proof["txs"]["fund"] = await call(client, cc.address, config.ESCROW_ADDRESS, esc.fund(job_id), "fund")
        assert esc.get_job(w3, job_id)["status"] == "Funded"

        # Provider performs the task, STORES it on Irys, submits hash+irysId on-chain
        deliverable = reasoning.provider_do_task(TASK, sabotage=(mode == "bad"))
        proof["deliverable"] = deliverable
        deliverable_hash = Web3.keccak(text=deliverable)
        print("[2] storing deliverable on Irys devnet...")
        irys = irys_store.upload(deliverable, tags={"app": "AgentWorks", "job-id": str(job_id),
                                                    "content-keccak": Web3.to_hex(deliverable_hash)})
        proof["irys"] = irys
        print(f"   [irys] {irys['url']}")
        proof["txs"]["submitWork"] = await call(provider, pp.address, config.ESCROW_ADDRESS,
            esc.submit_work(job_id, deliverable_hash, irys["id"]), "submitWork")
        j = esc.get_job(w3, job_id)
        assert j["status"] == "Submitted" and j["irys_id"] == irys["id"]

        # Evaluator FETCHES the deliverable FROM Irys (by the on-chain irysId), then judges
        print("[3] Evaluator fetches deliverable FROM Irys by on-chain irysId, then judges...")
        fetched = irys_store.fetch(j["irys_id"]).decode("utf-8", "replace")
        proof["fetched_matches_local"] = (fetched == deliverable)
        verdict = reasoning.evaluate(TASK, fetched)
        proof["reasoning"]["evaluate"] = verdict
        print(f"[reason] Evaluator verdict (on Irys-fetched content): {verdict}")
        if verdict.get("accept"):
            proof["txs"]["complete"] = await call(client, cc.address, config.ESCROW_ADDRESS, esc.complete(job_id), "complete")
            proof["branch"] = "payout"
        else:
            proof["txs"]["reject"] = await call(client, cc.address, config.ESCROW_ADDRESS, esc.reject(job_id), "reject")
            proof["branch"] = "refund"
        await client.close(); await provider.close()

    # VERIFY: on-chain hash == keccak of the bytes actually stored on Irys
    final = esc.get_job(w3, job_id)
    fetched_bytes = irys_store.fetch(final["irys_id"])
    proof["content_verified"] = (irys_store.keccak(fetched_bytes) == final["deliverable_hash"])
    proof["final_status"] = final["status"]
    proof["balances_post"] = {"client": esc.usdc_balance(w3, cc.address), "provider": esc.usdc_balance(w3, pp.address)}
    print(f"[4] VERIFY keccak256(Irys-fetched) == on-chain deliverableHash -> {proof['content_verified']}")
    print(f"[final] job {job_id} status={final['status']} branch={proof['branch']} irys={final['irys_id']}")
    print(f"        gateway: https://devnet.irys.xyz/{final['irys_id']}")
    out = Path(__file__).resolve().parent / f"phase5_demo_{mode}_proof.json"
    out.write_text(json.dumps(proof, default=str, indent=2), encoding="utf-8")
    print(f"proof -> {out}")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "good"))
