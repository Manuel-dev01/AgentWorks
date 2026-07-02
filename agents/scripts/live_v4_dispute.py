"""Live on-chain proof of the AgentWorksEscrowV4 STAKED DISPUTE path on Sepolia, settled by the REAL
UMA Optimistic Oracle V3 (no operator key).

Flow: createJob(committee 3, quorum 2) -> fund -> commit/reveal -> submitWork -> committee votes APPROVE
(2-0) -> Resolved(tentative PAYOUT) -> the losing side (client) STAKES a bond + dispute() -> the arbiter
adapter posts a real UMA assertion (assertTruth) -> after liveness, settle() -> UMA's assertionResolvedCallback
-> escrow.resolveDispute() OVERTURNS to REFUND (the disputer's claim held on the optimistic path) ->
client refunded, bond returned. Demonstrates the dispute escalation + decentralized-oracle ruling end-to-end.

Run: python agents/scripts/live_v4_dispute.py   (needs DEPLOYER_PRIVATE_KEY + a funded deployer)
"""
from __future__ import annotations

import json, os, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eth_account import Account
from web3 import Web3

import config
import escrow_v4 as esc

ERC20_MINT_ABI = json.loads('[{"name":"mint","type":"function","stateMutability":"nonpayable",'
    '"inputs":[{"name":"to","type":"address"},{"name":"a","type":"uint256"}],"outputs":[]},'
    '{"name":"approve","type":"function","stateMutability":"nonpayable",'
    '"inputs":[{"name":"s","type":"address"},{"name":"a","type":"uint256"}],"outputs":[{"type":"bool"}]},'
    '{"name":"balanceOf","type":"function","stateMutability":"view","inputs":[{"name":"a","type":"address"}],"outputs":[{"type":"uint256"}]}]')


def _settle_calldata(job_id: int) -> str:
    return "0x" + Web3.keccak(text="settle(uint256)")[:4].hex() + job_id.to_bytes(32, "big").hex()


