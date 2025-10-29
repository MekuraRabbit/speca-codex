---

**Description:** Generate a comprehensive, citation-rich natural-language specification for a target project by crawling local artefacts and designated references, optionally augmented with vetted web research. Output must conform to `security-agent/outputs/01_SPEC.json`.

**Usage:** `/01_spec <TARGET_DIRECTORY> <CATEGORY_LIST> <PROJECT_NAME> [REFERENCE_URL ...]`

**Example:** `/01_spec ../docs "ethereum-el,zk" "Atlas L2" https://example.com/spec https://example.com/audit`

**Language:** English only.

**Execution hint:** Always run with `/serena` to maximize token efficiency.

**Normative IDs:** Each element emitted under `domains[].normative_spec[]` receives an `id`. Treat this as the canonical `NORMATIVE_ID` for downstream phases (branch naming, `/02_order`, `/03_auditmap`, `/03b_dynamictest`, `/03c_auditissue`).

---

**Goal**

Produce a multi-domain specification for `{{PROJECT_NAME}}` that maintains consistent depth across architecture, normative behavior, algorithms, APIs, threat modeling, observability, runbooks, change history, and bug bounty coverage. Respect the category mix supplied through `CATEGORY_LIST` while retaining generality beyond Ethereum-specific ecosystems.

---

**Scope and Discovery Rules**

- Use `TARGET_DIRECTORY` as the primary crawl root; treat each `REFERENCE_URL` as an additional seed.
- Traverse Markdown, HTML, PDF, source comments, READMEs, release notes, configuration files, test fixtures, and architecture diagrams up to depth five per domain.
- Mirror the repository structure, deduplicate by canonical path or heading, and capture version identifiers (tags, commits, semantic versions) with release dates for critical artefacts.
- Record retrieval timestamps for all external URLs.
- When `CATEGORY_LIST` spans multiple domains, partition findings by domain and call out shared components explicitly.

---

**Web Research Expectations**

- After local crawling, search official documentation portals, RFCs, whitepapers, governance proposals (EIPs, NEPs, etc.), API references, release blog posts, audit reports, and bug bounty programs relevant to the categories.
- Prioritize sources in this order: official repositories, official foundation or standards sites, accredited audit firms, recognized bounty platforms (Immunefi, Sherlock, Code4rena, HackerOne, Bugcrowd), then high-signal community notes.
- If web access is unavailable, continue with local materials and record the limitation in `metadata.research_notes`.

---

**Argument Reference**

- `TARGET_DIRECTORY`: Root path containing local documentation, code, specs, configuration, and tests.
- `CATEGORY_LIST`: Comma-separated descriptors such as `ethereum-el`, `ethereum-cl`, `zk`, `blockchain`, `smart-contract`, `web`, `devops`. Use lowercase kebab-case; the first value is the primary category.
- `PROJECT_NAME`: Human-readable project or upgrade name that must appear throughout the generated specification.
- `REFERENCE_URL`: Optional list of absolute URLs (docs, repositories, audits, RFCs) used as additional crawl seeds.

---

**Category Guide**

- `ethereum-el`: Execution pipeline, EVM deltas, mempool policy, fee markets, Engine API, transaction validity, storage transitions, blob or data-availability bridges.
- `ethereum-cl`: Fork activation, consensus states, validator duties, Beacon APIs, data-availability sampling, sync committees, cross-layer expectations (payload attributes, finality, fork choice).
- `zk`: Circuit architecture, trusted setup, prover and verifier roles, commitment schemes, recursion strategy, performance heuristics, security assumptions, cryptographic parameters.
- `blockchain`: Protocol topology, networking, consensus (PoS, PoW, BFT), block structure, economic incentives, governance hooks, upgrade paths.
- `smart-contract`: Contract architecture, storage layout, role-based access, upgradeability, on-chain invariants, failure modes, integrations (oracles, bridges, token standards).
- `web`: Frontend and backend composition, authentication, session handling, API gateways, third-party services, content security, observability, DevSecOps lifecycle.
- `devops` (or similar): Deployment pipelines, infrastructure-as-code, secrets management, monitoring, compliance dependencies.

---

**Specification Goals**

1. Describe current architecture per domain, including components, data flows, state machines, and inter-domain contracts.
2. Provide normative behavior using RFC 2119 keywords with numbered procedures and clear decision outcomes.
3. Detail APIs, protocols, algorithms, configuration defaults, and error-handling semantics.
4. Enumerate security-critical invariants, threat surfaces, rate limits, custody rules, and economic guardrails.
5. Surface release history (latest two versions) with migration considerations and worked examples for edge cases.

---

**Citation Policy**

- Annotate every descriptive or prescriptive sentence with `[S#]` tokens referencing distinct sources.
- End each narrative string with `Sources: [S1] https://..., [S2] https://...` (comma-separated, no Markdown links).
- Reuse source identifiers consistently and keep them in chronological order when practical.

---

**Output Requirements**

