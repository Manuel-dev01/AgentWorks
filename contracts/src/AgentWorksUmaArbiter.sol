// SPDX-License-Identifier: MIT
pragma solidity 0.8.28;

import {IArbiter, IERC20} from "./AgentWorksEscrowV4.sol";

/// @notice Minimal subset of UMA's Optimistic Oracle V3 we integrate (inlined, like the escrow inlines
///         IERC20 — no external dependency). Verified Sepolia deployment:
///         0xFd9e2642a170aDD10F53Ee14a93FcF2F31924944.
interface IOptimisticOracleV3 {
    function assertTruth(
        bytes memory claim,
        address asserter,
        address callbackRecipient,
        address escalationManager,
        uint64 liveness,
        IERC20 currency,
        uint256 bond,
        bytes32 identifier,
        bytes32 domainId
    ) external returns (bytes32 assertionId);

    function settleAssertion(bytes32 assertionId) external;
    function settleAndGetAssertionResult(bytes32 assertionId) external returns (bool);
    function getAssertionResult(bytes32 assertionId) external view returns (bool);
    function getMinimumBond(address currency) external view returns (uint256);
    function defaultIdentifier() external view returns (bytes32);
}

/// @notice The escrow surface the adapter calls back into.
interface IAgentWorksEscrowResolver {
    function resolveDispute(uint256 jobId, bool payProvider) external;
}

