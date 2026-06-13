"""Phase 4 FREEZE demo - emergency stop via pact revocation (no native freeze API).

  1. Active Client pact -> one ALLOWED contract_call settles on-chain (tx hash).
  2. revoke_pact(pact_id)  ← the freeze.
  3. The next identical contract_call is DENIED - the agent's authority is gone.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import logging

import config
import escrow as esc
import pacts
from caw import CawWallet
from cobo_agentic_wallet.errors import APIError, PolicyDeniedError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def _denial(e: Exception) -> dict:
    if isinstance(e, PolicyDeniedError):
        d = getattr(e, "denial", None)
        return {"type": "PolicyDeniedError", "status_code": getattr(e, "status_code", None),
                "code": getattr(d, "code", None), "reason": getattr(d, "reason", None)}
    return {"type": type(e).__name__, "status_code": getattr(e, "status_code", None), "msg": str(e)[:200]}


async def revoke_all(w: CawWallet) -> None:
    page = await w.list_pacts(status="active")
    items = page if isinstance(page, list) else (page.get("items", []) if isinstance(page, dict) else [])
    for p in items:
        if isinstance(p, dict) and p.get("status") == "active" and p.get("id"):
            try:
                await w.revoke_pact(p["id"])
            except Exception:
                pass


async def main() -> None:
    cc = config.client_agent()
    proof: dict = {}
    print("\n=== Phase 4 FREEZE demo (emergency stop = revoke_pact) ===")
    async with CawWallet(api_url=config.CAW_API_URL, api_key=cc.api_key, wallet_uuid=cc.wallet_id, name="Client") as w:
        await revoke_all(w)
        active = await w.wait_pact_active((await w.submit_pact(
            intent="Client may call escrow + USDC", spec=pacts.client_escrow_pact(), name="phase4-freeze")).get("pact_id"))
        pid = active.get("id")
        proof["pact_id"] = pid
        s = w.scoped(active)

        # 1. allowed action settles on-chain
        print("[1] allowed contract_call (approve escrow 0) under active pact")
        rid = f"freeze-ok-{uuid4().hex[:8]}"
        await s.contract_call(src_addr=cc.address, contract_addr=config.USDC_ADDRESS,
                              calldata=esc.approve(config.ESCROW_ADDRESS, 0), chain_id=config.CHAIN_ID,
                              request_id=rid, description="allowed before freeze")
        rec = await s.wait_tx_final(rid)
        proof["allowed_tx"] = rec.get("transaction_hash")
        print(f"   ALLOWED tx={proof['allowed_tx']}")

        # 2. FREEZE
        print(f"[2] FREEZE: revoke_pact({pid})")
        await w.revoke_pact(pid)
        proof["revoked"] = pid

        # 3. next action denied
        print("[3] same contract_call again -> expect DENIED (authority revoked)")
        try:
            await s.contract_call(src_addr=cc.address, contract_addr=config.USDC_ADDRESS,
                                  calldata=esc.approve(config.ESCROW_ADDRESS, 0), chain_id=config.CHAIN_ID,
                                  request_id=f"freeze-deny-{uuid4().hex[:8]}", description="after freeze")
            proof["after_freeze"] = {"result": "ALLOWED (unexpected!)"}
            print("   UNEXPECTED: allowed after revoke")
        except (PolicyDeniedError, APIError) as e:
            proof["after_freeze"] = {"result": "denied", **_denial(e)}
            print(f"   DENIED: {proof['after_freeze']}")
        await s.close()

        audit = await w.list_audit_logs(limit=20)
        items = audit if isinstance(audit, list) else audit.get("items", [])
        proof["recent_denied"] = [{"action": e.get("action"), "result": e.get("result")}
                                  for e in items if isinstance(e, dict) and str(e.get("result", "")).lower() == "denied"][:3]

    proof["FREEZE_PASS"] = bool(proof.get("allowed_tx")) and proof.get("after_freeze", {}).get("result") == "denied"
    out = Path(__file__).resolve().parent / "phase4_freeze_proof.json"
    out.write_text(json.dumps(proof, default=str, indent=2), encoding="utf-8")
    print(f"\nFREEZE_PASS={proof['FREEZE_PASS']}  (allowed tx then denied after revoke)\nproof -> {out}")


if __name__ == "__main__":
    asyncio.run(main())
