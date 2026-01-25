
---
Description: Recursively crawl all specification documents starting from the provided SPEC_URLS. Discover all unique, relevant specification URLs (EIPs, RFCs, design documents) and create a work queue for the extraction stage. This ensures 100% coverage of the specification landscape.
Usage: `/01a_crawl KEYWORDS=... SPEC_URLS=...`
Example: `/01a_crawl KEYWORDS="geth,ethereum client,EIP,blockchain" SPEC_URLS="https://ethereum.org/en/developers/docs/,https://eips.ethereum.org/"`
Language: English only.
Execution hint: This is the first step. Run this before `/01b_extract`. It creates the work queue for iterative processing.
---

# **System Specification - Stage 1: Discovery & Queuing**

**Goal**
Recursively crawl all specification documents starting from the provided `SPEC_URLS`. The primary goal is to discover all unique, relevant specification URLs (like EIPs, RFCs, design documents) and create a work queue for the next stage. This ensures 100% coverage of the specification landscape.

**Output (required file):** `outputs/01a_STATE.json`

---

## 1) Inputs

1.  **`KEYWORDS`**: A comma-separated list of keywords to filter relevant links during crawling.
2.  **`SPEC_URLS`**: A comma-separated list of initial, top-level specification URLs provided by the user.

---

## 2) Discovery & Queuing Logic

### **Task 2.1: Recursive URL Crawling**

1.  Initialize two lists: `urls_to_visit` and `discovered_urls`.
2.  Add all `SPEC_URLS` to the `urls_to_visit` queue.
3.  **Loop until `urls_to_visit` is empty:**
    a.  Dequeue a URL.
    b.  If this URL is already in `discovered_urls`, continue to the next URL.
    c.  Add the URL to `discovered_urls`.
    d.  Visit the URL and parse its content for all hyperlink (`<a>`) tags.
    e.  For each found link:
        i.  Resolve it to an absolute URL.
        ii. If the URL points to a relevant specification domain (e.g., `eips.ethereum.org`, `github.com/.../specs`) or contains any of the `KEYWORDS`, add it to the `urls_to_visit` queue.

### **Task 2.2: Create the Initial State File**

1.  Once the crawling is complete, create the state file `outputs/01a_STATE.json`.
2.  This file will contain a JSON object with two main keys:
    *   **`work_queue`**: The complete list of `discovered_urls`. This is the master queue for the extraction stage.
    *   **`processed_urls`**: An empty list `[]`. This will be populated in the next stage.

---

## 3) Required Output Format (JSON)

**File:** `outputs/01a_STATE.json`

```json
{
  "metadata": {
    "crawled_at": "2025-01-16T12:00:00Z",
    "keywords": ["geth", "ethereum client", "EIP", "blockchain"],
    "initial_spec_urls": ["https://ethereum.org/en/developers/docs/"],
    "total_discovered": 152
  },
  "work_queue": [
    "https://eips.ethereum.org/EIPS/eip-1559",
    "https://eips.ethereum.org/EIPS/eip-2718",
    "https://eips.ethereum.org/EIPS/eip-2930",
    "https://eips.ethereum.org/EIPS/eip-3198",
    "https://eips.ethereum.org/EIPS/eip-4844"
  ],
  "processed_urls": []
}
```
