/** Server-side proxy for POST /trigger.
 *
 *  The agent service's /trigger spends the platform's CAW wallet, so it's protected by a bearer token
 *  (AGENT_TRIGGER_TOKEN). That token must NEVER reach the browser - so the dashboard posts here (same
 *  origin) and this route, running on the server, attaches the token and forwards to the agent service.
 *
 *  Env (server-only, NOT NEXT_PUBLIC):
 *    AGENT_TRIGGER_TOKEN  - the bearer token the agent service requires on /trigger.
 *    NEXT_PUBLIC_AGENT_API (or AGENT_API) - the agent-service base URL.
 */

import { NextRequest, NextResponse } from "next/server";
import { CFG } from "../../../lib/config";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

// Single source of truth for the agent-service URL (CFG.agentApi carries the default Railway URL, so this
// works even when NEXT_PUBLIC_AGENT_API isn't set in the environment).
const BASE = CFG.agentApi;
const TOKEN = process.env.AGENT_TRIGGER_TOKEN || "";

export async function POST(req: NextRequest) {
  if (!BASE) {
    return NextResponse.json({ ok: false, error: "agent service not configured" }, { status: 503 });
  }
  let body: unknown = {};
  try {
    body = await req.json();
  } catch {
    /* empty body is fine - the agent service applies its own defaults */
  }
  try {
    const ctl = new AbortController();
    const t = setTimeout(() => ctl.abort(), 15000);
    const r = await fetch(`${BASE}/trigger`, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        ...(TOKEN ? { authorization: `Bearer ${TOKEN}` } : {}),
      },
      body: JSON.stringify(body ?? {}),
      signal: ctl.signal,
      cache: "no-store",
    });
    clearTimeout(t);
    const data = await r.json().catch(() => null);
    return NextResponse.json(data ?? { ok: r.ok }, { status: r.status });
  } catch (e) {
    return NextResponse.json(
      { ok: false, error: e instanceof Error ? e.message : "network error" },
      { status: 502 },
    );
  }
}
