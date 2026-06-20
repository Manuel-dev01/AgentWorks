// SPDX-License-Identifier: MIT
pragma solidity 0.8.28;

import {Test} from "forge-std/Test.sol";
import {AgentWorksUmaArbiter} from "../src/AgentWorksUmaArbiter.sol";
import {MockOptimisticOracleV3} from "./MockOptimisticOracleV3.sol";
import {MockUSDC} from "../src/MockUSDC.sol";

/// @dev Stands in for AgentWorksEscrowV4: triggers openDispute (as escrow.dispute would) and records
///      the arbiter's resolveDispute callback.
contract MockEscrowResolver {
    AgentWorksUmaArbiter public arb;
    bool public resolved;
    uint256 public lastJobId;
    bool public lastPayProvider;

    function setArbiter(AgentWorksUmaArbiter a) external { arb = a; }

    function open(uint256 jobId, bool committeePayout, address disputer) external {
        arb.openDispute(jobId, committeePayout, disputer);
    }

    function resolveDispute(uint256 jobId, bool payProvider) external {
        require(msg.sender == address(arb), "only arb");
        resolved = true;
        lastJobId = jobId;
        lastPayProvider = payProvider;
    }
}

contract AgentWorksUmaArbiterTest is Test {
    AgentWorksUmaArbiter internal arb;
    MockOptimisticOracleV3 internal oo;
    MockEscrowResolver internal escrow;
    MockUSDC internal bondToken;

    address internal disputer = makeAddr("disputer");
    uint256 internal constant BOND = 10_000_000; // 10 (mock) units
    uint64 internal constant LIVENESS = 120;

    function setUp() public {
        oo = new MockOptimisticOracleV3();
        bondToken = new MockUSDC();
        arb = new AgentWorksUmaArbiter(address(oo), address(bondToken), BOND, LIVENESS);
        escrow = new MockEscrowResolver();
        escrow.setArbiter(arb);
        arb.setEscrow(address(escrow));

        bondToken.mint(disputer, 1_000_000_000);
        vm.prank(disputer);
        bondToken.approve(address(arb), type(uint256).max);
    }

    function test_setEscrow_revertsNonDeployer() public {
        AgentWorksUmaArbiter a2 = new AgentWorksUmaArbiter(address(oo), address(bondToken), BOND, LIVENESS);
        vm.prank(disputer);
        vm.expectRevert(AgentWorksUmaArbiter.OnlyDeployer.selector);
        a2.setEscrow(address(escrow));
    }

    function test_setEscrow_revertsTwice() public {
        vm.expectRevert(AgentWorksUmaArbiter.EscrowAlreadySet.selector);
        arb.setEscrow(address(escrow));
    }

    function test_openDispute_onlyEscrow() public {
        vm.prank(disputer);
        vm.expectRevert(AgentWorksUmaArbiter.OnlyEscrow.selector);
        arb.openDispute(1, true, disputer);
    }

    function test_openDispute_pullsBondAndAsserts() public {
        uint256 before = bondToken.balanceOf(disputer);
        escrow.open(1, true, disputer); // committee said payout; disputer (client) claims refund
        assertEq(bondToken.balanceOf(disputer), before - BOND); // bond pulled
        assertEq(bondToken.balanceOf(address(oo)), BOND);        // posted to the oracle
        bytes32 aid = arb.assertionByJob(1);
        assertTrue(aid != bytes32(0));
        (uint256 jobId, bool disputerClaim, address d, bool settled) = arb.caseByAssertion(aid);
        assertEq(jobId, 1);
        assertFalse(disputerClaim); // committeePayout=true → disputer claims payProvider=false
        assertEq(d, disputer);
        assertFalse(settled);
    }

    function test_settleTruthful_overturnsAndReturnsBond() public {
        // committee said REFUND (payout=false); provider disputes claiming payProvider=true
        escrow.open(7, false, disputer);
        bytes32 aid = arb.assertionByJob(7);
        uint256 before = bondToken.balanceOf(disputer);
        oo.settleAssertion(aid); // optimistic → truthful → disputer's claim holds
        assertTrue(escrow.resolved());
        assertEq(escrow.lastJobId(), 7);
        assertTrue(escrow.lastPayProvider()); // overturned to pay provider
        assertEq(bondToken.balanceOf(disputer), before + BOND); // bond returned to winner
    }

    function test_settleUntruthful_upholdsCommittee_bondLost() public {
        // committee said REFUND; provider disputes; UMA rules NOT truthful → uphold committee (refund)
        escrow.open(8, false, disputer);
        bytes32 aid = arb.assertionByJob(8);
        uint256 before = bondToken.balanceOf(disputer);
        oo.mockSettle(aid, false);
        assertTrue(escrow.resolved());
        assertFalse(escrow.lastPayProvider()); // upheld committee refund
        assertEq(bondToken.balanceOf(disputer), before); // bond NOT returned (lost on the oracle)
    }

    function test_resolvedCallback_onlyOracle() public {
        escrow.open(1, true, disputer);
        bytes32 aid = arb.assertionByJob(1);
        vm.prank(disputer);
        vm.expectRevert(AgentWorksUmaArbiter.OnlyOracle.selector);
        arb.assertionResolvedCallback(aid, true);
    }

    function test_doubleSettle_reverts() public {
        escrow.open(1, true, disputer);
        bytes32 aid = arb.assertionByJob(1);
        oo.settleAssertion(aid);
        vm.expectRevert(); // mock guards re-settle; adapter also guards AlreadySettled
        oo.settleAssertion(aid);
    }

    function test_disputedCallback_recordsOnly() public {
        escrow.open(1, true, disputer);
        bytes32 aid = arb.assertionByJob(1);
        oo.mockDispute(aid); // simulate a UMA counter-dispute (DVM path; no-op on Sepolia)
        assertFalse(escrow.resolved()); // not resolved by the dispute callback
    }

    function test_settle_helperRoutesThroughJobId() public {
        escrow.open(3, true, disputer);
        arb.settle(3); // permissionless settle by jobId
        assertTrue(escrow.resolved());
        assertEq(escrow.lastJobId(), 3);
    }
}
