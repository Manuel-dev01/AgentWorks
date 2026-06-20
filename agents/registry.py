"""Marketplace participant registry (Phase 6.5).

A POOL of CAW wallets that take roles in the open marketplace. v1 used two hardcoded wallets
(Client, Provider); this generalizes to N. Each participant binds a TEMPLATE Pact (the
permission/isolation boundary) when it acts.

Sources, in order:
  1. the canonical Client (CAW_CLIENT_*) and Provider (CAW_PROVIDER_*) from config,
  2. auto-discovered extra providers CAW_PROVIDER2_*, CAW_PROVIDER3_*, … (WALLET_ID/API_KEY/ADDRESS),
  3. optional external participants from `agents/registry.local.json` (the documented self-service
     path - users bring their own CAW wallet; that file holds keys so it is gitignored, never committed).

This invents NO new SDK surface: a participant is just an (api_key, wallet_uuid) pair driven through
the existing CawWallet, and onboarding = submit_pact(template) + wait_pact_active (agents/caw/client.py).
"""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass
from pathlib import Path

import config
import pacts
from caw import CawWallet

# External participants' credentials. On a host with ephemeral storage (e.g. Railway), set AGENT_DATA_DIR
# to a mounted volume so registrations persist across restarts; default is the in-repo path for local dev.
# Always gitignored (holds api_keys) - never committed.
_LOCAL_FILE = (Path(os.environ["AGENT_DATA_DIR"]) / "registry.local.json") if os.environ.get("AGENT_DATA_DIR") \
    else (Path(__file__).resolve().parent / "registry.local.json")


@dataclass(frozen=True)
class Participant:
    name: str
    role: str        # 'client' | 'provider' | 'evaluator'  (committee member)
    wallet_id: str
    api_key: str
    address: str
    tx_cap: int = 0  # 0 → use the template's default cap

    def template(self) -> dict:
        """The scoped Pact spec this participant binds, pinned to the live v4 escrow."""
        if self.role == "provider":
            return pacts.provider_pact(escrow=config.ESCROW_V4_ADDRESS, tx_cap=self.tx_cap or 20)
        if self.role == "evaluator":
            return pacts.evaluator_pact(escrow=config.ESCROW_V4_ADDRESS, tx_cap=self.tx_cap or 20)
        return pacts.client_escrow_pact(escrow=config.ESCROW_V4_ADDRESS, tx_cap=self.tx_cap or 50)

    def public(self) -> dict:
        """Non-secret view (never includes api_key) - safe to log / return over HTTP."""
        return {"name": self.name, "role": self.role, "wallet_id": self.wallet_id,
                "address": self.address}


def _from_env(prefix: str, *, name: str, role: str) -> Participant | None:
    wid = os.environ.get(f"CAW_{prefix}_WALLET_ID")
    key = os.environ.get(f"CAW_{prefix}_API_KEY")
    addr = os.environ.get(f"CAW_{prefix}_ADDRESS")
    if not (wid and key and addr):
        return None
    return Participant(name=name, role=role, wallet_id=wid, api_key=key, address=addr)


