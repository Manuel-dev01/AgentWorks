// SPDX-License-Identifier: MIT
pragma solidity 0.8.28;

import {Script, console2} from "forge-std/Script.sol";
import {AgentWorksEscrowV3} from "../src/AgentWorksEscrowV3.sol";

/// @notice Deploys AgentWorksEscrowV3 (open marketplace, sealed commit-reveal accept) bound to
///         USDC_TOKEN_ADDRESS with the configured reveal delay/window.
/// @dev Env: DEPLOYER_PRIVATE_KEY, USDC_TOKEN_ADDRESS, and optionally REVEAL_DELAY_BLOCKS (default 1)
///      and REVEAL_WINDOW_BLOCKS (default 256). The Sepolia demo uses delay=1 (~12s) so the mechanism
///      is provable in a live run, with a wide window so a reveal never expires while CAW's TSS relay
///      signs+broadcasts the second tx. Production should use delay >= 2.
contract DeployV3 is Script {
    function run() external returns (AgentWorksEscrowV3 escrow) {
        address token = vm.envAddress("USDC_TOKEN_ADDRESS");
        uint256 pk = vm.envUint("DEPLOYER_PRIVATE_KEY");
        uint64 delayBlocks = uint64(vm.envOr("REVEAL_DELAY_BLOCKS", uint256(1)));
        uint64 windowBlocks = uint64(vm.envOr("REVEAL_WINDOW_BLOCKS", uint256(256)));

        vm.startBroadcast(pk);
        escrow = new AgentWorksEscrowV3(token, delayBlocks, windowBlocks);
        vm.stopBroadcast();

        console2.log("AgentWorksEscrowV3:", address(escrow));
        console2.log("settlement token:", token);
        console2.log("revealDelayBlocks:", delayBlocks);
        console2.log("revealWindowBlocks:", windowBlocks);
    }
}