- Emit only `security-agent/outputs/01_SPEC.json`.
- Follow the schema below exactly; do not add or remove keys.
- Keep each narrative block under 250 words and flag unknowns as TODO items with justification and citations.

```
Schema (schema_version = "3.0.0-generic")
{
  "metadata": {
    "source_directory": "{{TARGET_DIRECTORY}}",
    "project_name": "{{PROJECT_NAME}}",
    "spec_generated_at": "<RFC3339 timestamp>",
    "primary_category": "<first entry of CATEGORY_LIST>",
    "secondary_categories": ["<other categories>"],
    "reference_urls": ["<url>", "<url>"],
    "artefact_versions": [
      {"name": "<repo or component>", "tag_or_commit": "<identifier>", "released_at": "<YYYY-MM-DD>", "notes": "<context>"}
    ],
    "research_notes": "Declare missing sources or offline-only coverage.[S1] Sources: [S1] https://...",
    "schema_version": "3.0.0-generic"
  },
  "domains": [
    {
      "name": "<domain label, e.g., Execution Layer>",
      "layer_or_scope": "execution|consensus|zk|application|web|infrastructure|other",
      "genre": "Ethereum Execution Spec|Ethereum Consensus Spec|Zero-Knowledge System|Blockchain Protocol|Smart Contract Suite|Web Platform|DevOps Runbook|Other",
      "architecture": {
        "overview": "Narrative describing scope, lifecycle, activation triggers, dependencies.[S1][S2] Sources: ...",
        "components": [
          {
            "name": "<component>",
            "type": "service|module|contract|circuit|ui|pipeline",
            "description": "Role, trust assumptions, interfaces.[S1] Sources: ...",
            "depends_on": ["<component>", "<external system>"],
            "technology": ["Rust", "EVM", "Halo2", "TypeScript", "Kubernetes"]
          }
        ],
        "state_machines": [
          {
            "name": "<process>",
            "inputs": ["<input>"],
            "outputs": ["<output>"],
            "invariants": ["Invariant stated with MUST/SHOULD and justification.[S1] Sources: ..."],
            "transitions": ["1. Step one.", "2. Step two."]
          }
        ],
        "data_flow_diagram": "Mermaid sequence or flowchart capturing actors, messages, storage, error paths.[S1] Sources: ..."
      },
      "normative_spec": [
        {
          "id": "<unique identifier>",
          "title": "<procedure title>",
          "summary": "Expected behavior overview.[S1] Sources: ...",
          "preconditions": ["Prerequisites and configs.[S1] Sources: ..."],
          "inputs": ["Artifacts consumed"],
          "procedure": [
            "1. Numbered step detailing validations and actions.",
            "2. Enumerate branching decisions with MUST/SHOULD."
          ],
          "postconditions": ["Outcomes and observable effects.[S1] Sources: ..."],
          "errors": [
            {"code": "<ERR_CODE>", "when": "Condition", "effect": "Outcome"}
          ],
          "rationale": "Security, safety, or UX justification.[S1] Sources: ..."
        }
      ],
      "algorithms": [
        {
          "name": "<algorithm or formula>",
          "purpose": "Reason for existence.[S1] Sources: ...",
          "pseudocode": "`pseudo\nfunction algo(...)\n`[S1] Sources: ...",
          "complexity": "O(n) or equivalent",
          "notes": "Corner cases, precision, cryptographic parameters.[S1] Sources: ..."
        }
      ],
      "apis": {
        "interfaces": [
          {
            "kind": "json_rpc|rest|graphql|engine_api|beacon_api|cli|abi",
            "name": "<endpoint or contract function>",
            "stability": "alpha|beta|stable|deprecated",
            "request_schema": "Describe fields and validation.[S1] Sources: ...",
            "response_schema": "Describe outputs and status codes.[S1] Sources: ...",
            "errors": ["List error codes or messages."],
            "notes": "Authentication, rate limits, pagination, retry semantics.[S1] Sources: ..."
          }
        ],
        "events": [
          {
            "name": "<event or log>",
            "payload": {"field": "description"},
            "trigger": "Condition raising the event.[S1] Sources: ...",
            "consumers": ["Services or contracts subscribing"]
          }
        ]
      },
      "data_models": [
        {
          "name": "<structure>",
          "schema": {"field": "type"},
          "constraints": ["Validation rules and ranges.[S1] Sources: ..."],
          "storage": "Persistence target (database, contract storage, commitments).[S1] Sources: ..."
        }
      ],
      "user_flows": [
        {
          "id": 1,
          "title": "<Flow title>",
          "actors": ["User", "Validator", "Web Client"],
          "preconditions": ["Required state."],
          "steps": ["1. Action", "2. Reaction"],
          "postconditions": ["System state or output.[S1] Sources: ..."]
        }
      ],
      "worked_examples": [
        {
          "id": "EX-001",
          "title": "<Scenario>",
          "scenario": "Context of example.[S1] Sources: ...",
          "given": "Initial conditions",
          "when": "Event or input",
          "then": "Expected result with math or reasoning.[S1] Sources: ..."
        }
      ],
      "edge_cases": ["Enumerate pathological scenarios and required handling.[S1] Sources: ..."],
      "compatibility": {
        "upstream": "Dependencies and backwards compatibility.[S1] Sources: ...",
        "downstream": "Consumers relying on this domain.[S1] Sources: ...",
        "external_interfaces": "Cross-protocol or third-party integrations.[S1] Sources: ..."
      },
      "observability": {
        "metrics": ["Key metrics, formulae, alert thresholds.[S1] Sources: ..."],
        "logs": ["Log categories, severity, structured fields.[S1] Sources: ..."],
        "dashboards": "Monitoring expectations or runbooks.[S1] Sources: ..."
      },
      "runbooks": [
        {
          "name": "<Runbook>",
          "triggers": ["Alarm conditions"],
          "steps": ["1. Mitigation", "2. Verification"],
          "resolution": "Success criteria and rollback guidance.[S1] Sources: ..."
        }
      ],
      "changelog": {
        "latest_version": "<tag|branch>",
        "since_previous": [
          {"commit": "<hash>", "date": "<YYYY-MM-DD>", "summary": "User-visible change.[S1] Sources: ..."}
        ],
        "breaking_changes": ["Explicit compatibility breaks.[S1] Sources: ..."]
      },
      "bug_bounty": {
        "scope": "Repos, contracts, services, exclusions.[S1] Sources: ...",
        "impact": "Eligible impact categories and severity tiers.[S1] Sources: ...",
        "exclusions": "Known safe harbors and out-of-scope vectors.[S1] Sources: ...",
        "reproduction": "Proof-of-concept and environment requirements.[S1] Sources: ...",
        "reporting": "Disclosure channels, encryption keys, expected SLA.[S1] Sources: ...",
        "rewards": "Payout structure or point system.[S1] Sources: ..."
      }
    }
  ],
  "cross_domain": {
    "interfaces": [
      {
        "name": "<Cross-domain interface>",
        "participants": ["Domain A", "Domain B"],
        "sequence_diagram": "Mermaid sequence capturing message exchange, authentication, retries.[S1] Sources: ...",
        "constraints": "Latency, throughput, data contracts, authentication.[S1] Sources: ...",
        "error_handling": ["Interface-level errors and fallback policies.[S1] Sources: ..."]
      }
    ],
    "data_availability": "Summaries of data propagation, redundancy, recovery across domains.[S1] Sources: ...",
    "upgrade_paths": "Coordinated rollout steps, migration prerequisites, backward and forward compatibility.[S1] Sources: ..."
  },
  "security_requirements": [
    {
      "id": "SR-001",
      "description": "Normative security statement with MUST or SHOULD language.[S1] Sources: ...",
      "risk_category": "integrity|availability|confidentiality|economic|compliance",
      "related_components": ["List components"]
    }
  ],
  "threat_catalog": {
    "attack_vectors": [
      {"name": "<Threat>", "category": "network|consensus|application|zk|web|infra", "description": "What could happen.[S1] Sources: ...", "mitigations": ["Controls mapped to normative_spec."]}
    ],
    "open_questions": ["Document unknowns or pending design decisions with owners.[S1] Sources: ..."]
  },
  "appendices": {
    "glossary": [
      {"term": "<Term>", "definition": "Definition with citation.[S1] Sources: ..."}
    ],
    "references": [
      {"id": "S1", "title": "<Doc title>", "url": "https://...", "retrieved_at": "<YYYY-MM-DD>"}
    ]
  }
}
```

