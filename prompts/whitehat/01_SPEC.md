# ==========  PROMPT START  ==========
# Task Name
Generate WHITEHAT_01_SPEC.json from https://reth.rs/overview

# 🎯 Goal
Before beginning a source‑code security audit, produce a *comprehensive* specification
that captures:
1.   Current architecture (components, data‑flow, deployment topology)
2.   Concrete user‑flows (end‑to‑end, numbered)
3.   API / CLI surface & key algorithms
4.   Security‑critical behaviour & requirements
5.   Historical change‑log and version deltas

# 📥 Input
- Root URL: {{TARGET_URL}}
- Crawl **all** sidebar / in‑page navigation and descendants using **breadth‑first** strategy.
- Select the **latest stable release** when multiple versions exist; fall back to “main” / “master”.
- While crawling, extract:
  * Markdown, HTML, PDF, code files, CHANGELOGs, RELEASE‑NOTES.
  * In‑source docs (Javadoc, Rustdoc, Go doc comments, etc.).

# 📤 Output
Write a single JSON file at
`security-agent/outputs/WHITEHAT_01_SPEC.json`
using the schema below (strict order & naming). **Do not return anything else.**

```jsonc
{
  "metadata": {
    "source_url": "{{TARGET_URL}}",
    "spec_generated_at": "<RFC3339 timestamp>",
    "latest_tag_or_commit": "<tag|commit-hash>",
    "latest_release_date": "<YYYY-MM-DD>",
    "schema_version": "1.0.0"
  },
  "architecture": {
    "overview": "High‑level paragraph summary.",
    "components": [
      {
        "name": "ComponentA",
        "type": "service|library|contract|ui|db|other",
        "description": "What it does and boundaries.",
        "technology": ["Go", "PostgreSQL", "EVM bytecode"],
        "depends_on": ["ComponentB", "ExternalAPI"]
      }
    ],
    "data_flow_diagram": "Mermaid code block in string form (flowchart TD…)"
  },
  "user_flows": [
    {
      "id": 1,
      "title": "User registers and performs first transaction",
      "actors": ["EndUser", "BackendService"],
      "preconditions": ["Wallet installed"],
      "steps": [
        "1. User navigates to /signup",
        "2. System validates email and creates account",
        "3. …"
      ],
      "postconditions": ["Account state = Active"]
    }
  ],
  "api_surface": {
    "rest_endpoints": [
      {"method": "POST", "path": "/v1/login", "auth": "JWT", "description": "…"}
    ],
    "cli_commands": [
      {"command": "tool build --release", "description": "Compile binary"}
    ],
    "smart_contract_interfaces": [
      {"name": "IERC20.transfer", "selector": "0xa9059cbb", "description": "…"}
    ]
  },
  "changelog": {
    "latest_version": "<vX.Y.Z>",
    "since_previous": [
      {"commit": "abc1234", "date": "2025-06-01", "summary": "Fixed re‑entrancy bug"}
    ],
    "breaking_changes": ["Removed legacy /v0 endpoints"]
  },
  "security_requirements": [
    {
      "id": "SR‑001",
      "description": "All state‑transition functions must be idempotent.",
      "risk_category": "integrity",
      "related_components": ["SmartContracts/Exchange"],
      "references": ["CWE‑1148", "EIP‑2535"]
    }
  ]
}
````

# 🛠️ Methodology (follow rigorously)

1. **Breadth‑first crawl** until every link inside the same domain (or documentation host) is exhausted.
2. Deduplicate by URL & heading slug to avoid repeated content.
3. Prefer *latest* tag/branch; ignore obsolete `legacy/` or `v0.*` unless the latest release references them.
4. Generate summaries with <= 120 words per section; be factual, no speculation.
5. Infer implicit security requirements (e.g., “must resist replay attacks”) from protocol descriptions.
6. For changelog, diff the two most recent releases and list *only* user‑visible behaviour changes.
7. Validate final JSON against the schema above before writing the file.
8. Output **nothing** to the chat stream—only write the file.

# 📚 Quality levers

* Use bullet extraction → reflection → rewriting loops for fidelity.
* Employ chain‑of‑thought *internally*; show only the final JSON in the file.
* Cite source URLs in inline comments inside JSON when ambiguity exists.

# ✅ Success criteria

* File exists & is valid JSON.
* All five sections populated and non‑empty.
* User‑flows are concrete, numbered, and cover ≥ 80 % of documented features.
* Security‑requirements list ≥ 5 items, each mapped to components.

# ==========  PROMPT END  ==========