
---
Description: [ORCHESTRATOR] Use the spec-discovery skill to find all specification documents from a seed URL.
Usage: `/01a_crawl URL=... [OUTPUT_FILE=...]`
Example: `/01a_crawl URL=https://ethereum.org/en/developers/docs/ OUTPUT_FILE=outputs/01a_STATE.json`
Language: English only.
Execution hint: This prompt invokes the spec-discovery skill.
---

<task>
  <goal>Use the /spec-discovery skill to find all relevant technical specification documents starting from the provided URL.</goal>
  <input type="param" id="url">{{URL}}</input>
  <output type="file" id="results">{{OUTPUT_FILE}}</output>

  <critical_requirements>
    1. You MUST invoke the `/spec-discovery` skill.
    2. The output of the skill MUST be saved to the file specified by <ref id="results"/>.
  </critical_requirements>

  <instructions>
    1. **Invoke Skill**: Call the `/spec-discovery` skill with the provided `URL` as input.
    2. **Save Output**: Take the JSON output from the skill and write it directly to the path specified in <ref id="results"/>.
    3. **Confirm Completion**: Print a summary of the number of discovered specs and end with: `Output File: {{OUTPUT_FILE}}`
  </instructions>

  <data_sources>
    - **Skill**: `/spec-discovery`
    - **MCP Tools**: `mcp__fetch__fetch` (primary, for static pages), browser tools (fallback, for JS-heavy pages)
  </data_sources>
</task>

<output>
  <format>JSON object</format>
  <stdout>Max 5 lines: summary of discovered specs.</stdout>
  <final_line>Output File: {{OUTPUT_FILE}}</final_line>
</output>
