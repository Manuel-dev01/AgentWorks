"""Escrow + ERC20 helpers: ABI-encoded calldata builders (for CAW contract_call) and
on-chain read helpers (via web3). The agents build calldata here and hand the hex to CAW.

Lifecycle calls mirror AgentWorksEscrow:
  createJob → fund → submitWork → complete | reject | claimRefund   (+ ERC20 approve)
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from eth_abi import encode
from web3 import Web3

import config


def _retry(thunk, tries: int = 5, delay: float = 2.0):
    """Retry a read against flaky public RPCs."""
    for i in range(tries):
        try:
            return thunk()
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(delay)

REPO_ROOT = Path(__file__).resolve().parents[1]
_ARTIFACT = REPO_ROOT / "contracts" / "out" / "AgentWorksEscrow.sol" / "AgentWorksEscrow.json"
ESCROW_ABI = json.loads(_ARTIFACT.read_text(encoding="utf-8"))["abi"]

ERC20_ABI = json.loads(
    '[{"name":"balanceOf","type":"function","stateMutability":"view",'
    '"inputs":[{"name":"a","type":"address"}],"outputs":[{"type":"uint256"}]},'
    '{"name":"allowance","type":"function","stateMutability":"view",'
    '"inputs":[{"name":"o","type":"address"},{"name":"s","type":"address"}],"outputs":[{"type":"uint256"}]}]'
)

STATUS = {0: "None", 1: "Created", 2: "Funded", 3: "Submitted", 4: "Completed", 5: "Rejected", 6: "Refunded"}

_cs = Web3.to_checksum_address


def _calldata(signature: str, types: list[str], args: list) -> str:
    selector = Web3.keccak(text=signature)[:4]
    return "0x" + (selector + encode(types, args)).hex()


# ── calldata builders (state-changing → sent via CAW contract_call) ──

def approve(spender: str, amount: int) -> str:
    return _calldata("approve(address,uint256)", ["address", "uint256"], [_cs(spender), amount])


def create_job(provider: str, evaluator: str, amount: int, spec_hash: bytes, deadline: int) -> str:
    return _calldata(
        "createJob(address,address,uint256,bytes32,uint64)",
        ["address", "address", "uint256", "bytes32", "uint64"],
        [_cs(provider), _cs(evaluator), amount, spec_hash, deadline],
    )


def fund(job_id: int) -> str:
    return _calldata("fund(uint256)", ["uint256"], [job_id])


def submit_work(job_id: int, deliverable_hash: bytes) -> str:
    return _calldata("submitWork(uint256,bytes32)", ["uint256", "bytes32"], [job_id, deliverable_hash])


def complete(job_id: int) -> str:
    return _calldata("complete(uint256)", ["uint256"], [job_id])


def reject(job_id: int) -> str:
    return _calldata("reject(uint256)", ["uint256"], [job_id])


def claim_refund(job_id: int) -> str:
    return _calldata("claimRefund(uint256)", ["uint256"], [job_id])


# ── on-chain reads (web3) ──

def web3() -> Web3:
    return Web3(Web3.HTTPProvider(config.RPC_URL, request_kwargs={"timeout": 30}))


def _escrow(w3: Web3):
    return w3.eth.contract(address=_cs(config.ESCROW_ADDRESS), abi=ESCROW_ABI)


def next_job_id(w3: Web3) -> int:
    return _retry(lambda: _escrow(w3).functions.nextJobId().call())


def get_job(w3: Web3, job_id: int) -> dict:
    j = _retry(lambda: _escrow(w3).functions.getJob(job_id).call())
    return {
        "client": j[0], "provider": j[1], "evaluator": j[2], "amount": j[3],
        "spec_hash": Web3.to_hex(j[4]), "deliverable_hash": Web3.to_hex(j[5]),
        "deadline": j[6], "status": STATUS.get(j[7], j[7]),
    }


def usdc_balance(w3: Web3, addr: str) -> int:
    t = w3.eth.contract(address=_cs(config.USDC_ADDRESS), abi=ERC20_ABI)
    return _retry(lambda: t.functions.balanceOf(_cs(addr)).call())


def usdc_allowance(w3: Web3, owner: str, spender: str) -> int:
    t = w3.eth.contract(address=_cs(config.USDC_ADDRESS), abi=ERC20_ABI)
    return _retry(lambda: t.functions.allowance(_cs(owner), _cs(spender)).call())