---

**User-Flow Templates**

- ethereum-el: peer discovery -> tx pool intake -> block building -> Engine API submission -> payload validation.
- ethereum-cl: validator duty scheduling -> gossip subscription -> block proposal -> attestation -> finality.
- zk: witness generation -> circuit proving -> proof aggregation -> on-chain verification.
- smart-contract: admin upgrade -> role-based action -> failure fallback -> monitoring.
- web: user auth -> session issuance -> API call -> data persistence -> audit logging.

---

**Quality and Writing Rules**

- Maintain active voice and precise terminology; place summaries before action lists.
- Declare assumptions explicitly (for example, "Assumes prover nodes have >= 16 GiB RAM") and cite supporting material.
- Keep pseudocode self-contained and specify units for constants or thresholds.
- Flag deprecated or experimental features and propose mitigations or guardrails.

---

**Bug Bounty Integration**

- Map bounty scope to specific domains and components, noting active programs and deadlines.
- Reference official bounty charters; if none exist, add TODO entries with recommended next steps.

---

**Change Log Guidance**

- Compare the two most recent tagged releases or commits per artefact, highlight user-visible changes and migrations, and recommend upgrade or rollback procedures.

---

**Runtime Notes**

- Verify every cited source is reachable. If a source is private or missing, mark the relevant entry as TODO with justification.
- When web search is unavailable, proceed with existing material and document the constraint in `metadata.research_notes`.

---
