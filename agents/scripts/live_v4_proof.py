"""Live on-chain proof of the AgentWorksEscrowV4 committee→finalize lifecycle (Ethereum Sepolia).

Drives the DEPLOYED v4 escrow end-to-end with raw EOAs to prove the contract works live:
  createJob(committee of 3, quorum 2) → fund → commitAccept → revealAccept → submitWork →
  2 evaluators castVote(approve) → Resolved(tentative payout) → finalize → Completed (provider paid).

This is the EOA proof of the on-chain mechanism. The AUTONOMOUS committee runs the same calls through
CAW (autonomous.py committee_worker) given CAW_EVALUATOR_* creds. Run: python agents/scripts/live_v4_proof.py
"""
from __future__ import annotations

import sys, time, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eth_account import Account
from web3 import Web3

import config
import escrow_v4 as esc

MOCKUSDC_ABI = json.loads('[{"name":"mint","type":"function","stateMutability":"nonpayable",'
                          '"inputs":[{"name":"to","type":"address"},{"name":"a","type":"uint256"}],"outputs":[]},'
                          '{"name":"approve","type":"function","stateMutability":"nonpayable",'
                          '"inputs":[{"name":"s","type":"address"},{"name":"a","type":"uint256"}],"outputs":[{"type":"bool"}]},'
                          '{"name":"balanceOf","type":"function","stateMutability":"view",'
                          '"inputs":[{"name":"a","type":"address"}],"outputs":[{"type":"uint256"}]}]')


