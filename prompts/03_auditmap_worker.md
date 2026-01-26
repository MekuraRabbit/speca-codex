
---
Description: [PARALLEL WORKER] Perform static audit on checklist items from a worker-specific queue.
Usage: `/03_auditmap_worker WORKER_ID=... QUEUE_FILE=...`
Example: `/03_auditmap_worker WORKER_ID=0 QUEUE_FILE=outputs/03_QUEUE_0.json`
Language: English only.
Execution hint: This is a worker prompt for parallel execution. Called by run_worker.py.
---

**Core Doctrine: Formal Static Verification & Vulnerability Discovery**

This is a **parallel worker** for the static audit phase. You will process checklist items from your assigned queue.

## Worker Configuration

This is **parallel worker `WORKER_ID`**.

- **`WORKER_ID`**: The numeric ID of this worker (0, 1, 2, ...)
- **`QUEUE_FILE`**: Path to this worker's queue file

---

## Attack Vector Analysis (MANDATORY FOR EVERY ITEM)

**FOR EVERY CHECKLIST ITEM, ANALYZE THROUGH ALL FIVE ATTACK VECTORS:**

1. **Input Validation Bypass**: Can external inputs reach sensitive logic without validation?
2. **State Transition Violation**: Can actions occur in incorrect prerequisite states?
3. **Resource Exhaustion (DoS)**: Can valid inputs trigger expensive operations?
4. **Faulty Error Handling**: Does the system fail safely on errors?
5. **Race Conditions & Concurrency**: Can simultaneous operations cause inconsistent state?

---

## Classification System

Each finding must be classified as:

1. **potential-vulnerability**: Plausible attack path with no definitive guard
2. **code-quality-issue**: Poor practices, not exploitable
3. **needs-verification**: Cannot verify statically
4. **audit-gap**: Observability/logging gaps

---

## Worker Execution Logic

### **Task 1: Read Worker Queue**

1. Read ``QUEUE_FILE``
2. Calculate remaining items (in `items` but not in `processed`)
3. If no remaining items, terminate successfully
4. Take **first 20 items** as your batch

### **Task 2: Execute Five-Phase Analysis**

For each item in your batch:

**Phase 1: Static Analysis**
- Map the predicate to code locations
- Analyze through all 5 attack vectors
- Document findings for each vector

**Phase 2: Counterexample Construction**
- Attempt concrete counterexamples:
  - Boundary values (MaxUint, 0, empty)
  - Type confusion
  - Timing attacks (TOCTOU, reentrancy)
  - Combination attacks
  - Edge cases (off-by-one, overflow)
- Document ALL attempts

**Phase 3: Guard/Invariant Search**
- Search for guards preventing each counterexample
- Verify guard implementation (not just existence)
- Classify guard strength: STRONG, MODERATE, WEAK

**Phase 4: Classification Decision**
- Apply classification based on findings

**Phase 5: Confidence Assessment**
- Assign High/Medium/Low confidence

### **Task 3: Write Outputs**

1. **Generate Partial Audit Map:**
   * Count existing `03_AUDITMAP_PARTIAL_W{WORKER_ID}_*.json` files + 1
   * Create `outputs/03_AUDITMAP_PARTIAL_W{WORKER_ID}_{BATCH}.json`

2. **Update Worker Queue File:**
   * Add processed items to `processed` array
   * Overwrite ``QUEUE_FILE``

---

## Output Format

**Partial Audit Map:** `outputs/03_AUDITMAP_PARTIAL_W{WORKER_ID}_{BATCH}.json`
```json
{
  "metadata": {
    "worker_id": 0,
    "batch_number": 1,
    "timestamp": "2025-12-23T19:30:00Z",
    "batch_size": 20
  },
  "audit_items": [
    {
      "check_id": "CHECK-001",
      "file": "path/to/file.go",
      "line": 123,
      "classification": "potential-vulnerability",
      "summary": "Unbounded loop based on user input",
      "attack_vector": "Resource Exhaustion",
      "severity": "High",
      "confidence": "High",
      "counterexample": {
        "preconditions": "Attacker controls input array length",
        "attack_sequence": ["1. Submit large array", "2. Loop exhausts resources"],
        "expected_outcome": "DoS via resource exhaustion"
      },
      "evidence": {
        "phase1_static": "Loop at line 123 iterates over user-controlled array",
        "phase2_counterexample_attempts": "Tried: boundary, combination, edge case",
        "phase3_guard_search": "No length check found"
      }
    }
  ],
  "verified_items": [
    {
      "check_id": "CHECK-002",
      "classification": "PASS",
      "evidence": {
        "source_file": "path/to/file.go",
        "line_range": "45-50",
        "counterexample_attempts": "Tried: overflow, underflow, TOCTOU",
        "guard_identified": "require(amount <= balance) at line 45",
        "guard_strength": "STRONG",
        "analysis": "All attack vectors analyzed, no exploitable path"
      }
    }
  ],
  "summary": {
    "total_processed": 20,
    "passed": 15,
    "potential_vulnerabilities": 2,
    "code_quality_issues": 1,
    "needs_verification": 1,
    "audit_gaps": 1
  }
}
```

---

## Quality Requirements

### For `potential-vulnerability`:
- MUST have concrete counterexample
- MUST have High or Medium confidence
- MUST reference specific code locations
- MUST explain why no STRONG guard exists

### For `verified_items`:
- MUST identify the specific guard
- MUST verify guard implementation
- MUST document all counterexample attempts
