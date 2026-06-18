/** Minimal ABIs for read-only dashboard enrichment. Mirrors contracts/src/AgentWorksEscrow.sol. */

export const escrowAbi = [
  {
    type: "function",
    name: "getJob",
    stateMutability: "view",
    inputs: [{ name: "jobId", type: "uint256" }],
    outputs: [
      {
        name: "",
        type: "tuple",
        components: [
          { name: "client", type: "address" },
          { name: "provider", type: "address" },
          { name: "evaluator", type: "address" },
          { name: "amount", type: "uint256" },
          { name: "specHash", type: "bytes32" },
          { name: "deliverableHash", type: "bytes32" },
          { name: "irysId", type: "string" },
          { name: "deadline", type: "uint64" },
          { name: "status", type: "uint8" },
        ],
      },
    ],
  },
  { type: "function", name: "nextJobId", stateMutability: "view", inputs: [], outputs: [{ type: "uint256" }] },
  // settlement events (jobId indexed) — let the dashboard recover the settle tx + outcome from chain
  // for jobs that have no run artifact (e.g. MCP-settled jobs).
  {
    type: "event", name: "JobCompleted",
    inputs: [
      { name: "jobId", type: "uint256", indexed: true },
      { name: "provider", type: "address", indexed: true },
      { name: "amount", type: "uint256", indexed: false },
    ],
  },
  {
    type: "event", name: "JobRejected",
    inputs: [
      { name: "jobId", type: "uint256", indexed: true },
      { name: "client", type: "address", indexed: true },
      { name: "amount", type: "uint256", indexed: false },
    ],
  },
  {
    type: "event", name: "RefundClaimed",
    inputs: [
      { name: "jobId", type: "uint256", indexed: true },
      { name: "client", type: "address", indexed: true },
      { name: "amount", type: "uint256", indexed: false },
    ],
  },
] as const;

/** Block the v2 open-marketplace escrow was deployed at — lower bound for settlement-event log scans. */
export const ESCROW_V2_FROM_BLOCK = 11035232n;

export const erc20Abi = [
  { type: "function", name: "balanceOf", stateMutability: "view", inputs: [{ name: "a", type: "address" }], outputs: [{ type: "uint256" }] },
  { type: "function", name: "decimals", stateMutability: "view", inputs: [], outputs: [{ type: "uint8" }] },
] as const;

/** v1 Status enum index → human label (matches AgentWorksEscrow.sol). */
export const STATUS_LABELS = ["None", "Created", "Funded", "Submitted", "Completed", "Rejected", "Refunded"] as const;

/** v2 Status enum index → human label (matches AgentWorksEscrowV2.sol — adds Open + Accepted). */
export const STATUS_LABELS_V2 = ["None", "Open", "Funded", "Accepted", "Submitted", "Completed", "Rejected", "Refunded"] as const;
