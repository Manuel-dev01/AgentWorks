"""Shared config for the AgentWorks agents. Single source of env truth.

Loads the repo-root .env. Holds CAW credentials, Base Sepolia chain/token ids
(confirmed in Phase 2), and on-chain contract addresses.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(REPO_ROOT / ".env")


def _req(name: str) -> str:
    v = os.environ.get(name)
    if not v:
        raise RuntimeError(f"Missing required env var: {name} (see repo-root .env)")
    return v


@dataclass(frozen=True)
class Agent:
    name: str
    wallet_id: str
    api_key: str
    address: str


# CAW API
CAW_API_URL = os.environ.get("AGENT_WALLET_API_URL", "https://api.agenticwallet.cobo.com")

# Base Sepolia ids — confirmed live in Phase 2 via `caw meta`.
CHAIN_ID = os.environ.get("CAW_CHAIN_ID", "TBASE_SETH")
NATIVE_TOKEN_ID = os.environ.get("CAW_NATIVE_TOKEN_ID", "TBASE_SETH")
USDC_TOKEN_ID = os.environ.get("CAW_USDC_TOKEN_ID", "TBASE_USDC")

# On-chain (Base Sepolia)
ESCROW_ADDRESS = os.environ.get("ESCROW_CONTRACT_ADDRESS", "")
USDC_ADDRESS = os.environ.get("USDC_TOKEN_ADDRESS", "")
EXPLORER_TX = "https://sepolia.basescan.org/tx/{}"
EXPLORER_ADDR = "https://sepolia.basescan.org/address/{}"


def client_agent() -> Agent:
    return Agent(
        name="Client",
        wallet_id=_req("CAW_CLIENT_WALLET_ID"),
        api_key=_req("CAW_CLIENT_API_KEY"),
        address=_req("CAW_CLIENT_ADDRESS"),
    )


def provider_agent() -> Agent:
    return Agent(
        name="Provider",
        wallet_id=_req("CAW_PROVIDER_WALLET_ID"),
        api_key=_req("CAW_PROVIDER_API_KEY"),
        address=_req("CAW_PROVIDER_ADDRESS"),
    )
