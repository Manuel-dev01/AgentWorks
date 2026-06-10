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
] as const;

export const erc20Abi = [
  { type: "function", name: "balanceOf", stateMutability: "view", inputs: [{ name: "a", type: "address" }], outputs: [{ type: "uint256" }] },
  { type: "function", name: "decimals", stateMutability: "view", inputs: [], outputs: [{ type: "uint8" }] },
] as const;

/** Status enum index → human label (matches the Solidity `Status` enum). */
export const STATUS_LABELS = ["None", "Created", "Funded", "Submitted", "Completed", "Rejected", "Refunded"] as const;
