// SPDX-License-Identifier: MIT
pragma solidity 0.8.28;

/// @notice Minimal ERC-20 interface (the subset of USDC the escrow uses).
interface IERC20 {
    function transfer(address to, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

/// @title AgentWorksEscrowV3
/// @notice Open-marketplace settlement layer between distrustful agents, hardened against
///         frontrunning of the accept race. A Client posts and funds a job WITHOUT naming a
///         provider; ANY agent may then claim the funded job — but instead of a single plaintext
///         {acceptJob} that leaks the jobId to the public mempool (v2), claiming is a sealed
///         two-phase COMMIT-REVEAL:
///           1. {commitAccept}(commitment)  — publishes only an opaque hash; reveals neither the
///              targeted jobId nor anything a frontrunner can reuse.
///           2. {revealAccept}(jobId, salt) — opens the commitment after a short block delay; the
///              first valid reveal wins the job (Funded -> Accepted). A copied commitment is useless
///              to anyone else because it is bound to the committer's address.
///         The claimer then submits a deliverable content-hash; the Evaluator accepts (pay Provider)
///         or rejects (refund Client). An unresolved funded job is reclaimable by the Client after
///         the deadline — including jobs nobody ever revealed.
/// @dev    Supersedes v2 (which used a raw, frontrunnable {acceptJob}). The {Status} enum and {Job}
///         struct are byte-identical to v2: a commitment is a pending *bid*, not a job state, so the
///         job stays Funded until a reveal lands and every downstream reader/indexer is unchanged.
///         Commitments live in a side mapping. Lifecycle:
///         createJob -> fund -> commitAccept -> revealAccept -> submitWork -> complete | reject | claimRefund.
///         Funds safety uses checks-effects-interactions: status is updated before any token transfer.
///         commit-reveal defeats the *hash-copy* frontrun completely; a narrow residual (a bot that
///         speculatively pre-commits to the same job could still race the reveal) is mitigated by
///         routing the reveal tx through a private mempool — defense-in-depth, see docs/MEV.md.
///         None of these are Cobo Agentic Wallet methods — they are our own settlement primitives.
contract AgentWorksEscrowV3 {
    enum Status {
        None,       // 0: unset / job does not exist
        Open,       // 1: created, awaiting funding (no provider yet)
        Funded,     // 2: USDC escrowed, open for any provider to commit + reveal
        Accepted,   // 3: a provider revealed and claimed the job, awaiting work
        Submitted,  // 4: deliverable submitted, awaiting evaluation
        Completed,  // 5: accepted, provider paid (terminal)
        Rejected,   // 6: rejected, client refunded (terminal)
        Refunded    // 7: reclaimed after deadline (terminal)
    }

    struct Job {
        address client;          // funds the job; can reclaim after deadline
        address provider;        // zero until revealAccept; performs the work, paid on completion
        address evaluator;       // accept/reject authority (named at createJob)
        uint256 amount;          // USDC base units (6 decimals)
        bytes32 specHash;        // hash of the task specification
        bytes32 deliverableHash; // keccak256 of the deliverable content, set on submitWork
        string  irysId;          // Irys data-item id where the deliverable is stored (retrievable + verifiable)
        uint64  deadline;        // unix seconds; after this an unresolved funded job is refundable
        Status  status;
    }

    /// @notice A sealed accept bid. Keyed by the commitment hash, which already encodes the
    ///         committer's address, so two providers can never collide on one slot.
    struct Commit {
        uint64 commitBlock; // block.number at commitAccept; 0 == no live commitment
        bool   revealed;    // set once on a successful reveal (one-shot anti-replay)
    }

    /// @notice The settlement token (USDC, or MockUSDC for tests). Immutable.
    IERC20 public immutable token;

    /// @notice Minimum blocks between a commit and its reveal. Forces the commitment to be buried
    ///         under at least one block before it can be opened (commit + reveal cannot share a
    ///         block, which would re-expose the plaintext race). Immutable, set at deploy.
    uint64 public immutable revealDelayBlocks;

    /// @notice Maximum additional blocks (after the delay) a commitment stays revealable. Past this
    ///         the commitment expires, so a stale-but-valid commitment cannot be hoarded to snipe a
    ///         job much later. Immutable, set at deploy.
    uint64 public immutable revealWindowBlocks;

    /// @notice Monotonic job id counter (first job is id 1).
    uint256 public nextJobId = 1;

    mapping(uint256 => Job) private jobs;

    /// @notice commitment hash => sealed accept bid.
    mapping(bytes32 => Commit) private commits;

    // ── Events: one per state transition (mirrors the lifecycle; read on the explorer) ──
    event JobCreated(
        uint256 indexed jobId,
        address indexed client,
        address indexed evaluator,
        uint256 amount,
        bytes32 specHash,
        uint64 deadline
    );
    event JobFunded(uint256 indexed jobId, uint256 amount);
    /// @dev Commit phase: intentionally JOB-AGNOSTIC. Emitting the jobId here would re-create the
    ///      exact frontrunning surface commit-reveal exists to close, so we emit only the opaque hash.
    event AcceptCommitted(bytes32 indexed commitment, uint64 commitBlock);
    /// @dev Reveal phase: same name + shape as v2's JobAccepted, so dashboards/indexers are unchanged.
    event JobAccepted(uint256 indexed jobId, address indexed provider);
    event WorkSubmitted(uint256 indexed jobId, bytes32 deliverableHash, string irysId);
    event JobCompleted(uint256 indexed jobId, address indexed provider, uint256 amount);
    event JobRejected(uint256 indexed jobId, address indexed client, uint256 amount);
    event RefundClaimed(uint256 indexed jobId, address indexed client, uint256 amount);

    // ── Custom errors (cheaper + clearer than require strings) ──
    error ZeroAddress();
    error ZeroAmount();
    error InvalidDeadline();
    error InvalidWindow();           // reveal delay/window misconfigured at deploy
    error JobNotFound(uint256 jobId);
    error BadStatus(Status have, Status want);
    error NotClient(address caller);
    error NotProvider(address caller);
    error NotEvaluator(address caller);
    error ProviderIsClient();        // the client cannot accept their own job
    error ProviderIsEvaluator();     // the evaluator cannot accept (would judge their own work)
    error DeadlineNotReached(uint64 deadline);
    error TransferFailed();
    // ── commit-reveal errors ──
    error EmptyCommitment();
    error CommitmentExists();        // a live, unrevealed commitment already occupies this slot
    error CommitNotFound();          // no commitment for (jobId, msg.sender, salt) — also wrong sender/salt
    error AlreadyRevealed();         // this commitment was already opened (anti-replay)
    error TooEarlyToReveal(uint64 readyBlock);
    error RevealWindowClosed(uint64 expiryBlock);

    constructor(address token_, uint64 revealDelayBlocks_, uint64 revealWindowBlocks_) {
        if (token_ == address(0)) revert ZeroAddress();
        if (revealDelayBlocks_ == 0 || revealWindowBlocks_ == 0) revert InvalidWindow();
        token = IERC20(token_);
        revealDelayBlocks = revealDelayBlocks_;
        revealWindowBlocks = revealWindowBlocks_;
    }

    /// @notice Client posts an OPEN job (no provider named) - price, evaluator, spec hash, deadline.
    /// @dev    Does NOT move funds - call {fund} after approving USDC to this contract.
    function createJob(
        address evaluator,
        uint256 amount,
        bytes32 specHash,
        uint64 deadline
    ) external returns (uint256 jobId) {
        if (evaluator == address(0)) revert ZeroAddress();
        if (amount == 0) revert ZeroAmount();
        if (deadline <= block.timestamp) revert InvalidDeadline();

        jobId = nextJobId++;
        jobs[jobId] = Job({
            client: msg.sender,
            provider: address(0),
            evaluator: evaluator,
            amount: amount,
            specHash: specHash,
            deliverableHash: bytes32(0),
            irysId: "",
            deadline: deadline,
            status: Status.Open
        });
        emit JobCreated(jobId, msg.sender, evaluator, amount, specHash, deadline);
    }

    /// @notice Client escrows the job amount in USDC (requires prior ERC-20 approval).
    /// @dev    Funding BEFORE acceptance means the board shows genuinely-funded open jobs that
    ///         providers can trust before committing work.
    function fund(uint256 jobId) external {
        Job storage job = _get(jobId);
        if (msg.sender != job.client) revert NotClient(msg.sender);
        if (job.status != Status.Open) revert BadStatus(job.status, Status.Open);

        job.status = Status.Funded;
        _safeTransferFrom(msg.sender, address(this), job.amount);
        emit JobFunded(jobId, job.amount);
    }

    /// @notice Step 1 of the sealed accept race: publish a hidden bid.
    /// @param  commitment MUST equal keccak256(abi.encode(jobId, msg.sender, salt)) where `salt` is
    ///         a 32-byte secret the caller keeps until reveal. The hash leaks neither the jobId nor
    ///         anything reusable: bound to msg.sender, a copied commitment is worthless to others.
    /// @dev    Job-agnostic and permissionless by design — even the client/evaluator may commit;
    ///         they simply can never {revealAccept} (checked there). Commit touches NO job state, so
    ///         it cannot reserve, block, or DoS a job.
    function commitAccept(bytes32 commitment) external {
        if (commitment == bytes32(0)) revert EmptyCommitment();
        Commit storage c = commits[commitment];
        if (c.revealed) revert AlreadyRevealed();         // never re-arm a used commitment
        if (c.commitBlock != 0) revert CommitmentExists(); // a live, unrevealed bid already here

        c.commitBlock = uint64(block.number);
        emit AcceptCommitted(commitment, uint64(block.number));
    }

    /// @notice Step 2 of the sealed accept race: open the bid and claim the job. The first valid
    ///         reveal wins (Funded -> Accepted); any later reveal reverts because the job left Funded.
    /// @param  jobId the job being claimed (hidden during commit, disclosed only now).
    /// @param  salt  the secret used to build the commitment.
    function revealAccept(uint256 jobId, bytes32 salt) external {
        Job storage job = _get(jobId);
        if (job.status != Status.Funded) revert BadStatus(job.status, Status.Funded);
        if (msg.sender == job.client) revert ProviderIsClient();
        if (msg.sender == job.evaluator) revert ProviderIsEvaluator();

        bytes32 commitment = keccak256(abi.encode(jobId, msg.sender, salt));
        Commit storage c = commits[commitment];
        // A wrong sender/salt/jobId yields a different hash whose slot is empty -> CommitNotFound.
        if (c.commitBlock == 0) revert CommitNotFound();
        if (c.revealed) revert AlreadyRevealed();

        uint64 ready = c.commitBlock + revealDelayBlocks;
        uint64 expiry = ready + revealWindowBlocks;
        if (block.number < ready) revert TooEarlyToReveal(ready);
        if (block.number > expiry) revert RevealWindowClosed(expiry);

        c.revealed = true;            // EFFECTS first (anti-replay), before the state transition
        job.provider = msg.sender;
        job.status = Status.Accepted; // job leaves Funded -> every other reveal now reverts BadStatus
        emit JobAccepted(jobId, msg.sender);
    }

    /// @notice Provider submits the deliverable's content hash + the Irys id where it's stored.
    /// @param deliverableHash keccak256 of the deliverable content (integrity commitment).
    /// @param irysId Irys data-item id; fetch at the gateway and verify keccak256 == deliverableHash.
    function submitWork(uint256 jobId, bytes32 deliverableHash, string calldata irysId) external {
        Job storage job = _get(jobId);
        if (msg.sender != job.provider) revert NotProvider(msg.sender);
        if (job.status != Status.Accepted) revert BadStatus(job.status, Status.Accepted);

        job.deliverableHash = deliverableHash;
        job.irysId = irysId;
        job.status = Status.Submitted;
        emit WorkSubmitted(jobId, deliverableHash, irysId);
    }

    /// @notice Evaluator accepts the deliverable; pays the provider.
    function complete(uint256 jobId) external {
        Job storage job = _get(jobId);
        if (msg.sender != job.evaluator) revert NotEvaluator(msg.sender);
        if (job.status != Status.Submitted) revert BadStatus(job.status, Status.Submitted);

        job.status = Status.Completed;
        _safeTransfer(job.provider, job.amount);
        emit JobCompleted(jobId, job.provider, job.amount);
    }

    /// @notice Evaluator rejects the deliverable; refunds the client.
    function reject(uint256 jobId) external {
        Job storage job = _get(jobId);
        if (msg.sender != job.evaluator) revert NotEvaluator(msg.sender);
        if (job.status != Status.Submitted) revert BadStatus(job.status, Status.Submitted);

        job.status = Status.Rejected;
        _safeTransfer(job.client, job.amount);
        emit JobRejected(jobId, job.client, job.amount);
    }

    /// @notice Client reclaims escrowed funds after the deadline if the job was never settled.
    /// @dev    Allowed from Funded (nobody revealed), Accepted (provider never submitted), or
    ///         Submitted (evaluator never decided). Outstanding commitments are inert — they revert
    ///         on reveal once the job leaves Funded — so they never block this backstop.
    function claimRefund(uint256 jobId) external {
        Job storage job = _get(jobId);
        if (msg.sender != job.client) revert NotClient(msg.sender);
        if (job.status != Status.Funded && job.status != Status.Accepted && job.status != Status.Submitted) {
            revert BadStatus(job.status, Status.Funded);
        }
        if (block.timestamp < job.deadline) revert DeadlineNotReached(job.deadline);

        job.status = Status.Refunded;
        _safeTransfer(job.client, job.amount);
        emit RefundClaimed(jobId, job.client, job.amount);
    }

    // ── Views ──

    /// @notice Returns the full job record; reverts if the job does not exist.
    function getJob(uint256 jobId) external view returns (Job memory) {
        return _get(jobId);
    }

    /// @notice Inspect a sealed bid (for off-chain UIs computing the reveal window). Returns a zero
    ///         commitBlock for an unknown commitment.
    function commitInfo(bytes32 commitment) external view returns (uint64 commitBlock, bool revealed) {
        Commit storage c = commits[commitment];
        return (c.commitBlock, c.revealed);
    }

    // ── Internal ──

    function _get(uint256 jobId) private view returns (Job storage job) {
        job = jobs[jobId];
        if (job.status == Status.None) revert JobNotFound(jobId);
    }

    function _safeTransfer(address to, uint256 amount) private {
        _safeCall(abi.encodeWithSelector(IERC20.transfer.selector, to, amount));
    }

    function _safeTransferFrom(address from, address to, uint256 amount) private {
        _safeCall(abi.encodeWithSelector(IERC20.transferFrom.selector, from, to, amount));
    }

    /// @dev Tolerates both bool-returning and void ERC-20s (USDC returns bool).
    function _safeCall(bytes memory data) private {
        (bool ok, bytes memory ret) = address(token).call(data);
        if (!ok || (ret.length != 0 && !abi.decode(ret, (bool)))) revert TransferFailed();
    }
}
