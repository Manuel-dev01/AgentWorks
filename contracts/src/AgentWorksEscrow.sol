// SPDX-License-Identifier: MIT
pragma solidity 0.8.28;

/// @notice Minimal ERC-20 interface (the subset of USDC the escrow uses).
interface IERC20 {
    function transfer(address to, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

/// @title AgentWorksEscrow
/// @notice Neutral settlement layer between two distrustful agents. A Client funds a job
///         in USDC; a Provider submits a deliverable content-hash; an Evaluator accepts
///         (pay Provider) or rejects (refund Client). If a funded job is never resolved,
///         the Client can reclaim the funds after the deadline.
/// @dev    Lifecycle naming mirrors the ERC-8183 DRAFT (we do not depend on it):
///         createJob -> fund -> submitWork -> complete | reject | claimRefund.
///         The Evaluator is a distinct per-job address (v1: Client-controlled, swappable).
///         Funds safety uses checks-effects-interactions: status is updated before any
///         token transfer, so a failed/reentrant transfer reverts the whole call.
contract AgentWorksEscrow {
    enum Status {
        None,       // 0: unset / job does not exist
        Created,    // 1: created, not yet funded
        Funded,     // 2: USDC escrowed, awaiting work
        Submitted,  // 3: deliverable submitted, awaiting evaluation
        Completed,  // 4: accepted, provider paid (terminal)
        Rejected,   // 5: rejected, client refunded (terminal)
        Refunded    // 6: reclaimed after deadline (terminal)
    }

    struct Job {
        address client;          // funds the job; can reclaim after deadline
        address provider;        // performs the work, paid on completion
        address evaluator;       // accept/reject authority
        uint256 amount;          // USDC base units (6 decimals)
        bytes32 specHash;        // hash of the task specification
        bytes32 deliverableHash; // hash of the deliverable (e.g. Irys tx id), set on submitWork
        uint64  deadline;        // unix seconds; after this an unresolved funded job is refundable
        Status  status;
    }

    /// @notice The settlement token (USDC on Base Sepolia, or MockUSDC for tests). Immutable.
    IERC20 public immutable token;

    /// @notice Monotonic job id counter (first job is id 1).
    uint256 public nextJobId = 1;

    mapping(uint256 => Job) private jobs;

    // ── Events: one per state transition (mirrors the lifecycle; read on the explorer) ──
    event JobCreated(
        uint256 indexed jobId,
        address indexed client,
        address indexed provider,
        address evaluator,
        uint256 amount,
        bytes32 specHash,
        uint64 deadline
    );
    event JobFunded(uint256 indexed jobId, uint256 amount);
    event WorkSubmitted(uint256 indexed jobId, bytes32 deliverableHash);
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
    error DeadlineNotReached(uint64 deadline);
    error TransferFailed();

    constructor(address token_) {
        if (token_ == address(0)) revert ZeroAddress();
        token = IERC20(token_);
    }

    /// @notice Client creates a job, naming the provider, evaluator, price, spec hash and deadline.
    /// @dev    Does NOT move funds — call {fund} after approving USDC to this contract.
    function createJob(
        address provider,
        address evaluator,
        uint256 amount,
        bytes32 specHash,
        uint64 deadline
    ) external returns (uint256 jobId) {
        if (provider == address(0) || evaluator == address(0)) revert ZeroAddress();
        if (amount == 0) revert ZeroAmount();
        if (deadline <= block.timestamp) revert InvalidDeadline();

        jobId = nextJobId++;
        jobs[jobId] = Job({
            client: msg.sender,
            provider: provider,
            evaluator: evaluator,
            amount: amount,
            specHash: specHash,
            deliverableHash: bytes32(0),
            deadline: deadline,
            status: Status.Created
        });
        emit JobCreated(jobId, msg.sender, provider, evaluator, amount, specHash, deadline);
    }

    /// @notice Client escrows the job amount in USDC (requires prior ERC-20 approval).
    function fund(uint256 jobId) external {
        Job storage job = _get(jobId);
        if (msg.sender != job.client) revert NotClient(msg.sender);
        if (job.status != Status.Created) revert BadStatus(job.status, Status.Created);

        job.status = Status.Funded;
        _safeTransferFrom(msg.sender, address(this), job.amount);
        emit JobFunded(jobId, job.amount);
    }

    /// @notice Provider submits the deliverable content-hash for a funded job.
    function submitWork(uint256 jobId, bytes32 deliverableHash) external {
        Job storage job = _get(jobId);
        if (msg.sender != job.provider) revert NotProvider(msg.sender);
        if (job.status != Status.Funded) revert BadStatus(job.status, Status.Funded);

        job.deliverableHash = deliverableHash;
        job.status = Status.Submitted;
        emit WorkSubmitted(jobId, deliverableHash);
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
    /// @dev    Allowed from Funded (provider never submitted) or Submitted (evaluator never decided).
    function claimRefund(uint256 jobId) external {
        Job storage job = _get(jobId);
        if (msg.sender != job.client) revert NotClient(msg.sender);
        if (job.status != Status.Funded && job.status != Status.Submitted) {
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
