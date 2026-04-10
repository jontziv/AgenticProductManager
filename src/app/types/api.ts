// ── Shared API types ────────────────────────────────────────────────────────

export type RunStatus =
  | "queued"
  | "processing"
  | "needs_review"
  | "qa_failed"
  | "qa_passed"
  | "approved"
  | "exported"
  | "failed"
  | "cancelled";

export type JobStatus = "queued" | "running" | "completed" | "failed" | "cancelled";

export type ArtifactType =
  | "problem_framing"
  | "personas"
  | "mvp_scope"
  | "success_metrics"
  | "user_stories"
  | "backlog_items"
  | "test_cases"
  | "risks"
  | "architecture"
  | "qa_report"
  | "export_pack";

export type ArtifactStatus = "generating" | "ready" | "stale" | "failed";

export interface ApiError {
  detail: string;
  code?: string;
  run_id?: string;
}

// ── Run ──────────────────────────────────────────────────────────────────────

export interface IntakeRunSummary {
  id: string;
  title: string;
  status: RunStatus;
  created_at: string;
  updated_at: string;
  artifact_count: number;
  qa_score?: number;
}

export interface AgentLogEntry {
  node: string;
  summary: string;
  ts: string;
}

export interface IntakeRun {
  id: string;
  user_id: string;
  title: string;
  status: RunStatus;
  graph_thread_id?: string;
  current_node?: string;
  missing_info: string[];
  run_logs: AgentLogEntry[];
  raw_requirements?: string;
  created_at: string;
  updated_at: string;
  source_documents: SourceDocument[];
  artifacts: ArtifactRecord[];
  latest_qa_report?: QaReport;
  missing_info_flags?: string[];
  idea_classification?: string;
  selected_pattern?: string;
}

export interface CreateRunPayload {
  title: string;
  meeting_notes?: string;
  raw_requirements: string;
  business_idea: string;
  constraints?: string;
  timeline?: string;
  target_users: string;
  assumptions?: string;
  audio_file_url?: string;
}

// ── Source Documents ─────────────────────────────────────────────────────────

export interface SourceDocument {
  id: string;
  run_id: string;
  doc_type: "meeting_notes" | "requirements" | "business_idea" | "constraints" | "audio_transcript";
  content: string;
  created_at: string;
}

// ── Artifacts ────────────────────────────────────────────────────────────────

export interface ArtifactRecord {
  id: string;
  run_id: string;
  artifact_type: ArtifactType;
  version: number;
  content: ArtifactContent;
  status: ArtifactStatus;
  created_at: string;
  updated_at: string;
}

export type ArtifactContent =
  | ProblemFramingArtifact
  | PersonasArtifact
  | MvpScopeArtifact
  | SuccessMetricsArtifact
  | UserStoriesArtifact
  | BacklogArtifact
  | TestCasesArtifact
  | RisksArtifact
  | ArchitectureArtifact;

export interface ProblemFramingArtifact {
  problem_statement: string;
  opportunity: string;
  hypothesis: string;
  goals: string[];
  non_goals: string[];
  assumptions: string[];
}

export interface Persona {
  name: string;
  role: string;
  archetype: string;
  goals: string[];
  pain_points: string[];
  behaviors: string[];
  jobs_to_be_done: string[];
}

export interface PersonasArtifact {
  personas: Persona[];
}

export interface MvpScopeArtifact {
  in_scope: string[];
  out_of_scope: string[];
  core_features: CoreFeature[];
  deferred_features: string[];
}

export interface CoreFeature {
  id: string;
  name: string;
  description: string;
  rationale: string;
  priority: "P0" | "P1" | "P2";
}

export interface SuccessMetric {
  id: string;
  category: string;
  metric_name: string;
  description: string;
  target: string;
  baseline?: string;
  signal_type: "leading" | "lagging";
  measurement_method: string;
}

export interface SuccessMetricsArtifact {
  metrics: SuccessMetric[];
}

export interface UserStory {
  id: string;
  persona_ref: string;
  as_a: string;
  i_want: string;
  so_that: string;
  acceptance_criteria: string[];
  priority: "High" | "Medium" | "Low";
  estimated_effort: string;
  epic: string;
  linked_test_ids: string[];
}

export interface UserStoriesArtifact {
  stories: UserStory[];
}

export interface BacklogItem {
  epic: string;
  epic_description: string;
  story_ids: string[];
  priority_rationale: string;
}

export interface BacklogArtifact {
  epics: BacklogItem[];
  total_story_count: number;
}

export interface TestCase {
  id: string;
  story_id?: string;
  scenario: string;
  preconditions: string[];
  steps: string[];
  expected_result: string;
  test_type: "unit" | "integration" | "e2e" | "manual";
  priority: "High" | "Medium" | "Low";
}

export interface TestCasesArtifact {
  test_cases: TestCase[];
}

export interface Risk {
  id: string;
  category: "technical" | "business" | "user_experience" | "operational" | "compliance";
  description: string;
  likelihood: "High" | "Medium" | "Low";
  impact: "High" | "Medium" | "Low";
  mitigation: string;
  owner: string;
  linked_artifact?: string;
}

export interface RisksArtifact {
  risks: Risk[];
}

export interface ArchitectureOption {
  name: string;
  description: string;
  components: string[];
  data_flow: string;
  pros: string[];
  cons: string[];
  cost_profile: string;
  recommended: boolean;
}

export interface ArchitectureArtifact {
  options: ArchitectureOption[];
  recommended_option: string;
  rationale: string;
  non_functional_requirements: string[];
  technical_considerations: string[];
}

// ── QA ───────────────────────────────────────────────────────────────────────

export type CheckStatus = "passed" | "failed" | "warning";

export interface QaCheck {
  id: string;
  category: string;
  name: string;
  description: string;
  status: CheckStatus;
  score: number;
  max_score: number;
  findings: string[];
  remediation?: string;
  artifact_type?: ArtifactType;
  artifact_field?: string;
}

export interface QaReport {
  id: string;
  run_id: string;
  overall_score: number;
  max_score: number;
  pass_rate: number;
  critical_issues: number;
  warnings: number;
  export_ready: boolean;
  checks: QaCheck[];
  remediation_tasks: RemediationTask[];
  created_at: string;
}

export interface RemediationTask {
  id: string;
  check_id: string;
  description: string;
  affected_artifact: ArtifactType;
  priority: "high" | "medium" | "low";
  auto_fixable: boolean;
}

// ── Jobs ─────────────────────────────────────────────────────────────────────

export interface JobRecord {
  id: string;
  run_id: string;
  job_type: string;
  status: JobStatus;
  progress?: number;
  current_step?: string;
  error_message?: string;
  retry_count: number;
  created_at: string;
  updated_at: string;
}

// ── Approvals ────────────────────────────────────────────────────────────────

export type ApprovalDecision = "approved" | "rejected" | "pending";

export interface Approval {
  id: string;
  run_id: string;
  user_id: string;
  decision: ApprovalDecision;
  comment?: string;
  created_at: string;
}

// ── Exports ──────────────────────────────────────────────────────────────────

export type ExportFormat = "markdown" | "json" | "html" | "jira_csv" | "linear_csv";

export interface ExportRecord {
  id: string;
  run_id: string;
  format: ExportFormat;
  file_url: string;
  file_size_bytes: number;
  generated_at: string;
}

export interface ExportPackRequest {
  run_id: string;
  formats: ExportFormat[];
}
