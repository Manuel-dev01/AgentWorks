"""Escrow v3 (OPEN marketplace, sealed commit-reveal accept) calldata builders + on-chain reads.

Supersedes escrow_v2.py: the raw, frontrunnable `acceptJob` is gone. Claiming a funded job is now a
two-phase race that hides the targeted jobId from the public mempool and binds the claim to the
committer's address (a copied commitment is worthless to anyone else):

  1. commitAccept(commitment)  — commitment = keccak256(abi.encode(jobId, sender, salt)); publishes
     only an opaque hash.
  2. revealAccept(jobId, salt) — after `REVEAL_DELAY_BLOCKS`, opens the bid; first valid reveal wins.

The Job struct / Status enum are identical to v2, so reads (`get_job`, `next_job_id`) are unchanged.
Agents build ABI-encoded calldata here and hand the hex to CAW `contract_call`. Reads go through web3
(preferring `PRIVATE_RPC_URL` when configured). See docs/MEV.md for the threat model.

v3 lifecycle:
  createJob(evaluator, …) → fund → commitAccept → revealAccept → submitWork → complete | reject | claimRefund
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

from eth_abi import encode
from web3 import Web3

import config

REPO_ROOT = Path(__file__).resolve().parents[1]
# Prefer the vendored ABI (tracked in git, shipped in the container); fall back to the Foundry
# build output for local dev. contracts/out is gitignored, so the vendored copy is what deploys.
_VENDORED = Path(__file__).resolve().parent / "abi" / "AgentWorksEscrowV3.json"
_ARTIFACT = REPO_ROOT / "contracts" / "out" / "AgentWorksEscrowV3.sol" / "AgentWorksEscrowV3.json"
_abi_path = _VENDORED if _VENDORED.exists() else _ARTIFACT
ESCROW_V3_ABI = json.loads(_abi_path.read_text(encoding="utf-8"))["abi"]

ERC20_ABI = json.loads(
    '[{"name":"balanceOf","type":"function","stateMutability":"view",'
    '"inputs":[{"name":"a","type":"address"}],"outputs":[{"type":"uint256"}]},'
    '{"name":"allowance","type":"function","stateMutability":"view",'
    '"inputs":[{"name":"o","type":"address"},{"name":"s","type":"address"}],"outputs":[{"type":"uint256"}]}]'
)

# v3 status enum (identical to v2; Accepted now means "a provider revealed + claimed").
STATUS = {0: "None", 1: "Open", 2: "Funded", 3: "Accepted", 4: "Submitted",
          5: "Completed", 6: "Rejected", 7: "Refunded"}

_cs = Web3.to_checksum_address


def _retry(thunk, tries: int = 5, delay: float = 2.0):
    """Retry a read against flaky public RPCs."""
    for i in range(tries):
        try:
            return thunk()
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(delay)


def _calldata(signature: str, types: list[str], args: list) -> str:
    selector = Web3.keccak(text=signature)[:4]
    return "0x" + (selector + encode(types, args)).hex()


# ── calldata builders (state-changing → sent via CAW contract_call) ──

def approve(spender: str, amount: int) -> str:
    return _calldata("approve(address,uint256)", ["address", "uint256"], [_cs(spender), amount])


def create_job(evaluator: str, amount: int, spec_hash: bytes, deadline: int) -> str:
    """v3: OPEN job - no provider named at creation."""
    return _calldata(
        "createJob(address,uint256,bytes32,uint64)",
        ["address", "uint256", "bytes32", "uint64"],
        [_cs(evaluator), amount, spec_hash, deadline],
    )


def fund(job_id: int) -> str:
    return _calldata("fund(uint256)", ["uint256"], [job_id])


# ── sealed commit-reveal accept ──

def random_salt() -> bytes:
    """A fresh 32-byte secret. Keep it until reveal; the commitment is worthless without it."""
    return os.urandom(32)


def commitment(job_id: int, sender: str, salt: bytes) -> bytes:
    """keccak256(abi.encode(jobId, sender, salt)) — exactly the contract's preimage. Hides the
    jobId during commit and binds the claim to `sender`, so a copied hash cannot be revealed by
    anyone else."""
    return Web3.keccak(encode(["uint256", "address", "bytes32"], [job_id, _cs(sender), salt]))


def commit_accept(commitment_hash: bytes) -> str:
    """v3 step 1: publish the sealed bid (opaque hash, no jobId leaked)."""
    return _calldata("commitAccept(bytes32)", ["bytes32"], [commitment_hash])


def reveal_accept(job_id: int, salt: bytes) -> str:
    """v3 step 2: open the bid and claim the job; first valid reveal wins."""
    return _calldata("revealAccept(uint256,bytes32)", ["uint256", "bytes32"], [job_id, salt])


def submit_work(job_id: int, deliverable_hash: bytes, irys_id: str) -> str:
    return _calldata("submitWork(uint256,bytes32,string)", ["uint256", "bytes32", "string"],
                     [job_id, deliverable_hash, irys_id])


def complete(job_id: int) -> str:
    return _calldata("complete(uint256)", ["uint256"], [job_id])


def reject(job_id: int) -> str:
    return _calldata("reject(uint256)", ["uint256"], [job_id])


def claim_refund(job_id: int) -> str:
    return _calldata("claimRefund(uint256)", ["uint256"], [job_id])


# ── on-chain reads (web3) ──

def web3() -> Web3:
    """Prefer the private/MEV-protected RPC for reads when configured (harmless either way),
    else the public RPC."""
    url = config.PRIVATE_RPC_URL or config.RPC_URL
    return Web3(Web3.HTTPProvider(url, request_kwargs={"timeout": 30}))


def _escrow(w3: Web3):
    return w3.eth.contract(address=_cs(config.ESCROW_V3_ADDRESS), abi=ESCROW_V3_ABI)


def next_job_id(w3: Web3) -> int:
    return _retry(lambda: _escrow(w3).functions.nextJobId().call())


def get_job(w3: Web3, job_id: int) -> dict:
    j = _retry(lambda: _escrow(w3).functions.getJob(job_id).call())
    return {
        "client": j[0], "provider": j[1], "evaluator": j[2], "amount": j[3],
        "spec_hash": Web3.to_hex(j[4]), "deliverable_hash": Web3.to_hex(j[5]),
        "irys_id": j[6], "deadline": j[7], "status": STATUS.get(j[8], j[8]),
    }


def commit_info(w3: Web3, commitment_hash: bytes) -> dict:
    """Read a sealed bid's (commitBlock, revealed) — for window/timing display."""
    c = _retry(lambda: _escrow(w3).functions.commitInfo(commitment_hash).call())
    return {"commit_block": c[0], "revealed": c[1]}


def reveal_delay_blocks(w3: Web3) -> int:
    return _retry(lambda: _escrow(w3).functions.revealDelayBlocks().call())


def usdc_balance(w3: Web3, addr: str) -> int:
    t = w3.eth.contract(address=_cs(config.USDC_ADDRESS), abi=ERC20_ABI)
    return _retry(lambda: t.functions.balanceOf(_cs(addr)).call())


def usdc_allowance(w3: Web3, owner: str, spender: str) -> int:
    t = w3.eth.contract(address=_cs(config.USDC_ADDRESS), abi=ERC20_ABI)
    return _retry(lambda: t.functions.allowance(_cs(owner), _cs(spender)).call())
