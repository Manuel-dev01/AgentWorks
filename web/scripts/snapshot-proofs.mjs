// Snapshot the VERIFIED proof artifacts + literal Pact JSON into web/data/ so the dashboard works
// inside a Vercel serverless bundle (Next only traces files under the project root — sibling dirs
// like ../agents are NOT bundled). Runs as predev/prebuild; idempotent. Local dev also falls back to
// reading the sibling dirs directly (see lib/proofs.ts), so a missing snapshot never breaks dev.

import { existsSync, mkdirSync, readdirSync, copyFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const WEB = path.resolve(__dirname, "..");
const REPO = path.resolve(WEB, "..");

const jobs = [
  { from: path.join(REPO, "agents", "scripts"), to: path.join(WEB, "data", "proofs"), match: (f) => f.endsWith("_proof.json") },
  { from: path.join(REPO, "docs", "pacts"), to: path.join(WEB, "data", "pacts"), match: (f) => f.endsWith(".json") },
  { from: path.join(REPO, "agents", "scripts", ".flow"), to: path.join(WEB, "data", "flows"), match: (f) => f.endsWith(".json") },
  // verified autonomous open-marketplace runs (seed the live board's track record)
  { from: path.join(REPO, "agents", "scripts", ".market", "runs"), to: path.join(WEB, "data", "market"), match: (f) => /^\d+\.json$/.test(f) },
];

let copied = 0;
for (const { from, to, match } of jobs) {
  mkdirSync(to, { recursive: true });
  if (!existsSync(from)) {
    console.log(`[snapshot] source absent, skipping: ${from}`);
    continue;
  }
  for (const f of readdirSync(from).filter(match)) {
    copyFileSync(path.join(from, f), path.join(to, f));
    copied++;
  }
}
// Best-effort: pull the deployed agent service's run artifacts so cloud-triggered runs (#7/#8…) bake
// into the hosted history even when the backend later sleeps. Never fails the build.
async function snapshotAgentRuns() {
  const base = (process.env.NEXT_PUBLIC_AGENT_API || "https://insightful-wisdom-production-5c62.up.railway.app").replace(/\/$/, "");
  const out = path.join(WEB, "data", "market");
  try {
    mkdirSync(out, { recursive: true });
    const ctl = new AbortController();
    const t = setTimeout(() => ctl.abort(), 12000);
    const res = await fetch(`${base}/runs`, { signal: ctl.signal });
    clearTimeout(t);
    if (!res.ok) { console.log(`[snapshot] agent /runs ${res.status} — skipping cloud runs`); return; }
    const runs = await res.json();
    let n = 0;
    for (const r of Array.isArray(runs) ? runs : []) {
      if (typeof r?.job_id === "number") {
        writeFileSync(path.join(out, `${r.job_id}.json`), JSON.stringify(r, null, 2));
        n++;
      }
    }
    console.log(`[snapshot] pulled ${n} cloud run(s) from ${base}`);
  } catch (e) {
    console.log(`[snapshot] agent service unreachable (${e?.name || "error"}) — using committed runs only`);
  }
}

await snapshotAgentRuns();

// marker so the loader can tell a snapshot exists even if a source dir was empty
writeFileSync(path.join(WEB, "data", ".snapshot"), new Date().toISOString());
console.log(`[snapshot] copied ${copied} artifact(s) into web/data/`);
