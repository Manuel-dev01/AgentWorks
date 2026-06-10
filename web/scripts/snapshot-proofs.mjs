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
// marker so the loader can tell a snapshot exists even if a source dir was empty
writeFileSync(path.join(WEB, "data", ".snapshot"), new Date().toISOString());
console.log(`[snapshot] copied ${copied} artifact(s) into web/data/`);
