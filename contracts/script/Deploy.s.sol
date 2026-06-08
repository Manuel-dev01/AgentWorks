// SPDX-License-Identifier: MIT
pragma solidity 0.8.28;

import {Script, console2} from "forge-std/Script.sol";
import {AgentWorksEscrow} from "../src/AgentWorksEscrow.sol";

/// @notice Deploys AgentWorksEscrow bound to USDC_TOKEN_ADDRESS.
/// @dev Env: DEPLOYER_PRIVATE_KEY, USDC_TOKEN_ADDRESS (see repo-root .env).
contract Deploy is Script {
    function run() external returns (AgentWorksEscrow escrow) {
        address token = vm.envAddress("USDC_TOKEN_ADDRESS");
        uint256 pk = vm.envUint("DEPLOYER_PRIVATE_KEY");

        vm.startBroadcast(pk);
        escrow = new AgentWorksEscrow(token);
        vm.stopBroadcast();

        console2.log("AgentWorksEscrow:", address(escrow));
        console2.log("settlement token:", token);
    }
}
