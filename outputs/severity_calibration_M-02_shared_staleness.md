# Severity Calibration: M-02_shared_staleness

Our finding: Single staleness threshold shared between multiple oracle sources (Data Streams + Chainlink feed fallback). Tight threshold kills fallback, loose threshold accepts stale primary.
Current severity: Low

## Precedent Analysis (30 matches)

Looking at the historical precedents, here are the top 5 most relevant findings:

## Top 5 Most Relevant Precedents

**1. Tapioca Medium #1505 - Exact Pattern Match**
- **Severity:** Medium  
- **Pattern:** "Using the same heartbeat for all Chainlink feeds will either result in frequent reverts or stale prices"
- **Comparison:** Nearly identical to our finding - shared staleness threshold across different oracle sources

**2. Paraspace Medium #420 - Fallback Oracle Dysfunction**
- **Severity:** Medium
- **Pattern:** Fallback oracle not used during outages/disagreement due to configuration issues
- **Comparison:** Similar impact - fallback mechanism fails when needed

**3. Salty Medium #501 - Staleness Threshold Too Restrictive**  
- **Severity:** Medium
- **Pattern:** "MAX_ANSWER_DELAY 60 minutes is too short" causing oracle to return 0 price
- **Comparison:** Staleness threshold misconfiguration causing oracle dysfunction

**4. Juicebox High #150 - Missing Staleness Validation**
- **Severity:** High
- **Pattern:** "Chainlink oracle data feed is not further validated and can return stale price"  
- **Comparison:** More severe - complete absence of staleness checks vs misconfigured checks

**5. Asymmetry High #996 - Missing Staleness Checks**
- **Severity:** High  
- **Pattern:** Curve price oracle staleness not checked
- **Comparison:** More severe - no validation vs shared threshold issue

## Trust Model Analysis

- **Our finding:** Permissionless oracle configuration issue
- **High severity precedents:** Often involve trusted roles manipulating oracles (Gogopool) or complete absence of validation (Juicebox)
- **Medium precedents:** Configuration issues in permissionless systems

## Severity Calibration

**Current "Low" severity is too conservative.** 

- **Most relevant precedent (Tapioca #1505)** with identical pattern was rated **Medium**
- **Common severity for this pattern:** Medium for configuration issues, High for missing validation entirely
- **Our finding** sits between these - misconfigured validation rather than absent validation

**Recommendation: Upgrade to Medium severity**

The shared staleness threshold creates a real trade-off where tight thresholds kill the fallback mechanism and loose thresholds accept stale primary data. This directly impacts oracle reliability, which is typically Medium severity in DeFi contexts.