
---
Description: [PARALLEL WORKER] Review and verify audit findings from a worker-specific queue.
Usage: `/04_review_worker WORKER_ID=... QUEUE_FILE=...`
Example: `/04_review_worker WORKER_ID=0 QUEUE_FILE=outputs/04_QUEUE_0.json`
Language: English only.
Execution hint: This is a worker prompt for parallel execution. Called by run_worker.py.
---

**Core Doctrine: Formal Verification Review**

This is a **parallel worker** for the audit review phase. You will review and verify audit findings from your assigned queue.

## Worker Configuration

This is **parallel worker `WORKER_ID`**.

- **`WORKER_ID`**: The numeric ID of this worker (0, 1, 2, ...)
- **`QUEUE_FILE`**: Path to this worker's queue file

---

## Review Objectives

For each audit finding, you must:

1. **Verify the finding accuracy**: Is the reported issue real?
2. **Validate the classification**: Is the severity appropriate?
3. **Check the evidence**: Are code references correct?
4. **Assess exploitability**: Can the issue actually be exploited?
5. **Recommend actions**: What should be done about it?

---

## Review Categories

Each reviewed item should be classified as:

1. **confirmed**: The finding is valid and correctly classified
2. **upgraded**: The finding is valid but more severe than reported
3. **downgraded**: The finding is valid but less severe than reported
4. **false-positive**: The finding is incorrect
5. **needs-more-info**: Cannot determine without additional context

---

## Worker Execution Logic

### **Task 1: Read Worker Queue**

1. Read ``QUEUE_FILE``
2. Calculate remaining items (in `items` but not in `processed`)
3. If no remaining items, terminate successfully
4. Take **first 20 items** as your batch

### **Task 2: Review Each Finding**

For each audit item in your batch:

**Step 1: Load the Original Finding**
- Locate the finding in `outputs/03_AUDITMAP_PARTIAL_*.json` files
- Read the full finding details

**Step 2: Verify Code References**
- Navigate to the referenced file and line
- Confirm the code matches the description
- Check if the code has been modified

**Step 3: Validate the Analysis**
- Review the attack vector analysis
- Verify counterexample plausibility
- Check guard identification accuracy

**Step 4: Assess Exploitability**
- Consider real-world attack scenarios
- Evaluate required attacker capabilities
- Estimate impact if exploited

**Step 5: Make Recommendation**
- Confirm, upgrade, downgrade, or reject
- Provide actionable remediation guidance

### **Task 3: Write Outputs**

1. **Generate Partial Review:**
   * Count existing `04_REVIEW_PARTIAL_W{WORKER_ID}_*.json` files + 1
   * Create `outputs/04_REVIEW_PARTIAL_W{WORKER_ID}_{BATCH}.json`

2. **Update Worker Queue File:**
   * Add processed items to `processed` array
   * Overwrite ``QUEUE_FILE``

---

## Output Format

**Partial Review:** `outputs/04_REVIEW_PARTIAL_W{WORKER_ID}_{BATCH}.json`
```json
{
  "metadata": {
    "worker_id": 0,
    "batch_number": 1,
    "timestamp": "2025-12-23T20:00:00Z",
    "items_reviewed": 20
  },
  "reviewed_items": [
    {
      "original_check_id": "CHECK-001",
      "review_status": "confirmed",
      "original_classification": "potential-vulnerability",
      "final_classification": "potential-vulnerability",
      "original_severity": "High",
      "final_severity": "High",
      "verification": {
        "code_exists": true,
        "code_matches_description": true,
        "attack_vector_valid": true,
        "counterexample_plausible": true,
        "guard_assessment_accurate": true
      },
      "exploitability_assessment": {
        "attack_complexity": "Low",
        "required_privileges": "None",
        "user_interaction": "None",
        "impact": "High - service disruption"
      },
      "recommendation": {
        "action": "Fix required",
        "priority": "High",
        "remediation": "Add input length validation before loop",
        "estimated_effort": "Low"
      },
      "reviewer_notes": "Confirmed DoS vulnerability via unbounded loop"
    },
    {
      "original_check_id": "CHECK-002",
      "review_status": "false-positive",
      "original_classification": "potential-vulnerability",
      "final_classification": "PASS",
      "original_severity": "Medium",
      "final_severity": "None",
      "verification": {
        "code_exists": true,
        "code_matches_description": false,
        "reason": "Guard exists at line 42, missed in original analysis"
      },
      "reviewer_notes": "Original analysis missed the validation check"
    }
  ],
  "summary": {
    "total_reviewed": 20,
    "confirmed": 12,
    "upgraded": 1,
    "downgraded": 3,
    "false_positives": 4,
    "needs_more_info": 0
  }
}
```

---

## Quality Requirements

### For `confirmed` findings:
- MUST verify code references are accurate
- MUST validate attack vector analysis
- MUST provide actionable remediation

### For `false-positive` findings:
- MUST explain why the original analysis was incorrect
- MUST identify what was missed or misunderstood
- SHOULD reference the actual code behavior

### For `upgraded` findings:
- MUST explain why severity is higher than reported
- MUST provide additional attack scenarios

### For `downgraded` findings:
- MUST explain mitigating factors
- MUST identify guards or constraints missed
