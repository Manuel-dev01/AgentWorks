"""Phase 4 DENIAL demo - CAW blocks out-of-policy actions server-side (criteria 2 & 5).

Two denial flavors, each captured with its structured PolicyDeniedError + the audit-log entry:
  (a) BUDGET CAP   - Client transfer pact caps native gas at 0.001; a 0.01 transfer is DENIED.
  (b) ALLOWLIST    - Client escrow pact allows only [escrow, USDC]; a call to another contract is DENIED.

Narrative: even if the agent is told to overspend / call an arbitrary contract, the Pact stops it.
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


def _denial(e: Exception) -> dict:
    if isinstance(e, PolicyDeniedError):
        d = getattr(e, "denial", None)
        return {"type": "PolicyDeniedError", "status_code": getattr(e, "status_code", None),
                "code": getattr(d, "code", None), "reason": getattr(d, "reason", None),
                "details": getattr(d, "details", None)}
    return {"type": type(e).__name__, "status_code": getattr(e, "status_code", None), "msg": str(e)[:200]}


async def revoke_all(w: CawWallet) -> list[str]:
    page = await w.list_pacts(status="active")
    items = page if isinstance(page, list) else (page.get("items", []) if isinstance(page, dict) else [])
    ids = [p["id"] for p in items if isinstance(p, dict) and p.get("status") == "active" and p.get("id")]
    for pid in ids:
        try:
            await w.revoke_pact(pid)
        except Exception:
            pass
    return ids


async def main() -> None:
    cc = config.client_agent()
    pp = config.provider_agent()
    proof: dict = {}
    print("\n=== Phase 4 DENIAL demo ===")
    async with CawWallet(api_url=config.CAW_API_URL, api_key=cc.api_key, wallet_uuid=cc.wallet_id, name="Client") as w:
        await revoke_all(w)

        # (a) BUDGET CAP - transfer pact caps native gas at 0.001; attempt 0.01.
        print("[a] budget cap: pact allows <=0.001 native; agent attempts 0.01 -> expect DENIED")
        budget = await w.wait_pact_active((await w.submit_pact(
            intent="Client gas budget: <=0.001 SETH per transfer",
            spec=pacts.client_budget_transfer_pact("0.001"), name="phase4-budget")).get("pact_id"))
        sb = w.scoped(budget)
        try:
            await sb.transfer(src_addr=cc.address, dst_addr=pp.address, amount="0.01",
                              token_id=config.NATIVE_TOKEN_ID, chain_id=config.CHAIN_ID,
                              request_id=f"deny-budget-{uuid4().hex[:8]}",
                              description="over-budget transfer (should be denied)")
            proof["budget_cap"] = {"result": "ALLOWED (unexpected!)"}
            print("   UNEXPECTED: over-budget transfer was allowed")
        except (PolicyDeniedError, APIError) as e:
            proof["budget_cap"] = {"result": "denied", **_denial(e)}
            print(f"   DENIED: {proof['budget_cap']}")
        await sb.close()
        await w.revoke_pact(budget.get("id"))

        # (b) ALLOWLIST - escrow pact allows only [escrow, USDC]; call a non-whitelisted contract.
        print("[b] allowlist: pact allows only [escrow,USDC]; agent calls 0x..dEaD -> expect DENIED")
        esc_pact = await w.wait_pact_active((await w.submit_pact(
            intent="Client may only call escrow + USDC", spec=pacts.client_escrow_pact(), name="phase4-allowlist")).get("pact_id"))
        sa = w.scoped(esc_pact)
        try:
            await sa.contract_call(src_addr=cc.address, contract_addr=NON_WHITELISTED,
                                   calldata=esc.approve(config.ESCROW_ADDRESS, 0), chain_id=config.CHAIN_ID,
                                   request_id=f"deny-allow-{uuid4().hex[:8]}",
                                   description="call to non-whitelisted contract (should be denied)")
            proof["allowlist"] = {"result": "ALLOWED (unexpected!)"}
            print("   UNEXPECTED: non-whitelisted call was allowed")
        except (PolicyDeniedError, APIError) as e:
            proof["allowlist"] = {"result": "denied", **_denial(e)}
            print(f"   DENIED: {proof['allowlist']}")
        await sa.close()

        # audit trail of the denials
        audit = await w.list_audit_logs(limit=100)
        items = audit if isinstance(audit, list) else audit.get("items", [])
        denied = [{"action": e.get("action"), "result": e.get("result"), "created_at": e.get("created_at")}
                  for e in items if isinstance(e, dict) and str(e.get("result", "")).lower() in ("denied", "blocked")]
        proof["audit_denied_entries"] = denied[:8]
        print(f"[audit] denied entries (recent): {len(denied)}")
        for d in denied[:5]:
            print("   -", d)

    proof["DENIAL_PASS"] = proof.get("budget_cap", {}).get("result") == "denied" and proof.get("allowlist", {}).get("result") == "denied"
    out = Path(__file__).resolve().parent / "phase4_denial_proof.json"
    out.write_text(json.dumps(proof, default=str, indent=2), encoding="utf-8")
    print(f"\nDENIAL_PASS={proof['DENIAL_PASS']}  (proof -> {out})")


if __name__ == "__main__":
    asyncio.run(main())
