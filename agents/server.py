"""FastAPI control surface for the autonomous agent service (Phase 6.5.4).

Cloud-deployable HTTP front for the autonomous open-marketplace agents. The dashboard (Vercel)
calls this instead of spawning local processes. The service talks to the CAW cloud API over HTTPS;
on-chain SIGNING happens via the TSS node connected to the CAW relay (run alongside, or on a host
you control — see docs/DEPLOY_AGENTS.md). This process holds NO key material.

Endpoints:
  GET  /health           liveness + config summary (escrow, providers, whether a run is active)
  GET  /board            current open-job listings (off-chain marketplace listing)
  GET  /runs             all run artifacts (settled + in-progress), newest first
  GET  /runs/{job_id}    one run artifact
  POST /trigger          launch an autonomous run; guarded by AGENT_TRIGGER_TOKEN if that env is set

A single run executes at a time (the autonomous loops settle `max_jobs` then return).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import autonomous
import config
import registry

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
log = logging.getLogger("server")

app = FastAPI(title="AgentWorks autonomous agent service", version="6.5")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o for o in os.environ.get("AGENT_CORS_ORIGINS", "*").split(",") if o],
    allow_methods=["*"], allow_headers=["*"],
)

_TOKEN = os.environ.get("AGENT_TRIGGER_TOKEN", "")  # if set, /trigger requires it

# single-run guard
_state: dict = {"active": False, "run_id": None, "started_at": None, "mode": None, "last_error": None}
_task: asyncio.Task | None = None


class TriggerBody(BaseModel):
    task: str | None = None
    criteria: str = ""
    mode: str = "good"          # 'good' | 'bad'
    reward_usdc: float = 5.0
    max_jobs: int = 1


def _artifacts() -> list[dict]:
    out = []
    if autonomous.RUNS_DIR.exists():
        for p in autonomous.RUNS_DIR.glob("*.json"):
            try:
                out.append(json.loads(p.read_text(encoding="utf-8")))
            except Exception:
                pass
    out.sort(key=lambda r: r.get("job_id", 0), reverse=True)
    return out


@app.get("/health")
def health() -> dict:
    pool = registry.load_pool()
    return {
        "status": "ok",
        "chain_id": config.CHAIN_ID,
        "escrow_v2": config.ESCROW_V2_ADDRESS,
        "usdc": config.USDC_ADDRESS,
        "participants": [p.public() for p in pool],
        "providers": len(registry.providers(pool)),
        "run": {k: _state[k] for k in ("active", "run_id", "mode", "started_at")},
        "trigger_protected": bool(_TOKEN),
    }


@app.get("/board")
def board() -> dict:
    return autonomous._read_board()


@app.get("/runs")
def runs() -> list[dict]:
    return _artifacts()


@app.get("/runs/{job_id}")
def run_one(job_id: int) -> dict:
    for r in _artifacts():
        if r.get("job_id") == job_id:
            return r
    raise HTTPException(status_code=404, detail=f"no run artifact for job {job_id}")


async def _run(body: TriggerBody) -> None:
    try:
        tasks = ([{"task": body.task, "criteria": body.criteria}] if body.task
                 else autonomous._default_tasks())
        out = await autonomous.run_market(tasks, mode=body.mode, reward_usdc=body.reward_usdc,
                                          max_jobs=body.max_jobs)
        _state["run_id"] = out.get("run_id")
        log.info("[server] run complete: %s", out.get("run_id"))
    except Exception as e:  # surface, don't hide
        _state["last_error"] = f"{type(e).__name__}: {e}"
        log.exception("[server] run failed")
    finally:
        _state["active"] = False


@app.post("/trigger")
async def trigger(body: TriggerBody, authorization: str = Header(default="")) -> dict:
    if _TOKEN and authorization != f"Bearer {_TOKEN}":
        raise HTTPException(status_code=401, detail="missing/invalid AGENT_TRIGGER_TOKEN")
    if _state["active"]:
        raise HTTPException(status_code=409, detail="a run is already active")
    if body.mode not in ("good", "bad"):
        raise HTTPException(status_code=400, detail="mode must be 'good' or 'bad'")
    global _task
    _state.update({"active": True, "run_id": None, "started_at": int(time.time()),
                   "mode": body.mode, "last_error": None})
    _task = asyncio.create_task(_run(body))
    return {"accepted": True, "mode": body.mode, "reward_usdc": body.reward_usdc,
            "max_jobs": body.max_jobs, "poll": "/runs"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
