"""Capture caw wallet creds into the repo .env WITHOUT printing the secret.

Usage:  caw wallet current --show-api-key | python _capture_caw_creds.py <ROLE> <ENV_PATH>
  ROLE is CLIENT or PROVIDER. Updates CAW_<ROLE>_API_KEY and CAW_<ROLE>_WALLET_ID,
  preserving all other lines/comments. Prints only a masked confirmation.
"""

import json
import pathlib
import re
import sys

role = sys.argv[1].upper()
env_path = pathlib.Path(sys.argv[2])

data = json.load(sys.stdin)
api_key = data["api_key"]
wallet = data["wallet_uuid"]

updates = {f"CAW_{role}_API_KEY": api_key, f"CAW_{role}_WALLET_ID": wallet}

lines = env_path.read_text(encoding="utf-8").splitlines()
seen: set[str] = set()
out: list[str] = []
for line in lines:
    m = re.match(r"^([A-Z0-9_]+)=", line)
    if m and m.group(1) in updates:
        k = m.group(1)
        out.append(f"{k}={updates[k]}")
        seen.add(k)
    else:
        out.append(line)
for k, v in updates.items():
    if k not in seen:
        out.append(f"{k}={v}")

env_path.write_text("\n".join(out) + "\n", encoding="utf-8")
print(f"updated {role}: wallet_uuid={wallet}, api_key=<{len(api_key)} chars, ...{api_key[-4:]}>")
