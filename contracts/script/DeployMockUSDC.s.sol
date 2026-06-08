// SPDX-License-Identifier: MIT
pragma solidity 0.8.28;

import {Script, console2} from "forge-std/Script.sol";
import {MockUSDC} from "../src/MockUSDC.sol";

/// @notice Fallback path: deploy our own 6-decimal USDC if the real Base Sepolia
///         faucet proves unreliable. Then point USDC_TOKEN_ADDRESS at this address.
/// @dev Env: DEPLOYER_PRIVATE_KEY.
contract DeployMockUSDC is Script {
    function run() external returns (MockUSDC usdc) {
        uint256 pk = vm.envUint("DEPLOYER_PRIVATE_KEY");
        vm.startBroadcast(pk);
        usdc = new MockUSDC();
        vm.stopBroadcast();
        console2.log("MockUSDC:", address(usdc));
    }
}