def _from_local_file() -> list[Participant]:
    if not _LOCAL_FILE.exists():
        return []
    try:
        rows = json.loads(_LOCAL_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []
    out: list[Participant] = []
    for r in rows if isinstance(rows, list) else []:
        if r.get("wallet_id") and r.get("api_key") and r.get("address"):
            out.append(Participant(
                name=r.get("name", r["address"][:10]), role=r.get("role", "provider"),
                wallet_id=r["wallet_id"], api_key=r["api_key"], address=r["address"],
                tx_cap=int(r.get("tx_cap", 0)),
            ))
    return out


def load_pool() -> list[Participant]:
    """The marketplace participant pool. Always includes the canonical Client + Provider; adds any
    CAW_PROVIDER{N}_* found in env, plus external participants from registry.local.json."""
    pool: list[Participant] = []
    client = _from_env("CLIENT", name="Client", role="client")
    if client:
        pool.append(client)
    provider = _from_env("PROVIDER", name="Provider", role="provider")
    if provider:
        pool.append(provider)
        # Extra ADDRESSES on the SAME provider wallet (CAW_PROVIDER_ADDRESS_2, _3, …). A second
        # address is a distinct on-chain msg.sender signed by the same Provider TSS node and bound
        # by the same provider Pact - a genuine second provider for the accept-race without a whole
        # new wallet/daemon. (Public address only; reuses the provider's wallet_id + api_key.)
        n = 2
        while True:
            extra = os.environ.get(f"CAW_PROVIDER_ADDRESS_{n}")
            if not extra:
                break
            pool.append(Participant(name=f"Provider{chr(64 + n)}", role="provider",  # ProviderB, ProviderC, …
                                    wallet_id=provider.wallet_id, api_key=provider.api_key,
                                    address=extra, tx_cap=provider.tx_cap))
            n += 1
    # auto-discover fully separate provider wallets CAW_PROVIDER2_*, CAW_PROVIDER3_*, …
    n = 2
    while True:
        p = _from_env(f"PROVIDER{n}", name=f"Provider{n}", role="provider")
        if p is None:
            break
        pool.append(p)
        n += 1
    pool.extend(_from_local_file())
    return pool


def providers(pool: list[Participant] | None = None) -> list[Participant]:
    return [p for p in (pool or load_pool()) if p.role == "provider"]


def evaluators() -> list[Participant]:
    """The evaluator COMMITTEE: extra addresses on a dedicated evaluator CAW wallet
    (CAW_EVALUATOR_WALLET_ID/_API_KEY + CAW_EVALUATOR_ADDRESS_1.._N), mirroring the provider-race
    pattern (distinct on-chain msg.senders, one TSS node, one Pact). Returns [] if not configured —
    the caller then falls back to externally-funded committee signers. Genuinely independent committees
    come from external operators each running their own evaluator wallet (docs/ARBITRATION.md)."""
    wid = os.environ.get("CAW_EVALUATOR_WALLET_ID")
    key = os.environ.get("CAW_EVALUATOR_API_KEY")
    if not (wid and key):
        return []
    out: list[Participant] = []
    n = 1
    while True:
        addr = os.environ.get(f"CAW_EVALUATOR_ADDRESS_{n}")
        if not addr:
            break
        out.append(Participant(name=f"Evaluator {chr(64 + n)}", role="evaluator",  # Evaluator A, B, C…
                               wallet_id=wid, api_key=key, address=addr))
        n += 1
    return out


def client(pool: list[Participant] | None = None) -> Participant:
    for p in (pool or load_pool()):
        if p.role == "client":
            return p
    raise RuntimeError("no client participant in the registry (set CAW_CLIENT_* in .env)")


# ── onboarding (bind the role's template Pact) ──────────────────────────────

async def _revoke_active(w: CawWallet) -> None:
    try:
        page = await w.list_pacts(status="active")
    except Exception:
        return
    items = page if isinstance(page, list) else (page.get("items", []) if isinstance(page, dict) else [])
    for p in items:
        if isinstance(p, dict) and p.get("status") == "active" and p.get("id"):
            try:
                await w.revoke_pact(p["id"])
            except Exception:
                pass


async def onboard(p: Participant, *, clean: bool = True, timeout: float = 120.0) -> dict:
    """Submit the participant's template Pact and wait until active. Returns a NON-SECRET summary
    (the scoped api_key is never returned/logged)."""
    async with CawWallet(api_url=config.CAW_API_URL, api_key=p.api_key,
                         wallet_uuid=p.wallet_id, name=p.name) as w:
        if clean:
            await _revoke_active(w)
        sub = await w.submit_pact(
            intent=f"{p.role} in the AgentWorks open marketplace",
            spec=p.template(), name=f"mkt-{p.role}-{p.wallet_id[:8]}",
        )
        pact = await w.wait_pact_active(sub.get("pact_id"), timeout=timeout)
        return {
            **p.public(),
            "pact_id": pact.get("id") or sub.get("pact_id"),
            "pact_status": pact.get("status"),
            "has_scoped_key": bool(pact.get("api_key")),
        }


async def register_external(wallet_id: str, api_key: str, address: str,
                            role: str = "provider", name: str | None = None,
                            tx_cap: int = 0) -> dict:
    """Register an external agent in the marketplace. Creates a scoped Pact via CAW, persists the
    participant to registry.local.json, and returns a non-secret summary.

    External agents bring their own CAW wallet (wallet_id + api_key). The platform creates a Pact
    for them using the parameterized template, then they can discover jobs via /marketplace/jobs
    and call acceptJob directly on-chain with their own CAW wallet.
    """
    if role not in ("client", "provider"):
        raise ValueError(f"role must be 'client' or 'provider', got '{role}'")

    # Check if already registered (by wallet_id)
    existing = _from_local_file()
    for p in existing:
        if p.wallet_id == wallet_id:
            # Already registered - just onboard (refresh Pact)
            result = await onboard(p, clean=True)
            return {**result, "already_registered": True}

    p = Participant(
        name=name or f"ext-{address[:10]}",
        role=role,
        wallet_id=wallet_id,
        api_key=api_key,
        address=address,
        tx_cap=tx_cap,
    )

    # Create the Pact
    result = await onboard(p, clean=True)

    # Persist to registry.local.json (gitignored - holds credentials)
    existing.append(p)
    _LOCAL_FILE.parent.mkdir(parents=True, exist_ok=True)
    _LOCAL_FILE.write_text(
        json.dumps([{
            "name": pr.name, "role": pr.role, "wallet_id": pr.wallet_id,
            "api_key": pr.api_key, "address": pr.address, "tx_cap": pr.tx_cap,
        } for pr in existing], indent=2),
        encoding="utf-8",
    )

    return {**result, "already_registered": False}


# ── CLI: print the pool (no secrets); `--onboard` binds each template live ──

def _main() -> None:
    import sys

    pool = load_pool()
    print(json.dumps({
        "escrow_v2": config.ESCROW_V2_ADDRESS,
        "count": len(pool),
        "providers": len(providers(pool)),
        "participants": [p.public() for p in pool],
    }, indent=2))

    if "--onboard" in sys.argv:
        async def run():
            for p in pool:
                try:
                    res = await onboard(p)
                    print("ONBOARDED:", json.dumps(res))
                except Exception as e:  # surface, don't hide
                    print(f"FAILED {p.name}: {type(e).__name__}: {e}")
        asyncio.run(run())


if __name__ == "__main__":
    _main()
