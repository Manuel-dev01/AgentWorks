"""Phase 4 (optional, LAST) - review_if human-in-the-loop beat.

A pact with `review_if` (soft block): native transfers above 0.0005 require owner approval.
We attempt a 0.001 transfer and expect status=PendingApproval + a pending_operation_id, then
approve it via approve_pending_operation (unpaired => in-conversation owner = us).

Per the build contract: this is source-verified but live-unconfirmed. If live behavior contradicts
(no PendingApproval / no pending_operation_id), the script reports REVIEW_CONFIRMED=False and we SKIP
the beat honestly rather than fake it.
"""

from __future__ import annotations

import asyncio
import json
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

import logging

import config
import pacts
from caw import CawWallet

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


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
    cc, pp = config.client_agent(), config.provider_agent()
    proof: dict = {}
    print("\n=== Phase 4 review_if beat (human-in-the-loop) ===")
    async with CawWallet(api_url=config.CAW_API_URL, api_key=cc.api_key, wallet_uuid=cc.wallet_id, name="Client") as w:
        await revoke_all(w)
        active = await w.wait_pact_active((await w.submit_pact(
            intent="Native transfers above 0.0005 require owner review",
            spec=pacts.review_pact("0.0005"), name="p4-review")).get("pact_id"))
        s = w.scoped(active)

        rid = f"review-{uuid4().hex[:8]}"
        print("[1] transfer 0.001 (> 0.0005 review threshold) -> expect PendingApproval")
        resp = await s.transfer(src_addr=cc.address, dst_addr=pp.address, amount="0.001",
                                token_id=config.NATIVE_TOKEN_ID, chain_id=config.CHAIN_ID,
                                request_id=rid, description="review_if beat")
        proof["transfer_response"] = resp
        op_id = (resp or {}).get("pending_operation_id")
        disp = (resp or {}).get("status_display")
        print(f"   status_display={disp} pending_operation_id={op_id}")

        if not op_id:
            proof["REVIEW_CONFIRMED"] = False
            proof["note"] = f"No pending_operation_id (status_display={disp}); unpaired may not gate review_if. Beat SKIPPED."
            print(f"   REVIEW NOT TRIGGERED -> {proof['note']}")
            await s.close()
        else:
            pend = await w.get_pending_operation(op_id)
            proof["pending_before"] = pend
            print(f"[2] pending op status={pend.get('status') if isinstance(pend,dict) else pend} -> approving")
            proof["approve_result"] = await w.approve_pending_operation(op_id)
            try:
                rec = await s.wait_tx_final(rid, timeout=180)
                proof["tx_hash"] = rec.get("transaction_hash")
                proof["REVIEW_CONFIRMED"] = True
                print(f"   APPROVED -> settled tx={proof['tx_hash']}")
            except Exception as e:
                proof["REVIEW_CONFIRMED"] = True
                proof["post_approve_note"] = f"approved; tx wait: {e}"
                print(f"   APPROVED (tx wait note: {e})")
            await s.close()

    out = Path(__file__).resolve().parent / "phase4_review_proof.json"
    out.write_text(json.dumps(proof, default=str, indent=2), encoding="utf-8")
    print(f"\nREVIEW_CONFIRMED={proof.get('REVIEW_CONFIRMED')}  (proof -> {out})")


if __name__ == "__main__":
    asyncio.run(main())
