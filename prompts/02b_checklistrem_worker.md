
---
Description: [PARALLEL WORKER] Generate audit checklist items for properties from a worker-specific queue.
Usage: `/02b_checklistrem_worker WORKER_ID=... QUEUE_FILE=...`
Example: `/02b_checklistrem_worker WORKER_ID=0 QUEUE_FILE=outputs/02b_QUEUE_0.json`
Language: English only.
Execution hint: This is a worker prompt for parallel execution. Called by run_worker.py.
---
**Always use /serena for development tasks to maximize token efficiency.**

# **Checklist Generation (Parallel Worker)**

**Goal**
Generate audit checklist items for properties assigned to this worker's queue. Process a batch of properties and output checklist items with worker-specific naming.

## Worker Configuration

This is **parallel worker `WORKER_ID`**. You have a dedicated queue file.

- **`WORKER_ID`**: The numeric ID of this worker (0, 1, 2, ...)
- **`QUEUE_FILE`**: Path to this worker's queue file

---

## 1) Inputs

1. **Property Catalog (Reference):** `outputs/01e_PROP.json`
2. **Worker Queue File:** ``QUEUE_FILE``
   - Contains `items`: list of property IDs assigned to this worker
   - Contains `processed`: list of already processed property IDs

---

## 2) Worker Execution Logic

### **Task 1: Read Worker Queue**

1. Read the worker queue file
2. Calculate remaining: property IDs in `items` but not in `processed`
3. If no remaining properties, terminate successfully
4. Take the **first 20 unprocessed property IDs** as your batch

### **Task 2: Generate Checklist Items**

For each property ID in your batch:

1. Look up the full property definition in `outputs/01e_PROP.json`
2. Generate **exactly one** checklist item focusing on the property's `primary_element`
3. Design each checklist item with:
   * `id`: Unique identifier (e.g., `CHECK-W{WORKER_ID}-{PROP_ID}-001`)
   * `property_id`: The source property ID
   * `title`: Descriptive title
   * `bug_class`: Type of vulnerability
   * `severity_hint`: Expected severity
   * `detection_procedure`: How to detect the issue
   * `executable_checks`: Specific verification steps
   * `notes`: Additional context

### **Task 3: Write Outputs**

1. **Generate Partial Checklist:**
   * Determine the batch number (count existing `02b_CHECKLIST_PARTIAL_W{WORKER_ID}_*.json` files + 1)
   * Create file `outputs/02b_CHECKLIST_PARTIAL_W{WORKER_ID}_{BATCH}.json`
   * Include metadata with `worker_id` and `batch_number`

2. **Update Worker Queue File:**
   * Add processed property IDs to the `processed` array
   * Overwrite ``QUEUE_FILE``

---

## 3) Required Output Format (JSON)

**Partial Checklist File:** `outputs/02b_CHECKLIST_PARTIAL_W{WORKER_ID}_{BATCH}.json`
```json
{
  "metadata": {
    "worker_id": 0,
    "batch_number": 1,
    "generated_at": "2025-12-23T10:00:00Z",
    "properties_processed": 20
  },
  "checklist": [
    {
      "id": "CHECK-W0-PROP-STATE-TX-INVALID-001",
      "property_id": "PROP-STATE-TX-INVALID-001",
      "title": "Verify transaction invalidation on signature failure",
      "bug_class": "Input Validation",
      "severity_hint": "High",
      "detection_procedure": "Review signature validation code paths",
      "executable_checks": [
        "Verify all signature types are checked",
        "Confirm invalid signatures lead to transaction rejection"
      ],
      "notes": "Focus on edge cases in signature encoding"
    }
  ]
}
```

**Updated Worker Queue File:** ``QUEUE_FILE``
```json
{
  "worker_id": 0,
  "phase": "02b",
  "total_workers": 4,
  "items": ["PROP-001", "PROP-002", "..."],
  "processed": ["PROP-001", "PROP-002", "..."],
  "total_items": 50
}
```


---

## 4) Quality Requirements

Each checklist item must be:
- **Specific:** Reference concrete code patterns or behaviors
- **Actionable:** Provide clear steps for verification
- **Prioritized:** Include severity hints based on impact
- **Traceable:** Link back to source property ID
