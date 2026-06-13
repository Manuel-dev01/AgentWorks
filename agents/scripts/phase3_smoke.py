"""Phase 3 smoke test - de-risk before building the full lifecycle.

Proves the two unknowns on Ethereum Sepolia:
  1. CAW can read token state (SETH native gas balance + USDC balance read).
  2. CAW can execute a real `contract_call` on Eth Sepolia - we call
     SETH_USDC.approve(escrow, 1) from the Client, then read the on-chain allowance back.

approve() needs no USDC balance (only gas), so this isolates the contract_call path.

Run:  agents/.venv/Scripts/python.exe agents/scripts/phase3_smoke.py
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
from eth_abi import encode
from web3 import Web3

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

w3 = Web3(Web3.HTTPProvider(config.RPC_URL))
USDC = Web3.to_checksum_address(config.USDC_ADDRESS)
ESCROW = Web3.to_checksum_address(config.ESCROW_ADDRESS)

ERC20_ABI = json.loads(
    '[{"name":"allowance","type":"function","stateMutability":"view",'
    '"inputs":[{"name":"o","type":"address"},{"name":"s","type":"address"}],'
    '"outputs":[{"type":"uint256"}]},'
    '{"name":"balanceOf","type":"function","stateMutability":"view",'
    '"inputs":[{"name":"a","type":"address"}],"outputs":[{"type":"uint256"}]}]'
)


def approve_calldata(spender: str, amount: int) -> str:
    selector = Web3.keccak(text="approve(address,uint256)")[:4]
    body = encode(["address", "uint256"], [Web3.to_checksum_address(spender), amount])
    return "0x" + (selector + body).hex()


def contract_call_pact(target: str) -> dict:
    return {
        "policies": [
            {
                "name": "phase3-smoke-approve",
                "type": "contract_call",
                "rules": {
                    "effect": "allow",
                    "when": {
                        "chain_in": [config.CHAIN_ID],
                        "target_in": [{"chain_id": config.CHAIN_ID, "contract_addr": target}],
                    },
                },
            }
        ],
        "completion_conditions": [{"type": "time_elapsed", "threshold": "86400"}],
    }


async def main() -> None:
    c = config.client_agent()
    proof: dict = {"chain_id": config.CHAIN_ID, "escrow": ESCROW, "usdc": USDC}
    client_addr = Web3.to_checksum_address(c.address)

    print(f"\n=== Phase 3 smoke (Eth Sepolia) ===\nrpc_connected={w3.is_connected()} client={client_addr}")

    # On-chain reads (RPC) - ground truth
    usdc = w3.eth.contract(address=USDC, abi=ERC20_ABI)
    proof["rpc_usdc_balance"] = usdc.functions.balanceOf(client_addr).call()
    allow_before = usdc.functions.allowance(client_addr, ESCROW).call()
    proof["allowance_before"] = allow_before
    print(f"[rpc] USDC balance={proof['rpc_usdc_balance']}  allowance(client->escrow) before={allow_before}")

    async with CawWallet(api_url=config.CAW_API_URL, api_key=c.api_key,
                         wallet_uuid=c.wallet_id, name="Client") as client:
        # 1. balance reads via CAW
        proof["caw_seth_balance"] = await client.list_balances(chain_id=config.CHAIN_ID, token_id="SETH")
        proof["caw_usdc_balance"] = await client.list_balances(chain_id=config.CHAIN_ID, token_id=config.USDC_TOKEN_ID)

        # 2. pact authorizing contract_call to the USDC contract
        pact = await client.submit_pact(
            intent="Phase 3 smoke: allow contract_call to SETH_USDC (approve escrow)",
            spec=contract_call_pact(config.USDC_ADDRESS),
            name="phase3-smoke",
        )
        pact_id = pact.get("pact_id") or pact.get("id")
        active = await client.wait_pact_active(pact_id)
        proof["pact_id"], proof["pact_status"] = pact_id, active.get("status")
        print(f"[pact] {pact_id} -> {active.get('status')}")

        # 3. the trivial contract_call: approve(escrow, 1)
        scoped = client.scoped(active)
        request_id = f"smoke-{uuid4().hex[:8]}"
        try:
            resp = await scoped.contract_call(
                src_addr=c.address, contract_addr=config.USDC_ADDRESS,
                calldata=approve_calldata(config.ESCROW_ADDRESS, 1),
                chain_id=config.CHAIN_ID, request_id=request_id,
                description="Phase 3 smoke approve(escrow,1)",
            )
            proof["contract_call_response"] = resp
            rec = await scoped.wait_tx_final(request_id)
            txh = rec.get("transaction_hash") or resp.get("transaction_hash")
            proof["tx_hash"] = txh
            print(f"[contract_call] SUCCESS tx={txh}\n  explorer: {config.EXPLORER_TX.format(txh)}")
        finally:
            await scoped.close()

    # 4. confirm the allowance changed on-chain
    allow_after = usdc.functions.allowance(client_addr, ESCROW).call()
    proof["allowance_after"] = allow_after
    print(f"[rpc] allowance(client->escrow) after={allow_after} (expected 1)")
    proof["SMOKE_PASS"] = allow_after == 1

    out = Path(__file__).resolve().parent / "phase3_smoke_proof.json"
    out.write_text(json.dumps(proof, default=str, indent=2), encoding="utf-8")
    print(f"\nSMOKE_PASS={proof['SMOKE_PASS']}  (proof -> {out})")


if __name__ == "__main__":
    asyncio.run(main())
