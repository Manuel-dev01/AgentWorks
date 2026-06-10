/** Public testnet config surfaced by the dashboard. No secrets — all values are public
 *  (deployed contracts, public RPC, explorer). Defaults mirror docs/FACTS.md + docs/STATUS.md. */

const env = (k: string, d: string) => (process.env[k] && process.env[k]!.length > 0 ? process.env[k]! : d);

export const CFG = {
  chainId: 11155111,
  rpc: env("NEXT_PUBLIC_RPC_URL", "https://sepolia.drpc.org"),
  escrow: env("NEXT_PUBLIC_ESCROW_ADDRESS", "0x812BcEEc2De8C8aC71C7af7A8E2d4467E65Fdf18") as `0x${string}`,
  usdc: env("NEXT_PUBLIC_USDC_ADDRESS", "0x4C4D1223BcC47E380CF4C37652EaDFe10A9Fd910") as `0x${string}`,
  clientCaw: env("NEXT_PUBLIC_CLIENT_CAW", "0x6dfbd0ac9feb5bb9a9ffeaf54df203c1633c1ddd") as `0x${string}`,
  providerCaw: env("NEXT_PUBLIC_PROVIDER_CAW", "0xef9349b3273b1a54faaf701231f499fe0282e643") as `0x${string}`,
  explorer: env("NEXT_PUBLIC_EXPLORER_BASE", "https://sepolia.etherscan.io"),
  irysGateway: env("NEXT_PUBLIC_IRYS_GATEWAY", "https://devnet.irys.xyz"),
  enableLiveRun: env("NEXT_PUBLIC_ENABLE_LIVE_RUN", "1") !== "0",
};

export const txUrl = (h: string) => `${CFG.explorer}/tx/${h}`;
export const addrUrl = (a: string) => `${CFG.explorer}/address/${a}`;
export const irysUrl = (id: string) => `${CFG.irysGateway}/${id}`;

/** 0x1234…cdef — short form for addresses/hashes (mono in the UI). */
export const shortHex = (s: string, head = 6, tail = 4) =>
  !s ? "" : s.length > head + tail + 1 ? `${s.slice(0, head)}…${s.slice(-tail)}` : s;
