// SPDX-License-Identifier: MIT
pragma solidity 0.8.28;

/// @notice Minimal ERC-20 interface (the subset of USDC the escrow uses).
interface IERC20 {
    function transfer(address to, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

/// @title AgentWorksEscrowV2
/// @notice Open-marketplace settlement layer between distrustful agents. A Client posts and funds
///         a job WITHOUT naming a provider; ANY agent may then claim the funded job via
///         {acceptJob} (first claimer wins — the on-chain race is the source of truth). The
///         claimer submits a deliverable content-hash; the Evaluator accepts (pay Provider) or
///         rejects (refund Client). An unresolved funded job is reclaimable by the Client after
///         the deadline — including jobs nobody ever accepted.
/// @dev    Supersedes the v1 closed escrow (which named the provider at createJob). Lifecycle:
///         createJob -> fund -> acceptJob -> submitWork -> complete | reject | claimRefund.
///         Funds safety uses checks-effects-interactions: status is updated before any token
///         transfer, so a failed/reentrant transfer reverts the whole call. `acceptJob` is our
///         own primitive — NOT a Cobo Agentic Wallet method.
contract AgentWorksEscrowV2 {
    enum Status {
        None,       // 0: unset / job does not exist
        Open,       // 1: created, awaiting funding (no provider yet)
        Funded,     // 2: USDC escrowed, open for any provider to accept
        Accepted,   // 3: a provider has claimed the job, awaiting work
        Submitted,  // 4: deliverable submitted, awaiting evaluation
        Completed,  // 5: accepted, provider paid (terminal)
        Rejected,   // 6: rejected, client refunded (terminal)
        Refunded    // 7: reclaimed after deadline (terminal)
    }

    struct Job {
        address client;          // funds the job; can reclaim after deadline
        address provider;        // zero until acceptJob; performs the work, paid on completion
        address evaluator;       // accept/reject authority (named at createJob)
        uint256 amount;          // USDC base units (6 decimals)
        bytes32 specHash;        // hash of the task specification
        bytes32 deliverableHash; // keccak256 of the deliverable content, set on submitWork
        string  irysId;          // Irys data-item id where the deliverable is stored (retrievable + verifiable)
        uint64  deadline;        // unix seconds; after this an unresolved funded job is refundable
        Status  status;
    }

    /// @notice The settlement token (USDC, or MockUSDC for tests). Immutable.
    IERC20 public immutable token;

    /// @notice Monotonic job id counter (first job is id 1).
    uint256 public nextJobId = 1;

    mapping(uint256 => Job) private jobs;

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
    event JobAccepted(uint256 indexed jobId, address indexed provider);
    event WorkSubmitted(uint256 indexed jobId, bytes32 deliverableHash, string irysId);
    event JobCompleted(uint256 indexed jobId, address indexed provider, uint256 amount);
    event JobRejected(uint256 indexed jobId, address indexed client, uint256 amount);
    event RefundClaimed(uint256 indexed jobId, address indexed client, uint256 amount);

    // ── Custom errors (cheaper + clearer than require strings) ──
    error ZeroAddress();
    error ZeroAmount();
    error InvalidDeadline();
    error JobNotFound(uint256 jobId);
    error BadStatus(Status have, Status want);
    error NotClient(address caller);
    error NotProvider(address caller);
    error NotEvaluator(address caller);
    error ProviderIsClient();    // the client cannot accept their own job
    error ProviderIsEvaluator(); // the evaluator cannot accept (would judge their own work)
    error DeadlineNotReached(uint64 deadline);
    error TransferFailed();

    constructor(address token_) {
        if (token_ == address(0)) revert ZeroAddress();
        token = IERC20(token_);
    }

    /// @notice Client posts an OPEN job (no provider named) — price, evaluator, spec hash, deadline.
    /// @dev    Does NOT move funds — call {fund} after approving USDC to this contract.
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

    /// @notice Any agent claims a funded, unclaimed job. First claimer wins; a second acceptJob
    ///         reverts (the job is no longer Funded). The claimer becomes the provider.
    function acceptJob(uint256 jobId) external {
        Job storage job = _get(jobId);
        if (job.status != Status.Funded) revert BadStatus(job.status, Status.Funded);
        if (msg.sender == job.client) revert ProviderIsClient();
        if (msg.sender == job.evaluator) revert ProviderIsEvaluator();

        job.provider = msg.sender;
        job.status = Status.Accepted;
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
    /// @dev    Allowed from Funded (nobody accepted), Accepted (provider never submitted), or
    ///         Submitted (evaluator never decided).
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
