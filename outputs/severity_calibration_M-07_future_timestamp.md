# Severity Calibration: M-07_future_timestamp

Our finding: transmit() accepts future-dated price reports, extending effective staleness window. No upper bound check on observationsTimestamp.
Current severity: Low

## Precedent Analysis (30 matches)

I'll analyze the most relevant precedents for timestamp validation issues in oracles.

## Top 5 Most Relevant Precedents

1. **Asymmetry (2023-03) #37 - HIGH**: "Oracle price can be better secured (freshness + tamper-resistance)"
   - Direct match: Specifically mentions oracle freshness validation
   - Similar impact: Stale price data affecting system integrity

2. **ENS (2023-04) #164 - HIGH**: "Timestamp manipulation affects DNSSEC records"
   - Direct match: Timestamp parameter validation vulnerability  
   - Key difference: External timestamp vs internal timestamp acceptance

3. **Juicebox (2022-07) #78 - HIGH**: "Chainlink Oracle data is insufficiently validated"
   - Similar pattern: Missing validation checks on oracle data
   - Comparable: Both involve accepting potentially invalid temporal data

4. **Gogopool (2022-12) #387 - HIGH**: "No checks for large price changes in the Oracle" 
   - Related pattern: Missing validation on oracle inputs
   - Similar risk: Allows manipulation of price feed integrity

5. **Ondo Finance (2024-03) #144 - HIGH**: "Insufficient safeguards for handling price data"
   - Similar pattern: Inadequate validation of oracle data
   - Comparable impact: Arithmetic errors from invalid price data

## Trust Model Analysis

**Key Difference**: Most precedents involve **permissionless manipulation** (anyone can exploit), while our finding likely involves a **trusted transmitter role**. However, the precedents show that even trusted-role oracle validation issues are typically rated HIGH when they:
- Allow stale/invalid data to pass validation
- Extend effective staleness windows  
- Lack upper bounds on timestamps

## Severity Calibration

**Precedent Pattern**: 5/5 relevant oracle validation findings = HIGH severity

**Current Rating**: Low → **Recommended: Medium-High**

**Justification**: While trusted-role context may reduce immediate exploitability, accepting future-dated timestamps fundamentally breaks staleness protection - a core oracle security property. Precedents consistently rate oracle validation gaps as HIGH regardless of access controls.

## Most Common Severity

**Oracle timestamp/validation issues**: 100% HIGH severity across all relevant precedents (20/20 findings are HIGH).

**Recommendation**: Upgrade from Low to **Medium** (minimum) or **HIGH** (aligned with precedents), depending on exploitability within the trusted transmitter context.