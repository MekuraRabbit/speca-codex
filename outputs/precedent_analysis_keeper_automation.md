# Precedent Analysis: keeper_automation

Pattern: Chainlink Keeper/Automation vulnerabilities - performUpkeep, checkUpkeep manipulation

Matches found: 20

## LLM Analysis

I'll analyze each historical finding for its severity reasoning and identify new vulnerability patterns applicable to Chainlink V2.

## Analysis of Historical Findings

### Severity Assessment Summary

**High Severity Findings (11/15)**: #158, #121, #100, #69, #68, #98, #69, #93, #91, #48, #402, #150, #528, #138, #102
- Common patterns: Access control bypass, critical function failure, silent failures causing loss
- Typically involve: Complete loss of funds, broken core functionality, unauthorized privilege escalation

**Notable severity patterns**:
- **Permission bypass** (#100, #69, #48): High due to unauthorized access after state changes
- **DoS of critical functions** (#402, #150, #528): High when keeper/liquidation mechanisms fail  
- **Silent failures** (#93, #91): High because users lose funds without error indication
- **Arithmetic failures** (#528, #138): High when automation breaks due to edge cases

## NEW Vulnerability Patterns (Not Covered by Known Findings)

### 1. **Permissionless Oracle Component Removal**
**Source**: Paraspace #402 - Anyone can remove oracle feeders
**Pattern**: Unlike oracle staleness (covered in M-01/M-03), this is about directly disabling oracle infrastructure

**Chainlink V2 Application**:
- **Location**: `PriceManager.sol` - could have functions to manage Data Streams or fallback feeds
- **Vulnerability**: If there are permissionless functions to disable/remove price feed sources
- **Attack**: Malicious actor removes all price feeds → `_getAssetPrice()` fails → auction `bid()` and `performUpkeep()` revert
- **Role Required**: Permissionless (if vulnerable function exists)
- **Severity**: **High** - Complete DoS of auction system

### 2. **Dutch Auction Arithmetic Underflow**  
**Source**: Maia #528 - getRebalance underflow when price moves beyond expected range
**Pattern**: Price-based calculations failing when market moves to extreme values

**Chainlink V2 Application**:
- **Location**: `BaseAuction.sol` - Dutch auction price calculation in `bid()` or `performUpkeep()`
- **Vulnerability**: If auction uses `currentPrice - timeElapsed * priceDecrease` without underflow protection
- **Attack**: Wait for auction duration to exceed price range → arithmetic underflow → `performUpkeep()` reverts
- **Role Required**: Permissionless (anyone can trigger via time passage)
- **Severity**: **Medium** - DoS of specific auction, not system-wide

### 3. **CowSwap Settlement Slippage Vulnerability**
**Source**: Canto #102 - TradeInputForExactOutput with unsafe maximum amount  
**Pattern**: Using entire balance as maximum input without proper slippage protection

**Chainlink V2 Application**:
- **Location**: `AuctionBidder.sol` - CowSwap integration in `_multiCall()` after auction callback
- **Vulnerability**: If settlement uses entire token balance as maximum input to swap operations
- **Attack**: Manipulate market during settlement → excessive slippage → significant value loss
- **Role Required**: AUCTION_BIDDER_ROLE + market manipulation
- **Severity**: **Medium** - Bounded loss per auction (not infinite drain)

### 4. **ERC20 Token Pausing Breaking Automation**
**Source**: Ethos #150 - Keeper functions fail when external contracts are paused
**Pattern**: Different from oracle staleness - this is about token contract state changes

**Chainlink V2 Application**:
- **Location**: `BaseAuction.sol` - `performUpkeep()` and `bid()` functions
- **Vulnerability**: If USDC/WETH/LINK tokens implement pausable functionality  
- **Attack**: Not directly exploitable, but paused tokens → transfer failures → automation breakdown
- **Role Required**: Token admin (external) or coincidental pausing
- **Severity**: **Low** - Temporary DoS until unpausing, external dependency

### 5. **Auction Configuration for Non-Existent Assets**
**Source**: Mimo #68 - Configuration set for non-existing entities
**Pattern**: Missing existence validation when setting up automation/management

**Chainlink V2 Application**:
- **Location**: Admin functions that configure new auction parameters
- **Vulnerability**: If auction can be configured for tokens not yet added to system
- **Attack**: Configure auction for non-existent token → partial system state corruption
- **Role Required**: AUCTION_WORKER_ROLE or admin roles  
- **Severity**: **Low** - Configuration error, not direct value loss

## Conclusion

**NEW vulnerabilities identified: 5 patterns**
- **1 High severity**: Permissionless oracle component removal  
- **2 Medium severity**: Dutch auction underflow, CowSwap slippage
- **2 Low severity**: ERC20 pausing, invalid auction configuration

The most critical new pattern is **permissionless oracle disruption** (#1), which differs from the known oracle staleness issues by allowing direct disabling of price infrastructure rather than waiting for stale data.

**Note**: These are potential vulnerability patterns based on historical findings. Actual exploitation would require examining the specific Chainlink V2 implementation to confirm vulnerable code paths exist.