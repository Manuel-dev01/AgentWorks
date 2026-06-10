/** Live per-step flow trigger. Spawns the resumable Python orchestrator (agents/scripts/flow_step.py)
 *  for one step and returns its JSON state. Localhost-only; disabled in production (Vercel serverless
 *  can't run the venv). The Marketplace's verified artifacts remain the fallback if a step fails. */

import { spawn } from "node:child_process";
import path from "node:path";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const STEPS = new Set(["start", "post", "accept", "submit", "settle"]);

export async function POST(req: Request) {
  const host = req.headers.get("host") ?? "";
  if (!/^(localhost|127\.0\.0\.1|\[::1\])(:\d+)?$/.test(host))
    return Response.json({ error: "live flow is localhost-only" }, { status: 403 });
  if (process.env.NODE_ENV === "production")
    return Response.json({ error: "live flow disabled in production" }, { status: 403 });

  let step = "", runId: string | undefined, mode = "good";
  try {
    const body = await req.json();
    step = String(body?.step ?? "");
    if (body?.runId) runId = String(body.runId);
    if (body?.mode === "bad") mode = "bad";
  } catch {
    /* ignore */
  }
  if (!STEPS.has(step)) return Response.json({ error: `unknown step '${step}'` }, { status: 400 });
  if (step !== "start" && !runId) return Response.json({ error: "step requires runId" }, { status: 400 });

  const repoRoot = path.resolve(process.cwd(), "..");
  const py = path.join(repoRoot, "agents", ".venv", "Scripts", "python.exe");
  const script = path.join(repoRoot, "agents", "scripts", "flow_step.py");
  const args = step === "start" ? [script, "start", mode] : [script, step, runId!];

  return await new Promise<Response>((resolve) => {
    const child = spawn(py, args, { cwd: repoRoot, env: { ...process.env, PYTHONUNBUFFERED: "1" } });
    let out = "", err = "";
    const timer = setTimeout(() => {
      child.kill();
      resolve(Response.json({ error: "step timed out (300s)", step }, { status: 504 }));
    }, 300_000);

    child.stdout.on("data", (d) => (out += d.toString()));
    child.stderr.on("data", (d) => (err += d.toString()));
    child.on("error", (e) => {
      clearTimeout(timer);
      resolve(Response.json({ error: `spawn failed: ${e.message} — is agents/.venv set up?`, step }, { status: 500 }));
    });
    child.on("close", (code) => {
      clearTimeout(timer);
      // The state JSON is the last non-empty stdout line.
      const line = out.trim().split(/\r?\n/).filter(Boolean).pop() ?? "";
      try {
        const state = JSON.parse(line);
        resolve(Response.json(state, { status: state.error ? 500 : 200 }));
      } catch {
        resolve(Response.json({ error: `bad step output (exit ${code})`, stderr: err.slice(-500), raw: line.slice(0, 300), step }, { status: 500 }));
      }
    });
  });
}
