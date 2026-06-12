import { LiveJob } from "../../../components/dashboard/LiveJob";

export const dynamic = "force-dynamic";

export default function NewJobPage() {
  return (
    <>
      <div className="head">
        <h1>New job — drive the autonomous agents</h1>
        <p>
          Post a task and the deployed agent service takes over: the Client agent reasons about funding and escrows
          USDC, any Provider can race to <code>acceptJob</code>, the winner delivers to Irys, and the evaluator
          settles — payout or refund. Every decision is the agents&apos; own, and every hash opens on Etherscan.
        </p>
      </div>
      <LiveJob />
    </>
  );
}
