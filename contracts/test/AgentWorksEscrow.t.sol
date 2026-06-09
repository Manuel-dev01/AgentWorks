// SPDX-License-Identifier: MIT
pragma solidity 0.8.28;

import {Test} from "forge-std/Test.sol";
import {AgentWorksEscrow, IERC20} from "../src/AgentWorksEscrow.sol";
import {MockUSDC} from "../src/MockUSDC.sol";

contract AgentWorksEscrowTest is Test {
    AgentWorksEscrow internal escrow;
    MockUSDC internal usdc;

    address internal client = makeAddr("client");
    address internal provider = makeAddr("provider");
    address internal evaluator = makeAddr("evaluator");
    address internal stranger = makeAddr("stranger");

    uint256 internal constant AMOUNT = 100_000_000; // 100 USDC (6 decimals)
    bytes32 internal constant SPEC = keccak256("spec: write a haiku about escrow");
    bytes32 internal constant DELIVERABLE = keccak256("irys://deliverable-content-id");
    string internal constant IRYS_ID = "kS5LZ8nT9example_irys_data_item_id_43charsAB";
    uint64 internal deadline;

    // Mirror of the contract's events for expectEmit.
    event JobCreated(uint256 indexed jobId, address indexed client, address indexed provider, address evaluator, uint256 amount, bytes32 specHash, uint64 deadline);
    event JobFunded(uint256 indexed jobId, uint256 amount);
    event WorkSubmitted(uint256 indexed jobId, bytes32 deliverableHash, string irysId);
    event JobCompleted(uint256 indexed jobId, address indexed provider, uint256 amount);
    event JobRejected(uint256 indexed jobId, address indexed client, uint256 amount);
    event RefundClaimed(uint256 indexed jobId, address indexed client, uint256 amount);

    function setUp() public {
        usdc = new MockUSDC();
        escrow = new AgentWorksEscrow(address(usdc));
        deadline = uint64(block.timestamp + 7 days);

        usdc.mint(client, 1_000_000_000); // 1,000 USDC
        vm.prank(client);
        usdc.approve(address(escrow), type(uint256).max);
    }

    // ── Helpers ──

    function _create() internal returns (uint256 jobId) {
        vm.prank(client);
        jobId = escrow.createJob(provider, evaluator, AMOUNT, SPEC, deadline);
    }

    function _createAndFund() internal returns (uint256 jobId) {
        jobId = _create();
        vm.prank(client);
        escrow.fund(jobId);
    }

    function _createFundSubmit() internal returns (uint256 jobId) {
        jobId = _createAndFund();
        vm.prank(provider);
        escrow.submitWork(jobId, DELIVERABLE, IRYS_ID);
    }

    // ── createJob ──

    function test_createJob_setsFieldsAndEmits() public {
        vm.expectEmit(true, true, true, true);
        emit JobCreated(1, client, provider, evaluator, AMOUNT, SPEC, deadline);

        uint256 jobId = _create();
        assertEq(jobId, 1);
        assertEq(escrow.nextJobId(), 2);

        AgentWorksEscrow.Job memory job = escrow.getJob(jobId);
        assertEq(job.client, client);
        assertEq(job.provider, provider);
        assertEq(job.evaluator, evaluator);
        assertEq(job.amount, AMOUNT);
        assertEq(job.specHash, SPEC);
        assertEq(job.deliverableHash, bytes32(0));
        assertEq(job.deadline, deadline);
        assertEq(uint8(job.status), uint8(AgentWorksEscrow.Status.Created));
    }

    function test_createJob_revertsZeroProvider() public {
        vm.prank(client);
        vm.expectRevert(AgentWorksEscrow.ZeroAddress.selector);
        escrow.createJob(address(0), evaluator, AMOUNT, SPEC, deadline);
    }

    function test_createJob_revertsZeroEvaluator() public {
        vm.prank(client);
        vm.expectRevert(AgentWorksEscrow.ZeroAddress.selector);
        escrow.createJob(provider, address(0), AMOUNT, SPEC, deadline);
    }

    function test_createJob_revertsZeroAmount() public {
        vm.prank(client);
        vm.expectRevert(AgentWorksEscrow.ZeroAmount.selector);
        escrow.createJob(provider, evaluator, 0, SPEC, deadline);
    }

    function test_createJob_revertsPastDeadline() public {
        vm.prank(client);
        vm.expectRevert(AgentWorksEscrow.InvalidDeadline.selector);
        escrow.createJob(provider, evaluator, AMOUNT, SPEC, uint64(block.timestamp));
    }

    // ── fund ──

    function test_fund_escrowsUSDC() public {
        uint256 jobId = _create();
        uint256 clientBefore = usdc.balanceOf(client);

        vm.expectEmit(true, false, false, true);
        emit JobFunded(jobId, AMOUNT);
        vm.prank(client);
        escrow.fund(jobId);

        assertEq(usdc.balanceOf(address(escrow)), AMOUNT);
        assertEq(usdc.balanceOf(client), clientBefore - AMOUNT);
        assertEq(uint8(escrow.getJob(jobId).status), uint8(AgentWorksEscrow.Status.Funded));
    }

    function test_fund_revertsIfNotClient() public {
        uint256 jobId = _create();
        vm.prank(stranger);
        vm.expectRevert(abi.encodeWithSelector(AgentWorksEscrow.NotClient.selector, stranger));
        escrow.fund(jobId);
    }

    function test_fund_revertsIfAlreadyFunded() public {
        uint256 jobId = _createAndFund();
        vm.prank(client);
        vm.expectRevert(
            abi.encodeWithSelector(
                AgentWorksEscrow.BadStatus.selector,
                AgentWorksEscrow.Status.Funded,
                AgentWorksEscrow.Status.Created
            )
        );
        escrow.fund(jobId);
    }

    // ── submitWork ──

    function test_submitWork_setsHashAndStatus() public {
        uint256 jobId = _createAndFund();
        vm.expectEmit(true, false, false, true);
        emit WorkSubmitted(jobId, DELIVERABLE, IRYS_ID);
        vm.prank(provider);
        escrow.submitWork(jobId, DELIVERABLE, IRYS_ID);

        AgentWorksEscrow.Job memory job = escrow.getJob(jobId);
        assertEq(job.deliverableHash, DELIVERABLE);
        assertEq(job.irysId, IRYS_ID);
        assertEq(uint8(job.status), uint8(AgentWorksEscrow.Status.Submitted));
    }

    function test_submitWork_revertsIfNotProvider() public {
        uint256 jobId = _createAndFund();
        vm.prank(stranger);
        vm.expectRevert(abi.encodeWithSelector(AgentWorksEscrow.NotProvider.selector, stranger));
        escrow.submitWork(jobId, DELIVERABLE, IRYS_ID);
    }

    function test_submitWork_revertsIfNotFunded() public {
        uint256 jobId = _create(); // created but not funded
        vm.prank(provider);
        vm.expectRevert(
            abi.encodeWithSelector(
                AgentWorksEscrow.BadStatus.selector,
                AgentWorksEscrow.Status.Created,
                AgentWorksEscrow.Status.Funded
            )
        );
        escrow.submitWork(jobId, DELIVERABLE, IRYS_ID);
    }

    // ── complete (payout branch) ──

    function test_complete_paysProvider() public {
        uint256 jobId = _createFundSubmit();
        uint256 providerBefore = usdc.balanceOf(provider);

        vm.expectEmit(true, true, false, true);
        emit JobCompleted(jobId, provider, AMOUNT);
        vm.prank(evaluator);
        escrow.complete(jobId);

        assertEq(usdc.balanceOf(provider), providerBefore + AMOUNT);
        assertEq(usdc.balanceOf(address(escrow)), 0);
        assertEq(uint8(escrow.getJob(jobId).status), uint8(AgentWorksEscrow.Status.Completed));
    }

    function test_complete_revertsIfNotEvaluator() public {
        uint256 jobId = _createFundSubmit();
        vm.prank(client); // even the client cannot complete unless they are the evaluator
        vm.expectRevert(abi.encodeWithSelector(AgentWorksEscrow.NotEvaluator.selector, client));
        escrow.complete(jobId);
    }

    function test_complete_revertsIfNotSubmitted() public {
        uint256 jobId = _createAndFund(); // not submitted yet
        vm.prank(evaluator);
        vm.expectRevert(
            abi.encodeWithSelector(
                AgentWorksEscrow.BadStatus.selector,
                AgentWorksEscrow.Status.Funded,
                AgentWorksEscrow.Status.Submitted
            )
        );
        escrow.complete(jobId);
    }

    // ── reject (refund branch) ──

    function test_reject_refundsClient() public {
        uint256 jobId = _createFundSubmit();
        uint256 clientBefore = usdc.balanceOf(client);

        vm.expectEmit(true, true, false, true);
        emit JobRejected(jobId, client, AMOUNT);
        vm.prank(evaluator);
        escrow.reject(jobId);

        assertEq(usdc.balanceOf(client), clientBefore + AMOUNT);
        assertEq(usdc.balanceOf(address(escrow)), 0);
        assertEq(uint8(escrow.getJob(jobId).status), uint8(AgentWorksEscrow.Status.Rejected));
    }

    function test_reject_revertsIfNotEvaluator() public {
        uint256 jobId = _createFundSubmit();
        vm.prank(provider);
        vm.expectRevert(abi.encodeWithSelector(AgentWorksEscrow.NotEvaluator.selector, provider));
        escrow.reject(jobId);
    }

    // ── claimRefund (expiry branch) ──

    function test_claimRefund_afterDeadline_whenFunded() public {
        uint256 jobId = _createAndFund(); // provider never submits
        uint256 clientBefore = usdc.balanceOf(client);

        vm.warp(deadline);
        vm.expectEmit(true, true, false, true);
        emit RefundClaimed(jobId, client, AMOUNT);
        vm.prank(client);
        escrow.claimRefund(jobId);

        assertEq(usdc.balanceOf(client), clientBefore + AMOUNT);
        assertEq(usdc.balanceOf(address(escrow)), 0);
        assertEq(uint8(escrow.getJob(jobId).status), uint8(AgentWorksEscrow.Status.Refunded));
    }

    function test_claimRefund_afterDeadline_whenSubmittedButUnresolved() public {
        uint256 jobId = _createFundSubmit(); // evaluator never decides
        uint256 clientBefore = usdc.balanceOf(client);

        vm.warp(deadline + 1);
        vm.prank(client);
        escrow.claimRefund(jobId);

        assertEq(usdc.balanceOf(client), clientBefore + AMOUNT);
        assertEq(uint8(escrow.getJob(jobId).status), uint8(AgentWorksEscrow.Status.Refunded));
    }

    function test_claimRefund_revertsBeforeDeadline() public {
        uint256 jobId = _createAndFund();
        vm.prank(client);
        vm.expectRevert(abi.encodeWithSelector(AgentWorksEscrow.DeadlineNotReached.selector, deadline));
        escrow.claimRefund(jobId);
    }

    function test_claimRefund_revertsIfNotClient() public {
        uint256 jobId = _createAndFund();
        vm.warp(deadline);
        vm.prank(stranger);
        vm.expectRevert(abi.encodeWithSelector(AgentWorksEscrow.NotClient.selector, stranger));
        escrow.claimRefund(jobId);
    }

    function test_claimRefund_revertsIfCompleted() public {
        uint256 jobId = _createFundSubmit();
        vm.prank(evaluator);
        escrow.complete(jobId);

        vm.warp(deadline);
        vm.prank(client);
        vm.expectRevert(
            abi.encodeWithSelector(
                AgentWorksEscrow.BadStatus.selector,
                AgentWorksEscrow.Status.Completed,
                AgentWorksEscrow.Status.Funded
            )
        );
        escrow.claimRefund(jobId);
    }

    // ── views / misc ──

    function test_getJob_revertsForUnknown() public {
        vm.expectRevert(abi.encodeWithSelector(AgentWorksEscrow.JobNotFound.selector, uint256(999)));
        escrow.getJob(999);
    }

    function test_token_isImmutableAndSet() public view {
        assertEq(address(escrow.token()), address(usdc));
    }

    function test_twoJobs_independentIds() public {
        uint256 a = _create();
        uint256 b = _create();
        assertEq(a, 1);
        assertEq(b, 2);
    }

    // ── reentrancy guard via CEI (malicious token cannot drain) ──

    function test_completeIsCEISafe_statusSetBeforeTransfer() public {
        // Deploy a reentrant token that calls back into complete() during transfer.
        ReentrantToken evil = new ReentrantToken();
        AgentWorksEscrow evilEscrow = new AgentWorksEscrow(address(evil));
        evil.setEscrow(address(evilEscrow));

        evil.mint(client, AMOUNT);
        vm.prank(client);
        evil.approve(address(evilEscrow), type(uint256).max);

        vm.prank(client);
        uint256 jobId = evilEscrow.createJob(provider, evaluator, AMOUNT, SPEC, deadline);
        vm.prank(client);
        evilEscrow.fund(jobId);
        vm.prank(provider);
        evilEscrow.submitWork(jobId, DELIVERABLE, IRYS_ID);

        // The reentrant complete() must fail because status is already Completed (CEI).
        evil.arm(jobId);
        vm.prank(evaluator);
        vm.expectRevert(); // inner reentrant call reverts BadStatus, bubbling up
        evilEscrow.complete(jobId);
    }
}

/// @dev ERC-20 that reenters escrow.complete() on transfer, to prove CEI ordering holds.
contract ReentrantToken {
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;
    address public escrow;
    uint256 public armedJobId;
    bool internal entered;

    function setEscrow(address e) external { escrow = e; }
    function arm(uint256 jobId) external { armedJobId = jobId; }
    function mint(address to, uint256 amt) external { balanceOf[to] += amt; }
    function approve(address s, uint256 a) external returns (bool) { allowance[msg.sender][s] = a; return true; }

    function transferFrom(address f, address t, uint256 a) external returns (bool) {
        balanceOf[f] -= a; balanceOf[t] += a; return true;
    }

    function transfer(address t, uint256 a) external returns (bool) {
        if (armedJobId != 0 && !entered) {
            entered = true;
            AgentWorksEscrow(escrow).complete(armedJobId); // reentrancy attempt
        }
        balanceOf[msg.sender] -= a; balanceOf[t] += a; return true;
    }
}
