"""Minimal proof that the CONTAINERIZED TSS signer can sign a real tx (Phase 6.5.4 Option B gate).

ProviderB accepts an open funded job via a single CAW contract_call. The only TSS nodes on the relay
right now are the ones inside the agentworks-tss container, so a confirmed tx hash here = the container
signed it. Usage: python scripts/container_sign_probe.py <jobId> [providerB_address]
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config
import escrow_v2 as esc
import pacts
from caw import CawWallet


async def main() -> None:
    job_id = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    addr = sys.argv[2] if len(sys.argv) > 2 else "0x7ea0701d657e3427c2bb3bc195e943a81c5fc69e"
    pp = config.provider_agent()
    async with CawWallet(api_url=config.CAW_API_URL, api_key=pp.api_key,
                         wallet_uuid=pp.wallet_id, name="ProviderB") as w:
        sub = await w.submit_pact(intent="Provider accepts a job (container-signer probe)",
                                  spec=pacts.provider_pact(escrow=config.ESCROW_V2_ADDRESS),
                                  name=f"probe-{uuid4().hex[:6]}")
        pact = await w.wait_pact_active(sub.get("pact_id"))
        pw = w.scoped(pact)
        rid = f"probe-{uuid4().hex[:10]}"
        await pw.contract_call(src_addr=addr, contract_addr=config.ESCROW_V2_ADDRESS,
                               calldata=esc.accept_job(job_id), chain_id=config.CHAIN_ID,
                               request_id=rid, description=f"acceptJob({job_id})")
        rec = await pw.wait_tx_final(rid, timeout=420.0)
        tx = (rec or {}).get("transaction_hash")
        await pw.close()
        print(f"\nCONTAINER-SIGNED tx: {tx}")
        print(f"status_display: {rec.get('status_display')} sub_status: {rec.get('sub_status')}")


if __name__ == "__main__":
    asyncio.run(main())
