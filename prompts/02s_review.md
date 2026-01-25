
---
Description: Review and validate the outputs from Stages 01a through 01e. Apply Chain of Thought, Tree of Thoughts, and Reflexion techniques to ensure completeness, consistency, and correctness of the formal model.
Usage: `/02s_review`
Language: English only.
Execution hint: Run after `/01e_prop`. This is a quality gate before proceeding to checklist generation.
---

# **Preparation Phase Review Prompt (Enhanced with Prompt Engineering)**

**Goal**
Review and validate the outputs from Stages 01a through 01e. This prompt applies advanced prompt engineering techniques—**Chain of Thought (CoT)**, **Tree of Thoughts (ToT)**, and **Reflexion**—to ensure the formal model is complete, consistent, and correct before proceeding to the audit phase.

**Output (required file):** `outputs/02s_REVIEW_REPORT.json`

---

## 1) Inputs

1.  **System Specification:** `outputs/01_SPEC.json`
2.  **Trust Model:** `outputs/01d_TRUSTMODEL.json`
3.  **Property Catalog:** `outputs/01e_PROP.json`

---

## 2) Reviewer Mindset (Meta-Prompting)

You are a **skeptical senior security analyst**. Your role is to find flaws, inconsistencies, and gaps in the formal model. Adopt the following mindset:

| Principle | Description |
|-----------|-------------|
| **Zero Trust Thinking** | Do not assume any part of the model is correct. Verify everything. |
| **Adversarial Thinking** | Consider how an attacker might exploit gaps or ambiguities in the model. |
| **Root Cause Pursuit** | When you find an issue, trace it back to its source (which stage, which input). |
| **Burden of Proof** | The model is guilty until proven innocent. Document evidence for every "PASS" verdict. |

---

## 3) Review Phases (Chain of Thought Structure)

Each phase follows a **Thought → Action → Reflection** structure.

### **Phase 1: Specification Completeness Review**

*   **Thought:** "Is the `01_SPEC.json` a complete representation of the system? Are all relevant specifications covered?"
*   **Action:**
    1.  Count the number of source URLs in `processed_urls` (from `01a_STATE.json` if available, or infer from `ambiguities`/`implicit_assumptions` source URLs).
    2.  Verify that all major EIPs and specifications mentioned in the initial `SPEC_URLS` are represented.
    3.  Check for orphan nodes (nodes with no incoming or outgoing edges).
*   **Reflection:** "Did I miss any obvious specifications? Are there any gaps in the graph structure?"

### **Phase 2: Trust Model Consistency Review (Tree of Thoughts)**

*   **Thought:** "Is the trust model consistent with the specification and with security best practices?"
*   **Action (Explore 3 Branches):**
    1.  **Branch A (Entity Coverage):** Verify that every `external_entity` in `01_SPEC.json` has a corresponding entry in `trusted_external_entities`.
    2.  **Branch B (Boundary Edge Coverage):** Verify that every edge with a `source` matching an `external_entity` ID is listed in `boundary_edges`.
    3.  **Branch C (Trust Level Appropriateness):** For each trust level assignment, critically evaluate if it's appropriate. Is `TRUSTED` ever used? If so, is it justified?
*   **Reflection:** "Do all three branches converge on a consistent model? Are there any contradictions?"

### **Phase 3: Adversarial Scenario Testing**

*   **Thought:** "Can I construct an attack scenario that the current model would miss?"
*   **Action:**
    1.  Select 3-5 `boundary_edges` with `UNTRUSTED` or `SEMI_TRUSTED` sources.
    2.  For each, hypothesize an attack (e.g., malformed input, replay attack, injection).
    3.  Trace the attack path through the graph. Does the model have properties that would detect/prevent this attack?
*   **Reflection:** "Did any attack scenario reveal a gap in the property coverage?"

### **Phase 4: Property Coverage Review (Self-Consistency)**

*   **Thought:** "Does the property catalog achieve 100% coverage, and are the reachability analyses correct?"
*   **Action:**
    1.  **Approach A (Node/Edge → Property):** For a sample of 10 nodes and 10 edges, verify that at least one property covers them.
    2.  **Approach B (Property → Node/Edge):** For a sample of 10 properties, verify that the `graph_elements` they reference actually exist in the spec.
    3.  **Approach C (Boundary Cross-Reference):** Verify that every `boundary_edge` has at least one property with `is_boundary_edge: true`.
*   **Reflection:** "Do all three approaches yield consistent results? If not, where is the discrepancy?"

### **Phase 5: Ambiguity and Assumption Handling Review**

*   **Thought:** "Are all ambiguities and implicit assumptions properly addressed in the property catalog?"
*   **Action:**
    1.  For each `ambiguity` in `01_SPEC.json`, verify that at least one property references it via `related_ambiguity_id`.
    2.  For each `implicit_assumption` in `01_SPEC.json`, verify that at least one property references it via `related_assumption_id`.
*   **Reflection:** "Are there any unaddressed ambiguities or assumptions that could lead to security issues?"

---

## 4) Required Output Format (JSON)

**File:** `outputs/02s_REVIEW_REPORT.json`

```json
{
  "metadata": {
    "reviewed_at": "2025-01-16T17:00:00Z",
    "reviewer_mindset": "Skeptical Senior Security Analyst"
  },
  "overall_verdict": "PASS_WITH_OBSERVATIONS",
  "phases": [
    {
      "phase_id": 1,
      "title": "Specification Completeness Review",
      "thought_process": "I need to verify that all relevant specifications are covered...",
      "findings": [
        {
          "type": "OBSERVATION",
          "description": "EIP-7702 is mentioned in EIP-4844 but not found in processed URLs.",
          "severity": "LOW",
          "recommendation": "Consider adding EIP-7702 to the specification crawl."
        }
      ],
      "self_reflection": "The specification appears largely complete, but there may be minor gaps in newer EIPs.",
      "verdict": "PASS_WITH_OBSERVATIONS"
    }
  ],
  "adversarial_scenarios_tested": [
    {
      "scenario_id": "ADV-01",
      "boundary_edge": "EDGE-USER-SUBMIT-TX",
      "attack_hypothesis": "Malformed RLP encoding in transaction data.",
      "path_traced": ["STATE-TX-RECEIVED", "ACTION-DECODE-TX", "STATE-TX-INVALID"],
      "property_coverage": "PROP-BOUNDARY-TX-VALIDATION covers this scenario.",
      "result": "COVERED"
    }
  ],
  "summary": {
    "total_issues": 3,
    "critical": 0,
    "high": 0,
    "medium": 1,
    "low": 2,
    "ready_for_next_phase": true
  }
}
```
