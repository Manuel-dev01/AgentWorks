/**
 * The AgentWorks "escrow chip" mark: chip body (the contract) + vertical escrow
 * seam with a locked node (escrowed USDC, held by neither party) + an A-peak
 * (Client) and a W-valley (Provider). Inlined per-instance so it works anywhere
 * and inherits `color` via currentColor. Ported verbatim from the brand SVG symbol.
 */
export function AwMark({
  size = 34,
  className,
  style,
}: {
  size?: number;
  className?: string;
  style?: React.CSSProperties;
}) {
  return (
    <svg
      className={className}
      width={size}
      height={size}
      viewBox="0 0 100 100"
      style={{ flex: "0 0 auto", ...style }}
      role="img"
      aria-label="AgentWorks mark"
    >
      <rect x="6" y="6" width="88" height="88" rx="20" fill="none" stroke="currentColor" strokeWidth="6" />
      <line x1="50" y1="14" x2="50" y2="42" stroke="currentColor" strokeWidth="4" strokeLinecap="round" />
      <line x1="50" y1="58" x2="50" y2="86" stroke="currentColor" strokeWidth="4" strokeLinecap="round" />
      <rect x="42" y="42" width="16" height="16" rx="4" fill="currentColor" />
      <path d="M20 70 L31 30 L42 70" fill="none" stroke="currentColor" strokeWidth="6" strokeLinejoin="round" strokeLinecap="round" />
      <path d="M58 30 L63.5 70 L69 46 L74.5 70 L80 30" fill="none" stroke="currentColor" strokeWidth="6" strokeLinejoin="round" strokeLinecap="round" />
    </svg>
  );
}
