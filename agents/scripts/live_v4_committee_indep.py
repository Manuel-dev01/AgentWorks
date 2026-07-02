"""Live proof: an M-of-N committee that is INDEPENDENT ON BOTH AXES — each member signs from its OWN
CAW wallet (own TSS node + Pact + key) AND reasons on its OWN model (DeepSeek / Groq-Llama / Gemini).

This closes the "the committee are CAW wallets but all one LLM / one wallet" gap: a quorum here is a
genuine M-of-N of independent judges, not one model/wallet voting N times.

Flow: an EOA client+provider set up a fresh job (createJob naming the 3 evaluator CAW wallets, quorum=3
so ALL three must vote → all three land on-chain → fund → commit/reveal → submitWork). Then, for each
committee member IN TURN, bring that wallet's local TSS node online (this dev box runs one node at a
time; in production each evaluator is a separate host), judge the deliverable with that member's OWN
model, and castVote through that member's OWN CAW wallet under its evaluator_pact. Quorum → finalize → paid.

Run: python agents/scripts/live_v4_committee_indep.py   (needs DEPLOYER_PRIVATE_KEY + a funded deployer)
"""
from __future__ import annotations

import asyncio, json, os, subprocess, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eth_account import Account
from web3 import Web3

import config, registry, pacts
import escrow_v4 as esc
import reasoning, irys_store
from caw.client import CawWallet
from uuid import uuid4

ERC20_MINT_ABI = json.loads('[{"name":"mint","type":"function","stateMutability":"nonpayable",'
    '"inputs":[{"name":"to","type":"address"},{"name":"a","type":"uint256"}],"outputs":[]},'
    '{"name":"approve","type":"function","stateMutability":"nonpayable",'
    '"inputs":[{"name":"s","type":"address"},{"name":"a","type":"uint256"}],"outputs":[{"type":"bool"}]}]')

CAW_BIN = os.path.expanduser("~/.cobo-agentic-wallet/bin/caw.exe")
# session id per evaluator wallet (used to bring that wallet's TSS node online before its vote)
SESSIONS = {
    "8ea34ab0-b3f6-4175-956a-82e93d27979f": "sess-d7dd98fd9ff3fdfd",   # Evaluator A (DeepSeek)
    "12c93f9a-33e7-4e35-9e41-74dda22494d9": "sess-35fc700846d83b93",   # Evaluator B (Groq/Llama)
    "5020aa5f-07c6-4fd3-b08e-df0065e636e3": "sess-445208eb6d6cc966",   # Evaluator C (Gemini)
}

DELIVERABLE = ("An on-chain escrow is a neutral smart contract that holds the buyer's payment until the "
               "agreed work is delivered. Because the funds are locked by code rather than by either party, "
               "the seller knows payment is guaranteed on delivery and the buyer knows their money is safe "
               "until they receive what they ordered. This lets two agents who don't trust each other "
               "transact safely, trusting only the neutral escrow to release funds fairly.")
SPEC_TASK = ("Write a clear 2-3 sentence explanation, for a non-expert, of how an on-chain escrow lets two "
             "agents who don't trust each other transact safely.")
SPEC_CRITERIA = "Plain language, 2-3 sentences, mentions the neutral escrow holding funds."


def _bring_node_up(wallet_id: str) -> None:
    """No-op: each evaluator wallet's TSS signer is hosted on Railway (agentworks-tss), always-on and
    relay-connected — exactly like Client/Provider. We must NOT start a local node (one node per identity
    on the relay), so signing just routes to the hosted signer via the relay."""
    return


def judge(member, spec, deliverable, tries=6):
    for i in range(tries):
        try:
            return reasoning.evaluate_member(spec, deliverable, member_name=member.name, llm=member.llm())
        except Exception as e:
            print(f"  [{member.name}] judge try {i+1} failed ({type(e).__name__}); retry"); time.sleep(4 * (i + 1))
    raise RuntimeError(f"{member.name} judging failed")


async def cast_vote_caw(member, job_id, approve) -> tuple[str, bool]:
    async with CawWallet(api_url=config.CAW_API_URL, api_key=member.api_key,
                         wallet_uuid=member.wallet_id, name=member.name) as root:
        sub = await root.submit_pact(intent=f"{member.name} votes on marketplace deliverables",
                                     spec=pacts.evaluator_pact(escrow=config.ESCROW_V4_ADDRESS),
                                     name=f"indep-{member.name.replace(' ', '')}-{uuid4().hex[:5]}")
        pact = await root.wait_pact_active(sub.get("pact_id"))
        async with root.scoped(pact, name_suffix="") as ew:
            rid = f"indep-{uuid4().hex[:8]}"
            resp = await ew.contract_call(src_addr=member.address, contract_addr=config.ESCROW_V4_ADDRESS,
                                          calldata=esc.cast_vote(job_id, approve), chain_id=config.CHAIN_ID,
                                          request_id=rid, description=f"castVote[{member.name}]")
            rec = await ew.wait_tx_final(rid, timeout=360.0)
            h = (rec or {}).get("transaction_hash") or (resp or {}).get("transaction_hash")
            return h, (rec or {}).get("status_display") == "Success"


