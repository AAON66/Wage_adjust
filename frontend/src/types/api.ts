export interface ApiErrorPayload {
  error: string;
  message: string;
  details?: unknown;
}

export interface UserProfile {
  id: string;
  email: string;
  role: string;
  created_at: string;
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

export interface LoginPayload {
  email: string;
  password: string;
}

export interface RegisterPayload extends LoginPayload {
  role: string;
}

export interface EmployeeRecord {
  id: string;
  employee_no: string;
  name: string;
  department: string;
  job_family: string;
  job_level: string;
  manager_id: string | null;
  status: string;
  created_at: string;
  updated_at: string;
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
}

export interface CycleRecord {
  id: string;
  name: string;
  review_period: string;
  budget_amount: string;
  status: string;
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
  created_at: string;
  size_label?: string;
}

export interface UploadedFileListResponse {
  items: UploadedFileRecord[];
  total: number;
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
  raw_score: number;
  weighted_score: number;
  rationale: string;
  created_at: string;
}

export interface EvaluationRecord {
  id: string;
  submission_id: string;
  overall_score: number;
  ai_level: string;
  confidence_score: number;
  explanation: string;
  status: string;
  created_at: string;
  updated_at: string;
  needs_manual_review: boolean;
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

export interface DashboardSnapshotResponse {
  overview: DashboardOverviewResponse;
  ai_level_distribution: DashboardDistributionResponse;
  roi_distribution: DashboardDistributionResponse;
  heatmap: DashboardHeatmapResponse;
}

export interface ImportJobRecord {
  id: string;
  file_name: string;
  import_type: string;
  status: 'pending' | 'queued' | 'processing' | 'completed' | 'failed';
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
