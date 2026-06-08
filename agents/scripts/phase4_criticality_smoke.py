"""Phase 4 criticality smoke — verify CAW actually ENFORCES pacts (deny + freeze) before
building the demo beats. No LLM needed.

  A. clean slate: revoke all active pacts
  B. with NO active pact, a contract_call is DENIED
  C. submit the restrictive Client pact -> a whitelisted contract_call is ALLOWED
  D. a contract_call to a NON-whitelisted contract is DENIED
  E. revoke the pact -> the next contract_call is DENIED (emergency freeze)
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

NON_WHITELISTED = "0x000000000000000000000000000000000000dEaD"
HARMLESS = esc.approve(config.ESCROW_ADDRESS, 0)  # approve(escrow, 0): harmless if it executes


async def revoke_all_active(w: CawWallet) -> list[str]:
    page = await w.list_pacts(status="active")
    items = page if isinstance(page, list) else (page.get("items", []) if isinstance(page, dict) else [])
    ids = [p.get("id") for p in items if isinstance(p, dict) and p.get("status") == "active" and p.get("id")]
    for pid in ids:
        try:
            await w.revoke_pact(pid)
        except Exception as e:
            print(f"   (revoke {pid} note: {e})")
    return ids


async def attempt(w: CawWallet, target: str, label: str) -> dict:
    """Attempt a contract_call. Return {result: allowed|denied|error, ...}."""
    rid = f"smoke4-{uuid4().hex[:8]}"
    try:
        resp = await w.contract_call(src_addr=config.client_agent().address, contract_addr=target,
                                     calldata=HARMLESS, chain_id=config.CHAIN_ID, request_id=rid,
                                     description=label)
        print(f"   [{label}] ALLOWED (passed policy) resp.status={resp.get('status')}/{resp.get('status_display')}")
        return {"result": "allowed", "response": resp}
    except PolicyDeniedError as e:
        d = getattr(e, "denial", None)
        info = {"code": getattr(d, "code", None), "reason": getattr(d, "reason", None),
                "status_code": getattr(e, "status_code", None)}
        print(f"   [{label}] DENIED (PolicyDeniedError) {info}")
        return {"result": "denied", "denial": info}
    except APIError as e:
        print(f"   [{label}] DENIED/ERROR (APIError {getattr(e,'status_code',None)}): {str(e)[:160]}")
        return {"result": "denied", "api_error": str(e)[:300], "status_code": getattr(e, "status_code", None)}


async def main() -> None:
    cc = config.client_agent()
    proof: dict = {}
    print("\n=== Phase 4 criticality smoke ===")
    async with CawWallet(api_url=config.CAW_API_URL, api_key=cc.api_key, wallet_uuid=cc.wallet_id, name="Client") as w:
        print("[A] revoke all active pacts (clean slate)")
        proof["revoked"] = await revoke_all_active(w)

        print("[B] no active pact -> expect DENIED")
        proof["B_no_pact"] = await attempt(w, config.USDC_ADDRESS, "no-pact")

        print("[C] submit restrictive Client pact, then whitelisted call -> expect ALLOWED")
        active = await w.wait_pact_active((await w.submit_pact(
            intent="Client may only call escrow + USDC", spec=pacts.client_escrow_pact(), name="phase4-smoke")).get("pact_id"))
        proof["pact_id"] = active.get("id")
        scoped = w.scoped(active)
        proof["C_whitelisted"] = await attempt(scoped, config.USDC_ADDRESS, "whitelisted-USDC")

        print("[D] non-whitelisted target -> expect DENIED")
        proof["D_non_whitelisted"] = await attempt(scoped, NON_WHITELISTED, "non-whitelisted")

        print("[E] revoke pact -> next call DENIED (freeze)")
        await w.revoke_pact(active.get("id"))
        proof["E_post_revoke"] = await attempt(scoped, config.USDC_ADDRESS, "post-revoke-freeze")
        await scoped.close()

    pass_b = proof["B_no_pact"]["result"] == "denied"
    pass_c = proof["C_whitelisted"]["result"] == "allowed"
    pass_d = proof["D_non_whitelisted"]["result"] == "denied"
    pass_e = proof["E_post_revoke"]["result"] == "denied"
    proof["SMOKE_PASS"] = pass_b and pass_c and pass_d and pass_e
    out = Path(__file__).resolve().parent / "phase4_smoke_proof.json"
    out.write_text(json.dumps(proof, default=str, indent=2), encoding="utf-8")
    print(f"\nRESULT: B(no-pact deny)={pass_b} C(whitelist allow)={pass_c} D(non-whitelist deny)={pass_d} E(freeze deny)={pass_e}")
    print(f"SMOKE_PASS={proof['SMOKE_PASS']}  (proof -> {out})")


if __name__ == "__main__":
    asyncio.run(main())
