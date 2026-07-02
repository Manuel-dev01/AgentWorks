// SPDX-License-Identifier: MIT
pragma solidity 0.8.28;

import {IOptimisticOracleV3} from "../src/AgentWorksUmaArbiter.sol";
import {IERC20} from "../src/AgentWorksEscrowV4.sol";

interface IOOv3Callback {
    function assertionResolvedCallback(bytes32 assertionId, bool assertedTruthfully) external;
    function assertionDisputedCallback(bytes32 assertionId) external;
}

/// @notice Deterministic test double for UMA's Optimistic Oracle V3 — enough surface for
///         AgentWorksUmaArbiter's assert → settle → callback flow. NOT for production.
contract MockOptimisticOracleV3 {
    struct Assertion {
        address asserter;
        address callbackRecipient;
        IERC20  currency;
        uint256 bond;
        bool    settled;
    }
    mapping(bytes32 => Assertion) public assertions;
    uint256 private _nonce;
    bytes32 public constant DEFAULT_IDENTIFIER = bytes32("ASSERT_TRUTH");

    function defaultIdentifier() external pure returns (bytes32) {
        return DEFAULT_IDENTIFIER;
    }

    function getMinimumBond(address) external pure returns (uint256) {
        return 0;
    }

    function assertTruth(
        bytes memory,            // claim
        address asserter,
        address callbackRecipient,
        address,                 // escalationManager
        uint64,                  // liveness
        IERC20 currency,
        uint256 bond,
        bytes32,                 // identifier
        bytes32                  // domainId
    ) external returns (bytes32 assertionId) {
        // pull the bond from the asserter (the adapter approved this mock)
        require(currency.transferFrom(asserter, address(this), bond), "bond pull failed");
        assertionId = keccak256(abi.encode(asserter, callbackRecipient, bond, ++_nonce));
        assertions[assertionId] = Assertion(asserter, callbackRecipient, currency, bond, false);
    }

    /// @notice Optimistic settle (undisputed): rules truthful and returns the bond to the asserter.
    function settleAssertion(bytes32 assertionId) external {
        _settle(assertionId, true);
    }

    function settleAndGetAssertionResult(bytes32 assertionId) external returns (bool) {
        _settle(assertionId, true);
        return true;
    }

    function getAssertionResult(bytes32) external pure returns (bool) {
        return true;
    }

    // ── test controls ──

    /// @notice Settle with a chosen result. Truthful → bond back to asserter; false → bond kept (lost).
    function mockSettle(bytes32 assertionId, bool truthfully) external {
        _settle(assertionId, truthfully);
    }

    /// @notice Simulate a UMA counter-dispute (→ DVM on mainnet; unresolved on Sepolia).
    function mockDispute(bytes32 assertionId) external {
        IOOv3Callback(assertions[assertionId].callbackRecipient).assertionDisputedCallback(assertionId);
    }

    function _settle(bytes32 assertionId, bool truthfully) private {
        Assertion storage a = assertions[assertionId];
        require(a.callbackRecipient != address(0), "unknown");
        require(!a.settled, "settled");
        a.settled = true;
        if (truthfully) {
            require(a.currency.transfer(a.asserter, a.bond), "bond return failed");
        }
        IOOv3Callback(a.callbackRecipient).assertionResolvedCallback(assertionId, truthfully);
    }
}
