"""Shared config for the AgentWorks agents. Single source of env truth.

Loads the repo-root .env. Holds CAW credentials, Ethereum Sepolia chain/token ids
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

# Ethereum Sepolia CAW ids (the project switched off Base Sepolia in Phase 2; .env overrides these).
CHAIN_ID = os.environ.get("CAW_CHAIN_ID", "SETH")
NATIVE_TOKEN_ID = os.environ.get("CAW_NATIVE_TOKEN_ID", "SETH")
USDC_TOKEN_ID = os.environ.get("CAW_USDC_TOKEN_ID", "SETH_USDC")

# On-chain (Ethereum Sepolia)
RPC_URL = os.environ.get("RPC_URL", "https://sepolia.drpc.org")
ESCROW_ADDRESS = os.environ.get("ESCROW_CONTRACT_ADDRESS", "")  # v1 (closed 1:1) - legacy
# v2 open-marketplace escrow (Phase 6.5). Defaults to the deployed+verified address so the v2
# agents/dashboard work out of the box; override in .env to point at a different deployment.
ESCROW_V2_ADDRESS = os.environ.get("ESCROW_V2_CONTRACT_ADDRESS", "0xD6cB413c0E4a5839Fd4B02aFFeBF65e6868726b9")
USDC_ADDRESS = os.environ.get("USDC_TOKEN_ADDRESS", "")
EXPLORER_TX = "https://sepolia.etherscan.io/tx/{}"
EXPLORER_ADDR = "https://sepolia.etherscan.io/address/{}"


# LLM (agent reasoning) - DeepSeek via OpenAI-compatible API
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_MODEL = os.environ.get("LLM_MODEL", "deepseek-v4-flash")
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.deepseek.com")


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
