import "../dashboard.css";
import { Shell } from "../../components/dashboard/Shell";
import { usdcBalance } from "../../lib/chain";
import { CFG } from "../../lib/config";

// Live balances read per navigation; degrades to "—" if RPC is unreachable.
export const dynamic = "force-dynamic";

export default async function DashboardLayout({ children }: { children: React.ReactNode }) {
  const [clientBal, providerBal] = await Promise.all([usdcBalance(CFG.clientCaw), usdcBalance(CFG.providerCaw)]);
  return (
    <div className="dp">
      <Shell clientBal={clientBal} providerBal={providerBal} />
      <main className="wrap main">{children}</main>
    </div>
  );
}
