export type Severity = 'Critical' | 'High' | 'Medium' | 'Low' | 'Informational';

export type ReachabilityClassification = 'external-reachable' | 'internal-only' | 'api-only';

export type BugBountyScope = 'in-scope' | 'out-of-scope' | 'conditional';

export type AuditClassification =
  | 'vulnerable'
  | 'vulnerability'
  | 'safe'
  | 'not-a-vulnerability'
  | 'inconclusive'
  | 'potential-vulnerability'
  | 'out-of-scope'
  | 'informational';

export type ReviewVerdict =
  | 'CONFIRMED_VULNERABILITY'
  | 'CONFIRMED_POTENTIAL'
  | 'DISPUTED_FP'
  | 'DOWNGRADED'
  | 'NEEDS_MANUAL_REVIEW'
  | 'PASS_THROUGH';

export type ResolutionStatus =
  | 'resolved'
  | 'not_found'
  | 'specification_only'
  | 'out_of_scope'
  | 'skipped'
  | 'error';

export type PhaseId = '01a' | '01b' | '01e' | '02c' | '03' | '04';

// --- Phase 01a ---
export interface DiscoveredSpec {
  url: string;
  title: string;
  status: string;
  category?: string;
  type?: string;
  layer?: string;
  description?: string;
}

export interface Phase01aData {
  found_specs: DiscoveredSpec[];
  metadata?: Record<string, unknown>;
}

// --- Phase 01b ---
export interface ProgramGraph {
  Q: string[];
  q_init: string;
  q_final: string;
  Act: string[];
  E: [string, string, string][];
}

export interface SubGraph {
  id: string;
  name: string;
  mermaid_file: string;
  program_graph?: ProgramGraph;
  invariants?: string[];
}

export interface SpecSubGraphs {
  source_url: string;
  title: string;
  sub_graphs: SubGraph[];
}

export interface Phase01bData {
  specs: SpecSubGraphs[];
}

// --- Phase 01e ---
export interface PropertyReachability {
  classification: string;
  entry_points: string[];
  attacker_controlled: boolean;
  bug_bounty_scope: string;
}

export interface Property {
  property_id: string;
  text: string;
  type: string;
  assertion: string;
  severity: string;
  covers: string;
  reachability: PropertyReachability;
  exploitability: string;
  bug_bounty_eligible: boolean;
}

export interface Phase01eData {
  properties: Property[];
}

// --- Phase 02c ---
export interface LineRange {
  start: number;
  end: number;
}

export interface CodeLocation {
  file: string;
  symbol: string;
  line_range: LineRange;
  role: string;
  note: string;
}

export interface CodeScope {
  locations: CodeLocation[];
  resolution_status: string;
  resolution_error?: string;
}

export interface PropertyWithCode extends Property {
  code_scope: CodeScope;
  code_excerpt?: string;
}

export interface Phase02cData {
  properties_with_code: PropertyWithCode[];
}

// --- Phase 03 ---
export interface AuditTrail {
  phase1_abstract_interpretation?: Record<string, unknown>;
  phase2_symbolic_execution?: Record<string, unknown>;
  phase2_5_reachability_analysis?: Record<string, unknown>;
  phase3_invariant_proving?: Record<string, unknown>;
  phase3_5_scope_filtering?: Record<string, unknown>;
}

export interface AuditMapItem {
  property_id: string;
  check_id?: string;
  checklist_id?: string;
  classification: string;
  code_scope?: CodeScope | string;
  code_path?: string;
  code_snippet?: string;
  proof_trace?: string;
  bug_bounty_eligible?: boolean;
  summary?: string;
  attack_scenario?: string;
  audit_trail?: AuditTrail;
  // Flat format (older outputs)
  phase1_abstract_interpretation?: Record<string, unknown>;
  phase2_symbolic_execution?: Record<string, unknown>;
  phase3_invariant_proving?: Record<string, unknown>;
}

export interface Phase03Data {
  audit_items: AuditMapItem[];
}

// --- Phase 04 ---
export interface OriginalFinding {
  classification: string;
  summary: string;
}

export interface ReviewedItem {
  property_id: string;
  check_id?: string;
  original_finding?: OriginalFinding;
  original_classification?: string;
  review_verdict: string;
  adjusted_severity: string;
  reviewer_notes: string;
  final_recommendation?: string;
  spec_reference?: string;
}

export interface Phase04Data {
  reviewed_items: ReviewedItem[];
}

// --- Supporting ---
export interface TargetInfo {
  target_repo: string;
  target_ref_type: string;
  target_ref_label: string;
  target_commit: string;
  target_commit_short: string;
}

export interface PartialMetadata {
  phase: string;
  worker_id: number;
  batch_index: number;
  item_count: number;
  timestamp: string;
  processed_ids: string[];
}

// --- Phase data union ---
export type PhaseData =
  | Phase01aData
  | Phase01bData
  | Phase01eData
  | Phase02cData
  | Phase03Data
  | Phase04Data;
