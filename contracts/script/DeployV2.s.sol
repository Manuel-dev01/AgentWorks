// SPDX-License-Identifier: MIT
pragma solidity 0.8.28;

import {Script, console2} from "forge-std/Script.sol";
import {AgentWorksEscrowV2} from "../src/AgentWorksEscrowV2.sol";

/// @notice Deploys AgentWorksEscrowV2 (open marketplace) bound to USDC_TOKEN_ADDRESS.
/// @dev Env: DEPLOYER_PRIVATE_KEY, USDC_TOKEN_ADDRESS (see repo-root .env).
contract DeployV2 is Script {
    function run() external returns (AgentWorksEscrowV2 escrow) {
        address token = vm.envAddress("USDC_TOKEN_ADDRESS");
        uint256 pk = vm.envUint("DEPLOYER_PRIVATE_KEY");

        vm.startBroadcast(pk);
        escrow = new AgentWorksEscrowV2(token);
        vm.stopBroadcast();

        console2.log("AgentWorksEscrowV2:", address(escrow));
        console2.log("settlement token:", token);
    }
}
