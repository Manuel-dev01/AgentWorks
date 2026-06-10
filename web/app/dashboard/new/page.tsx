import { Journey } from "../../../components/dashboard/Journey";
import { CFG } from "../../../lib/config";

export const dynamic = "force-dynamic";

export default function NewJobPage() {
  // Live flow drives the real Python agents — only when running locally (hidden on Vercel).
  const enabled = CFG.enableLiveRun && process.env.NODE_ENV !== "production";
  return (
    <>
      <div className="head">
        <h1>New job — the live journey</h1>
        <p>
          Walk one escrow across both agents, each step a real action on Ethereum Sepolia: the Client posts and
          escrows, the Provider binds its Pact and submits the Irys-anchored deliverable, and the evaluator settles.
        </p>
      </div>
      <Journey enabled={enabled} />
    </>
  );
}
