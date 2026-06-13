"""Genuine agent reasoning layer (DeepSeek via the OpenAI-compatible API).

The agents call these to actually DECIDE at the economic decision points (criterion 1):
  - client_decide_fund: is this task worth funding within policy/budget?
  - provider_do_task:    actually perform the task (produce the deliverable).
  - evaluate:            the real accept/reject judgment on the deliverable.

CAW Pacts remain the hard boundary regardless of what the LLM decides - that's the safety story.
Every call is logged (decision + rationale) so the demo's audit trail is legible.
"""

from __future__ import annotations

import json
import logging

from openai import OpenAI

import config

log = logging.getLogger("reason")

_client: OpenAI | None = None


def _llm() -> OpenAI:
    global _client
    if _client is None:
        if not config.LLM_API_KEY:
            raise RuntimeError("LLM_API_KEY is empty - paste your DeepSeek key into .env")
        _client = OpenAI(api_key=config.LLM_API_KEY, base_url=config.LLM_BASE_URL)
    return _client


# DeepSeek's deepseek-v4-flash is a REASONING model: chain-of-thought goes to reasoning_content
# and consumes completion tokens, so budgets must be generous or `content` comes back empty.
def _chat(system: str, user: str, *, json_mode: bool = False, max_tokens: int = 2000) -> str:
    kwargs = {}
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    resp = _llm().chat.completions.create(
        model=config.LLM_MODEL,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0.2,
        max_tokens=max_tokens,
        **kwargs,
    )
    return resp.choices[0].message.content or ""


def _json(system: str, user: str) -> dict:
    raw = _chat(system, user, json_mode=True)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}")
        return json.loads(raw[start : end + 1])


def smoke() -> str:
    """One-call check that the endpoint + model id work. Returns the model's reply."""
    out = _chat("You are a terse assistant.", "Reply with exactly: OK", max_tokens=200)
    log.info("[reason] smoke model=%s base=%s -> %r", config.LLM_MODEL, config.LLM_BASE_URL, out)
    return out


# ── decision points ──

def client_decide_fund(task: str, price_usdc: float, budget_usdc: float) -> dict:
    system = (
        "You are the Client agent in a trustless escrow marketplace. Decide whether to fund a job. "
        "Consider whether the task is legitimate and the price is reasonable and within budget. "
        'Respond ONLY as JSON: {"fund": true|false, "reason": "<one sentence>"}.'
    )
    user = f"Task: {task}\nPrice: {price_usdc} USDC\nRemaining budget: {budget_usdc} USDC"
    d = _json(system, user)
    log.info("[reason] client_decide_fund -> %s", d)
    return d


def provider_decide_accept(spec: str, reward_usdc: float, *, provider_name: str = "Provider") -> dict:
    """Provider genuinely decides whether to CLAIM an open, funded job (criterion 1).

    In the open marketplace multiple providers see the same job; each reasons independently about
    whether the reward justifies the work. The on-chain acceptJob race then settles who gets it.
    """
    system = (
        "You are a Provider agent in an open, trustless escrow marketplace. An OPEN job has been "
        "funded and any provider may claim it by accepting on-chain. Decide whether YOU should accept "
        "this job: is the task something you can deliver well, and is the reward worth the effort? "
        'Respond ONLY as JSON: {"accept": true|false, "reason": "<one sentence>"}.'
    )
    user = f"Provider: {provider_name}\nTask: {spec}\nReward: {reward_usdc} USDC"
    d = _json(system, user)
    log.info("[reason] provider_decide_accept(%s) -> %s", provider_name, d)
    return d


def provider_do_task(spec: str, *, sabotage: bool = False) -> str:
    if sabotage:
        # Deliberately produce an off-spec deliverable so the evaluator genuinely rejects it.
        system = "You are a lazy contractor. Produce a deliverable that does NOT satisfy the request (wrong topic / wrong form)."
    else:
        system = "You are the Provider agent. Complete the requested task well and concisely. Output only the deliverable."
    out = _chat(system, spec, max_tokens=2000)
    log.info("[reason] provider_do_task(sabotage=%s) -> %r", sabotage, out[:120])
    return out.strip()


def evaluate(spec: str, deliverable: str) -> dict:
    system = (
        "You are the Evaluator in an escrow marketplace. Judge whether the deliverable satisfies the task spec. "
        "Be fair but strict: accept only if it genuinely meets the request. "
        'Respond ONLY as JSON: {"accept": true|false, "reason": "<one sentence>"}.'
    )
    user = f"TASK SPEC:\n{spec}\n\nDELIVERABLE:\n{deliverable}"
    d = _json(system, user)
    log.info("[reason] evaluate -> %s", d)
    return d
