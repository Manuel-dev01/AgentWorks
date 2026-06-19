// SPDX-License-Identifier: MIT
pragma solidity 0.8.28;

import {Test} from "forge-std/Test.sol";
import {AgentWorksEscrowV3, IERC20} from "../src/AgentWorksEscrowV3.sol";
import {MockUSDC} from "../src/MockUSDC.sol";

contract AgentWorksEscrowV3Test is Test {
    AgentWorksEscrowV3 internal escrow;
    MockUSDC internal usdc;

    address internal client = makeAddr("client");
    address internal provider = makeAddr("provider");
    address internal provider2 = makeAddr("provider2");
    address internal evaluator = makeAddr("evaluator");
    address internal stranger = makeAddr("stranger");

    uint256 internal constant AMOUNT = 100_000_000; // 100 USDC (6 decimals)
    bytes32 internal constant SPEC = keccak256("spec: write a haiku about escrow");
    bytes32 internal constant DELIVERABLE = keccak256("irys://deliverable-content-id");
    string internal constant IRYS_ID = "kS5LZ8nT9example_irys_data_item_id_43charsAB";
    bytes32 internal constant SALT = keccak256("provider-secret-salt");
    bytes32 internal constant SALT2 = keccak256("provider2-secret-salt");

    // Demo timing: 1-block reveal delay, 50-block window (matches the documented Foundry config).
    uint64 internal constant DELAY = 1;
    uint64 internal constant WINDOW = 50;

    uint64 internal deadline;

    // Mirror of the contract's events for expectEmit.
    event JobCreated(uint256 indexed jobId, address indexed client, address indexed evaluator, uint256 amount, bytes32 specHash, uint64 deadline);
    event JobFunded(uint256 indexed jobId, uint256 amount);
    event AcceptCommitted(bytes32 indexed commitment, uint64 commitBlock);
    event JobAccepted(uint256 indexed jobId, address indexed provider);
    event WorkSubmitted(uint256 indexed jobId, bytes32 deliverableHash, string irysId);
    event JobCompleted(uint256 indexed jobId, address indexed provider, uint256 amount);
    event JobRejected(uint256 indexed jobId, address indexed client, uint256 amount);
    event RefundClaimed(uint256 indexed jobId, address indexed client, uint256 amount);

    function setUp() public {
        usdc = new MockUSDC();
        escrow = new AgentWorksEscrowV3(address(usdc), DELAY, WINDOW);
        deadline = uint64(block.timestamp + 7 days);

        usdc.mint(client, 1_000_000_000); // 1,000 USDC
        vm.prank(client);
        usdc.approve(address(escrow), type(uint256).max);
    }

    // ── Helpers ──

    function _commitment(uint256 jobId, address who, bytes32 salt) internal pure returns (bytes32) {
        return keccak256(abi.encode(jobId, who, salt));
    }

    function _commit(address who, uint256 jobId, bytes32 salt) internal {
        vm.prank(who);
        escrow.commitAccept(_commitment(jobId, who, salt));
    }

    function _create() internal returns (uint256 jobId) {
        vm.prank(client);
        jobId = escrow.createJob(evaluator, AMOUNT, SPEC, deadline);
    }

    function _createAndFund() internal returns (uint256 jobId) {
        jobId = _create();
        vm.prank(client);
        escrow.fund(jobId);
    }

    /// @dev create + fund + commit (as `provider`) + roll past the delay + reveal. Returns jobId
    ///      in the Accepted state, held by `provider`. Replaces v2's _createFundAccept.
    function _createFundCommitReveal() internal returns (uint256 jobId) {
        jobId = _createAndFund();
        _commit(provider, jobId, SALT);
        vm.roll(block.number + DELAY);
        vm.prank(provider);
        escrow.revealAccept(jobId, SALT);
    }

    function _createFundAcceptSubmit() internal returns (uint256 jobId) {
        jobId = _createFundCommitReveal();
        vm.prank(provider);
        escrow.submitWork(jobId, DELIVERABLE, IRYS_ID);
    }

    // ── constructor / immutables ──

    function test_constructor_setsImmutableTiming() public view {
        assertEq(address(escrow.token()), address(usdc));
        assertEq(escrow.revealDelayBlocks(), DELAY);
        assertEq(escrow.revealWindowBlocks(), WINDOW);
    }

    function test_constructor_revertsZeroDelay() public {
        vm.expectRevert(AgentWorksEscrowV3.InvalidWindow.selector);
        new AgentWorksEscrowV3(address(usdc), 0, WINDOW);
    }

    function test_constructor_revertsZeroWindow() public {
        vm.expectRevert(AgentWorksEscrowV3.InvalidWindow.selector);
        new AgentWorksEscrowV3(address(usdc), DELAY, 0);
    }

    function test_constructor_revertsZeroToken() public {
        vm.expectRevert(AgentWorksEscrowV3.ZeroAddress.selector);
        new AgentWorksEscrowV3(address(0), DELAY, WINDOW);
    }

    // ── createJob (open: no provider) ──

    function test_createJob_setsFieldsAndEmits() public {
        vm.expectEmit(true, true, true, true);
        emit JobCreated(1, client, evaluator, AMOUNT, SPEC, deadline);

        uint256 jobId = _create();
        assertEq(jobId, 1);
        assertEq(escrow.nextJobId(), 2);

        AgentWorksEscrowV3.Job memory job = escrow.getJob(jobId);
        assertEq(job.client, client);
        assertEq(job.provider, address(0)); // open - no provider yet
        assertEq(job.evaluator, evaluator);
        assertEq(job.amount, AMOUNT);
        assertEq(job.specHash, SPEC);
        assertEq(job.deliverableHash, bytes32(0));
        assertEq(job.deadline, deadline);
        assertEq(uint8(job.status), uint8(AgentWorksEscrowV3.Status.Open));
    }

    function test_createJob_revertsZeroEvaluator() public {
        vm.prank(client);
        vm.expectRevert(AgentWorksEscrowV3.ZeroAddress.selector);
        escrow.createJob(address(0), AMOUNT, SPEC, deadline);
    }

    function test_createJob_revertsZeroAmount() public {
        vm.prank(client);
        vm.expectRevert(AgentWorksEscrowV3.ZeroAmount.selector);
        escrow.createJob(evaluator, 0, SPEC, deadline);
    }

    function test_createJob_revertsPastDeadline() public {
        vm.prank(client);
        vm.expectRevert(AgentWorksEscrowV3.InvalidDeadline.selector);
        escrow.createJob(evaluator, AMOUNT, SPEC, uint64(block.timestamp));
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
        assertEq(uint8(escrow.getJob(jobId).status), uint8(AgentWorksEscrowV3.Status.Funded));
    }

    function test_fund_revertsIfNotClient() public {
        uint256 jobId = _create();
        vm.prank(stranger);
        vm.expectRevert(abi.encodeWithSelector(AgentWorksEscrowV3.NotClient.selector, stranger));
        escrow.fund(jobId);
    }

    function test_fund_revertsIfAlreadyFunded() public {
        uint256 jobId = _createAndFund();
        vm.prank(client);
        vm.expectRevert(
            abi.encodeWithSelector(
                AgentWorksEscrowV3.BadStatus.selector,
                AgentWorksEscrowV3.Status.Funded,
                AgentWorksEscrowV3.Status.Open
            )
        );
        escrow.fund(jobId);
    }

    // ── commitAccept (sealed bid) ──

    function test_commitAccept_storesBlockAndEmits() public {
        uint256 jobId = _createAndFund();
        bytes32 c = _commitment(jobId, provider, SALT);

        vm.expectEmit(true, false, false, true);
        emit AcceptCommitted(c, uint64(block.number));
        vm.prank(provider);
        escrow.commitAccept(c);

        (uint64 commitBlock, bool revealed) = escrow.commitInfo(c);
        assertEq(commitBlock, uint64(block.number));
        assertEq(revealed, false);
    }

    /// @dev Commit reveals NOTHING about the job: the job stays Funded with no provider set.
    function test_commitAccept_doesNotChangeJobState() public {
        uint256 jobId = _createAndFund();
        _commit(provider, jobId, SALT);

        AgentWorksEscrowV3.Job memory job = escrow.getJob(jobId);
        assertEq(uint8(job.status), uint8(AgentWorksEscrowV3.Status.Funded));
        assertEq(job.provider, address(0));
    }

    function test_commitAccept_revertsEmptyCommitment() public {
        vm.prank(provider);
        vm.expectRevert(AgentWorksEscrowV3.EmptyCommitment.selector);
        escrow.commitAccept(bytes32(0));
    }

    function test_commitAccept_revertsDuplicateLiveCommitment() public {
        uint256 jobId = _createAndFund();
        bytes32 c = _commitment(jobId, provider, SALT);
        vm.prank(provider);
        escrow.commitAccept(c);

        vm.prank(provider);
        vm.expectRevert(AgentWorksEscrowV3.CommitmentExists.selector);
        escrow.commitAccept(c);
    }

    /// @dev Commit is permissionless + job-agnostic: client/evaluator may commit (they just can
    ///      never reveal). It cannot reserve or block a job.
    function test_commitAccept_clientOrEvaluatorMayCommit() public {
        uint256 jobId = _createAndFund();
        _commit(client, jobId, SALT);
        _commit(evaluator, jobId, SALT2);
        // job untouched
        assertEq(uint8(escrow.getJob(jobId).status), uint8(AgentWorksEscrowV3.Status.Funded));
    }

    function test_commitAccept_differentSaltDistinctSlots() public {
        uint256 jobId = _createAndFund();
        _commit(provider, jobId, SALT);
        _commit(provider, jobId, SALT2); // different salt => different hash => independent slot, OK

        (uint64 b1,) = escrow.commitInfo(_commitment(jobId, provider, SALT));
        (uint64 b2,) = escrow.commitInfo(_commitment(jobId, provider, SALT2));
        assertGt(b1, 0);
        assertGt(b2, 0);
    }

    // ── revealAccept (happy path + boundaries) ──

    function test_revealAccept_setsProviderAndStatusAndEmits() public {
        uint256 jobId = _createAndFund();
        _commit(provider, jobId, SALT);
        vm.roll(block.number + DELAY);

        vm.expectEmit(true, true, false, false);
        emit JobAccepted(jobId, provider);
        vm.prank(provider);
        escrow.revealAccept(jobId, SALT);

        AgentWorksEscrowV3.Job memory job = escrow.getJob(jobId);
        assertEq(job.provider, provider);
        assertEq(uint8(job.status), uint8(AgentWorksEscrowV3.Status.Accepted));

        (, bool revealed) = escrow.commitInfo(_commitment(jobId, provider, SALT));
        assertEq(revealed, true);
    }

    function test_revealAccept_atExactReadyBlock() public {
        uint256 jobId = _createAndFund();
        uint256 commitBlock = block.number;
        _commit(provider, jobId, SALT);
        vm.roll(commitBlock + DELAY); // exactly ready
        vm.prank(provider);
        escrow.revealAccept(jobId, SALT);
        assertEq(escrow.getJob(jobId).provider, provider);
    }

    function test_revealAccept_atExactExpiryBlock() public {
        uint256 jobId = _createAndFund();
        uint256 commitBlock = block.number;
        _commit(provider, jobId, SALT);
        vm.roll(commitBlock + DELAY + WINDOW); // last valid block (inclusive)
        vm.prank(provider);
        escrow.revealAccept(jobId, SALT);
        assertEq(escrow.getJob(jobId).provider, provider);
    }

    // ── revealAccept timing ──

    function test_revealAccept_revertsBeforeDelay() public {
        uint256 jobId = _createAndFund();
        uint64 ready = uint64(block.number) + DELAY;
        _commit(provider, jobId, SALT); // same block, before delay
        vm.prank(provider);
        vm.expectRevert(abi.encodeWithSelector(AgentWorksEscrowV3.TooEarlyToReveal.selector, ready));
        escrow.revealAccept(jobId, SALT);
    }

    function test_revealAccept_revertsAfterWindow() public {
        uint256 jobId = _createAndFund();
        uint64 expiry = uint64(block.number) + DELAY + WINDOW;
        _commit(provider, jobId, SALT);
        vm.roll(uint256(expiry) + 1); // one block past expiry
        vm.prank(provider);
        vm.expectRevert(abi.encodeWithSelector(AgentWorksEscrowV3.RevealWindowClosed.selector, expiry));
        escrow.revealAccept(jobId, SALT);
    }

    // ── revealAccept anti-theft binding ──

    /// @dev A frontrunner copies the published commitment hash and commits it under THEIR address.
    ///      At reveal the contract recomputes with the attacker's address -> different hash -> the
    ///      attacker's stored slot does not match -> CommitNotFound. The copied hash is worthless.
    function test_revealAccept_copiedCommitmentByOtherSenderFails() public {
        uint256 jobId = _createAndFund();
        bytes32 victimCommitment = _commitment(jobId, provider, SALT);

        // Attacker copies the exact hash off the mempool and commits it themselves.
        vm.prank(provider2);
        escrow.commitAccept(victimCommitment);
        vm.roll(block.number + DELAY);

        // Attacker cannot open it: revealAccept hashes (jobId, provider2, SALT) != victimCommitment.
        vm.prank(provider2);
        vm.expectRevert(AgentWorksEscrowV3.CommitNotFound.selector);
        escrow.revealAccept(jobId, SALT);
    }

    function test_revealAccept_wrongSaltFails() public {
        uint256 jobId = _createAndFund();
        _commit(provider, jobId, SALT);
        vm.roll(block.number + DELAY);
        vm.prank(provider);
        vm.expectRevert(AgentWorksEscrowV3.CommitNotFound.selector);
        escrow.revealAccept(jobId, SALT2);
    }

    function test_revealAccept_wrongJobIdFails() public {
        uint256 jobA = _createAndFund();
        uint256 jobB = _createAndFund();
        _commit(provider, jobA, SALT); // committed for A
        vm.roll(block.number + DELAY);
        // Reveal against B: hash (jobB, provider, SALT) has no commitment.
        vm.prank(provider);
        vm.expectRevert(AgentWorksEscrowV3.CommitNotFound.selector);
        escrow.revealAccept(jobB, SALT);
    }

    function test_revealAccept_neverCommittedFails() public {
        uint256 jobId = _createAndFund();
        vm.roll(block.number + DELAY);
        vm.prank(provider);
        vm.expectRevert(AgentWorksEscrowV3.CommitNotFound.selector);
        escrow.revealAccept(jobId, SALT);
    }

    // ── revealAccept replay ──

    function test_revealAccept_doubleRevealReverts() public {
        uint256 jobId = _createFundCommitReveal(); // already accepted by provider
        // A second reveal of the same commitment: job is no longer Funded -> BadStatus first.
        vm.prank(provider);
        vm.expectRevert(
            abi.encodeWithSelector(
                AgentWorksEscrowV3.BadStatus.selector,
                AgentWorksEscrowV3.Status.Accepted,
                AgentWorksEscrowV3.Status.Funded
            )
        );
        escrow.revealAccept(jobId, SALT);
    }

    function test_commitAccept_revertsReuseAfterReveal() public {
        uint256 jobId = _createFundCommitReveal();
        // Re-arming a revealed commitment hash is rejected.
        vm.prank(provider);
        vm.expectRevert(AgentWorksEscrowV3.AlreadyRevealed.selector);
        escrow.commitAccept(_commitment(jobId, provider, SALT));
    }

    // ── revealAccept race / winner ──

    /// @dev Two providers both validly commit (own salts) and are in-window; the first to reveal
    ///      wins (Funded -> Accepted), the second reveal reverts because the job left Funded.
    function test_revealAccept_twoValidCommits_firstRevealWins() public {
        uint256 jobId = _createAndFund();
        _commit(provider, jobId, SALT);
        _commit(provider2, jobId, SALT2);
        vm.roll(block.number + DELAY);

        vm.prank(provider);
        escrow.revealAccept(jobId, SALT); // provider wins

        vm.prank(provider2);
        vm.expectRevert(
            abi.encodeWithSelector(
                AgentWorksEscrowV3.BadStatus.selector,
                AgentWorksEscrowV3.Status.Accepted,
                AgentWorksEscrowV3.Status.Funded
            )
        );
        escrow.revealAccept(jobId, SALT2);

        assertEq(escrow.getJob(jobId).provider, provider); // first revealer holds it
    }

    // ── revealAccept status / access guards ──

    function test_revealAccept_revertsIfNotFunded() public {
        uint256 jobId = _create(); // Open, not funded
        _commit(provider, jobId, SALT);
        vm.roll(block.number + DELAY);
        vm.prank(provider);
        vm.expectRevert(
            abi.encodeWithSelector(
                AgentWorksEscrowV3.BadStatus.selector,
                AgentWorksEscrowV3.Status.Open,
                AgentWorksEscrowV3.Status.Funded
            )
        );
        escrow.revealAccept(jobId, SALT);
    }

    function test_revealAccept_revertsIfClient() public {
        uint256 jobId = _createAndFund();
        _commit(client, jobId, SALT);
        vm.roll(block.number + DELAY);
        vm.prank(client);
        vm.expectRevert(AgentWorksEscrowV3.ProviderIsClient.selector);
        escrow.revealAccept(jobId, SALT);
    }

    function test_revealAccept_revertsIfEvaluator() public {
        uint256 jobId = _createAndFund();
        _commit(evaluator, jobId, SALT);
        vm.roll(block.number + DELAY);
        vm.prank(evaluator);
        vm.expectRevert(AgentWorksEscrowV3.ProviderIsEvaluator.selector);
        escrow.revealAccept(jobId, SALT);
    }

    function test_revealAccept_revertsUnknownJob() public {
        vm.prank(provider);
        vm.expectRevert(abi.encodeWithSelector(AgentWorksEscrowV3.JobNotFound.selector, uint256(999)));
        escrow.revealAccept(999, SALT);
    }

    // ── submitWork ──

    function test_submitWork_setsHashAndStatus() public {
        uint256 jobId = _createFundCommitReveal();
        vm.expectEmit(true, false, false, true);
        emit WorkSubmitted(jobId, DELIVERABLE, IRYS_ID);
        vm.prank(provider);
        escrow.submitWork(jobId, DELIVERABLE, IRYS_ID);

        AgentWorksEscrowV3.Job memory job = escrow.getJob(jobId);
        assertEq(job.deliverableHash, DELIVERABLE);
        assertEq(job.irysId, IRYS_ID);
        assertEq(uint8(job.status), uint8(AgentWorksEscrowV3.Status.Submitted));
    }

    function test_submitWork_revertsIfNotProvider() public {
        uint256 jobId = _createFundCommitReveal();
        vm.prank(stranger);
        vm.expectRevert(abi.encodeWithSelector(AgentWorksEscrowV3.NotProvider.selector, stranger));
        escrow.submitWork(jobId, DELIVERABLE, IRYS_ID);
    }

    function test_submitWork_revertsIfNotAccepted() public {
        uint256 jobId = _createAndFund(); // funded but not accepted (no provider)
        vm.prank(provider);
        vm.expectRevert(abi.encodeWithSelector(AgentWorksEscrowV3.NotProvider.selector, provider));
        escrow.submitWork(jobId, DELIVERABLE, IRYS_ID);
    }

    // ── complete (payout branch) ──

    function test_complete_paysProvider() public {
        uint256 jobId = _createFundAcceptSubmit();
        uint256 providerBefore = usdc.balanceOf(provider);

        vm.expectEmit(true, true, false, true);
        emit JobCompleted(jobId, provider, AMOUNT);
        vm.prank(evaluator);
        escrow.complete(jobId);

        assertEq(usdc.balanceOf(provider), providerBefore + AMOUNT);
        assertEq(usdc.balanceOf(address(escrow)), 0);
        assertEq(uint8(escrow.getJob(jobId).status), uint8(AgentWorksEscrowV3.Status.Completed));
    }

    function test_complete_revertsIfNotEvaluator() public {
        uint256 jobId = _createFundAcceptSubmit();
        vm.prank(client);
        vm.expectRevert(abi.encodeWithSelector(AgentWorksEscrowV3.NotEvaluator.selector, client));
        escrow.complete(jobId);
    }

    function test_complete_revertsIfNotSubmitted() public {
        uint256 jobId = _createFundCommitReveal(); // accepted, not submitted
        vm.prank(evaluator);
        vm.expectRevert(
            abi.encodeWithSelector(
                AgentWorksEscrowV3.BadStatus.selector,
                AgentWorksEscrowV3.Status.Accepted,
                AgentWorksEscrowV3.Status.Submitted
            )
        );
        escrow.complete(jobId);
    }

    // ── reject (refund branch) ──

    function test_reject_refundsClient() public {
        uint256 jobId = _createFundAcceptSubmit();
        uint256 clientBefore = usdc.balanceOf(client);

        vm.expectEmit(true, true, false, true);
        emit JobRejected(jobId, client, AMOUNT);
        vm.prank(evaluator);
        escrow.reject(jobId);

        assertEq(usdc.balanceOf(client), clientBefore + AMOUNT);
        assertEq(usdc.balanceOf(address(escrow)), 0);
        assertEq(uint8(escrow.getJob(jobId).status), uint8(AgentWorksEscrowV3.Status.Rejected));
    }

    function test_reject_revertsIfNotEvaluator() public {
        uint256 jobId = _createFundAcceptSubmit();
        vm.prank(provider);
        vm.expectRevert(abi.encodeWithSelector(AgentWorksEscrowV3.NotEvaluator.selector, provider));
        escrow.reject(jobId);
    }

    // ── claimRefund (expiry branch / backstop) ──

    /// @dev The deadline backstop is intact: commitments never block a refund. A job funded but
    ///      never revealed is reclaimable after the deadline.
    function test_claimRefund_worksIfNobodyEverReveals() public {
        uint256 jobId = _createAndFund();
        _commit(provider, jobId, SALT);   // sealed bid exists but is never revealed
        _commit(provider2, jobId, SALT2);
        uint256 clientBefore = usdc.balanceOf(client);

        vm.warp(deadline);
        vm.expectEmit(true, true, false, true);
        emit RefundClaimed(jobId, client, AMOUNT);
        vm.prank(client);
        escrow.claimRefund(jobId);

        assertEq(usdc.balanceOf(client), clientBefore + AMOUNT);
        assertEq(usdc.balanceOf(address(escrow)), 0);
        assertEq(uint8(escrow.getJob(jobId).status), uint8(AgentWorksEscrowV3.Status.Refunded));
    }

    /// @dev After the job is refunded, an outstanding in-window commitment is inert (reveal reverts).
    function test_commitThenJobRefunded_revealReverts() public {
        uint256 jobId = _createAndFund();
        _commit(provider, jobId, SALT);
        vm.warp(deadline);
        vm.prank(client);
        escrow.claimRefund(jobId);

        vm.roll(block.number + DELAY);
        vm.prank(provider);
        vm.expectRevert(
            abi.encodeWithSelector(
                AgentWorksEscrowV3.BadStatus.selector,
                AgentWorksEscrowV3.Status.Refunded,
                AgentWorksEscrowV3.Status.Funded
            )
        );
        escrow.revealAccept(jobId, SALT);
    }

    function test_claimRefund_afterDeadline_whenAcceptedButNoWork() public {
        uint256 jobId = _createFundCommitReveal(); // provider claimed but never submitted
        uint256 clientBefore = usdc.balanceOf(client);

        vm.warp(deadline + 1);
        vm.prank(client);
        escrow.claimRefund(jobId);

        assertEq(usdc.balanceOf(client), clientBefore + AMOUNT);
        assertEq(uint8(escrow.getJob(jobId).status), uint8(AgentWorksEscrowV3.Status.Refunded));
    }

    function test_claimRefund_afterDeadline_whenSubmittedButUnresolved() public {
        uint256 jobId = _createFundAcceptSubmit(); // evaluator never decides
        uint256 clientBefore = usdc.balanceOf(client);

        vm.warp(deadline + 1);
        vm.prank(client);
        escrow.claimRefund(jobId);

        assertEq(usdc.balanceOf(client), clientBefore + AMOUNT);
        assertEq(uint8(escrow.getJob(jobId).status), uint8(AgentWorksEscrowV3.Status.Refunded));
    }

    function test_claimRefund_revertsBeforeDeadline() public {
        uint256 jobId = _createAndFund();
        vm.prank(client);
        vm.expectRevert(abi.encodeWithSelector(AgentWorksEscrowV3.DeadlineNotReached.selector, deadline));
        escrow.claimRefund(jobId);
    }

    function test_claimRefund_revertsIfNotClient() public {
        uint256 jobId = _createAndFund();
        vm.warp(deadline);
        vm.prank(stranger);
        vm.expectRevert(abi.encodeWithSelector(AgentWorksEscrowV3.NotClient.selector, stranger));
        escrow.claimRefund(jobId);
    }

    function test_claimRefund_revertsIfCompleted() public {
        uint256 jobId = _createFundAcceptSubmit();
        vm.prank(evaluator);
        escrow.complete(jobId);

        vm.warp(deadline);
        vm.prank(client);
        vm.expectRevert(
            abi.encodeWithSelector(
                AgentWorksEscrowV3.BadStatus.selector,
                AgentWorksEscrowV3.Status.Completed,
                AgentWorksEscrowV3.Status.Funded
            )
        );
        escrow.claimRefund(jobId);
    }

    // ── views / misc ──

    function test_getJob_revertsForUnknown() public {
        vm.expectRevert(abi.encodeWithSelector(AgentWorksEscrowV3.JobNotFound.selector, uint256(999)));
        escrow.getJob(999);
    }

    function test_commitInfo_zeroForUnknown() public view {
        (uint64 b, bool r) = escrow.commitInfo(keccak256("nope"));
        assertEq(b, 0);
        assertEq(r, false);
    }

    function test_twoJobs_independentIds() public {
        uint256 a = _create();
        uint256 b = _create();
        assertEq(a, 1);
        assertEq(b, 2);
    }

    // ── reentrancy guard via CEI (malicious token cannot drain) ──

    function test_completeIsCEISafe_statusSetBeforeTransfer() public {
        ReentrantToken evil = new ReentrantToken();
        AgentWorksEscrowV3 evilEscrow = new AgentWorksEscrowV3(address(evil), DELAY, WINDOW);
        evil.setEscrow(address(evilEscrow));

        evil.mint(client, AMOUNT);
        vm.prank(client);
        evil.approve(address(evilEscrow), type(uint256).max);

        vm.prank(client);
        uint256 jobId = evilEscrow.createJob(evaluator, AMOUNT, SPEC, deadline);
        vm.prank(client);
        evilEscrow.fund(jobId);
        vm.prank(provider);
        evilEscrow.commitAccept(_commitment(jobId, provider, SALT));
        vm.roll(block.number + DELAY);
        vm.prank(provider);
        evilEscrow.revealAccept(jobId, SALT);
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
            AgentWorksEscrowV3(escrow).complete(armedJobId); // reentrancy attempt
        }
        balanceOf[msg.sender] -= a; balanceOf[t] += a; return true;
    }
}
