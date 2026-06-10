import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AgentWorks — Trustless escrow for agents that transact",
  description:
    "A trustless two-agent job-escrow marketplace. A Client Agent escrows USDC, a Provider Agent delivers and proves it on-chain, and the contract settles — authority by Cobo Agentic Wallet, settlement by a neutral contract.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        {/* Fonts via CDN link (matches the design source; no build-time fetch). */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link
          href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
