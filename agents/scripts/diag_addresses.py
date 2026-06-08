"""Diagnostic: list the Client wallet's addresses + force-refreshed TBASE_SETH balances."""

from __future__ import annotations
import asyncio, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config
from cobo_agentic_wallet.client import WalletAPIClient


async def main() -> None:
    c = config.client_agent()
    async with WalletAPIClient(base_url=config.CAW_API_URL, api_key=c.api_key) as cl:
        addrs = await cl.list_wallet_addresses(c.wallet_id)
        print("=== addresses ===")
        print(json.dumps(addrs, default=str, indent=2))
        for cid in (config.CHAIN_ID, "SETH"):
            bals = await cl.list_balances(c.wallet_id, chain_id=cid, force_refresh=True)
            print(f"=== balances chain={cid} (force_refresh) ===")
            print(json.dumps(bals, default=str, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
