"""Phase 5 Irys smoke - prove upload -> fetch -> hash roundtrip on Irys devnet."""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import irys_store

text = f"AgentWorks Irys devnet smoke @ {int(time.time())} - trustless deliverable storage."
print("[1] uploading to Irys devnet...")
res = irys_store.upload(text, tags={"app": "AgentWorks", "kind": "smoke"})
print(f"   id={res['id']}  url={res['url']}  bytes={res.get('bytes')} price={res.get('price')} funded={res.get('funded')}")

print("[2] fetching back from gateway...")
data = irys_store.fetch(res["id"])
print(f"   fetched {len(data)} bytes")

match = data == text.encode("utf-8")
khash = irys_store.keccak(data) == irys_store.keccak(text.encode("utf-8"))
print(f"[3] bytes_match={match}  keccak_match={khash}")
print(f"ROUNDTRIP_PASS={match and khash}")
