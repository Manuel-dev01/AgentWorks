"""One-off: top up the deployer gas hub from the Client CAW wallet (native SETH) so we can redeploy
v4 + run the live dispute. Uses a scoped budget pact (cap 0.05) and transfers 0.02 SETH."""
from __future__ import annotations

import asyncio, sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config
import pacts
from caw import CawWallet

DEPLOYER = "0xBCA6f82e240C6AC36B23b4f7D21adF17e03966Fe"
AMOUNT = "0.02"


async def main() -> None:
    cc = config.client_agent()
    async with CawWallet(api_url=config.CAW_API_URL, api_key=cc.api_key,
                         wallet_uuid=cc.wallet_id, name="Client") as cw:
        # clean slate + a budget pact that permits this native transfer
        try:
            page = await cw.list_pacts(status="active")
            items = page if isinstance(page, list) else (page.get("items", []) if isinstance(page, dict) else [])
            for p in items:
                if isinstance(p, dict) and p.get("id"):
                    await cw.revoke_pact(p["id"])
        except Exception as e:
            print("revoke skip:", e)
        sub = await cw.submit_pact(intent="Top up deployer gas hub",
                                   spec=pacts.client_budget_transfer_pact(cap="0.05"),
                                   name=f"topup-{uuid4().hex[:6]}")
        pact = await cw.wait_pact_active(sub.get("pact_id"))
        async with cw.scoped(pact) as s:
            rid = f"topup-{uuid4().hex[:8]}"
            await s.transfer(src_addr=cc.address, dst_addr=DEPLOYER, amount=AMOUNT,
                             token_id=config.NATIVE_TOKEN_ID, chain_id=config.CHAIN_ID,
                             request_id=rid, description="gas top-up for v4 redeploy")
            rec = await s.wait_tx_final(rid, timeout=420.0)
            print("topup tx:", (rec or {}).get("transaction_hash"))


if __name__ == "__main__":
    asyncio.run(main())
