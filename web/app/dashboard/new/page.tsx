import { Journey } from "../../../components/dashboard/Journey";
import { loadReplay } from "../../../lib/proofs";
import { CFG } from "../../../lib/config";

export const dynamic = "force-dynamic";

export default function NewJobPage() {
  // Live = real agents on Sepolia (localhost only). Otherwise the journey runs as a deterministic
  // replay of a recorded verified run so anyone on the hosted site can walk the whole flow.
  const enabled = CFG.enableLiveRun && process.env.NODE_ENV !== "production";
  const replay = loadReplay();
  return (
    <>
      <div className="head">
        <h1>Post a job — the live journey</h1>
        <p>
          Author a task, then walk it across both agents: the Client posts and escrows, the Provider binds its
          Pact and submits the Irys-anchored deliverable, and the evaluator settles.{" "}
          {enabled ? "Each step signs a real transaction on Ethereum Sepolia." : "This hosted demo replays a verified run — every hash opens on Etherscan; run it locally to drive the agents for real."}
        </p>
      </div>
      <Journey enabled={enabled} replay={replay} />
    </>
  );
}
