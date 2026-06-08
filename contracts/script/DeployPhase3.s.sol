// SPDX-License-Identifier: MIT
pragma solidity 0.8.28;

import {Script, console2} from "forge-std/Script.sol";
import {AgentWorksEscrow} from "../src/AgentWorksEscrow.sol";
import {MockUSDC} from "../src/MockUSDC.sol";

/// @notice Phase 3 stack on Eth Sepolia: deploy MockUSDC, deploy the escrow bound to it,
///         and mint USDC to the Client CAW address so it can fund jobs deterministically.
/// @dev Env: DEPLOYER_PRIVATE_KEY, CAW_CLIENT_ADDRESS.
contract DeployPhase3 is Script {
    function run() external returns (MockUSDC usdc, AgentWorksEscrow escrow) {
        uint256 pk = vm.envUint("DEPLOYER_PRIVATE_KEY");
        address client = vm.envAddress("CAW_CLIENT_ADDRESS");

        vm.startBroadcast(pk);
        usdc = new MockUSDC();
        escrow = new AgentWorksEscrow(address(usdc));
        usdc.mint(client, 1_000_000_000); // 1,000 USDC (6 decimals) to the Client
        vm.stopBroadcast();

        console2.log("MockUSDC:", address(usdc));
        console2.log("Escrow:", address(escrow));
        console2.log("Minted 1000 USDC to client:", client);
    }
}