/// @title AgentWorksUmaArbiter
/// @notice A REAL decentralized-oracle arbiter for AgentWorksEscrowV4, integrating UMA's Optimistic
///         Oracle V3. It IS the escrow's immutable `arbiter`, so disputes are ruled by UMA's economic
///         oracle — NEVER by an operator key. This is the structural decoupling the escrow demands: the
///         escrow only knows an {IArbiter} address; swapping this for a Kleros ERC-792 adapter is a
///         deploy-time change with zero escrow changes.
/// @dev    Flow: escrow.dispute() → this.openDispute() pulls the staked bond from the disputer and
///         OOv3.assertTruth()s the disputer's claim with a configurable liveness. When the assertion
///         settles, UMA calls {assertionResolvedCallback}, which routes the outcome back via
///         escrow.resolveDispute() and returns the bond to a winning disputer.
///
///         HONEST Sepolia caveat: UMA docs list Sepolia "DVM Support: No". The OPTIMISTIC path
///         (assert + liveness, no UMA-dispute) settles live; a COUNTER-disputed assertion needs the
///         mainnet DVM. {assertionDisputedCallback} records that path. See docs/ARBITRATION.md.
contract AgentWorksUmaArbiter is IArbiter {
    IOptimisticOracleV3 public immutable oo;
    IERC20 public immutable bondCurrency; // MUST be UMA-whitelisted (separate from the MockUSDC escrow)
    uint256 public immutable bond;        // dispute stake (≥ OOv3.getMinimumBond(bondCurrency))
    uint64 public immutable liveness;     // assertion liveness in seconds (short for the demo)
    bytes32 public immutable identifier;  // OOv3 default identifier

    address public immutable deployer;
    address public escrow; // set once, post-escrow-deploy (resolves the ctor circular dependency)

    struct Case {
        uint256 jobId;
        bool    disputerClaimPayProvider; // the disputer claims the OPPOSITE of the committee
        address disputer;
        bool    settled;
    }
    mapping(bytes32 => Case) public caseByAssertion; // assertionId => case
    mapping(uint256 => bytes32) public assertionByJob;

    event EscrowSet(address escrow);
    event DisputeOpened(uint256 indexed jobId, bytes32 indexed assertionId, address indexed disputer, bool disputerClaimPayProvider);
    event DisputeSettled(uint256 indexed jobId, bytes32 indexed assertionId, bool assertedTruthfully, bool payProvider);
    event AssertionDisputedOnUma(bytes32 indexed assertionId, uint256 indexed jobId);

    error OnlyEscrow();
    error OnlyOracle();
    error OnlyDeployer();
    error EscrowAlreadySet();
    error AlreadySettled();
    error UnknownAssertion();
    error TransferFailed();

    constructor(address oo_, address bondCurrency_, uint256 bond_, uint64 liveness_) {
        if (oo_ == address(0) || bondCurrency_ == address(0)) revert OnlyOracle();
        oo = IOptimisticOracleV3(oo_);
        bondCurrency = IERC20(bondCurrency_);
        bond = bond_;
        liveness = liveness_;
        identifier = IOptimisticOracleV3(oo_).defaultIdentifier();
        deployer = msg.sender;
    }

    /// @notice One-shot wiring of the escrow address (the escrow ctor needs the arbiter address, so the
    ///         arbiter is deployed first and pointed at the escrow afterward).
    function setEscrow(address escrow_) external {
        if (msg.sender != deployer) revert OnlyDeployer();
        if (escrow != address(0)) revert EscrowAlreadySet();
        if (escrow_ == address(0)) revert OnlyEscrow();
        escrow = escrow_;
        emit EscrowSet(escrow_);
    }

    /// @inheritdoc IArbiter
    function openDispute(uint256 jobId, bool committeePayout, address disputer) external {
        if (msg.sender != escrow) revert OnlyEscrow();
        bool disputerClaim = !committeePayout; // the disputer asserts the opposite of the committee

        // Pull the stake from the disputer (who approved THIS adapter for bondCurrency beforehand),
        // then post it as the UMA assertion bond.
        _pull(disputer, bond);
        _approveOO(bond);

        bytes memory claim = abi.encodePacked(
            "AgentWorks job #", _toString(jobId),
            ": the correct resolution is to PAY THE PROVIDER = ",
            disputerClaim ? "true" : "false"
        );
        bytes32 assertionId = oo.assertTruth(
            claim,
            address(this),   // asserter (the adapter manages the bond; refunds the disputer on win)
            address(this),   // callbackRecipient
            address(0),      // no escalation manager
            liveness,
            bondCurrency,
            bond,
            identifier,
            bytes32(0)       // no domain
        );
        caseByAssertion[assertionId] = Case(jobId, disputerClaim, disputer, false);
        assertionByJob[jobId] = assertionId;
        emit DisputeOpened(jobId, assertionId, disputer, disputerClaim);
    }

    /// @notice UMA settlement callback. assertedTruthfully == true means the disputer's claim held
    ///         (optimistic: nobody counter-disputed within liveness, or the DVM ruled for it).
    function assertionResolvedCallback(bytes32 assertionId, bool assertedTruthfully) external {
        if (msg.sender != address(oo)) revert OnlyOracle();
        Case storage c = caseByAssertion[assertionId];
        if (c.disputer == address(0)) revert UnknownAssertion();
        if (c.settled) revert AlreadySettled();
        c.settled = true;

        bool payProvider = assertedTruthfully ? c.disputerClaimPayProvider : !c.disputerClaimPayProvider;
        IAgentWorksEscrowResolver(escrow).resolveDispute(c.jobId, payProvider);
        emit DisputeSettled(c.jobId, assertionId, assertedTruthfully, payProvider);

        // UMA returns the bond to the asserter (this adapter) on a truthful settlement; forward whatever
        // we hold back to the disputer (they won / it was undisputed). On a non-truthful settlement UMA
        // pays the bond to the UMA-disputer, so there is nothing to forward.
        uint256 bal = bondCurrency.balanceOf(address(this));
        if (bal != 0) _push(c.disputer, bal);
    }

    /// @notice UMA fires this if someone counter-disputes the assertion (→ DVM). On Sepolia there is no
    ///         DVM to resolve it; recorded for transparency. On mainnet the DVM vote settles it and
    ///         {assertionResolvedCallback} follows.
    function assertionDisputedCallback(bytes32 assertionId) external {
        if (msg.sender != address(oo)) revert OnlyOracle();
        emit AssertionDisputedOnUma(assertionId, caseByAssertion[assertionId].jobId);
    }

    /// @notice Permissionless: anyone may settle a matured assertion on UMA, which triggers the callback.
    function settle(uint256 jobId) external {
        oo.settleAssertion(assertionByJob[jobId]);
    }

    // ── internal ──

    function _pull(address from, uint256 amount) private {
        _call(abi.encodeWithSelector(IERC20.transferFrom.selector, from, address(this), amount));
    }

    function _push(address to, uint256 amount) private {
        _call(abi.encodeWithSelector(IERC20.transfer.selector, to, amount));
    }

    function _approveOO(uint256 amount) private {
        // ERC-20 approve(address,uint256)
        _call(abi.encodeWithSelector(0x095ea7b3, address(oo), amount));
    }

    function _call(bytes memory data) private {
        (bool ok, bytes memory ret) = address(bondCurrency).call(data);
        if (!ok || (ret.length != 0 && !abi.decode(ret, (bool)))) revert TransferFailed();
    }

    function _toString(uint256 v) private pure returns (string memory) {
        if (v == 0) return "0";
        uint256 j = v;
        uint256 len;
        while (j != 0) { len++; j /= 10; }
        bytes memory b = new bytes(len);
        while (v != 0) { len--; b[len] = bytes1(uint8(48 + v % 10)); v /= 10; }
        return string(b);
    }
}
