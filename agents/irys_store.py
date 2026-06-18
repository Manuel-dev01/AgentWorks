"""Irys deliverable storage - Python wrapper around the Node uploader + HTTP retrieval.

upload(text, tags) -> {id, url, ...} via the @irys/upload devnet Node helper (agents/irys/upload.mjs).
fetch(irys_id)     -> bytes via GET gateway.irys.xyz/<id> (with retry for gateway propagation).
keccak(bytes)      -> 0x-prefixed keccak256, to compare against the on-chain deliverableHash.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
import urllib.request
from pathlib import Path

from web3 import Web3

import config

IRYS_DIR = Path(__file__).resolve().parent / "irys"
UPLOAD_JS = IRYS_DIR / "upload.mjs"
# Devnet data is served by the devnet gateway; the prod gateway.irys.xyz 403s for devnet ids
# (and only resolves after propagation). devnet.irys.xyz serves it immediately.
GATEWAY = "https://devnet.irys.xyz/{}"


def keccak(data: bytes) -> str:
    return Web3.to_hex(Web3.keccak(data))


def upload(text: str, tags: dict[str, str] | None = None) -> dict:
    env = dict(os.environ)
    env.setdefault("RPC_URL", config.RPC_URL)
    args = ["node", str(UPLOAD_JS)]
    if tags:
        args.append(json.dumps([{"name": k, "value": str(v)} for k, v in tags.items()]))
    p = subprocess.run(args, input=text.encode("utf-8"), capture_output=True, cwd=str(IRYS_DIR), env=env)
    out = (p.stdout or b"").decode("utf-8", "replace").strip()
    if p.returncode != 0:
        raise RuntimeError(f"irys upload failed (rc={p.returncode}): {(p.stderr or b'').decode('utf-8','replace')[:500]}\n{out[:300]}")
    result = json.loads(out.splitlines()[-1])
    if result.get("error"):
        raise RuntimeError(f"irys upload error: {result['error']}")
    return result


def fetch(irys_id: str, *, tries: int = 6, delay: float = 3.0) -> bytes:
    # The Irys gateway 403s the default Python-urllib User-Agent - send a normal UA.
    url = GATEWAY.format(irys_id)
    last = None
    for _ in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "AgentWorks/1.0"})
            with urllib.request.urlopen(req, timeout=20) as r:
                if r.status == 200:
                    return r.read()
        except Exception as e:  # noqa: BLE001 - brief unavailability right after upload
            last = e
        time.sleep(delay)
    raise RuntimeError(f"could not fetch {url} after {tries} tries ({last})")