def main() -> None:
    pk = os.environ["DEPLOYER_PRIVATE_KEY"]
    if not pk.startswith("0x"):
        pk = "0x" + pk
    w3 = esc.web3()
    client = Account.from_key(pk)
    chain_id = w3.eth.chain_id
    txs: dict = {}
    usdc = w3.eth.contract(address=Web3.to_checksum_address(config.USDC_ADDRESS), abi=ERC20_MINT_ABI)

    keyfile = Path(__file__).resolve().parent / "live_v4_dispute_keys.json"
    if keyfile.exists():
        provider = Account.from_key(json.loads(keyfile.read_text(encoding="utf-8"))["provider"])
    else:
        provider = Account.create()
        keyfile.write_text(json.dumps({"provider": provider.key.hex(), "ev": []}), encoding="utf-8")

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
                if not any(x in str(e).lower() for x in ("already known", "nonce too low", "already imported")):
                    if attempt == 5: raise
                    time.sleep(4); continue
            try:
                r = w3.eth.wait_for_transaction_receipt(h, timeout=150)
                if r["status"] != 1: raise RuntimeError(f"reverted: {h.hex()}")
                return h.hex(), r
            except RuntimeError: raise
            except Exception: time.sleep(5)
        raise RuntimeError(f"unconfirmed: {h.hex()}")

    members = registry.evaluators()
    committee = [m.address for m in members]
    quorum = len(committee)  # unanimous → every member must cast → every wallet lands an on-chain vote
    print("Client(EOA):", client.address, "| Provider(EOA):", provider.address)
    for m in members:
        print(f"  committee {m.name}: wallet {m.wallet_id[:8]}… addr {m.address} model {m.llm()['model']}")
    print("quorum:", quorum)

    if w3.eth.get_balance(provider.address) < w3.to_wei(0.0015, "ether"):
        send(client, provider.address, b"", 21000, value=w3.to_wei(0.003, "ether"))
    amount = 5_000_000
    send(client, config.USDC_ADDRESS, usdc.encode_abi("mint", [client.address, amount]), 80_000)
    send(client, config.USDC_ADDRESS, esc.approve(config.ESCROW_V4_ADDRESS, amount), 80_000)

    spec = f"{SPEC_TASK}\n\nAcceptance criteria: {SPEC_CRITERIA}"
    job_id = esc.next_job_id(w3)
    spec_hash = Web3.keccak(text=f"{spec}#{job_id}")
    deadline = int(time.time()) + 7 * 24 * 3600
    txs["createJob"], _ = send(client, config.ESCROW_V4_ADDRESS,
                               esc.create_job(committee, quorum, amount, spec_hash, deadline), 700_000)
    txs["fund"], _ = send(client, config.ESCROW_V4_ADDRESS, esc.fund(job_id), 120_000)
    print(f"createJob #{job_id} (committee=3 wallets, quorum {quorum}) + fund")

    salt = esc.random_salt()
    _, rc = send(provider, config.ESCROW_V4_ADDRESS,
                 esc.commit_accept(esc.commitment(job_id, provider.address, salt)), 120_000)
    while w3.eth.block_number < rc["blockNumber"] + config.REVEAL_DELAY_BLOCKS:
        time.sleep(3)
    txs["revealAccept"], _ = send(provider, config.ESCROW_V4_ADDRESS, esc.reveal_accept(job_id, salt), 200_000)
    dhash = Web3.keccak(text=DELIVERABLE)
    txs["submitWork"], _ = send(provider, config.ESCROW_V4_ADDRESS,
                                esc.submit_work(job_id, dhash, "local-indep-committee"), 200_000)
    assert irys_store.keccak(DELIVERABLE.encode()).lower() == esc.get_job(w3, job_id)["deliverable_hash"].lower()
    print("accept + submitWork done (deliverable keccak == on-chain anchor)")

    # ── each member: own node up → own model judges → own CAW wallet votes (sequential) ──
    vote_txs = {}
    for m in members:
        if esc.get_vote(w3, job_id)["approve"] >= quorum:
            break
        print(f"\n[{m.name}] bringing its TSS node online…")
        _bring_node_up(m.wallet_id)
        verdict = judge(m, spec, DELIVERABLE)
        approve = bool(verdict.get("accept"))
        print(f"[{m.name}] model={m.llm()['model']} -> accept={approve} ({str(verdict.get('reason'))[:70]})")
        h, ok = asyncio.run(cast_vote_caw(m, job_id, approve))
        print(f"[{m.name}] castVote tx={h} success={ok}")
        if ok:
            vote_txs[m.name] = {"wallet": m.wallet_id, "addr": m.address, "model": m.llm()["model"], "tx": h}

    v = esc.get_vote(w3, job_id)
    print(f"\nvotes {v['approve']}-{v['reject']} | status {esc.get_job(w3, job_id)['status']} | tentative_payout {v['tentative_payout']}")

    # finalize (EOA, permissionless) once the dispute window elapses
    rb = int(v["resolved_block"]) or w3.eth.block_number
    while w3.eth.block_number <= rb + config.DISPUTE_WINDOW_BLOCKS:
        time.sleep(5)
    txs["finalize"], _ = send(client, config.ESCROW_V4_ADDRESS, esc.finalize(job_id), 200_000)
    job = esc.get_job(w3, job_id)
    print("\n=== INDEPENDENT COMMITTEE RESULT ===")
    print("final status:", job["status"], "(Completed = 3 independent wallets + 3 distinct models -> quorum -> payout)")
    print(json.dumps({"job_id": job_id, "quorum": quorum, "committee_votes": vote_txs, "txs": txs}, indent=2))


if __name__ == "__main__":
    main()
