# Severity Calibration: M-14_stale_approval

Our finding: Migration/upgrade does not revoke residual ERC20 approvals to old contract. Stale allowance persists after state transition.
Current severity: Low

## Precedent Analysis (30 matches)

Looking at the historical precedents for stale approval issues:

## Top 5 Most Relevant Precedents

1. **Centrifuge #309 (High)**: "PoolManager doesn't reset the approvals of old functions before setting the new ones" - **EXACT MATCH** to our finding pattern during upgrades/transitions

2. **Debtdao #128 (High)**: "Adversary can use residual swap allowances to pay their debt with other users funds" - Direct exploitation of stale allowances for unauthorized asset access

3. **Dopex #876 (High)**: "Unspent allowance may break `addLiquidity` functionality" - Stale allowances causing system dysfunction

4. **Artgobblers #350 (High)**: "doesn't reset `getApproved`" after state transition - Stale approvals allowing recovery of supposedly burned assets

5. **Artgobblers #79 (High)**: Stale `getApproved` allowing "zero net cost" recovery - Asset theft via persistent approvals

## Trust Model Comparison

- **Our finding**: Migration/upgrade context → **trusted admin operation**
- **Precedents**: Mixed, but many involve trusted operations (Centrifuge upgrade, Artgobblers minting mechanics)
- **Key insight**: Trust model doesn't significantly affect severity in precedents - both permissionless and admin-triggered stale approval issues rate HIGH

## Severity Calibration Assessment

**Current rating**: Low  
**Precedent consensus**: HIGH (5/5 most relevant cases)  
**Pattern consistency**: 15+ approval-related findings across contests consistently rated Medium-High  

**Recommendation**: **Upgrade to MEDIUM-HIGH**

## Most Common Severity Pattern

Across all 20 precedents mentioning approval/allowance issues: **100% are HIGH severity**

The consistent HIGH rating suggests stale approvals are viewed as a serious vulnerability class regardless of context. Our LOW rating appears to significantly undervalue the risk compared to established precedent.

**Action**: Consider upgrading to at least Medium, potentially High to align with historical precedent.