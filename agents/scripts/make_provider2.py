"""Provision a SECOND provider identity for the live accept-race (Phase 6.5.2 gap fix).

A second EVM address on the EXISTING Provider CAW wallet is a distinct on-chain msg.sender, signed
by the same Provider TSS node and governed by the same provider Pact (which allowlists the v2
escrow). That gives a genuine, live, Pact-scoped second provider WITHOUT onboarding a whole new
wallet/daemon. Prints the new address; fund it with Sepolia gas, then add CAW_PROVIDER2_* to .env.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # agents/ on path

import config
from caw import CawWallet


def _addrs(resp) -> list[str]:
    items = resp if isinstance(resp, list) else (resp.get("items") or resp.get("addresses") or [])
    out = []
    for a in items:
        if isinstance(a, dict):
            out.append(a.get("address") or a.get("addr") or "")
        elif isinstance(a, str):
            out.append(a)
    return [x for x in out if x]


async def main() -> None:
    pp = config.provider_agent()
    async with CawWallet(api_url=config.CAW_API_URL, api_key=pp.api_key,
                         wallet_uuid=pp.wallet_id, name="Provider") as w:
        before = _addrs(await w.list_addresses())
        print("existing provider addresses:", json.dumps(before, indent=2))
        created = await w.create_address(config.CHAIN_ID)
        new_addr = created.get("address") if isinstance(created, dict) else None
        after = _addrs(await w.list_addresses())
        # pick the address that is new vs before, else the created one
        fresh = [a for a in after if a not in before]
        print(json.dumps({
            "wallet_id": pp.wallet_id,
            "canonical_provider": pp.address,
            "created_raw_address": new_addr,
            "new_addresses": fresh,
            "all_addresses": after,
        }, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
