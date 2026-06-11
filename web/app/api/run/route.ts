/** Live-run trigger (additive, guarded). Spawns the verified Python lifecycle and streams
 *  its stdout to the dashboard. Localhost-only. The proof artifacts remain the source of truth; if
 *  this fails the UI keeps rendering the last verified run. */

import { spawn } from "node:child_process";
import path from "node:path";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(req: Request) {
  const host = req.headers.get("host") ?? "";
  const isLocal = /^(localhost|127\.0\.0\.1|\[::1\])(:\d+)?$/.test(host);
  if (!isLocal) return new Response("live run is localhost-only", { status: 403 });
  if (process.env.NEXT_PUBLIC_ENABLE_LIVE_RUN === "0") return new Response("live run disabled", { status: 403 });

  let mode = "good";
  try {
    const body = await req.json();
    if (body?.mode === "bad") mode = "bad";
  } catch {
    /* default good */
  }

  const repoRoot = path.resolve(process.cwd(), "..");
  const py = path.join(repoRoot, "agents", ".venv", "Scripts", "python.exe");
  const script = path.join(repoRoot, "agents", "scripts", "phase5_demo.py");
  const child = spawn(py, [script, mode], { cwd: repoRoot, env: { ...process.env, PYTHONUNBUFFERED: "1" } });

  const enc = new TextEncoder();
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      const push = (d: Buffer) => {
        try {
          controller.enqueue(enc.encode(d.toString()));
        } catch {
          /* stream closed */
        }
      };
      child.stdout.on("data", push);
      child.stderr.on("data", push);
      child.on("error", (e) => {
        push(Buffer.from(`\n[spawn error] ${e.message} — is agents/.venv set up?`));
        controller.close();
      });
      child.on("close", (code) => {
        push(Buffer.from(`\n[exit ${code}]`));
        controller.close();
      });
    },
    cancel() {
      child.kill();
    },
  });

  return new Response(stream, {
    headers: { "content-type": "text/plain; charset=utf-8", "cache-control": "no-store" },
  });
}