def main() -> None:
    pk = os.environ["DEPLOYER_PRIVATE_KEY"]
    if not pk.startswith("0x"):
        pk = "0x" + pk
    w3 = esc.web3()
    client = Account.from_key(pk)         # Client AND the (losing) disputer
    chain_id = w3.eth.chain_id
    txs: dict = {}
    arbiter = Web3.to_checksum_address(config.UMA_ARBITER_ADDRESS)
    bond_cur = w3.eth.contract(address=Web3.to_checksum_address(config.UMA_BOND_CURRENCY), abi=ERC20_MINT_ABI)
    usdc = w3.eth.contract(address=Web3.to_checksum_address(config.USDC_ADDRESS), abi=ERC20_MINT_ABI)

    # Reuse already-funded ephemeral EOAs across re-runs (gas-efficient + lets us retry the window).
    keyfile = Path(__file__).resolve().parent / "live_v4_dispute_keys.json"
    if keyfile.exists():
        k = json.loads(keyfile.read_text(encoding="utf-8"))
        provider = Account.from_key(k["provider"]); ev = [Account.from_key(x) for x in k["ev"]]
    else:
        provider = Account.create(); ev = [Account.create() for _ in range(3)]
        keyfile.write_text(json.dumps({"provider": provider.key.hex(), "ev": [a.key.hex() for a in ev]}), encoding="utf-8")

    def send(acct, to, data, gas, value=0):
        tx = {"to": Web3.to_checksum_address(to), "data": data, "value": value, "gas": gas,
              "gasPrice": int(w3.eth.gas_price * 1.3), "nonce": w3.eth.get_transaction_count(acct.address),
              "chainId": chain_id}
        signed = acct.sign_transaction(tx)
        h = w3.keccak(signed.raw_transaction)
        for attempt in range(6):
            try:
                w3.eth.send_raw_transaction(signed.raw_transaction)
            except Exception as e:
                m = str(e).lower()
                if not any(x in m for x in ("already known", "nonce too low", "already imported")):
                    if attempt == 5: raise
                    time.sleep(4); continue
            try:
                r = w3.eth.wait_for_transaction_receipt(h, timeout=120)
                if r["status"] != 1: raise RuntimeError(f"reverted: {h.hex()}")
                return h.hex(), r
            except RuntimeError: raise
            except Exception: time.sleep(5)
        raise RuntimeError(f"unconfirmed: {h.hex()}")

    print("Client/disputer:", client.address, "| Provider:", provider.address)
    print("Committee:", [a.address for a in ev], "quorum 2 | arbiter:", arbiter)

    # fund only EOAs that are short on gas (re-runs reuse already-funded ones)
    for acct, amt in [(provider, 0.0016), (ev[0], 0.0009), (ev[1], 0.0009)]:
        if w3.eth.get_balance(acct.address) < w3.to_wei(amt / 2, "ether"):
            send(client, acct.address, b"", 21000, value=w3.to_wei(amt, "ether"))
    print("EOAs funded/reused")

    amount = 5_000_000
    # Bond mint + approve UP FRONT (so dispute() lands inside the 8-block window right after Resolved).
    send(client, config.UMA_BOND_CURRENCY, bond_cur.encode_abi("mint", [client.address, config.UMA_BOND]), 100_000)
    send(client, config.UMA_BOND_CURRENCY, bond_cur.encode_abi("approve", [arbiter, config.UMA_BOND]), 80_000)
    send(client, config.USDC_ADDRESS, usdc.encode_abi("mint", [client.address, 10_000_000]), 80_000)
    send(client, config.USDC_ADDRESS, esc.approve(config.ESCROW_V4_ADDRESS, amount), 80_000)
    spec = "Summarize on-chain escrow in 2 sentences for a non-expert."
    job_id = esc.next_job_id(w3)
    spec_hash = Web3.keccak(text=f"{spec}#{job_id}")
    deadline = int(time.time()) + 7 * 24 * 3600
    committee = [a.address for a in ev]
    txs["createJob"], _ = send(client, config.ESCROW_V4_ADDRESS, esc.create_job(committee, 2, amount, spec_hash, deadline), 600_000)
    txs["fund"], _ = send(client, config.ESCROW_V4_ADDRESS, esc.fund(job_id), 120_000)
    print(f"createJob #{job_id} + fund")

    salt = esc.random_salt()
    _, rc = send(provider, config.ESCROW_V4_ADDRESS, esc.commit_accept(esc.commitment(job_id, provider.address, salt)), 120_000)
    while w3.eth.block_number < rc["blockNumber"] + config.REVEAL_DELAY_BLOCKS:
        time.sleep(3)
    txs["revealAccept"], _ = send(provider, config.ESCROW_V4_ADDRESS, esc.reveal_accept(job_id, salt), 200_000)
    dhash = Web3.keccak(text="An escrow holds funds neutrally until work is delivered; neither party can take them unilaterally.")
    txs["submitWork"], _ = send(provider, config.ESCROW_V4_ADDRESS, esc.submit_work(job_id, dhash, "live-v4-dispute"), 200_000)
    print("accept + submitWork done")

    # committee APPROVES (2-0) -> tentative PAYOUT -> loser = client
    txs["vote1"], _ = send(ev[0], config.ESCROW_V4_ADDRESS, esc.cast_vote(job_id, True), 150_000)
    txs["vote2"], _ = send(ev[1], config.ESCROW_V4_ADDRESS, esc.cast_vote(job_id, True), 150_000)
    v = esc.get_vote(w3, job_id)
    print(f"committee {v['approve']}-{v['reject']} tentative_payout={v['tentative_payout']} status={esc.get_job(w3, job_id)['status']}")

    # client (losing side) disputes immediately (bond already minted+approved) -> adapter asserts to UMA OOv3
    # (gas-heavy: escrow.dispute -> adapter.openDispute -> OOv3.assertTruth; give it ample gas)
    txs["dispute"], _ = send(client, config.ESCROW_V4_ADDRESS, esc.dispute(job_id), 1_500_000)
    aid = w3.eth.contract(address=arbiter, abi=json.loads('[{"name":"assertionByJob","type":"function","stateMutability":"view","inputs":[{"type":"uint256"}],"outputs":[{"type":"bytes32"}]}]')).functions.assertionByJob(job_id).call()
    print(f"DISPUTED -> UMA assertionId 0x{aid.hex()}  (status={esc.get_job(w3, job_id)['status']})")

    print(f"waiting UMA liveness ({config.UMA_BOND and 120}s)...")
    time.sleep(135)
    # settle is gas-heavy too: OOv3.settleAssertion -> assertionResolvedCallback -> escrow.resolveDispute -> _execute transfer
    txs["settle"], _ = send(client, arbiter, _settle_calldata(job_id), 800_000)  # anyone can settle
    job = esc.get_job(w3, job_id)
    client_usdc = esc.usdc_balance(w3, client.address)
    print("\n=== V4 LIVE DISPUTE RESULT ===")
    print("final status:", job["status"], "(Rejected = dispute overturned the committee payout -> client refunded)")
    print(json.dumps({"job_id": job_id, "committee_tentative": "payout", "dispute_outcome": job["status"],
                      "uma_assertion": "0x" + aid.hex(), "txs": txs}, indent=2))


if __name__ == "__main__":
    main()
