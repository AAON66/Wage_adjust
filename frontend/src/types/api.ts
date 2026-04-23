export interface ApiErrorPayload {
  error: string;
  message: string;
  details?: unknown;
}

export interface UserProfile {
  id: string;
  email: string;
  role: string;
  id_card_no: string | null;
  must_change_password: boolean;
  employee_id: string | null;
  employee_name: string | null;
  employee_no: string | null;
  feishu_open_id: string | null;
  departments: DepartmentRecord[];
  created_at: string;
}

export interface DepartmentRecord {
  id: string;
  name: string;
  description: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface DepartmentListResponse {
  items: DepartmentRecord[];
  total: number;
}

export interface DepartmentCreatePayload {
  name: string;
  description?: string;
  status: string;
}

export interface DepartmentUpdatePayload {
  name?: string;
  description?: string | null;
  status?: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface AuthResponse {
  user: UserProfile;
  tokens: TokenPair;
}

export interface FeishuAuthorizeResponse {
  authorize_url: string;
  state: string;
}

export interface FeishuCallbackPayload {
  code: string;
  state: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface RegisterPayload extends LoginPayload {
  role: string;
  id_card_no?: string | null;
}

export interface ChangePasswordPayload {
  current_password: string;
  new_password: string;
}

export interface EmployeeRecord {
  id: string;
  employee_no: string;
  name: string;
  id_card_no: string | null;
  company: string | null;
  department: string;
  sub_department: string | null;
  job_family: string;
  job_level: string;
  manager_id: string | null;
  status: string;
  bound_user_id: string | null;
  bound_user_email: string | null;
  created_at: string;
  updated_at: string;
}

export interface EmployeeCreatePayload {
  employee_no: string;
  name: string;
  id_card_no: string | null;
  company: string | null;
  department: string;
  sub_department: string | null;
  job_family: string;
  job_level: string;
  manager_id: string | null;
  status: string;
}

export interface EmployeeUpdatePayload {
  employee_no?: string;
  name?: string;
  id_card_no?: string | null;
  company?: string | null;
  department?: string;
  sub_department?: string | null;
  job_family?: string;
  job_level?: string;
  manager_id?: string | null;
  status?: string;
}

export interface EmployeeListResponse {
  items: EmployeeRecord[];
  total: number;
  page: number;
  page_size: number;
}

export interface EmployeeQuery {
  page?: number;
  page_size?: number;
  department?: string;
  job_family?: string;
  status?: string;
  keyword?: string;
}

export interface CycleRecord {
  id: string;
  name: string;
  review_period: string;
  budget_amount: string;
  status: string;
  department_budgets: CycleDepartmentBudgetRecord[];
  created_at: string;
  updated_at: string;
}

export interface CycleListResponse {
  items: CycleRecord[];
  total: number;
}

export interface CycleCreatePayload {
  name: string;
  review_period: string;
  budget_amount: string;
  status: string;
  department_budgets: CycleDepartmentBudgetPayload[];
}

export interface CycleUpdatePayload {
  name?: string;
  review_period?: string;
  budget_amount?: string;
  status?: string;
  department_budgets?: CycleDepartmentBudgetPayload[];
}

export interface CycleDepartmentBudgetRecord {
  id: string;
  department_id: string;
  department_name: string;
  budget_amount: string;
  created_at: string;
  updated_at: string;
}

export interface CycleDepartmentBudgetPayload {
  department_id: string;
  budget_amount: string;
}

export interface SubmissionRecord {
  id: string;
  employee_id: string;
  cycle_id: string;
  self_summary: string | null;
  manager_summary: string | null;
  status: string;
  submitted_at: string | null;
  created_at: string;
  evaluation_id?: string | null;
}

export interface SubmissionListResponse {
  items: SubmissionRecord[];
  total: number;
}

export interface UploadedFileRecord {
  id: string;
  submission_id: string;
  file_name: string;
  file_type: string;
  storage_key: string;
  parse_status: 'pending' | 'parsing' | 'parsed' | 'failed';
  sharing_status?: 'pending' | null;
  sharing_status_label?: string | null;
  created_at: string;
  size_label?: string;
}

export interface SharingCleanupNoticeRecord {
  request_id: string;
  status: 'rejected' | 'expired';
  file_name: string;
  message: string;
  resolved_at?: string | null;
}

export interface UploadedFileListResponse {
  items: UploadedFileRecord[];
  total: number;
  sharing_cleanup_notices: SharingCleanupNoticeRecord[];
}

export interface FileDeleteResponse {
  deleted_file_id: string;
}

export interface ParseResultRecord {
  file_id: string;
  parse_status: 'pending' | 'parsing' | 'parsed' | 'failed';
  evidence_count: number;
}

export interface EvidenceRecord {
  id: string;
  submission_id: string;
  source_type: string;
  title: string;
  content: string;
  confidence_score: number;
  metadata_json: Record<string, unknown>;
  created_at: string;
  tags?: string[];
}

export interface EvidenceListResponse {
  items: EvidenceRecord[];
  total: number;
}

export interface DimensionScoreRecord {
  id: string;
  dimension_code: string;
  weight: number;
  ai_raw_score: number;
  ai_weighted_score: number;
  raw_score: number;
  weighted_score: number;
  ai_rationale: string;
  rationale: string;
  prompt_hash?: string | null;
  created_at: string;
}

export interface EvaluationRecord {
  id: string;
  submission_id: string;
  overall_score: number;
  ai_overall_score: number;
  manager_score: number | null;
  score_gap: number | null;
  ai_level: string;
  confidence_score: number;
  explanation: string;
  manager_comment: string | null;
  hr_comment: string | null;
  hr_decision: string | null;
  status: string;
  created_at: string;
  updated_at: string;
  needs_manual_review: boolean;
  integrity_flagged: boolean;
  integrity_issue_count: number;
  integrity_examples: string[];
  used_fallback?: boolean;
  dimension_scores: DimensionScoreRecord[];
}

export interface SalaryRecommendationRecord {
  id: string;
  evaluation_id: string;
  current_salary: string;
  recommended_ratio: number;
  recommended_salary: string;
  ai_multiplier: number;
  certification_bonus: number;
  final_adjustment_ratio: number;
  status: string;
  created_at: string;
  explanation?: string | null;
}

export interface SalaryHistoryRecord {
  recommendation_id: string;
  evaluation_id: string;
  submission_id: string;
  cycle_id: string;
  cycle_name: string;
  review_period: string;
  current_salary: string;
  recommended_salary: string;
  recommended_ratio: number;
  final_adjustment_ratio: number;
  adjustment_amount: string;
  ai_level: string;
  overall_score: number;
  status: string;
  created_at: string;
}

export interface SalaryHistoryResponse {
  items: SalaryHistoryRecord[];
  total: number;
}

export interface SalarySimulationItem {
  employee_id: string;
  employee_name: string;
  department: string;
  job_family: string;
  evaluation_id: string;
  ai_level: string;
  current_salary: string;
  recommended_salary: string;
  final_adjustment_ratio: number;
}

export interface SalarySimulationResponse {
  cycle_id: string;
  budget_amount: string;
  total_recommended_amount: string;
  over_budget: boolean;
  items: SalarySimulationItem[];
}

export interface ApprovalRecord {
  id: string;
  recommendation_id: string;
  evaluation_id: string;
  employee_id: string;
  employee_name: string;
  department: string;
  cycle_id: string;
  cycle_name: string;
  ai_level: string;
  current_salary: string;
  recommended_salary: string;
  final_adjustment_ratio: number;
  recommendation_status: string;
  approver_id: string;
  approver_email: string;
  approver_role: string;
  step_name: string;
  step_order: number;
  is_current_step: boolean;
  decision: 'pending' | 'approved' | 'rejected' | 'deferred';
  comment: string | null;
  decided_at: string | null;
  created_at: string;
  defer_until: string | null;
  defer_target_score: number | null;
  defer_reason: string | null;
  dimension_scores: DimensionScoreRecord[];
  project_contributors?: ProjectContributorSummary[];
}

export interface ApprovalListResponse {
  items: ApprovalRecord[];
  total: number;
}

export interface ApprovalCandidateRecord {
  recommendation_id: string;
  evaluation_id: string;
  employee_id: string;
  employee_name: string;
  department: string;
  cycle_id: string;
  cycle_name: string;
  ai_level: string;
  current_salary: string;
  recommended_salary: string;
  final_adjustment_ratio: number;
  recommendation_status: string;
  route_preview: string[];
  route_error: string | null;
  can_edit_route: boolean;
  route_edit_error: string | null;
  defer_until: string | null;
  defer_target_score: number | null;
  defer_reason: string | null;
}

export interface ApprovalCandidateListResponse {
  items: ApprovalCandidateRecord[];
  total: number;
}

export interface ApprovalStatusResponse {
  approval_id: string;
  recommendation_id: string;
  decision: 'approved' | 'rejected' | 'deferred';
  recommendation_status: string;
  defer_until: string | null;
  defer_target_score: number | null;
  defer_reason: string | null;
}

export interface ApprovalStepPayload {
  step_name: string;
  approver_id: string;
  comment?: string;
}

export interface DashboardOverviewItem {
  label: string;
  value: string;
  note: string;
}

export interface DashboardOverviewResponse {
  items: DashboardOverviewItem[];
}

export interface DashboardDistributionItem {
  label: string;
  value: number;
  percentage?: number;
}

export interface DashboardDistributionResponse {
  items: DashboardDistributionItem[];
  total: number;
}

export interface DashboardHeatmapCell {
  department: string;
  level: string;
  intensity: number;
}

export interface DashboardHeatmapResponse {
  items: DashboardHeatmapCell[];
  total: number;
}

export interface DashboardCycleSummary {
  cycle_id: string | null;
  cycle_name: string;
  review_period: string;
  status: string;
  budget_amount: string;
}

export interface DashboardDepartmentInsight {
  department: string;
  employee_count: number;
  avg_score: number;
  high_potential_count: number;
  pending_review_count: number;
  approved_count: number;
  budget_used: string;
  avg_increase_ratio: number;
}

export interface DashboardTalentSpotlight {
  employee_id: string;
  employee_name: string;
  department: string;
  ai_level: string;
  overall_score: number;
  recommendation_status: string | null;
  final_adjustment_ratio: number | null;
}

export interface DashboardActionItem {
  title: string;
  value: string;
  note: string;
  severity: string;
}

export interface DashboardSnapshotResponse {
  cycle_summary: DashboardCycleSummary | null;
  overview: DashboardOverviewResponse;
  ai_level_distribution: DashboardDistributionResponse;
  roi_distribution: DashboardDistributionResponse;
  heatmap: DashboardHeatmapResponse;
  department_insights: DashboardDepartmentInsight[];
  top_talents: DashboardTalentSpotlight[];
  action_items: DashboardActionItem[];
}

export interface PublicDimensionScoreRecord {
  dimension_code: string;
  display_score: number;
  raw_score: number;
  weighted_contribution: number;
  weighted_score: number;
  rationale: string;
}

export interface PublicSalaryRecommendationRecord {
  recommendation_id: string;
  status: string;
  current_salary: string;
  recommended_salary: string;
  final_adjustment_ratio: number;
}

export interface PublicLatestEvaluationRecord {
  employee_id: string;
  employee_no: string;
  employee_name: string;
  department: string;
  job_family: string;
  job_level: string;
  cycle_id: string;
  cycle_name: string;
  cycle_status: string;
  submission_id: string;
  evaluation_id: string;
  evaluation_status: string;
  ai_level: string;
  overall_score: number;
  confidence_score: number;
  explanation: string;
  evaluated_at: string;
  dimension_scores: PublicDimensionScoreRecord[];
  salary_recommendation: PublicSalaryRecommendationRecord | null;
}

export interface ImportRowResult {
  row_index: number | null;
  status: 'success' | 'failed';
  message: string;
  error_column?: string;
}

export interface ImportJobRecord {
  id: string;
  file_name: string;
  import_type: string;
  status: 'pending' | 'queued' | 'processing' | 'completed' | 'failed' | 'partial';
  total_rows: number;
  success_rows: number;
  failed_rows: number;
  result_summary: Record<string, unknown>;
  created_at: string;
}

export interface ImportJobListResponse {
  items: ImportJobRecord[];
  total: number;
}

export interface UserListResponse {
  items: UserProfile[];
  total: number;
  page: number;
  page_size: number;
}

export interface UserQuery {
  page?: number;
  page_size?: number;
  role?: string;
  keyword?: string;
}

export interface AdminUserCreatePayload {
  email: string;
  password: string;
  role: string;
  id_card_no?: string | null;
  department_ids?: string[];
}

export interface EmployeeHandbookRecord {
  id: string;
  title: string;
  file_name: string;
  file_type: string;
  storage_key: string;
  parse_status: string;
  summary: string | null;
  key_points_json: string[];
  tags_json: string[];
  uploaded_by_user_id: string | null;
  uploaded_by_email: string | null;
  created_at: string;
  updated_at: string;
}

export interface EmployeeHandbookListResponse {
  items: EmployeeHandbookRecord[];
  total: number;
}

export interface BulkFailureRecord {
  identifier: string;
  message: string;
}

export interface BulkUserCreateResponse {
  created: UserProfile[];
  failed: BulkFailureRecord[];
  total_requested: number;
}

export interface BulkUserDeleteResponse {
  deleted_user_ids: string[];
  failed: BulkFailureRecord[];
  total_requested: number;
}

export interface ContributorInput {
  employee_id: string;
  contribution_pct: number;
}

export interface ProjectContributorSummary {
  employee_id: string;
  employee_name: string;
  contribution_pct: number;
  file_name: string;
  is_owner: boolean;
}

export interface DuplicateFileError {
  error: 'duplicate_file';
  existing_file_id: string;
  uploaded_by: string;
  uploaded_at: string;
  message: string;
}

// === File Sharing (Phase 16) ===

export interface CheckDuplicateRequest {
  content_hash: string;
  submission_id: string;
}

export interface CheckDuplicateResponse {
  is_duplicate: boolean;
  original_file_id: string;
  original_submission_id: string;
  uploader_name: string;
  uploaded_at: string;
}

export interface SharingRequestRecord {
  id: string;
  requester_file_id: string;
  original_file_id: string;
  requester_submission_id: string;
  original_submission_id: string;
  status: 'pending' | 'approved' | 'rejected' | 'expired';
  proposed_pct: number;
  final_pct: number | null;
  resolved_at: string | null;
  created_at: string;
  requester_name: string;
  file_name: string;
  original_uploader_name: string;
  cycle_archived: boolean;
}

export interface SharingRequestListResponse {
  items: SharingRequestRecord[];
  total: number;
}

export interface AuditLogRead {
  id: string;
  operator_id: string | null;
  operator_role: string | null;
  action: string;
  target_type: string;
  target_id: string;
  detail: Record<string, unknown>;
  request_id: string | null;
  created_at: string;
}

export interface AuditLogListResponse {
  items: AuditLogRead[];
  total: number;
  limit: number;
  offset: number;
}

export interface KpiSummaryResponse {
  pending_approvals: number;
  total_employees: number;
  evaluated_employees: number;
  avg_adjustment_ratio: number;
  level_summary: DashboardDistributionItem[];
}

export interface ApprovalPipelineResponse {
  items: DashboardDistributionItem[];
  total: number;
}

export interface DepartmentDrilldownResponse {
  department: string;
  level_distribution: DashboardDistributionItem[];
  avg_adjustment_ratio: number;
  employee_count: number;
}

// === 飞书考勤集成 (Phase 09) ===

export interface FieldMappingItem {
  feishu_field: string;
  system_field: string;
}

export interface FeishuConfigRead {
  id: string;
  app_id: string;
  app_secret_masked: string;
  bitable_app_token: string;
  bitable_table_id: string;
  field_mapping: FieldMappingItem[];
  sync_hour: number;
  sync_minute: number;
  sync_timezone: string;
  is_active: boolean;
}

export interface FeishuConfigCreate {
  app_id: string;
  app_secret: string;
  bitable_app_token: string;
  bitable_table_id: string;
  field_mapping: FieldMappingItem[];
  sync_hour: number;
  sync_minute: number;
  sync_timezone: string;
}

export interface FeishuConfigUpdate {
  app_id?: string;
  app_secret?: string;
  bitable_app_token?: string;
  bitable_table_id?: string;
  field_mapping?: FieldMappingItem[];
  sync_hour?: number;
  sync_minute?: number;
  sync_timezone?: string;
}

export interface SyncTriggerResponse {
  sync_log_id: string;
  status: string;
  message: string;
}

export type SyncLogSyncType =
  | 'attendance'
  | 'performance'
  | 'salary_adjustments'
  | 'hire_info'
  | 'non_statutory_leave';

export type SyncLogStatus = 'running' | 'success' | 'partial' | 'failed';

export interface SyncLogRead {
  id: string;
  sync_type: SyncLogSyncType;
  mode: string;
  status: SyncLogStatus;
  total_fetched: number;
  synced_count: number;
  updated_count: number;
  skipped_count: number;
  unmatched_count: number;
  mapping_failed_count: number;
  failed_count: number;
  leading_zero_fallback_count: number;
  error_message: string | null;
  unmatched_employee_nos: string[] | null;
  started_at: string;
  finished_at: string | null;
  triggered_by: string | null;
}

export interface AttendanceSummaryRead {
  employee_id: string;
  employee_no: string;
  period: string;
  attendance_rate: number | null;
  absence_days: number | null;
  overtime_hours: number | null;
  late_count: number | null;
  early_leave_count: number | null;
  leave_days: number | null;
  data_as_of: string;
}

export interface AttendanceRecordRead extends AttendanceSummaryRead {
  id: string;
  synced_at: string;
}

export interface AttendanceListResponse {
  items: AttendanceRecordRead[];
  total: number;
}

// === API Key Management (Phase 10) ===

export interface ApiKeyRead {
  id: string;
  name: string;
  key_prefix: string;
  is_active: boolean;
  rate_limit: number;
  expires_at: string | null;
  last_used_at: string | null;
  last_used_ip: string | null;
  created_at: string;
  updated_at: string;
  created_by: string;
}

export interface ApiKeyCreatePayload {
  name: string;
  rate_limit?: number;
  expires_at?: string | null;
}

export interface ApiKeyCreateResponse {
  key: ApiKeyRead;
  plain_key: string;
}

export interface ApiKeyRotateResponse {
  key: ApiKeyRead;
  plain_key: string;
  old_key_id: string;
}

// === Webhook Management (Phase 10) ===

export interface WebhookEndpointRead {
  id: string;
  url: string;
  is_active: boolean;
  description: string | null;
  events: string[];
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface WebhookEndpointCreatePayload {
  url: string;
  description?: string;
  events?: string[];
}

// === Account-Employee Binding (Phase 12) ===

export interface SelfBindPreviewResult {
  employee_id: string;
  employee_no: string;
  name: string;
  department: string;
}

export interface EmployeeSearchQuery {
  page?: number;
  page_size?: number;
  keyword?: string;
}

export interface WebhookDeliveryLogRead {
  id: string;
  webhook_id: string;
  event_type: string;
  payload: Record<string, unknown>;
  response_status: number | null;
  response_body: string | null;
  attempt: number;
  success: boolean;
  error_message: string | null;
  created_at: string;
}

// === Eligibility Management (Phase 14) ===

export interface EligibilityRuleResult {
  rule_code: string;
  rule_label: string;
  status: 'eligible' | 'ineligible' | 'data_missing' | 'overridden';
  detail: string;
}

export interface EligibilityResult {
  overall_status: 'eligible' | 'ineligible' | 'pending';
  rules: EligibilityRuleResult[];
}

/**
 * Phase 32.1 D-19: GET /api/v1/eligibility/me 返回扩展类型
 * data_updated_at: ISO 8601 字符串，源自 max(employee/performance/salary_adjustment/leave .updated_at)
 * null 时前端展示「数据从未更新」
 */
export type EligibilityResultWithTimestamp = EligibilityResult & {
  data_updated_at: string | null;
};

export interface EligibilityBatchItem {
  employee_id: string;
  employee_no: string;
  name: string;
  department: string;
  job_family: string | null;
  job_level: string | null;
  overall_status: 'eligible' | 'ineligible' | 'pending';
  rules: EligibilityRuleResult[];
}

export interface EligibilityBatchResponse {
  items: EligibilityBatchItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface EligibilityOverrideRecord {
  id: string;
  employee_id: string;
  employee_no: string;
  employee_name: string;
  requester_id: string;
  requester_name: string;
  override_rules: string[];
  reason: string;
  status: 'pending_hrbp' | 'pending_admin' | 'approved' | 'rejected';
  hrbp_approver_id: string | null;
  hrbp_decision: string | null;
  hrbp_comment: string | null;
  hrbp_decided_at: string | null;
  admin_approver_id: string | null;
  admin_decision: string | null;
  admin_comment: string | null;
  admin_decided_at: string | null;
  year: number;
  reference_date: string | null;
  created_at: string;
  updated_at: string;
}

export interface EligibilityOverrideListResponse {
  items: EligibilityOverrideRecord[];
  total: number;
  page: number;
  page_size: number;
}

export interface EligibilityOverrideCreatePayload {
  employee_id: string;
  override_rules: string[];
  reason: string;
  year?: number;
  reference_date?: string;
}

export interface EligibilityOverrideDecisionPayload {
  decision: 'approve' | 'reject';
  comment?: string;
}

// === Async Task Polling (Phase 22) ===

export interface TaskTriggerResponse {
  task_id: string;
  status: 'pending';
}

export interface TaskStatusResponse {
  task_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress?: { processed: number; total: number; errors: number };
  result?: unknown;
  error?: string;
}

// ===================== Phase 32 调薪资格导入 (IMPORT-01/02/05/06/07) =====================

/** 调薪资格导入支持的 4 种数据类型（与后端 ImportType enum 一一对应）。 */
export type EligibilityImportType =
  | 'performance_grades'
  | 'salary_adjustments'
  | 'hire_info'
  | 'non_statutory_leave';

/**
 * ImportJob 状态机 union — Phase 32 加 'previewing' / 'cancelled'
 * （解决 Pitfall 2 stricter typing：旧 `ImportJobRecord.status` 不含两阶段提交所需新状态）。
 *
 * 状态流：pending → previewing → processing → completed / partial / failed / cancelled
 */
export type ImportJobStatus =
  | 'pending'
  | 'previewing'
  | 'processing'
  | 'completed'
  | 'failed'
  | 'partial'
  | 'cancelled';

/** 覆盖模式：merge=空值保留旧值；replace=空值清空字段（破坏性，需二次确认）。 */
export type OverwriteMode = 'merge' | 'replace';

/** Preview 单行的动作分类（D-08）。 */
export type PreviewRowAction = 'insert' | 'update' | 'no_change' | 'conflict';

/** 字段级 diff（D-08）：old 旧值 / new 新值并排展示。 */
export interface FieldDiff {
  old: unknown | null;
  new: unknown | null;
}

/** Preview 单行结果（D-07 / D-08）。 */
export interface PreviewRow {
  /** Excel 行号（含表头偏移；与 HR 看到的行号一致：pandas idx + 2） */
  row_number: number;
  action: PreviewRowAction;
  employee_no: string;
  fields: Record<string, FieldDiff>;
  conflict_reason?: string | null;
}

/** Preview 4 色计数（D-08）。 */
export interface PreviewCounters {
  insert: number;
  update: number;
  no_change: number;
  conflict: number;
}

/** D-07: preview 端点返回结构。 */
export interface PreviewResponse {
  job_id: string;
  import_type: EligibilityImportType;
  file_name: string;
  total_rows: number;
  counters: PreviewCounters;
  rows: PreviewRow[];
  rows_truncated: boolean;
  truncated_count: number;
  /** ISO datetime 字符串；preview 暂存文件过期时间（D-17） */
  preview_expires_at: string;
  /** 暂存文件 sha256，confirm 阶段后端会再次校验防外部篡改（T-32-14） */
  file_sha256: string;
}

/** confirm 端点请求体（job_id 在 URL path）。 */
export interface ConfirmRequest {
  overwrite_mode: OverwriteMode;
  /** replace 模式下必须为 true（与前端二次确认 modal 的 checkbox 对应；D-11） */
  confirm_replace?: boolean;
}

/** confirm 端点返回结构（执行结果汇总）。 */
export interface ConfirmResponse {
  job_id: string;
  status: Extract<ImportJobStatus, 'completed' | 'partial' | 'failed'>;
  total_rows: number;
  inserted_count: number;
  updated_count: number;
  no_change_count: number;
  failed_count: number;
  execution_duration_ms: number;
  /**
   * Phase 34 W-1：仅 import_type=performance_grades 时填充；其他类型为 null。
   * - completed → 5 秒内重算成功
   * - in_progress → 5 秒超时后台继续
   * - busy_skipped → 撞上 HR 手动重算锁（D-06）
   * - failed → 重算异常（D-04 已落库不阻塞）
   * - skipped → 不适用（非 performance_grades 路径）
   */
  tier_recompute_status?: 'completed' | 'in_progress' | 'busy_skipped' | 'failed' | 'skipped' | null;
}

/** D-18: GET /excel/active?import_type=X 返回（前端轮询锁状态）。 */
export interface ActiveJobResponse {
  active: boolean;
  job_id?: string | null;
  status?: Extract<ImportJobStatus, 'previewing' | 'processing'> | null;
  /** ISO datetime 字符串 */
  created_at?: string | null;
  file_name?: string | null;
}

/** 409 错误响应 detail 结构（D-16 + Plan 04）；body 顶层即为此结构（无 detail 包裹）。 */
export interface ImportConflictDetail {
  error: 'import_in_progress';
  import_type: EligibilityImportType;
  message: string;
}

// ===================== Phase 34 绩效管理 (PERF-01/02/05/08) =====================

/** D-09：tiers_count 4 键（含 'none' 未分档键） */
export interface TierCounts {
  '1': number;
  '2': number;
  '3': number;
  none: number;
}

/** D-09：actual_distribution 仅含 1/2/3 三个分档比例 */
export interface ActualDistribution {
  '1': number;
  '2': number;
  '3': number;
}

/** GET /api/v1/performance/tier-summary 响应（D-09 平铺 9 字段） */
export interface TierSummaryResponse {
  year: number;
  /** ISO datetime（UTC） */
  computed_at: string;
  sample_size: number;
  insufficient_sample: boolean;
  distribution_warning: boolean;
  tiers_count: TierCounts;
  actual_distribution: ActualDistribution;
  skipped_invalid_grades: number;
}

/** 单条绩效记录（GET /api/v1/performance/records 列表项） */
export interface PerformanceRecordItem {
  id: string;
  employee_id: string;
  employee_no: string;
  employee_name: string;
  year: number;
  /** A / B / C / D / E */
  grade: string;
  /** manual / excel / feishu */
  source: string;
  /** D-07：可空。null 时 UI 显示「—」 */
  department_snapshot: string | null;
  /** ISO datetime */
  created_at: string;
}

/** GET /api/v1/performance/records 响应 */
export interface PerformanceRecordsListResponse {
  items: PerformanceRecordItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

/** POST /api/v1/performance/records 请求体 */
export interface PerformanceRecordCreatePayload {
  employee_id: string;
  year: number;
  grade: string;
  source?: 'manual' | 'excel' | 'feishu';
}

/** POST /api/v1/performance/recompute-tiers 响应 */
export interface RecomputeTriggerResponse {
  year: number;
  /** ISO datetime */
  computed_at: string;
  sample_size: number;
  insufficient_sample: boolean;
  distribution_warning: boolean;
  message: string;
}

/** D-10：404 no_snapshot 错误 detail 结构 */
export interface NoSnapshotErrorDetail {
  error: 'no_snapshot';
  message: string;
  year: number;
  hint: string;
}

/** D-06：409 tier_recompute_busy 错误 detail 结构 */
export interface TierRecomputeBusyDetail {
  error: 'tier_recompute_busy';
  message: string;
  year: number;
  retry_after_seconds: number;
}

/** B-3：GET /api/v1/performance/available-years 响应 */
export interface AvailableYearsResponse {
  years: number[];
}

// ===================== Phase 35 员工自助档次 (ESELF-03) =====================

/**
 * Phase 35 D-12: GET /api/v1/performance/me/tier 响应契约
 *
 * 与后端 Pydantic MyTierResponse 一一对应：
 *   - tier 有值 ↔ reason 为 null（员工有档次）
 *   - tier=null ↔ reason 非空（3 种语义分层）
 *
 * 不含 display_label / percentile / rank 等字段 —— 文案本地化由前端负责（D-04）；
 * 排名/百分位属 PIPL 红线不返回（REQUIREMENTS line 89-103）。
 */
export interface MyTierResponse {
  year: number | null;
  tier: 1 | 2 | 3 | null;
  reason: 'insufficient_sample' | 'no_snapshot' | 'not_ranked' | null;
  /** ISO 8601 字符串；snapshot.updated_at；reason='no_snapshot' 时为 null */
  data_updated_at: string | null;
}
