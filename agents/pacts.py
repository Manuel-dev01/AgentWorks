"""Scoped CAW Pact specs — the literal risk-boundary policy (judging criterion 5).

These are the authority boundaries each agent operates within. CAW enforces them server-side;
nothing the agent (or a prompt-injection) does can exceed them. Rendered JSON is written to
docs/pacts/ as first-class deliverables for the risk-boundary doc.

Verified spec shape (docs/FACTS.md): effect "allow" only; block via deny_if; when.target_in is the
contract allowlist; deny_if.usage_limits.rolling_24h.tx_count_gt caps tx count; deny_if.amount_gt
caps transfer amount.
"""

from __future__ import annotations

import json
from pathlib import Path

import config

CHAIN = config.CHAIN_ID
REPO_ROOT = Path(__file__).resolve().parents[1]


def _completion() -> list[dict]:
    return [{"type": "time_elapsed", "threshold": "86400"}]


def client_escrow_pact() -> dict:
    """Client may ONLY contract_call the escrow + USDC contracts, capped at 50 tx/24h."""
    return {
        "policies": [{
            "name": "client-escrow-allowlist",
            "type": "contract_call",
            "rules": {
                "effect": "allow",
                "when": {"chain_in": [CHAIN], "target_in": [
                    {"chain_id": CHAIN, "contract_addr": config.ESCROW_ADDRESS},
                    {"chain_id": CHAIN, "contract_addr": config.USDC_ADDRESS},
                ]},
                "deny_if": {"usage_limits": {"rolling_24h": {"tx_count_gt": 50}}},
            },
        }],
        "completion_conditions": _completion(),
    }


def provider_pact() -> dict:
    """Provider may ONLY contract_call the escrow contract, capped at 20 tx/24h."""
    return {
        "policies": [{
            "name": "provider-escrow-allowlist",
            "type": "contract_call",
            "rules": {
                "effect": "allow",
                "when": {"chain_in": [CHAIN], "target_in": [
                    {"chain_id": CHAIN, "contract_addr": config.ESCROW_ADDRESS},
                ]},
                "deny_if": {"usage_limits": {"rolling_24h": {"tx_count_gt": 20}}},
            },
        }],
        "completion_conditions": _completion(),
    }


def client_budget_transfer_pact(cap: str = "0.001") -> dict:
    """Budget cap: Client may transfer native gas up to `cap`; anything larger is DENIED."""
    return {
        "policies": [{
            "name": "client-budget-cap",
            "type": "transfer",
            "rules": {
                "effect": "allow",
                "when": {"chain_in": [CHAIN],
                         "token_in": [{"chain_id": CHAIN, "token_id": config.NATIVE_TOKEN_ID}]},
                "deny_if": {"amount_gt": cap},
            },
        }],
        "completion_conditions": _completion(),
    }


def review_pact(review_amount_gt: str = "0.0005") -> dict:
    """Soft-review: native transfers above the threshold require owner approval (review_if)."""
    return {
        "policies": [{
            "name": "client-review-threshold",
            "type": "transfer",
            "rules": {
                "effect": "allow",
                "when": {"chain_in": [CHAIN],
                         "token_in": [{"chain_id": CHAIN, "token_id": config.NATIVE_TOKEN_ID}]},
                "review_if": {"amount_gt": review_amount_gt},
            },
        }],
        "completion_conditions": _completion(),
    }


def dump_all() -> Path:
    """Write the rendered pact JSONs to docs/pacts/ for the risk-boundary deliverable."""
    out = REPO_ROOT / "docs" / "pacts"
    out.mkdir(parents=True, exist_ok=True)
    artifacts = {
        "client_escrow_pact.json": client_escrow_pact(),
        "provider_pact.json": provider_pact(),
        "client_budget_transfer_pact.json": client_budget_transfer_pact(),
        "review_pact.json": review_pact(),
    }
    for name, spec in artifacts.items():
        (out / name).write_text(json.dumps(spec, indent=2), encoding="utf-8")
    return out
