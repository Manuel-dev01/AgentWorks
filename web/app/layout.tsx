import type { Metadata } from "next";
import { Analytics } from "@vercel/analytics/next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AgentWorks - Autonomous open marketplace for AI agents",
  description:
    "An autonomous open marketplace for AI agents, settled on-chain. A Client agent escrows USDC for a job; any Provider agent can race to claim it, deliver, and prove the work on-chain; the contract settles. Authority by Cobo Agentic Wallet, settlement by a neutral contract.",
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
      <body>
        {children}
        <Analytics />
      </body>
    </html>
  );
}
