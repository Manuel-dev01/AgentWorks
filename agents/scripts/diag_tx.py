"""Diagnostic: dump a transaction record by request_id, and list pending operations."""

from __future__ import annotations
import asyncio, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config
from cobo_agentic_wallet.client import WalletAPIClient

REQ = sys.argv[1] if len(sys.argv) > 1 else None


async def main() -> None:
    c = config.client_agent()
    async with WalletAPIClient(base_url=config.CAW_API_URL, api_key=c.api_key) as cl:
        if REQ:
            rec = await cl.get_user_transaction_by_request_id(c.wallet_id, REQ)
            print("=== tx record ===")
            print(json.dumps(rec, default=str, indent=2))
        recents = await cl.list_user_transactions(c.wallet_id, limit=5)
        print("=== recent txs ===")
        print(json.dumps(recents, default=str, indent=2)[:2000])


if __name__ == "__main__":
    asyncio.run(main())
