/** Lifecycle state badge. The five states map 1:1 to the brand lifecycle palette. */
export type BadgeState = "open" | "escrow" | "work" | "settled" | "reclaim";

const LABELS: Record<BadgeState, string> = {
  open: "Posted",
  escrow: "Escrowed",
  work: "In progress",
  settled: "Settled",
  reclaim: "Reclaimed",
};

export function Badge({ state, label }: { state: BadgeState; label?: string }) {
  return (
    <span className={`badge b-${state}`}>
      <span className="bd" />
      {label ?? LABELS[state]}
    </span>
  );
}