def main() -> None:
    import os
    pk = os.environ["DEPLOYER_PRIVATE_KEY"]
    if not pk.startswith("0x"):
        pk = "0x" + pk
    w3 = esc.web3()
    client = Account.from_key(pk)  # the deployer EOA acts as the Client
    provider = Account.create()
    ev = [Account.create() for _ in range(3)]
    chain_id = w3.eth.chain_id
    txs: dict = {}

    def send(acct, to, data, gas, value=0):
        # Sign ONCE with a fixed nonce so a re-broadcast after a flaky RPC is an idempotent duplicate
        # (never a second distinct tx). Retries only re-poll the receipt by hash; they never re-sign.
        nonce = None
        for _ in range(5):
            try:
                nonce = w3.eth.get_transaction_count(acct.address); break
            except Exception:
                time.sleep(3)
        tx = {"to": Web3.to_checksum_address(to), "data": data, "value": value, "gas": gas,
              "gasPrice": int(w3.eth.gas_price * 1.3), "nonce": nonce, "chainId": chain_id}
        signed = acct.sign_transaction(tx)
        h = w3.keccak(signed.raw_transaction)
        for attempt in range(6):
            try:
                w3.eth.send_raw_transaction(signed.raw_transaction)
            except Exception as e:
                msg = str(e).lower()
                if "already known" not in msg and "nonce too low" not in msg and "already imported" not in msg:
                    if attempt == 5:
                        raise
                    print(f"  rebroadcast retry ({type(e).__name__})"); time.sleep(4); continue
            try:
                rcpt = w3.eth.wait_for_transaction_receipt(h, timeout=120)
                if rcpt["status"] != 1:
                    raise RuntimeError(f"tx reverted: {h.hex()}")
                return h.hex(), rcpt
            except RuntimeError:
                raise
            except Exception:
                print("  re-poll receipt..."); time.sleep(5)
        raise RuntimeError(f"tx not confirmed: {h.hex()}")

    # persist ephemeral keys so a mid-run crash is recoverable (gitignored scratch file)
    keyfile = Path(__file__).resolve().parent / "live_v4_keys.json"
    keyfile.write_text(json.dumps({"provider": provider.key.hex(),
                                   "ev": [a.key.hex() for a in ev]}), encoding="utf-8")

    print("Client(deployer):", client.address)
    print("Provider:", provider.address)
    print("Committee:", [a.address for a in ev], "quorum 2")

    # fund the EOAs that will transact (provider + 2 voters; ev[2] only needs to be a committee address)
    for acct, amt in [(provider, 0.0016), (ev[0], 0.0009), (ev[1], 0.0009)]:
        h, _ = send(client, acct.address, b"", 21000, value=w3.to_wei(amt, "ether"))
        print(f"funded {acct.address[:10]} {amt} ETH  {h}")

    usdc = w3.eth.contract(address=Web3.to_checksum_address(config.USDC_ADDRESS), abi=MOCKUSDC_ABI)
    amount = 5_000_000  # 5 USDC
    txs["mint"], _ = send(client, config.USDC_ADDRESS, usdc.encode_abi("mint", [client.address, 10_000_000]), 80_000)
    print("minted 10 USDC ->", txs["mint"])
    txs["approve"], _ = send(client, config.USDC_ADDRESS, esc.approve(config.ESCROW_V4_ADDRESS, amount), 80_000)

    spec = "Write a 2-sentence explanation of on-chain escrow for a non-expert."
    job_id = esc.next_job_id(w3)
    spec_hash = Web3.keccak(text=f"{spec}#{job_id}")
    deadline = int(time.time()) + 7 * 24 * 3600
    committee = [a.address for a in ev]
    txs["createJob"], _ = send(client, config.ESCROW_V4_ADDRESS,
                               esc.create_job(committee, 2, amount, spec_hash, deadline), 600_000)
    print(f"createJob #{job_id} committee=3 quorum=2 ->", txs["createJob"])
    txs["fund"], _ = send(client, config.ESCROW_V4_ADDRESS, esc.fund(job_id), 120_000)
    print("fund ->", txs["fund"])

    # provider sealed accept
    salt = esc.random_salt()
    txs["commitAccept"], rc = send(provider, config.ESCROW_V4_ADDRESS,
                                   esc.commit_accept(esc.commitment(job_id, provider.address, salt)), 120_000)
    print("commitAccept ->", txs["commitAccept"])
    cblock = rc["blockNumber"]
    while w3.eth.block_number < cblock + config.REVEAL_DELAY_BLOCKS:
        time.sleep(3)
    txs["revealAccept"], _ = send(provider, config.ESCROW_V4_ADDRESS, esc.reveal_accept(job_id, salt), 200_000)
    print("revealAccept ->", txs["revealAccept"])

    deliverable = "An on-chain escrow holds a buyer's funds in a neutral contract until the agreed work is delivered. Neither party can take the money unilaterally, so two agents who don't trust each other can transact safely."
    dhash = Web3.keccak(text=deliverable)
    txs["submitWork"], _ = send(provider, config.ESCROW_V4_ADDRESS,
                                esc.submit_work(job_id, dhash, "live-v4-proof"), 200_000)
    print("submitWork ->", txs["submitWork"])

    # committee votes (2 approve → quorum → Resolved tentative payout)
    txs["vote1"], _ = send(ev[0], config.ESCROW_V4_ADDRESS, esc.cast_vote(job_id, True), 150_000)
    print("castVote ev0 approve ->", txs["vote1"])
    txs["vote2"], _ = send(ev[1], config.ESCROW_V4_ADDRESS, esc.cast_vote(job_id, True), 150_000)
    print("castVote ev1 approve ->", txs["vote2"])

    v = esc.get_vote(w3, job_id)
    print(f"vote tally {v['approve']}-{v['reject']} tentative_payout={v['tentative_payout']} resolvedBlock={v['resolved_block']}")
    print(f"status now: {esc.get_job(w3, job_id)['status']}")

    # wait out the dispute window, then finalize
    target = int(v["resolved_block"]) + config.DISPUTE_WINDOW_BLOCKS
    print(f"waiting for dispute window to close (block > {target})...")
    while w3.eth.block_number <= target:
        time.sleep(6)
    txs["finalize"], _ = send(client, config.ESCROW_V4_ADDRESS, esc.finalize(job_id), 150_000)
    print("finalize ->", txs["finalize"])

    job = esc.get_job(w3, job_id)
    prov_usdc = esc.usdc_balance(w3, provider.address)
    print("\n=== V4 LIVE PROOF RESULT ===")
    print("final status:", job["status"], "| provider USDC:", prov_usdc / 1e6)
    print(json.dumps({"job_id": job_id, "committee": committee, "quorum": 2,
                      "tentative": "payout" if v["tentative_payout"] else "refund",
                      "final_status": job["status"], "txs": txs}, indent=2))


if __name__ == "__main__":
    main()
