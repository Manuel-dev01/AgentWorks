"""CLI for the resumable live flow (driven by the web /api/flow route).

Usage:
  python flow_step.py start [good|bad]     -> {run_id, fund_decision, status, ...}
  python flow_step.py post   <run_id>
  python flow_step.py accept <run_id>
  python flow_step.py submit <run_id>
  python flow_step.py settle <run_id>

Prints the updated flow state as a single JSON line on stdout. Exits non-zero with {"error": ...} on failure.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import flow  # noqa: E402


def main() -> int:
    if len(sys.argv) < 2:
        print(json.dumps({"error": "usage: flow_step.py <start|post|accept|submit|settle> [run_id|mode]"}))
        return 2
    step = sys.argv[1]
    arg = sys.argv[2] if len(sys.argv) > 2 else None
    try:
        if step == "start":
            # arg is either a bare mode ("good"/"bad") or a JSON blob {mode,task,criteria,amount_usdc}
            params = {"mode": "good"}
            if arg:
                if arg.strip().startswith("{"):
                    params.update(json.loads(arg))
                else:
                    params["mode"] = arg
            state = flow.run_step("start", mode=params.get("mode", "good"), task=params.get("task"),
                                  criteria=params.get("criteria"), amount_usdc=params.get("amount_usdc"))
        else:
            state = flow.run_step(step, run_id=arg)
        print(json.dumps(state, default=str))
        return 0
    except Exception as e:  # noqa: BLE001 — surface the failure as JSON for the UI
        print(json.dumps({"error": str(e), "step": step, "run_id": arg}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
