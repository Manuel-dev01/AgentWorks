"""Phase 2 — CAW hello-world (Base Sepolia).

Proves the CAW loop end to end:
  1. Connect to the two onboarded wallets (Client, Provider).
  2. Ensure each has a Base Sepolia (TBASE_SETH) address; show balances.
  3. Client submits a minimal transfer pact; wait until active; take the pact-scoped key.
  4. Client transfers a tiny amount of native gas (TBASE_SETH) -> Provider.
  5. Poll the tx to a final status; print the on-chain tx hash (open on BaseScan).
  6. Read the Client's audit log and show the transfer entry.

Run:  agents/.venv/Scripts/python.exe agents/scripts/phase2_hello.py
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config
from caw import CawWallet

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# Phase 2 hello-world runs on Ethereum Sepolia (SETH): the CAW faucet funds SETH directly
# (CAW-native => balance is reliably indexed), making the demo deterministic. Base Sepolia
# (TBASE_SETH) is CONFIRMED supported on CAW (chain + TBASE_USDC token), but CAW did not
# surface an externally-deposited Base Sepolia native balance — a funding item flagged for Phase 3.
HELLO_CHAIN = "SETH"
HELLO_TOKEN = "SETH"
HELLO_EXPLORER_TX = "https://sepolia.etherscan.io/tx/{}"
TRANSFER_AMOUNT = "0.001"            # SETH (native gas, 18 decimals); faucet grants 0.01
PACT_CAP = "0.005"                    # deny transfers above this


def _hash_of(rec: dict) -> str | None:
    for k in ("transaction_hash", "tx_hash", "hash", "txn_id"):
        v = (rec or {}).get(k)
        if v:
            return v
    return None


def transfer_pact_spec() -> dict:
    return {
        "policies": [
            {
                "name": "phase2-hello-transfer",
                "type": "transfer",
                "rules": {
                    "effect": "allow",
                    "when": {
                        "chain_in": [HELLO_CHAIN],
                        "token_in": [{"chain_id": HELLO_CHAIN, "token_id": HELLO_TOKEN}],
                    },
                    "deny_if": {"amount_gt": PACT_CAP},
                },
            }
        ],
        "completion_conditions": [{"type": "time_elapsed", "threshold": "86400"}],
    }


async def main() -> None:
    client_cfg = config.client_agent()
    provider_cfg = config.provider_agent()
    proof: dict = {"chain_id": config.CHAIN_ID}

    print(f"\n=== Phase 2: CAW hello-world on {HELLO_CHAIN} ===")
    print(f"Client   wallet={client_cfg.wallet_id} addr={client_cfg.address}")
    print(f"Provider wallet={provider_cfg.wallet_id} addr={provider_cfg.address}")

    async with CawWallet(api_url=config.CAW_API_URL, api_key=client_cfg.api_key,
                         wallet_uuid=client_cfg.wallet_id, name="Client") as client:

        # 1. Show balance for the funded default EVM address.
        bal_before = await client.list_balances(chain_id=HELLO_CHAIN)
        proof["client_balance_before"] = bal_before

        # 2. Submit a minimal transfer pact and wait until active
        pact_resp = await client.submit_pact(
            intent=f"Phase 2 hello-world: allow small {config.NATIVE_TOKEN_ID} transfers on Base Sepolia",
            spec=transfer_pact_spec(),
            name="phase2-hello",
        )
        pact_id = pact_resp.get("pact_id") or pact_resp.get("id")
        print(f"\n[pact] submitted id={pact_id}")
        active = await client.wait_pact_active(pact_id)
        proof["pact_id"] = pact_id
        proof["pact_status"] = active.get("status")
        print(f"[pact] active: {pact_id}")

        # 3. Use the pact-scoped key for the constrained transfer
        scoped = client.scoped(active)
        request_id = f"phase2-{uuid4().hex[:8]}"
        try:
            tx_resp = await scoped.transfer(
                src_addr=client_cfg.address,
                dst_addr=provider_cfg.address,
                amount=TRANSFER_AMOUNT,
                token_id=HELLO_TOKEN,
                chain_id=HELLO_CHAIN,
                request_id=request_id,
                description="AgentWorks Phase 2 hello-world transfer",
            )
            proof["transfer_response"] = tx_resp
            print(f"\n[transfer] submitted request_id={request_id}")

            # 4. Poll to final status, capture on-chain hash
            rec = await scoped.wait_tx_final(request_id)
            proof["transfer_record"] = rec
            txh = _hash_of(rec) or _hash_of(tx_resp)
            proof["tx_hash"] = txh
            if txh:
                print(f"[transfer] SUCCESS tx={txh}")
                print(f"[transfer] explorer: {HELLO_EXPLORER_TX.format(txh)}")
        finally:
            await scoped.close()

        # 5. Post-transfer balance + audit log
        proof["client_balance_after"] = await client.list_balances(chain_id=HELLO_CHAIN)
        audit = await client.list_audit_logs(limit=20)
        proof["audit_sample"] = audit

    out = Path(__file__).resolve().parent / "phase2_proof.json"
    out.write_text(json.dumps(proof, default=str, indent=2), encoding="utf-8")
    print(f"\n=== proof written to {out} ===")
    print("tx_hash:", proof.get("tx_hash"))
    print("pact:", proof.get("pact_id"), proof.get("pact_status"))


if __name__ == "__main__":
    asyncio.run(main())
