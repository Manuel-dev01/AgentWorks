"""Phase 3 — two agents drive the escrow lifecycle headless via CAW contract_call.

  Client  (CAW wallet, v1 also evaluator): createJob -> approve -> fund -> complete|reject
  Provider(CAW wallet):                    submitWork

Both branches:
  python agents/scripts/phase3_lifecycle.py complete   # payout to provider
  python agents/scripts/phase3_lifecycle.py reject     # refund to client

Every state-changing step is an on-chain CAW contract_call; we verify each transition by
reading escrow.getJob + USDC balances over RPC, and capture every tx hash.
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

import config
import escrow as esc
from caw import CawWallet
from web3 import Web3

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("phase3")

AMOUNT = 10_000_000  # 10 USDC (6 decimals)
USDC = config.USDC_ADDRESS
ESCROW = config.ESCROW_ADDRESS
CHAIN = config.CHAIN_ID


def cc_pact(targets: list[str], name: str) -> dict:
    return {
        "policies": [{
            "name": name, "type": "contract_call",
            "rules": {"effect": "allow", "when": {
                "chain_in": [CHAIN],
                "target_in": [{"chain_id": CHAIN, "contract_addr": t} for t in targets],
            }},
        }],
        "completion_conditions": [{"type": "time_elapsed", "threshold": "86400"}],
    }


def usdc(x: int) -> str:
    return f"{x / 1e6:.6f} USDC"


async def call(agent: CawWallet, target: str, calldata: str, label: str) -> str:
    """One CAW contract_call → wait final → return tx hash."""
    rid = f"p3-{uuid4().hex[:10]}"
    resp = await agent.contract_call(src_addr=agent.src, contract_addr=target, calldata=calldata,
                                     chain_id=CHAIN, request_id=rid, description=label)
    rec = await agent.wait_tx_final(rid)
    txh = (rec or {}).get("transaction_hash") or (resp or {}).get("transaction_hash")
    print(f"   [ok] {label}: {txh}")
    return txh


async def main(outcome: str) -> None:
    assert outcome in ("complete", "reject"), "outcome must be 'complete' or 'reject'"
    w3 = esc.web3()
    cc = config.client_agent()
    pp = config.provider_agent()
    proof: dict = {"outcome": outcome, "amount": AMOUNT, "txs": {}}

    spec_hash = Web3.keccak(text=f"AgentWorks task spec / {outcome} / {uuid4().hex[:6]}")
    deliverable_hash = Web3.keccak(text="irys://placeholder-deliverable-id (Phase 5 real)")
    deadline = int(time.time()) + 7 * 24 * 3600

    print(f"\n=== Phase 3 lifecycle: {outcome.upper()} branch (Eth Sepolia) ===")
    print(f"Client/Evaluator {cc.address}\nProvider         {pp.address}\nEscrow {ESCROW}  USDC {USDC}")

    bal0 = {"client": esc.usdc_balance(w3, cc.address), "provider": esc.usdc_balance(w3, pp.address),
            "escrow": esc.usdc_balance(w3, ESCROW)}
    print(f"[balances pre]  client={usdc(bal0['client'])} provider={usdc(bal0['provider'])} escrow={usdc(bal0['escrow'])}")
    proof["balances_pre"] = bal0

    async with CawWallet(api_url=config.CAW_API_URL, api_key=cc.api_key, wallet_uuid=cc.wallet_id, name="Client") as client_w, \
               CawWallet(api_url=config.CAW_API_URL, api_key=pp.api_key, wallet_uuid=pp.wallet_id, name="Provider") as provider_w:

        # Pacts: Client may contract_call USDC + escrow; Provider may contract_call escrow.
        client_pact = await client_w.wait_pact_active(
            (await client_w.submit_pact(intent="Client: run+fund+evaluate escrow jobs",
                                        spec=cc_pact([USDC, ESCROW], "client-escrow"), name="phase3-client")).get("pact_id"))
        provider_pact = await provider_w.wait_pact_active(
            (await provider_w.submit_pact(intent="Provider: submit deliverables to escrow",
                                          spec=cc_pact([ESCROW], "provider-escrow"), name="phase3-provider")).get("pact_id"))
        client = client_w.scoped(client_pact); client.src = cc.address
        provider = provider_w.scoped(provider_pact); provider.src = pp.address
        proof["client_pact"], proof["provider_pact"] = client_pact.get("id"), provider_pact.get("id")

        try:
            # jobId is the pre-increment nextJobId
            job_id = esc.next_job_id(w3)
            proof["job_id"] = job_id
            print(f"\n[1] Client.createJob(jobId={job_id}, provider, evaluator=client, {usdc(AMOUNT)})")
            proof["txs"]["createJob"] = await call(client, ESCROW,
                esc.create_job(pp.address, cc.address, AMOUNT, spec_hash, deadline), "createJob")
            assert esc.get_job(w3, job_id)["status"] == "Created"

            print(f"[2] Client.approve(escrow, {usdc(AMOUNT)})")
            proof["txs"]["approve"] = await call(client, USDC, esc.approve(ESCROW, AMOUNT), "approve")

            print(f"[3] Client.fund(jobId={job_id}) — escrow pulls USDC")
            proof["txs"]["fund"] = await call(client, ESCROW, esc.fund(job_id), "fund")
            assert esc.get_job(w3, job_id)["status"] == "Funded"
            print(f"    escrow now holds {usdc(esc.usdc_balance(w3, ESCROW))}")

            print(f"[4] Provider.submitWork(jobId={job_id}, deliverableHash)")
            proof["txs"]["submitWork"] = await call(provider, ESCROW,
                esc.submit_work(job_id, deliverable_hash), "submitWork")
            j = esc.get_job(w3, job_id)
            assert j["status"] == "Submitted" and j["deliverable_hash"] == Web3.to_hex(deliverable_hash)

            if outcome == "complete":
                print(f"[5] Evaluator(Client).complete(jobId={job_id}) -> pay Provider")
                proof["txs"]["complete"] = await call(client, ESCROW, esc.complete(job_id), "complete")
                assert esc.get_job(w3, job_id)["status"] == "Completed"
            else:
                print(f"[5] Evaluator(Client).reject(jobId={job_id}) -> refund Client")
                proof["txs"]["reject"] = await call(client, ESCROW, esc.reject(job_id), "reject")
                assert esc.get_job(w3, job_id)["status"] == "Rejected"
        finally:
            await client.close(); await provider.close()

    bal1 = {"client": esc.usdc_balance(w3, cc.address), "provider": esc.usdc_balance(w3, pp.address),
            "escrow": esc.usdc_balance(w3, ESCROW)}
    proof["balances_post"] = bal1
    proof["final_status"] = esc.get_job(w3, job_id)["status"]
    print(f"\n[balances post] client={usdc(bal1['client'])} provider={usdc(bal1['provider'])} escrow={usdc(bal1['escrow'])}")
    print(f"[final] job {job_id} status = {proof['final_status']}")
    if outcome == "complete":
        print(f"[delta] provider +{usdc(bal1['provider']-bal0['provider'])}  (payout)")
    else:
        print(f"[delta] client net {usdc(bal1['client']-bal0['client'])}  (funded then refunded ~ 0)")

    out = Path(__file__).resolve().parent / f"phase3_{outcome}_proof.json"
    out.write_text(json.dumps(proof, default=str, indent=2), encoding="utf-8")
    print(f"proof -> {out}")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "complete"))
