import axios from 'axios';
import { useEffect, useMemo, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';

import { DuplicateWarningModal } from '../components/evaluation/DuplicateWarningModal';
import { EvidenceCard } from '../components/evaluation/EvidenceCard';
import { EvidenceWorkspaceOverview } from '../components/evaluation/EvidenceWorkspaceOverview';
import { FileList } from '../components/evaluation/FileList';
import { FileUploadPanel } from '../components/evaluation/FileUploadPanel';
import { StatusIndicator } from '../components/evaluation/StatusIndicator';
import { AppShell } from '../components/layout/AppShell';
import { CalibrationCompareTable, type CalibrationCompareRow } from '../components/review/CalibrationCompareTable';
import { DimensionScoreEditor, type DimensionScoreDraft } from '../components/review/DimensionScoreEditor';
import { ReviewPanel } from '../components/review/ReviewPanel';
import { AttendanceKpiCard } from '../components/attendance/AttendanceKpiCard';
import { SalaryHistoryPanel } from '../components/salary/SalaryHistoryPanel';
import { useAuth } from '../hooks/useAuth';
import { submitDefaultApproval } from '../services/approvalService';
import { fetchCycles } from '../services/cycleService';
import { confirmEvaluation, fetchEvaluationBySubmission, generateEvaluation, regenerateEvaluation, submitHrReview, submitManualReview } from '../services/evaluationService';
import {
  deleteSubmissionFile,
  fetchSubmissionEvidence,
  fetchSubmissionFiles,
  importGitHubSubmissionFile,
  parseFile,
  replaceSubmissionFile,
  uploadSubmissionFiles,
  uploadSubmissionFilesWithDuplicate,
  DuplicateFileException,
} from '../services/fileService';
import { checkDuplicate } from '../services/sharingService';
import { computeFileSHA256 } from '../utils/fileHash';
import { fetchEmployee } from '../services/employeeService';
import { fetchSalaryHistoryByEmployee, fetchSalaryRecommendationByEvaluation, recommendSalary, updateSalaryRecommendation } from '../services/salaryService';
import { ensureSubmission } from '../services/submissionService';
import type {
  CycleRecord,
  EmployeeRecord,
  EvaluationRecord,
  EvidenceRecord,
  SalaryHistoryRecord,
  SalaryRecommendationRecord,
  SubmissionRecord,
  UploadedFileRecord,
} from '../types/api';
import { getRoleHomePath } from '../utils/roleAccess';

const DIMENSION_LABELS: Record<string, string> = {
  TOOL_MASTERY: 'AI工具掌握度',
  APPLICATION_DEPTH: 'AI应用深度',
  LEARNING_ABILITY: 'AI学习能力',
  SHARING_CONTRIBUTION: 'AI分享贡献',
  OUTCOME_CONVERSION: 'AI成果转化',
  TOOL: 'AI工具掌握度',
  DEPTH: 'AI应用深度',
  LEARNING: 'AI学习能力',
  SHARING: 'AI分享贡献',
  OUTCOME: 'AI成果转化',
};

const FALLBACK_VISIBLE_STATUSES = ['evaluated', 'reviewing', 'calibrated', 'approved'];

const FLOW = ['collecting', 'submitted', 'parsing', 'evaluated', 'reviewing', 'calibrated', 'approved', 'published'] as const;
const MODULE_KEYS = ['overview', 'parse', 'evidence', 'review', 'salary'] as const;

type DetailModuleKey = (typeof MODULE_KEYS)[number];

type ModuleTab = {
  key: DetailModuleKey;
  label: string;
  note: string;
  helper: string;
};

type FileQueueStatus =
  | 'pending'
  | 'checking'
  | 'currentDuplicate'
  | 'approvedToUpload'
  | 'skipped'
  | 'clean'
  | 'completed'
  | 'failed';

interface FileQueueItem {
  file: File;
  status: FileQueueStatus;
  duplicateInfo?: {
    originalFileId: string;
    originalSubmissionId: string;
    uploaderName: string;
    uploadedAt: string;
  };
}

type BatchParseItemStatus = 'queued' | 'parsing' | 'parsed' | 'failed';

type BatchParseItem = {
  fileId: string;
  fileName: string;
  status: BatchParseItemStatus;
  detail: string;
  evidenceCount: number;
  startedAt: string | null;
  updatedAt: string | null;
};

const MAX_PARSE_CONCURRENCY = 10;

const FLOW_LABELS: Record<string, string> = {
  collecting: '收集材料',
  submitted: '材料就绪',
  parsing: 'AI 解析',
  evaluated: 'AI 评分',
  reviewing: '人工复核',
  calibrated: '结果确认',
  approved: '审批通过',
  published: '结果发布',
};

const EVALUATION_STATUS_LABELS: Record<string, string> = {
  draft: '未生成',
  generated: '已生成',
  pending_manager: '待主管评分',
  pending_hr: '待 HR 审核',
  returned: '已打回',
  confirmed: '已确认',
};

const RECOMMENDATION_STATUS_LABELS: Record<string, string> = {
  draft: '未生成',
  recommended: '已建议',
  pending_approval: '待审批',
  approved: '已审批',
  locked: '已锁定',
};

const FILE_STATUS_LABELS: Record<UploadedFileRecord['parse_status'], string> = {
  pending: '待解析',
  parsing: '解析中',
  parsed: '已解析',
  failed: '解析失败',
};

function resolveError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    return (
      (error.response?.data as { detail?: string; message?: string } | undefined)?.detail ??
      (error.response?.data as { detail?: string; message?: string } | undefined)?.message ??
      '加载员工评估详情失败。'
    );
  }
  return '加载员工评估详情失败。';
}

function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value));
}

function formatTime(value: string | null): string {
  if (!value) {
    return '--';
  }
  return new Intl.DateTimeFormat('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' }).format(new Date(value));
}

function formatCurrency(value: string): string {
  return new Intl.NumberFormat('zh-CN', {
    style: 'currency',
    currency: 'CNY',
    maximumFractionDigits: 0,
  }).format(Number(value));
}

function formatPercent(value: number | null | undefined, digits = 1): string {
  if (value == null) {
    return '--';
  }
  return `${(value * 100).toFixed(digits)}%`;
}

function formatFlowLabel(status: string): string {
  return FLOW_LABELS[status] ?? status;
}

function formatEvaluationStatus(status: string | null | undefined): string {
  if (!status) {
    return '未生成';
  }
  return EVALUATION_STATUS_LABELS[status] ?? status;
}

function formatRecommendationStatus(status: string | null | undefined): string {
  if (!status) {
    return '未生成';
  }
  return RECOMMENDATION_STATUS_LABELS[status] ?? status;
}

function createInitialDimensions(): DimensionScoreDraft[] {
  return [
    { code: 'TOOL', label: 'AI 工具掌握度', weight: 0.15, score: 70, rationale: '等待评估结果。' },
    { code: 'DEPTH', label: 'AI 应用深度', weight: 0.15, score: 70, rationale: '等待评估结果。' },
    { code: 'LEARN', label: 'AI 学习速度', weight: 0.2, score: 70, rationale: '等待评估结果。' },
    { code: 'SHARE', label: '知识分享', weight: 0.2, score: 70, rationale: '等待评估结果。' },
    { code: 'IMPACT', label: '业务影响力', weight: 0.3, score: 70, rationale: '等待评估结果。' },
  ];
}

function formatDimensionLabel(code: string): string {
  return {
    TOOL: 'AI 工具掌握度',
    DEPTH: 'AI 应用深度',
    LEARN: 'AI 学习速度',
    SHARE: '知识分享',
    IMPACT: '业务影响力',
  }[code] ?? code;
}

function formatLevelLabel(level: string): string {
  return {
    'Level 1': '一级',
    'Level 2': '二级',
    'Level 3': '三级',
    'Level 4': '四级',
    'Level 5': '五级',
  }[level] ?? level;
}

const SALARY_LEVEL_RULES: Record<string, { multiplier: number; baseRatio: number; floor: number; ceiling: number }> = {
  'Level 1': { multiplier: 1.0, baseRatio: 0.0, floor: 0.0, ceiling: 0.04 },
  'Level 2': { multiplier: 1.04, baseRatio: 0.03, floor: 0.02, ceiling: 0.08 },
  'Level 3': { multiplier: 1.08, baseRatio: 0.06, floor: 0.04, ceiling: 0.12 },
  'Level 4': { multiplier: 1.13, baseRatio: 0.1, floor: 0.07, ceiling: 0.18 },
  'Level 5': { multiplier: 1.18, baseRatio: 0.14, floor: 0.1, ceiling: 0.22 },
};

const SALARY_JOB_LEVEL_ADJUSTMENTS: Record<string, number> = {
  P4: 0,
  P5: 0.01,
  P6: 0.02,
  P7: 0.03,
};

const SALARY_DEPARTMENT_ADJUSTMENTS: Record<string, number> = {
  Engineering: 0.01,
  研发: 0.01,
  研发中心: 0.01,
  Product: 0.008,
  产品: 0.008,
  产品中心: 0.008,
  Design: 0.005,
  设计: 0.005,
  设计中心: 0.005,
};

const SALARY_JOB_FAMILY_ADJUSTMENTS: Record<string, number> = {
  Platform: 0.01,
  平台: 0.01,
  平台研发: 0.01,
  Product: 0.008,
  产品: 0.008,
  Design: 0.005,
  设计: 0.005,
  Operations: 0.003,
  运营: 0.003,
};

function estimateCurrentSalary(jobLevel: string): number {
  return {
    P4: 35000,
    P5: 45000,
    P6: 60000,
    P7: 80000,
  }[jobLevel] ?? 30000;
}

function resolveSalaryAdjustment(source: Record<string, number>, value: string | null | undefined): number {
  if (!value) {
    return 0;
  }
  const trimmed = value.trim();
  if (!trimmed) {
    return 0;
  }
  if (trimmed in source) {
    return source[trimmed];
  }
  const lowered = trimmed.toLowerCase();
  const matchedKey = Object.keys(source).find((item) => item.toLowerCase() === lowered);
  return matchedKey ? source[matchedKey] : 0;
}

function calculateSalaryPreview(params: {
  aiLevel: string;
  overallScore: number;
  currentSalary: number;
  certificationBonus: number;
  jobLevel: string;
  department: string;
  jobFamily: string;
}) {
  const rule = SALARY_LEVEL_RULES[params.aiLevel] ?? SALARY_LEVEL_RULES['Level 1'];
  const scoreBonus = Math.max(0, Math.min((params.overallScore - 60) / 450, 0.06));
  const jobLevelBonus = SALARY_JOB_LEVEL_ADJUSTMENTS[params.jobLevel] ?? 0;
  const departmentBonus = resolveSalaryAdjustment(SALARY_DEPARTMENT_ADJUSTMENTS, params.department);
  const jobFamilyBonus = resolveSalaryAdjustment(SALARY_JOB_FAMILY_ADJUSTMENTS, params.jobFamily);
  const certificationBonus = Math.max(0, Math.min(params.certificationBonus, 0.12));
  const rawRatio = rule.baseRatio + scoreBonus + certificationBonus + jobLevelBonus + departmentBonus + jobFamilyBonus;
  const finalAdjustmentRatio = Math.max(rule.floor, Math.min(rawRatio, rule.ceiling));
  const recommendedRatio = rule.baseRatio + scoreBonus;
  const recommendedSalary = params.currentSalary * (1 + finalAdjustmentRatio);

  return {
    aiMultiplier: rule.multiplier,
    recommendedRatio,
    certificationBonus,
    finalAdjustmentRatio,
    recommendedSalary,
  };
}

function hasChineseText(value: string): boolean {
  return /[\u4e00-\u9fff]/.test(value);
}

function looksCorruptedText(value: string): boolean {
  const trimmed = value.trim();
  if (!trimmed) {
    return false;
  }
  return /\?{2,}|�|��|锟|Ã|Â|ð|æ|å/.test(trimmed);
}

function localizeDimensionRationale(code: string, rationale: string): string {
  const trimmed = rationale.trim();
  const dimensionLabel = formatDimensionLabel(code);

  if (!trimmed) {
    return '暂无维度说明，等待 AI 重新分析该维度。';
  }
  if (looksCorruptedText(trimmed)) {
    return `当前维度"${dimensionLabel}"的原始说明存在乱码，建议重新执行 AI 评分以生成新的中文说明。`;
  }
  if (hasChineseText(trimmed)) {
    return trimmed;
  }

  const englishPattern = /used\s+(\d+)\s+keyword hits,\s+(\d+)\s+source types,\s+average confidence\s+([\d.]+),\s+and evidence reliability\s+([\d.]+)/i;
  const matched = trimmed.match(englishPattern);
  if (matched) {
    const [, keywordHits, sourceTypes, confidence, reliability] = matched;
    const penaltyMatched = trimmed.match(/(\d+)\s+evidence item\(s\) contained blocked prompt-like instructions and were penalized/i);
    let localized = `当前维度"${dimensionLabel}"识别到 ${keywordHits} 个相关能力信号，覆盖 ${sourceTypes} 类证据来源，平均置信度 ${confidence}，证据可靠度 ${reliability}。`;
    localized += Number(keywordHits) > 2
      ? '该维度证据较充分，能够支撑当前评分判断。'
      : '该维度已有初步支撑，建议结合更多项目细节继续复核。';
    if (penaltyMatched) {
      localized += ` 同时检测到 ${penaltyMatched[1]} 条疑似引导评分内容，相关材料已降权处理。`;
    }
    return localized;
  }

  return `当前维度"${dimensionLabel}"的历史说明为旧版英文内容，建议重新执行 AI 评分以生成新的中文说明。`;
}

function localizeEvaluationNarrative(text: string): string {
  const trimmed = text.trim();
  if (!trimmed) {
    return '暂无综合说明。';
  }
  if (looksCorruptedText(trimmed)) {
    return '当前综合说明存在乱码，建议重新执行 AI 评分以生成新的中文说明。';
  }
  if (hasChineseText(trimmed)) {
    return trimmed;
  }

  const matched = trimmed.match(/Generated from\s+(\d+)\s+evidence items with average confidence\s+([\d.]+)\.\s+The strongest dimension is\s+(.+?),\s+the overall score is\s+([\d.]+),\s+and the result maps to\s+(Level\s+\d)/i);
  if (matched) {
    const [, evidenceCount, confidence, strongestDimension, overallScore, level] = matched;
    return `综合分析基于 ${evidenceCount} 份证据材料，平均置信度 ${confidence}。当前表现最突出的维度是"${formatDimensionLabel(strongestDimension.trim())}"，综合得分 ${overallScore}，对应 ${formatLevelLabel(level)}。`;
  }

  return '当前说明为旧版英文内容，建议重新执行 AI 评分以生成新的中文说明。';
}
function mapEvaluationToDrafts(evaluation: EvaluationRecord | null): DimensionScoreDraft[] {
  if (!evaluation?.dimension_scores.length) {
    return createInitialDimensions();
  }
  const hasManualReview = evaluation.manager_score != null;
  return evaluation.dimension_scores.map((dimension) => ({
    code: dimension.dimension_code,
    label: formatDimensionLabel(dimension.dimension_code),
    weight: dimension.weight,
    aiScore: dimension.ai_raw_score,
    aiRationale: localizeDimensionRationale(dimension.dimension_code, dimension.ai_rationale || dimension.rationale),
    score: hasManualReview ? dimension.raw_score : dimension.ai_raw_score,
    rationale: localizeDimensionRationale(
      dimension.dimension_code,
      hasManualReview ? dimension.rationale : (dimension.ai_rationale || dimension.rationale),
    ),
  }));
}

function toMetadataTag(key: string, value: unknown): string | null {
  if (value == null || value === '') {
    return null;
  }

  const labelMap: Record<string, string> = {
    extension: '类型',
    pages: '页数',
    lines: '行数',
    characters: '字数',
    source_file: '来源',
  };

  if (!(key in labelMap)) {
    return null;
  }

  return `${labelMap[key]}:${String(value)}`;
}

function mapEvidence(item: EvidenceRecord): EvidenceRecord {
  const derivedTags = Object.entries(item.metadata_json ?? {})
    .map(([key, value]) => toMetadataTag(key, value))
    .filter((tag): tag is string => Boolean(tag));
  const originalTags = item.tags ?? [];
  const tags = Array.from(new Set([...originalTags, ...derivedTags])).slice(0, 8);
  return { ...item, tags };
}

function averageDimensionScore(dimensions: DimensionScoreDraft[]): number {
  const totalWeight = dimensions.reduce((sum, dimension) => sum + dimension.weight, 0);
  if (!totalWeight) {
    return 0;
  }
  return Number((dimensions.reduce((sum, dimension) => sum + dimension.score * dimension.weight, 0) / totalWeight).toFixed(1));
}

function inferStatus(
  submission: SubmissionRecord | null,
  files: UploadedFileRecord[],
  evaluation: EvaluationRecord | null,
  recommendation: SalaryRecommendationRecord | null,
): string {
  if (recommendation?.status === 'locked' || recommendation?.status === 'approved') {
    return 'approved';
  }
  if (recommendation?.status === 'pending_approval') {
    return 'reviewing';
  }
  if (evaluation?.status === 'confirmed') {
    return 'calibrated';
  }
  if (evaluation?.status === 'pending_hr' || evaluation?.status === 'returned') {
    return 'reviewing';
  }
  if (evaluation) {
    return 'evaluated';
  }
  if (files.some((file) => file.parse_status === 'parsing')) {
    return 'parsing';
  }
  if (files.some((file) => file.parse_status === 'parsed')) {
    return 'submitted';
  }
  return submission?.status ?? 'collecting';
}

function getParseStatusColor(status: UploadedFileRecord['parse_status']): string {
  return {
    pending: 'var(--color-steel)',
    parsing: 'var(--color-warning)',
    parsed: 'var(--color-success)',
    failed: 'var(--color-danger)',
  }[status];
}

function normalizeModuleKey(value: string | null): DetailModuleKey {
  return MODULE_KEYS.includes(value as DetailModuleKey) ? (value as DetailModuleKey) : 'overview';
}

export function EvaluationDetailPage() {
  const { employeeId } = useParams<{ employeeId: string }>();
  const [searchParams] = useSearchParams();
  const { user } = useAuth();
  const requestedCycleId = searchParams.get('cycleId');
  const requestedTab = searchParams.get('tab');

  const [employee, setEmployee] = useState<EmployeeRecord | null>(null);
  const [cycles, setCycles] = useState<CycleRecord[]>([]);
  const [selectedCycleId, setSelectedCycleId] = useState('');
  const [activeModule, setActiveModule] = useState<DetailModuleKey>(() => normalizeModuleKey(requestedTab));
  const [submission, setSubmission] = useState<SubmissionRecord | null>(null);
  const [files, setFiles] = useState<UploadedFileRecord[]>([]);
  const [evidenceItems, setEvidenceItems] = useState<EvidenceRecord[]>([]);
  const [evaluation, setEvaluation] = useState<EvaluationRecord | null>(null);
  const [salaryRecommendation, setSalaryRecommendation] = useState<SalaryRecommendationRecord | null>(null);
  const [salaryHistory, setSalaryHistory] = useState<SalaryHistoryRecord[]>([]);
  const [dimensions, setDimensions] = useState<DimensionScoreDraft[]>(() => createInitialDimensions());
  const [reviewLevel, setReviewLevel] = useState('Level 3');
  const [reviewComment, setReviewComment] = useState('请填写主管评分依据；如进入 HR 审核，请填写同意或打回原因。');
  const [isUploading, setIsUploading] = useState(false);
  const [pendingContributors, setPendingContributors] = useState<import('../types/api').ContributorInput[]>([]);
  const [fileQueue, setFileQueue] = useState<FileQueueItem[]>([]);
  const [hashCheckStatus, setHashCheckStatus] = useState<'idle' | 'checking' | 'error'>('idle');
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [isGithubImporting, setIsGithubImporting] = useState(false);
  const [isParsingAll, setIsParsingAll] = useState(false);
  const [batchParseTotal, setBatchParseTotal] = useState(0);
  const [batchParseConcurrency, setBatchParseConcurrency] = useState(0);
  const [batchParseItems, setBatchParseItems] = useState<BatchParseItem[]>([]);
  const [lastBatchParseActivityAt, setLastBatchParseActivityAt] = useState<string | null>(null);
  const [parseMonitorNow, setParseMonitorNow] = useState(() => Date.now());
  const [workingFileId, setWorkingFileId] = useState<string | null>(null);
  const [isReviewSubmitting, setIsReviewSubmitting] = useState(false);
  const [isConfirming, setIsConfirming] = useState(false);
  const [isReturning, setIsReturning] = useState(false);
  const [isGeneratingEvaluation, setIsGeneratingEvaluation] = useState(false);
  const [isGeneratingSalary, setIsGeneratingSalary] = useState(false);
  const [isSalaryHistoryLoading, setIsSalaryHistoryLoading] = useState(false);
  const [isSalaryEditorOpen, setIsSalaryEditorOpen] = useState(true);
  const [manualAdjustmentPercent, setManualAdjustmentPercent] = useState('');
  const [manualRecommendedSalary, setManualRecommendedSalary] = useState('');
  const [isSavingSalaryAdjustment, setIsSavingSalaryAdjustment] = useState(false);
  const [isSubmittingApproval, setIsSubmittingApproval] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const canSubmitApproval = user?.role === 'admin' || user?.role === 'hrbp' || user?.role === 'manager';
  const canHrReview = user?.role === 'admin' || user?.role === 'hrbp';
  const canViewSalaryHistory = user?.role === 'admin' || user?.role === 'hrbp' || user?.role === 'manager';

  async function refreshSalaryHistory(targetEmployeeId: string) {
    if (!canViewSalaryHistory) {
      setSalaryHistory([]);
      setIsSalaryHistoryLoading(false);
      return;
    }

    setIsSalaryHistoryLoading(true);
    try {
      const historyResponse = await fetchSalaryHistoryByEmployee(targetEmployeeId);
      setSalaryHistory(historyResponse.items);
    } catch (error) {
      if (axios.isAxiosError(error) && error.response?.status === 403) {
        setSalaryHistory([]);
        return;
      }
      throw error;
    } finally {
      setIsSalaryHistoryLoading(false);
    }
  }

  async function refreshSubmissionData(targetSubmissionId: string) {
    const [filesResponse, evidenceResponse, evaluationResult, salaryHistoryResult] = await Promise.all([
      fetchSubmissionFiles(targetSubmissionId),
      fetchSubmissionEvidence(targetSubmissionId),
      fetchEvaluationBySubmission(targetSubmissionId)
        .then((response) => ({ ok: true as const, response }))
        .catch(() => ({ ok: false as const })),
      employeeId && canViewSalaryHistory
        ? fetchSalaryHistoryByEmployee(employeeId)
            .then((response) => ({ ok: true as const, response }))
            .catch((error: unknown) => ({ ok: false as const, error }))
        : Promise.resolve({ ok: true as const, response: null }),
    ]);

    setFiles(filesResponse.items);
    setEvidenceItems(evidenceResponse.items.map(mapEvidence));

    if (salaryHistoryResult.ok) {
      setSalaryHistory(salaryHistoryResult.response?.items ?? []);
    } else if (axios.isAxiosError(salaryHistoryResult.error) && salaryHistoryResult.error.response?.status === 403) {
      setSalaryHistory([]);
    } else {
      setSalaryHistory([]);
    }

    if (evaluationResult.ok) {
      const evaluationResponse = evaluationResult.response;
      setEvaluation(evaluationResponse);
      setDimensions(mapEvaluationToDrafts(evaluationResponse));
      setReviewLevel(evaluationResponse.ai_level);
      setReviewComment(localizeEvaluationNarrative(evaluationResponse.manager_comment ?? evaluationResponse.hr_comment ?? evaluationResponse.explanation));

      try {
        const recommendationResponse = await fetchSalaryRecommendationByEvaluation(evaluationResponse.id);
        setSalaryRecommendation(recommendationResponse);
      } catch {
        setSalaryRecommendation(null);
      }
    } else {
      setEvaluation(null);
      setSalaryRecommendation(null);
      setDimensions(createInitialDimensions());
      setReviewLevel('Level 3');
      setReviewComment('请填写主管评分依据；如进入 HR 审核，请填写同意或打回原因。');
    }
  }

  async function loadCycleSubmission(targetEmployeeId: string, cycleId: string) {
    const submissionResponse = await ensureSubmission(targetEmployeeId, cycleId);
    setSubmission(submissionResponse);
    await refreshSubmissionData(submissionResponse.id);
  }
  useEffect(() => {
    let cancelled = false;

    async function loadBase() {
      if (!employeeId) {
        setErrorMessage('缺少员工 ID。');
        setIsLoading(false);
        return;
      }

      setIsLoading(true);
      setErrorMessage(null);
      try {
        const [employeeResponse, cycleResponse] = await Promise.all([fetchEmployee(employeeId), fetchCycles()]);
        if (cancelled) {
          return;
        }

        setEmployee(employeeResponse);
        setCycles(cycleResponse.items);

        const fallbackCycleId = cycleResponse.items[0]?.id ?? '';
        const nextCycleId = requestedCycleId && cycleResponse.items.some((cycle) => cycle.id === requestedCycleId)
          ? requestedCycleId
          : fallbackCycleId;
        setSelectedCycleId(nextCycleId);
        setActiveModule(normalizeModuleKey(requestedTab));
      } catch (error) {
        if (!cancelled) {
          setErrorMessage(resolveError(error));
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    void loadBase();
    return () => {
      cancelled = true;
    };
  }, [employeeId, requestedCycleId, requestedTab]);

  useEffect(() => {
    let cancelled = false;

    async function loadSubmissionData() {
      if (!employeeId || !selectedCycleId) {
        return;
      }

      try {
        await loadCycleSubmission(employeeId, selectedCycleId);
      } catch (error) {
        if (!cancelled) {
          setErrorMessage(resolveError(error));
        }
      }
    }

    void loadSubmissionData();
    return () => {
      cancelled = true;
    };
  }, [employeeId, selectedCycleId]);

  useEffect(() => {
    if (!isParsingAll) {
      return;
    }

    const interval = window.setInterval(() => {
      setParseMonitorNow(Date.now());
    }, 1000);

    return () => window.clearInterval(interval);
  }, [isParsingAll]);

  useEffect(() => {
    if (!salaryRecommendation) {
      setIsSalaryEditorOpen(false);
      setManualAdjustmentPercent('');
      setManualRecommendedSalary('');
      return;
    }

    setIsSalaryEditorOpen(true);
    setManualAdjustmentPercent((salaryRecommendation.final_adjustment_ratio * 100).toFixed(2));
    setManualRecommendedSalary(Number(salaryRecommendation.recommended_salary).toFixed(2));
  }, [salaryRecommendation]);

  useEffect(() => {
    if (canViewSalaryHistory || !salaryHistory.length) {
      return;
    }
    setSalaryHistory([]);
  }, [canViewSalaryHistory, salaryHistory.length]);

  const currentCycle = useMemo(() => cycles.find((cycle) => cycle.id === selectedCycleId) ?? null, [cycles, selectedCycleId]);
  const currentStatus = useMemo(() => inferStatus(submission, files, evaluation, salaryRecommendation), [submission, files, evaluation, salaryRecommendation]);
  const activeIndex = Math.max(FLOW.indexOf(currentStatus as (typeof FLOW)[number]), 0);
  const integrityFlagged = Boolean(evaluation?.integrity_flagged);
  const integrityExamples = evaluation?.integrity_examples ?? [];
  const hasFiles = files.length > 0;
  const parsePendingCount = files.filter((file) => file.parse_status === 'pending').length;
  const parseInProgressCount = files.filter((file) => file.parse_status === 'parsing').length;
  const parseCompletedCount = files.filter((file) => file.parse_status === 'parsed').length;
  const parseFailedCount = files.filter((file) => file.parse_status === 'failed').length;
  const needsBatchParse = parsePendingCount > 0 || parseFailedCount > 0;
  const parseProgressPercent = hasFiles ? Math.round(((parseCompletedCount + parseInProgressCount * 0.4) / files.length) * 100) : 0;
  const hasBatchParseSnapshot = batchParseItems.length > 0 && batchParseTotal > 0;
  const batchParseQueuedCount = batchParseItems.filter((item) => item.status === 'queued').length;
  const batchParseRunningCount = batchParseItems.filter((item) => item.status === 'parsing').length;
  const batchParseCompletedRealCount = batchParseItems.filter((item) => item.status === 'parsed').length;
  const batchParseFailedRealCount = batchParseItems.filter((item) => item.status === 'failed').length;
  const batchParseProcessedCount = batchParseCompletedRealCount + batchParseFailedRealCount;
  const batchParseProgressPercent = batchParseTotal > 0
    ? Math.min(
        100,
        Math.round((((batchParseProcessedCount + batchParseRunningCount * 0.35) || 0) / batchParseTotal) * 100),
      )
    : 0;
  const displayedParseProgressPercent = hasBatchParseSnapshot ? batchParseProgressPercent : parseProgressPercent;
  const displayedParseCompletedCount = hasBatchParseSnapshot ? batchParseCompletedRealCount : parseCompletedCount;
  const displayedParseInProgressCount = hasBatchParseSnapshot ? batchParseRunningCount : parseInProgressCount;
  const displayedParsePendingCount = hasBatchParseSnapshot ? batchParseQueuedCount : parsePendingCount;
  const displayedParseFailedCount = hasBatchParseSnapshot ? batchParseFailedRealCount : parseFailedCount;
  const secondsSinceLastBatchActivity = lastBatchParseActivityAt
    ? Math.max(0, Math.floor((parseMonitorNow - new Date(lastBatchParseActivityAt).getTime()) / 1000))
    : 0;
  const batchParsePossiblyStalled = isParsingAll && batchParseRunningCount > 0 && secondsSinceLastBatchActivity >= 15;
  const activeBatchItems = batchParseItems.filter((item) => item.status === 'parsing').slice(0, 6);
  const recentBatchItems = [...batchParseItems]
    .filter((item) => item.updatedAt)
    .sort((left, right) => new Date(right.updatedAt ?? 0).getTime() - new Date(left.updatedAt ?? 0).getTime())
    .slice(0, 8);
  const reviewAverage = averageDimensionScore(dimensions);
  const canEditSalaryRecommendation = Boolean(
    salaryRecommendation &&
    salaryRecommendation.status !== 'pending_approval' &&
    salaryRecommendation.status !== 'approved' &&
    salaryRecommendation.status !== 'locked',
  );
  const baseSalaryAmount = salaryRecommendation ? Number(salaryRecommendation.current_salary) : 0;
  const manualAdjustmentPercentNumber = Number(manualAdjustmentPercent);
  const manualRecommendedSalaryNumber = Number(manualRecommendedSalary);
  const isManualPercentValid = Number.isFinite(manualAdjustmentPercentNumber) && manualAdjustmentPercentNumber >= 0 && manualAdjustmentPercentNumber <= 100;
  const isManualSalaryValid = Number.isFinite(manualRecommendedSalaryNumber) && manualRecommendedSalaryNumber >= baseSalaryAmount;
  const manualAdjustmentRatio = isManualPercentValid ? manualAdjustmentPercentNumber / 100 : null;
  const manualSalaryDelta = salaryRecommendation && isManualSalaryValid ? manualRecommendedSalaryNumber - baseSalaryAmount : null;
  const liveSalaryPreview = useMemo(() => {
    if (!employee || !evaluation) {
      return null;
    }

    const currentSalary = salaryRecommendation ? Number(salaryRecommendation.current_salary) : estimateCurrentSalary(employee.job_level);
    const certificationBonus = salaryRecommendation?.certification_bonus ?? 0;

    return calculateSalaryPreview({
      aiLevel: evaluation.ai_level,
      overallScore: evaluation.overall_score,
      currentSalary,
      certificationBonus,
      jobLevel: employee.job_level,
      department: employee.department,
      jobFamily: employee.job_family,
    });
  }, [employee, evaluation, salaryRecommendation]);
  const recommendationNeedsRefresh = useMemo(() => {
    if (!salaryRecommendation || !liveSalaryPreview) {
      return false;
    }

    return (
      Math.abs(salaryRecommendation.recommended_ratio - liveSalaryPreview.recommendedRatio) > 0.0001 ||
      Math.abs(salaryRecommendation.ai_multiplier - liveSalaryPreview.aiMultiplier) > 0.0001 ||
      Math.abs(salaryRecommendation.certification_bonus - liveSalaryPreview.certificationBonus) > 0.0001 ||
      Math.abs(salaryRecommendation.final_adjustment_ratio - liveSalaryPreview.finalAdjustmentRatio) > 0.0001 ||
      Math.abs(Number(salaryRecommendation.recommended_salary) - liveSalaryPreview.recommendedSalary) > 0.01
    );
  }, [liveSalaryPreview, salaryRecommendation]);

  const calibrationRows = useMemo<CalibrationCompareRow[]>(
    () =>
      dimensions.map((dimension) => {
        const evaluationDimension = evaluation?.dimension_scores.find((item) => item.dimension_code === dimension.code);
        const hasManualComparison = Boolean(evaluation && evaluation.manager_score != null);
        return {
          code: dimension.code,
          label: dimension.label,
          aiScore: evaluationDimension?.ai_raw_score ?? evaluationDimension?.raw_score ?? dimension.score,
          manualScore: hasManualComparison ? dimension.score : null,
          note: hasManualComparison
            ? dimension.rationale
            : evaluationDimension?.ai_rationale ?? evaluationDimension?.rationale ?? '等待人工复核后显示详细对比说明。',
          status: hasManualComparison ? 'completed' : 'waiting',
        };
      }),
    [dimensions, evaluation],
  );

  const evidenceAverageConfidence = useMemo(
    () => (evidenceItems.length ? Math.round(evidenceItems.reduce((sum, item) => sum + item.confidence_score * 100, 0) / evidenceItems.length) : 0),
    [evidenceItems],
  );

  const flaggedEvidenceCount = useMemo(
    () => evidenceItems.filter((item) => Boolean(item.metadata_json?.prompt_manipulation_detected)).length,
    [evidenceItems],
  );

  const latestParsedFile = useMemo(() => {
    if (!files.length) {
      return null;
    }
    return [...files].sort((left, right) => new Date(right.created_at).getTime() - new Date(left.created_at).getTime())[0];
  }, [files]);

  const insightPanels = [
    submission?.self_summary ? { title: '员工自述', content: submission.self_summary } : null,
    submission?.manager_summary ? { title: '主管补充', content: submission.manager_summary } : null,
    evaluation?.explanation ? { title: 'AI 评分说明', content: localizeEvaluationNarrative(evaluation.explanation) } : null,
  ].filter((item): item is { title: string; content: string } => Boolean(item));

  const parseStatusTitle = isParsingAll
    ? 'AI 正在逐份重新解析材料'
    : parseInProgressCount > 0
      ? '材料解析进行中'
      : parseFailedCount > 0
        ? '有材料等待重新解析'
        : parseCompletedCount > 0
          ? '证据工作区已准备就绪'
          : '等待上传或导入材料';

  const parseStatusDescription = isParsingAll
    ? `系统正在按顺序重新解析本周期的 ${batchParseTotal || files.length} 份材料，完成后会自动刷新新的证据结果。`
    : parseInProgressCount > 0
      ? '可先查看已完成内容。'
      : parseFailedCount > 0
        ? '先处理失败材料。'
        : parseCompletedCount > 0
          ? '可继续生成评分或进入复核。'
          : '先上传材料。';

  const moduleTabs: ModuleTab[] = [
    {
      key: 'overview',
      label: '概览',
      note: currentCycle?.name ?? '当前周期',
      helper: '查看周期状态与下一步',
    },
    {
      key: 'parse',
      label: '材料解析',
      note: hasFiles ? `${parseCompletedCount}/${files.length} 已完成` : '等待上传',
      helper: '上传材料并查看解析状态',
    },
    {
      key: 'evidence',
      label: '证据卡片',
      note: evidenceItems.length ? `${evidenceItems.length} 条证据` : '暂无证据',
      helper: '查看证据摘要与风险',
    },
    {
      key: 'review',
      label: '人工复核',
      note: formatEvaluationStatus(evaluation?.status),
      helper: '处理主管评分与 HR 审核',
    },
    {
      key: 'salary',
      label: '调薪建议',
      note: formatRecommendationStatus(salaryRecommendation?.status),
      helper: '确认建议并提交审批',
    },
  ];

  const estimatedProcessedCount = hasBatchParseSnapshot
    ? displayedParseCompletedCount + displayedParseFailedCount + displayedParseInProgressCount
    : 0;
  const parsePanelTitle = isParsingAll
    ? 'AI 正在并行解析材料'
    : parseInProgressCount > 0
      ? '材料解析进行中'
      : parseFailedCount > 0
        ? '有材料等待重新解析'
        : parseCompletedCount > 0
          ? '证据工作区已准备就绪'
          : '等待上传或导入材料';
  const parsePanelDescription = isParsingAll
    ? `当前批次共 ${batchParseTotal || files.length} 份材料，最多同时并行 ${batchParseConcurrency || 1} 份，页面会按真实完成情况逐份刷新。`
    : parseInProgressCount > 0
      ? '可先查看已完成内容。'
      : parseFailedCount > 0
        ? '先处理失败材料。'
        : parseCompletedCount > 0
          ? '可继续生成评分或进入复核。'
          : '先上传材料。';

  const activeModuleMeta = moduleTabs.find((item) => item.key === activeModule) ?? moduleTabs[0];

  async function reloadCurrentCycleData() {
    if (!employeeId || !selectedCycleId) {
      return;
    }
    await loadCycleSubmission(employeeId, selectedCycleId);
  }

  function resetBatchParseMonitor() {
    setBatchParseTotal(0);
    setBatchParseConcurrency(0);
    setBatchParseItems([]);
    setLastBatchParseActivityAt(null);
  }

  function updateBatchParseItem(fileId: string, patch: Partial<BatchParseItem>) {
    setBatchParseItems((current) =>
      current.map((item) => (item.fileId === fileId ? { ...item, ...patch } : item)),
    );
  }

  async function parseFilesInParallel(
    targetFiles: UploadedFileRecord[],
    options: { showBatchProgress: boolean },
  ): Promise<{ completed: number; failed: number; errors: string[]; total: number }> {
    const { showBatchProgress } = options;
    if (!targetFiles.length) {
      return { completed: 0, failed: 0, errors: [], total: 0 };
    }

    const concurrency = Math.min(MAX_PARSE_CONCURRENCY, targetFiles.length);
    const targetIds = new Set(targetFiles.map((file) => file.id));
    const now = new Date().toISOString();

    if (showBatchProgress) {
      setIsParsingAll(true);
      setBatchParseTotal(targetFiles.length);
      setBatchParseConcurrency(concurrency);
      setLastBatchParseActivityAt(now);
      setBatchParseItems(
        targetFiles.map((file) => ({
          fileId: file.id,
          fileName: file.file_name,
          status: 'queued',
          detail: '等待进入并行解析队列。',
          evidenceCount: 0,
          startedAt: null,
          updatedAt: now,
        })),
      );
    }

    setFiles((current) =>
      current.map((file) => (targetIds.has(file.id) ? { ...file, parse_status: 'pending' } : file)),
    );

    let nextIndex = 0;
    let completed = 0;
    let failed = 0;
    const errors: string[] = [];

    const worker = async () => {
      while (nextIndex < targetFiles.length) {
        const currentIndex = nextIndex;
        nextIndex += 1;
        const currentFile = targetFiles[currentIndex];
        const startedAt = new Date().toISOString();

        setLastBatchParseActivityAt(startedAt);
        setFiles((current) =>
          current.map((file) => (file.id === currentFile.id ? { ...file, parse_status: 'parsing' } : file)),
        );

        if (showBatchProgress) {
          updateBatchParseItem(currentFile.id, {
            status: 'parsing',
            detail: '已发送 AI 解析请求，正在等待模型返回结果。',
            startedAt,
            updatedAt: startedAt,
          });
        }

        try {
          const result = await parseFile(currentFile.id);
          const finishedAt = new Date().toISOString();
          const nextStatus = result.parse_status === 'parsed' ? 'parsed' : 'failed';

          if (nextStatus === 'parsed') {
            completed += 1;
          } else {
            failed += 1;
          }

          setLastBatchParseActivityAt(finishedAt);
          setFiles((current) =>
            current.map((file) => (file.id === currentFile.id ? { ...file, parse_status: nextStatus } : file)),
          );

          if (showBatchProgress) {
            updateBatchParseItem(currentFile.id, {
              status: nextStatus,
              detail:
                nextStatus === 'parsed'
                  ? `AI 解析完成，已提取 ${result.evidence_count} 条证据。`
                  : '解析请求已返回，但当前文件未成功产出有效证据。',
              evidenceCount: result.evidence_count,
              updatedAt: finishedAt,
            });
          }
        } catch (error) {
          const finishedAt = new Date().toISOString();
          const message = resolveError(error);
          failed += 1;
          errors.push(`${currentFile.file_name}: ${message}`);
          setLastBatchParseActivityAt(finishedAt);
          setFiles((current) =>
            current.map((file) => (file.id === currentFile.id ? { ...file, parse_status: 'failed' } : file)),
          );

          if (showBatchProgress) {
            updateBatchParseItem(currentFile.id, {
              status: 'failed',
              detail: message,
              evidenceCount: 0,
              updatedAt: finishedAt,
            });
          }
        }
      }
    };

    await Promise.all(Array.from({ length: concurrency }, () => worker()));
    return { completed, failed, errors, total: targetFiles.length };
  }

  function showToast(message: string) {
    setToastMessage(message);
    setTimeout(() => setToastMessage(null), 4000);
  }

  async function finishQueueAndUpload(queue: FileQueueItem[]) {
    if (!submission) return;
    const cleanFiles = queue.filter((i) => i.status === 'clean').map((i) => i.file);
    const duplicateItems = queue.filter((i) => i.status === 'approvedToUpload');

    if (cleanFiles.length === 0 && duplicateItems.length === 0) {
      setIsUploading(false);
      setFileQueue([]);
      return;
    }

    setIsUploading(true);
    setErrorMessage(null);
    try {
      const uploadedFiles: typeof files = [];
      if (cleanFiles.length > 0) {
        const resp = await uploadSubmissionFiles(
          submission.id,
          cleanFiles,
          pendingContributors.length > 0 ? pendingContributors : undefined,
        );
        uploadedFiles.push(...resp.items);
      }
      for (const item of duplicateItems) {
        // upload with allow_duplicate=true creates SharingRequest atomically (REVIEW FIX #2)
        const resp = await uploadSubmissionFilesWithDuplicate(
          submission.id,
          item.file,
          item.duplicateInfo!.originalFileId,
          pendingContributors.length > 0 ? pendingContributors : undefined,
        );
        uploadedFiles.push(...resp.items);
        showToast(`文件已上传，共享申请已发送给 ${item.duplicateInfo!.uploaderName}`);
      }

      await reloadCurrentCycleData();
      if (uploadedFiles.length > 0) {
        const summary = await parseFilesInParallel(uploadedFiles, { showBatchProgress: false });
        await reloadCurrentCycleData();
        if (summary.failed > 0) {
          setErrorMessage(`材料已上传，但有 ${summary.failed} 份文件解析失败，可在列表中点击”重新解析”。`);
        } else {
          setSuccessMessage('材料已上传，系统正在自动解析。');
        }
      }
    } catch (error) {
      if (error instanceof DuplicateFileException) {
        const who = error.detail.uploaded_by || '其他人';
        setErrorMessage(`此文件已由「${who}」提交过，无法重复上传。`);
      } else {
        setErrorMessage(resolveError(error));
      }
    } finally {
      setIsUploading(false);
      setFileQueue([]);
    }
  }

  async function processQueue(queue: FileQueueItem[]) {
    if (!submission) return;
    const nextQueue = queue.map((i) => ({ ...i }));
    for (let idx = 0; idx < nextQueue.length; idx++) {
      const item = nextQueue[idx];
      if (item.status !== 'pending') continue;
      item.status = 'checking';
      setHashCheckStatus('checking');
      setFileQueue([...nextQueue]);
      try {
        const hash = await computeFileSHA256(item.file);
        const result = await checkDuplicate(hash, submission.id);
        setHashCheckStatus('idle');
        if (result.is_duplicate) {
          item.status = 'currentDuplicate';
          item.duplicateInfo = {
            originalFileId: result.original_file_id,
            originalSubmissionId: result.original_submission_id,
            uploaderName: result.uploader_name,
            uploadedAt: result.uploaded_at,
          };
          setFileQueue([...nextQueue]);
          return; // wait for user decision
        }
        item.status = 'clean';
        setFileQueue([...nextQueue]);
      } catch {
        // graceful degradation: mark as clean, allow upload without check
        setHashCheckStatus('error');
        item.status = 'clean';
        setFileQueue([...nextQueue]);
      }
    }

    // All items resolved — upload
    await finishQueueAndUpload(nextQueue);
  }

  async function handleFilesSelected(selectedFiles: globalThis.FileList | null) {
    if (!selectedFiles?.length || !submission) {
      return;
    }

    setErrorMessage(null);
    setSuccessMessage(null);
    setHashCheckStatus('idle');

    const initialQueue: FileQueueItem[] = Array.from(selectedFiles).map((f) => ({
      file: f,
      status: 'pending' as const,
    }));
    setFileQueue(initialQueue);
    await processQueue(initialQueue);
  }

  async function handleDuplicateConfirm() {
    const queue = fileQueue.map((i) => ({ ...i }));
    const idx = queue.findIndex((i) => i.status === 'currentDuplicate');
    if (idx === -1) return;
    queue[idx].status = 'approvedToUpload';
    setFileQueue(queue);
    await processQueue(queue);
  }

  async function handleDuplicateCancel() {
    const queue = fileQueue.map((i) => ({ ...i }));
    const idx = queue.findIndex((i) => i.status === 'currentDuplicate');
    if (idx === -1) return;
    queue[idx].status = 'skipped';
    setFileQueue(queue);
    await processQueue(queue);
  }

  async function handleGitHubImport(url: string) {
    if (!submission) {
      return;
    }

    setIsGithubImporting(true);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      await importGitHubSubmissionFile(submission.id, url);
      await reloadCurrentCycleData();
      setSuccessMessage('GitHub 材料已导入。');
    } catch (error) {
      setErrorMessage(resolveError(error));
    } finally {
      setIsGithubImporting(false);
    }
  }

  async function handleRetryParse(fileId: string) {
    setWorkingFileId(fileId);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      await parseFile(fileId);
      await reloadCurrentCycleData();
      setSuccessMessage('已重新发起解析。');
    } catch (error) {
      setErrorMessage(resolveError(error));
    } finally {
      setWorkingFileId(null);
    }
  }

  async function handleReplaceFile(fileId: string, nextFile: File) {
    setWorkingFileId(fileId);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      const updated = await replaceSubmissionFile(fileId, nextFile);
      await reloadCurrentCycleData();
      try {
        await parseFile(updated.id);
      } catch (error) {
        await reloadCurrentCycleData();
        setErrorMessage(`文件已替换，但重新解析失败：${resolveError(error)}`);
        return;
      }
      await reloadCurrentCycleData();
      setSuccessMessage('文件已替换，并重新进入解析。');
    } catch (error) {
      setErrorMessage(resolveError(error));
    } finally {
      setWorkingFileId(null);
    }
  }
  async function handleDeleteFile(fileId: string) {
    setWorkingFileId(fileId);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      await deleteSubmissionFile(fileId);
      await reloadCurrentCycleData();
      setSuccessMessage('材料已移除。');
    } catch (error) {
      setErrorMessage(resolveError(error));
    } finally {
      setWorkingFileId(null);
    }
  }

  async function handleParseAllMaterials() {
    if (!submission || !hasFiles) {
      return;
    }

    const totalFiles = files.length;
    resetBatchParseMonitor();
    setIsParsingAll(true);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      const summary = await parseFilesInParallel(files, { showBatchProgress: true });
      await reloadCurrentCycleData();
      setSuccessMessage(
        summary.failed > 0
          ? `本次批量解析已完成，共 ${totalFiles} 份材料，成功 ${summary.completed} 份，失败 ${summary.failed} 份。`
          : `已完成 ${totalFiles} 份材料的批量解析，材料状态和证据结果已刷新。`,
      );
      setSuccessMessage(`已完成 ${totalFiles} 份材料的批量重新解析，材料状态和证据结果已刷新。`);
      setSuccessMessage(
        summary.failed > 0
          ? `本次批量解析已完成，共 ${totalFiles} 份材料，成功 ${summary.completed} 份，失败 ${summary.failed} 份。`
          : `已完成 ${totalFiles} 份材料的批量解析，材料状态和证据结果已刷新。`,
      );
    } catch (error) {
      await reloadCurrentCycleData();
      setErrorMessage(resolveError(error));
    } finally {
      setIsParsingAll(false);
    }
  }

  async function handleGenerateEvaluation() {
    if (!submission) {
      return;
    }

    setIsGeneratingEvaluation(true);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      if (needsBatchParse) {
        resetBatchParseMonitor();
        setIsParsingAll(true);
        const summary = await parseFilesInParallel(
          files.filter((file) => file.parse_status !== 'parsed'),
          { showBatchProgress: true },
        );
        if (summary.failed > 0) {
          throw new Error(`仍有 ${summary.failed} 份材料解析失败，请先处理失败材料后再生成 AI 评分。`);
        }
      }
      const nextEvaluation = evaluation ? await regenerateEvaluation(submission.id) : await generateEvaluation(submission.id);
      setEvaluation(nextEvaluation);
      setSalaryRecommendation(null);
      setDimensions(mapEvaluationToDrafts(nextEvaluation));
      setReviewLevel(nextEvaluation.ai_level);
      setReviewComment(localizeEvaluationNarrative(nextEvaluation.explanation));
      await reloadCurrentCycleData();
      setSuccessMessage(evaluation ? 'AI 评分已按最新材料重新生成，可以继续主管复核。' : 'AI 评分已生成，可以继续主管复核。');
    } catch (error) {
      setErrorMessage(resolveError(error));
    } finally {
      setIsParsingAll(false);
      setIsGeneratingEvaluation(false);
    }
  }

  async function handleSubmitReview() {
    if (!evaluation) {
      return;
    }

    setIsReviewSubmitting(true);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      const reviewed = await submitManualReview(evaluation.id, {
        ai_level: reviewLevel,
        overall_score: averageDimensionScore(dimensions),
        explanation: reviewComment,
        dimension_scores: dimensions.map((dimension) => ({
          dimension_code: dimension.code,
          raw_score: dimension.score,
          rationale: dimension.rationale,
        })),
      });
      setEvaluation(reviewed);
      setDimensions(mapEvaluationToDrafts(reviewed));
      setReviewComment(localizeEvaluationNarrative(reviewed.manager_comment ?? reviewed.explanation));
      if (reviewed.status === 'confirmed') {
        await syncSalaryRecommendationByEvaluation(reviewed.id, '评分已确认，调薪建议已同步到最新复核结果。');
      } else {
        setSuccessMessage('主管评分已提交。');
        setActiveModule('review');
      }
    } catch (error) {
      setErrorMessage(resolveError(error));
    } finally {
      setIsReviewSubmitting(false);
    }
  }

  async function handleConfirmEvaluation() {
    if (!evaluation || !submission) {
      return;
    }

    setIsConfirming(true);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      let confirmedEvaluationId = evaluation.id;
      if (evaluation.status === 'pending_hr') {
        const reviewed = await submitHrReview(evaluation.id, { decision: 'approved', comment: reviewComment });
        confirmedEvaluationId = reviewed.id;
      } else {
        await confirmEvaluation(evaluation.id);
      }
      await syncSalaryRecommendationByEvaluation(confirmedEvaluationId, '最终审核已确认，调薪建议已按最终评分刷新。');
      await reloadCurrentCycleData();
    } catch (error) {
      setErrorMessage(resolveError(error));
    } finally {
      setIsConfirming(false);
    }
  }

  async function handleReturnEvaluation() {
    if (!evaluation) {
      return;
    }

    setIsReturning(true);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      await submitHrReview(evaluation.id, { decision: 'returned', comment: reviewComment });
      await reloadCurrentCycleData();
      setSuccessMessage('评估已打回，等待重新处理。');
    } catch (error) {
      setErrorMessage(resolveError(error));
    } finally {
      setIsReturning(false);
    }
  }

  async function syncSalaryRecommendationByEvaluation(evaluationId: string, successText: string) {
    const recommendation = await recommendSalary(evaluationId);
    setSalaryRecommendation(recommendation);
    if (employeeId) {
      await refreshSalaryHistory(employeeId);
    }
    setManualAdjustmentPercent((recommendation.final_adjustment_ratio * 100).toFixed(2));
    setManualRecommendedSalary(Number(recommendation.recommended_salary).toFixed(2));
    setSuccessMessage(successText);
    setActiveModule('salary');
    return recommendation;
  }

  async function handleGenerateSalary() {
    if (!evaluation) {
      return;
    }

    setIsGeneratingSalary(true);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      await syncSalaryRecommendationByEvaluation(evaluation.id, '调薪建议已按当前评分结果更新。');
    } catch (error) {
      setErrorMessage(resolveError(error));
    } finally {
      setIsGeneratingSalary(false);
    }
  }

  function handleManualPercentChange(value: string) {
    setManualAdjustmentPercent(value);
    const numericValue = Number(value);
    if (!Number.isFinite(numericValue) || !salaryRecommendation) {
      return;
    }
    const nextSalary = Number(salaryRecommendation.current_salary) * (1 + numericValue / 100);
    setManualRecommendedSalary(nextSalary.toFixed(2));
  }

  function handleManualSalaryChange(value: string) {
    setManualRecommendedSalary(value);
    const numericValue = Number(value);
    if (!Number.isFinite(numericValue) || !salaryRecommendation) {
      return;
    }
    const currentSalary = Number(salaryRecommendation.current_salary);
    const nextPercent = ((numericValue - currentSalary) / currentSalary) * 100;
    setManualAdjustmentPercent(nextPercent.toFixed(2));
  }

  function handleCloseSalaryEditor() {
    if (!salaryRecommendation) {
      return;
    }
    setManualAdjustmentPercent((salaryRecommendation.final_adjustment_ratio * 100).toFixed(2));
    setManualRecommendedSalary(Number(salaryRecommendation.recommended_salary).toFixed(2));
  }

  async function handleSaveSalaryAdjustment() {
    if (!salaryRecommendation || manualAdjustmentRatio == null || !isManualSalaryValid) {
      return;
    }

    setIsSavingSalaryAdjustment(true);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      const updated = await updateSalaryRecommendation(salaryRecommendation.id, {
        final_adjustment_ratio: Number(manualAdjustmentRatio.toFixed(4)),
        status: 'adjusted',
      });
      setSalaryRecommendation(updated);
      if (employeeId) {
        await refreshSalaryHistory(employeeId);
      }
      setSuccessMessage('人工调薪结果已保存。');
    } catch (error) {
      setErrorMessage(resolveError(error));
    } finally {
      setIsSavingSalaryAdjustment(false);
    }
  }

  async function handleSubmitApproval() {
    if (!salaryRecommendation || !user) {
      return;
    }

    setIsSubmittingApproval(true);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      await submitDefaultApproval(salaryRecommendation.id);
      setSalaryRecommendation((current) => (current ? { ...current, status: 'pending_approval' } : current));
      if (employeeId) {
        await refreshSalaryHistory(employeeId);
      }
      setSuccessMessage('调薪建议已按默认审批路线提交。');
    } catch (error) {
      setErrorMessage(resolveError(error));
    } finally {
      setIsSubmittingApproval(false);
    }
  }

  const overviewStats = [
    { label: '已上传材料', value: `${files.length}`, note: hasFiles ? `${parseCompletedCount} 份已解析` : '等待上传' },
    { label: '证据卡片', value: `${evidenceItems.length}`, note: evidenceItems.length ? `平均置信度 ${evidenceAverageConfidence}%` : '等待提取' },
    { label: '评估状态', value: formatEvaluationStatus(evaluation?.status), note: evaluation ? `当前评分 ${reviewAverage.toFixed(1)}` : '等待生成' },
    { label: '调薪状态', value: formatRecommendationStatus(salaryRecommendation?.status), note: salaryRecommendation ? formatPercent(salaryRecommendation.final_adjustment_ratio, 2) : '尚未生成' },
  ];

  const DIMENSION_LABELS: Record<string, string> = {
    TOOL_MASTERY: 'AI工具掌握度',
    APPLICATION_DEPTH: 'AI应用深度',
    LEARNING_ABILITY: 'AI学习能力',
    SHARING_CONTRIBUTION: 'AI分享贡献',
    OUTCOME_CONVERSION: 'AI成果转化',
    // Legacy codes used by current evaluation engine
    TOOL: 'AI工具掌握度',
    DEPTH: 'AI应用深度',
    LEARN: 'AI学习速度',
    SHARE: '知识分享',
    IMPACT: '业务影响力',
  };

  const activeModuleContent = (() => {
    if (activeModule === 'overview') {
      return (
        <div className="grid gap-5 xl:grid-cols-[1.1fr_0.9fr]">
          <section className="surface animate-fade-up overflow-hidden px-0 py-0">
            <div style={{ borderBottom: '1px solid var(--color-border)', background: 'var(--color-bg-subtle)', padding: '20px 24px' }}>
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <p className="eyebrow">当前概览</p>
                  <h2 className="mt-2 text-[24px] font-semibold tracking-[-0.03em] text-ink">这个周期先看什么</h2>
                  <p className="mt-2 max-w-3xl text-sm leading-6 text-steel">先看状态、风险和下一步。</p>
                </div>
                <StatusIndicator status={currentStatus} />
              </div>
            </div>

            <div className="px-6 py-6 lg:px-7">
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                {overviewStats.map((item) => (
                  <div className="surface-subtle px-4 py-4" key={item.label}>
                    <p className="text-sm text-steel">{item.label}</p>
                    <p className="mt-2 text-[26px] font-semibold tracking-[-0.04em] text-ink">{item.value}</p>
                    <p className="mt-2 text-xs leading-5 text-steel">{item.note}</p>
                  </div>
                ))}
              </div>

              <div style={{ marginTop: 20, border: '1px solid var(--color-border)', borderRadius: 8, background: '#FFFFFF', padding: '16px' }}>
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <p className="text-sm font-semibold text-ink">流程状态</p>
                  <span className="text-xs text-steel">当前处于 {formatFlowLabel(currentStatus)}</span>
                </div>
                <div className="mt-4 grid gap-3 md:grid-cols-4 xl:grid-cols-8">
                  {FLOW.map((status, index) => {
                    const isDone = activeIndex >= index;
                    return (
                      <div
                        key={status}
                        style={{
                          borderRadius: 6,
                          border: `1px solid ${isDone ? 'var(--color-primary)' : 'var(--color-border)'}`,
                          background: isDone ? 'var(--color-primary)' : 'var(--color-bg-subtle)',
                          color: isDone ? '#FFFFFF' : 'var(--color-steel)',
                          padding: '10px 8px',
                          textAlign: 'center',
                        }}
                      >
                        <div style={{ fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.18em' }}>步骤 {index + 1}</div>
                        <div className="mt-2 flex justify-center">
                          <StatusIndicator status={status} />
                        </div>
                        <div className="mt-2 text-xs">{formatFlowLabel(status)}</div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {insightPanels.length ? (
                <div className="mt-5 grid gap-4 lg:grid-cols-3">
                  {insightPanels.map((panel) => (
                    <details key={panel.title} style={{ border: '1px solid var(--color-border)', borderRadius: 8, background: 'var(--color-bg-subtle)', padding: '12px 16px' }}>
                      <summary className="cursor-pointer text-sm font-semibold text-ink">{panel.title}</summary>
                      <p className="mt-3 text-sm leading-7 text-steel">{panel.content}</p>
                    </details>
                  ))}
                </div>
              ) : null}

              {integrityFlagged ? (
                <div style={{ marginTop: 20, border: '1px solid var(--color-danger)', borderRadius: 8, background: 'var(--color-danger-bg)', padding: '12px 16px', fontSize: 14, lineHeight: 1.6, color: 'var(--color-danger)' }}>
                  检测到 {evaluation?.integrity_issue_count ?? 0} 条诚信风险提示，建议优先切到「人工复核」模块查看。
                </div>
              ) : null}

              {evaluation?.used_fallback ? (
                <div style={{ marginTop: 20 }} className="rounded border border-yellow-400 bg-yellow-50 px-4 py-3 text-sm text-yellow-800 mb-4">
                  当前结果为规则引擎估算，AI 未参与评估，请结合实际情况人工复核。
                </div>
              ) : null}

              <section className="mt-6">
                <h3 className="text-base font-semibold mb-3">维度评分详情</h3>
                {evaluation && evaluation.dimension_scores && evaluation.dimension_scores.length > 0 ? (
                  <div className="space-y-3">
                    {evaluation.dimension_scores.map((ds) => (
                      <div key={ds.id} className="rounded border border-gray-200 p-3 bg-white">
                        <div className="flex items-center justify-between mb-1">
                          <span className="font-medium text-gray-700">
                            {DIMENSION_LABELS[ds.dimension_code] ?? ds.dimension_code}
                          </span>
                          <span className="text-sm text-gray-500">
                            权重 {Math.round(ds.weight * 100)}% · AI得分 {ds.ai_raw_score.toFixed(1)}
                          </span>
                        </div>
                        {ds.ai_rationale && (
                          <p className="text-sm text-gray-600 mt-1">{ds.ai_rationale}</p>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-gray-400">暂无维度评分数据</p>
                )}
              </section>
            </div>
          </section>

          <aside className="surface animate-fade-up px-6 py-6 lg:px-7">
            <div style={{ borderBottom: '1px solid var(--color-border)', paddingBottom: 12, marginBottom: 16 }}>
              <p className="eyebrow">下一步动作</p>
              <h2 className="mt-2 text-[24px] font-semibold tracking-[-0.03em] text-ink">处理建议</h2>
              <p className="mt-2 text-sm leading-6 text-steel">优先处理当前动作。</p>
            </div>

            <div className="mt-5 grid gap-3">
              <button className="surface-subtle px-4 py-4 text-left disabled:opacity-60" disabled={isParsingAll || !submission || !hasFiles} onClick={handleParseAllMaterials} type="button">
                <h3 className="font-medium text-ink">{isParsingAll ? 'AI 解析中...' : '启动 AI 解析'}</h3>
                <p className="mt-2 text-sm leading-6 text-steel">先解析材料。</p>
              </button>
              <button className="surface-subtle px-4 py-4 text-left disabled:opacity-60" disabled={isGeneratingEvaluation || !submission || !hasFiles} onClick={handleGenerateEvaluation} type="button">
                <h3 className="font-medium text-ink">{isGeneratingEvaluation ? '生成中...' : evaluation ? '重新生成 AI 评分' : '生成 AI 评分'}</h3>
                <p className="mt-2 text-sm leading-6 text-steel">解析后生成评分。</p>
              </button>
              <button className="surface-subtle px-4 py-4 text-left disabled:opacity-60" disabled={isGeneratingSalary || !evaluation || evaluation.status !== 'confirmed'} onClick={handleGenerateSalary} type="button">
                <h3 className="font-medium text-ink">{isGeneratingSalary ? '生成中...' : '生成调薪建议'}</h3>
                <p className="mt-2 text-sm leading-6 text-steel">确认后生成调薪建议。</p>
              </button>
            </div>

            <div style={{ marginTop: 20, border: '1px solid var(--color-border)', borderRadius: 8, background: 'var(--color-bg-subtle)', padding: '16px' }}>
              <p style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.18em', color: 'var(--color-steel)' }}>当前上下文</p>
              <div className="mt-3 space-y-2 text-sm text-steel">
                <div className="flex items-center justify-between gap-4"><span>提交记录</span><span className="max-w-[60%] truncate font-medium text-ink">{submission?.id ?? '未创建'}</span></div>
                <div className="flex items-center justify-between gap-4"><span>评估状态</span><span className="font-medium text-ink">{formatEvaluationStatus(evaluation?.status)}</span></div>
                <div className="flex items-center justify-between gap-4"><span>调薪状态</span><span className="font-medium text-ink">{formatRecommendationStatus(salaryRecommendation?.status)}</span></div>
                <div className="flex items-center justify-between gap-4"><span>主管当前均分</span><span className="font-medium text-ink">{reviewAverage.toFixed(1)}</span></div>
              </div>
            </div>
          </aside>
        </div>
      );
    }
    if (activeModule === 'parse') {
      return (
        <div className="grid gap-5 xl:grid-cols-[1.02fr_0.98fr]">
          <div className="flex flex-col gap-5">
            <div className="surface px-6 py-6 lg:px-7">
              <FileUploadPanel
                isGithubImporting={isGithubImporting}
                isUploading={isUploading}
                onFilesSelected={handleFilesSelected}
                onGitHubImport={handleGitHubImport}
                showContributorPicker
                contributors={pendingContributors}
                onContributorsChange={setPendingContributors}
                hashCheckStatus={hashCheckStatus}
              />
            </div>
            <div className="surface px-6 py-6 lg:px-7">
              <FileList
                files={files}
                onDelete={handleDeleteFile}
                onReplace={handleReplaceFile}
                onRetryParse={handleRetryParse}
                workingFileId={workingFileId}
              />
            </div>
          </div>

          <section className="surface overflow-hidden px-0 py-0">
            <div style={{ borderBottom: '1px solid var(--color-border)', background: 'var(--color-bg-subtle)', padding: '20px 24px' }}>
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <p className="eyebrow">材料解析</p>
                  <h2 className="mt-2 text-[24px] font-semibold tracking-[-0.03em] text-ink">{parsePanelTitle}</h2>
                  <p className="mt-2 max-w-3xl text-sm leading-6 text-steel">{parsePanelDescription}</p>
                </div>
                <div style={{ background: '#FFFFFF', border: '1px solid var(--color-border)', borderRadius: 8, padding: '12px 16px', textAlign: 'right' }}>
                  <p style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.18em', color: 'var(--color-steel)' }}>完成度</p>
                  <p className="mt-2 text-[34px] font-semibold tracking-[-0.05em] text-ink">{displayedParseProgressPercent}%</p>
                  <p className="text-xs text-steel">
                    {isParsingAll
                      ? `预计已处理 ${Math.min(estimatedProcessedCount, batchParseTotal || files.length)}/${batchParseTotal || files.length} 份材料`
                      : `${parseCompletedCount}/${files.length || 0} 份材料已完成解析`}
                  </p>
                </div>
              </div>
            </div>

            <div className="px-6 py-6 lg:px-7">
              <div style={{ height: 8, borderRadius: 4, overflow: 'hidden', background: 'var(--color-bg-subtle)' }}>
                <div
                  style={{
                    height: '100%',
                    borderRadius: 4,
                    transition: 'width 0.5s',
                    width: `${displayedParseProgressPercent}%`,
                    background: displayedParseFailedCount > 0 ? 'var(--color-danger)' : 'var(--color-primary)',
                  }}
                />
              </div>

              {isParsingAll ? (
                <div style={{ marginTop: 14, border: '1px solid var(--color-border)', borderRadius: 8, background: '#FFFFFF', padding: '14px 16px' }}>
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-ink">批量重解析进行中</p>
                      <p className="mt-1 text-sm text-steel">系统正在重新读取文件内容、重建证据卡片，并在完成后自动刷新当前页面。</p>
                    </div>
                    <div className="text-right">
                      <p className="text-xs uppercase tracking-[0.18em] text-steel">当前进度</p>
                      <p className="mt-1 text-lg font-semibold text-ink">{Math.min(estimatedProcessedCount, batchParseTotal || files.length)}/{batchParseTotal || files.length}</p>
                    </div>
                  </div>
                </div>
              ) : null}

              {hasBatchParseSnapshot ? (
                <div className="mt-5 grid gap-3 lg:grid-cols-[1.2fr_0.8fr]">
                  <div style={{ border: '1px solid var(--color-border)', borderRadius: 8, background: '#FFFFFF', padding: '16px' }}>
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <p className="text-sm font-semibold text-ink">逐份解析动态</p>
                        <p className="mt-1 text-sm text-steel">每个文件完成、失败或排队状态都会在这里立即更新。</p>
                      </div>
                      <div className="text-right">
                        <p className="text-xs uppercase tracking-[0.18em] text-steel">最近活动</p>
                        <p className="mt-1 text-sm font-semibold text-ink">{lastBatchParseActivityAt ? formatTime(lastBatchParseActivityAt) : '--'}</p>
                      </div>
                    </div>

                    {batchParsePossiblyStalled ? (
                      <div className="mt-4" style={{ border: '1px solid var(--color-warning)', borderRadius: 8, background: 'var(--color-warning-bg)', padding: '10px 12px', fontSize: 13, lineHeight: 1.6, color: 'var(--color-warning)' }}>
                        当前已经 {secondsSinceLastBatchActivity} 秒没有新的完成反馈，更像是 LLM 响应较慢，不一定是真的卡死。
                      </div>
                    ) : null}

                    <div className="mt-4 grid gap-2">
                      {recentBatchItems.length ? (
                        recentBatchItems.map((item) => (
                          <div key={item.fileId} style={{ border: '1px solid var(--color-border)', borderRadius: 8, background: 'var(--color-bg-subtle)', padding: '12px 14px' }}>
                            <div className="flex flex-wrap items-center justify-between gap-3">
                              <p className="text-sm font-semibold text-ink">{item.fileName}</p>
                              <span
                                style={{
                                  borderRadius: 999,
                                  padding: '2px 10px',
                                  fontSize: 12,
                                  fontWeight: 600,
                                  background:
                                    item.status === 'parsed'
                                      ? 'var(--color-success-bg)'
                                      : item.status === 'failed'
                                        ? 'var(--color-danger-bg)'
                                        : item.status === 'parsing'
                                          ? 'var(--color-warning-bg)'
                                          : 'var(--color-bg-subtle)',
                                  color:
                                    item.status === 'parsed'
                                      ? 'var(--color-success)'
                                      : item.status === 'failed'
                                        ? 'var(--color-danger)'
                                        : item.status === 'parsing'
                                          ? 'var(--color-warning)'
                                          : 'var(--color-steel)',
                                }}
                              >
                                {item.status === 'queued' ? '排队中' : item.status === 'parsing' ? '解析中' : item.status === 'parsed' ? '已完成' : '失败'}
                              </span>
                            </div>
                            <p className="mt-2 text-sm leading-6 text-steel">{item.detail}</p>
                            <div className="mt-2 flex flex-wrap items-center gap-3 text-xs text-steel">
                              <span>开始: {formatTime(item.startedAt)}</span>
                              <span>更新: {formatTime(item.updatedAt)}</span>
                              <span>证据: {item.evidenceCount}</span>
                            </div>
                          </div>
                        ))
                      ) : (
                        <p className="text-sm text-steel">当前还没有可展示的解析动态。</p>
                      )}
                    </div>
                  </div>

                  <div style={{ border: '1px solid var(--color-border)', borderRadius: 8, background: 'var(--color-bg-subtle)', padding: '16px' }}>
                    <p className="text-sm font-semibold text-ink">并行状态</p>
                    <div className="mt-4 grid gap-3 sm:grid-cols-2">
                      <div style={{ border: '1px solid var(--color-border)', borderRadius: 8, background: '#FFFFFF', padding: '12px 14px' }}>
                        <p className="text-xs uppercase tracking-[0.18em] text-steel">并行槽位</p>
                        <p className="mt-2 text-2xl font-semibold text-ink">{batchParseRunningCount}/{batchParseConcurrency || 1}</p>
                      </div>
                      <div style={{ border: '1px solid var(--color-border)', borderRadius: 8, background: '#FFFFFF', padding: '12px 14px' }}>
                        <p className="text-xs uppercase tracking-[0.18em] text-steel">等待队列</p>
                        <p className="mt-2 text-2xl font-semibold text-ink">{batchParseQueuedCount}</p>
                      </div>
                    </div>

                    <div className="mt-4">
                      <p className="text-sm font-semibold text-ink">当前正在解析</p>
                      <div className="mt-3 grid gap-2">
                        {activeBatchItems.length ? (
                          activeBatchItems.map((item) => (
                            <div key={item.fileId} style={{ border: '1px solid var(--color-border)', borderRadius: 8, background: '#FFFFFF', padding: '10px 12px', fontSize: 13, color: 'var(--color-ink)' }}>
                              <div className="font-medium">{item.fileName}</div>
                              <div className="mt-1 text-xs text-steel">开始时间 {formatTime(item.startedAt)}</div>
                            </div>
                          ))
                        ) : (
                          <p className="text-sm text-steel">{isParsingAll ? '当前没有活跃解析槽位。' : '本次批量解析已结束。'}</p>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              ) : null}

              <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                <div className="surface-subtle px-4 py-4"><p className="text-sm text-steel">已完成</p><p className="mt-2 text-2xl font-semibold" style={{ color: 'var(--color-success)' }}>{displayedParseCompletedCount}</p></div>
                <div className="surface-subtle px-4 py-4"><p className="text-sm text-steel">进行中</p><p className="mt-2 text-2xl font-semibold" style={{ color: 'var(--color-warning)' }}>{displayedParseInProgressCount}</p></div>
                <div className="surface-subtle px-4 py-4"><p className="text-sm text-steel">待处理</p><p className="mt-2 text-2xl font-semibold text-ink">{displayedParsePendingCount}</p></div>
                <div className="surface-subtle px-4 py-4" style={parseFailedCount > 0 ? { borderColor: 'var(--color-danger)', background: 'var(--color-danger-bg)' } : {}}><p className="text-sm text-steel">失败</p><p className="mt-2 text-2xl font-semibold" style={{ color: parseFailedCount > 0 ? 'var(--color-danger)' : 'var(--color-ink)' }}>{parseFailedCount}</p></div>
              </div>

              <div className="mt-5 grid gap-3 lg:grid-cols-2">
                <div style={{ border: '1px solid var(--color-border)', borderRadius: 8, background: '#FFFFFF', padding: '16px' }}>
                  <p className="text-sm font-semibold text-ink">材料快照</p>
                  <div className="mt-4 space-y-3 text-sm text-steel">
                    <div className="flex items-center justify-between gap-4"><span>当前周期</span><span className="font-medium text-ink">{currentCycle?.name ?? '未选择'}</span></div>
                    <div className="flex items-center justify-between gap-4"><span>最近材料</span><span className="max-w-[58%] truncate font-medium text-ink">{latestParsedFile?.file_name ?? '暂无'}</span></div>
                    <div className="flex items-center justify-between gap-4"><span>最近状态</span><span className="font-medium" style={{ color: latestParsedFile ? getParseStatusColor(latestParsedFile.parse_status) : 'var(--color-ink)' }}>{latestParsedFile ? FILE_STATUS_LABELS[latestParsedFile.parse_status] : '暂无'}</span></div>
                    <div className="flex items-center justify-between gap-4"><span>风险证据</span><span className="font-medium" style={{ color: flaggedEvidenceCount > 0 ? 'var(--color-danger)' : 'var(--color-ink)' }}>{flaggedEvidenceCount} 条</span></div>
                  </div>
                </div>
                <div style={{ border: '1px solid var(--color-border)', borderRadius: 8, background: 'var(--color-bg-subtle)', padding: '16px', fontSize: 14, lineHeight: 1.6, color: 'var(--color-steel)' }}>
                  <p className="text-sm font-semibold text-ink">处理建议</p>
                  <p className="mt-3">上传新材料后系统会自动解析；如果某个文件失败，优先替换或重试，再继续生成 AI 评分。</p>
                  <button className="action-primary mt-4" disabled={isParsingAll || !submission || !hasFiles} onClick={handleParseAllMaterials} type="button">
                    {isParsingAll ? 'AI 解析中...' : '重新批量解析'}
                  </button>
                </div>
              </div>
            </div>
          </section>
        </div>
      );
    }

    if (activeModule === 'evidence') {
      return (
        <section className="surface px-0 py-0">
          <div style={{ borderBottom: '1px solid var(--color-border)', padding: '20px 24px' }}>
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <p className="eyebrow">证据工作区</p>
                <h2 className="mt-2 text-[24px] font-semibold tracking-[-0.03em] text-ink">提取出的证据卡片</h2>
                <p className="mt-2 max-w-3xl text-sm leading-6 text-steel">左侧总览，右侧单条证据。</p>
              </div>
              </div>
          </div>

          <div className="grid gap-0 xl:grid-cols-[320px_minmax(0,1fr)]">
            <div style={{ borderBottom: '1px solid var(--color-border)', padding: '24px' }} className="xl:border-b-0 xl:border-r">
              <EvidenceWorkspaceOverview evidenceItems={evidenceItems} />
            </div>

            <div className="px-6 py-6 lg:px-7">
              <div className="mb-5 grid gap-3 md:grid-cols-3">
                <div className="surface-subtle px-4 py-4"><p className="text-sm text-steel">证据数量</p><p className="mt-2 text-2xl font-semibold text-ink">{evidenceItems.length}</p></div>
                <div className="surface-subtle px-4 py-4"><p className="text-sm text-steel">平均置信度</p><p className="mt-2 text-2xl font-semibold text-ink">{evidenceAverageConfidence}%</p></div>
                <div className="surface-subtle px-4 py-4" style={flaggedEvidenceCount > 0 ? { borderColor: 'var(--color-danger)', background: 'var(--color-danger-bg)' } : {}}><p className="text-sm text-steel">风险证据</p><p className="mt-2 text-2xl font-semibold" style={{ color: flaggedEvidenceCount > 0 ? 'var(--color-danger)' : 'var(--color-ink)' }}>{flaggedEvidenceCount}</p></div>
              </div>

              <div className="grid gap-4">
                {evidenceItems.map((item) => (
                  <EvidenceCard evidence={item} key={item.id} />
                ))}
                {!evidenceItems.length ? (
                  <div style={{ border: '1px dashed var(--color-border)', borderRadius: 8, background: 'var(--color-bg-subtle)', padding: '24px', fontSize: 14, lineHeight: 1.8, color: 'var(--color-steel)' }}>
                    当前还没有证据卡片。先上传材料或导入 GitHub 链接，完成解析后这里会按摘要卡片的形式自动整理出来。
                  </div>
                ) : null}
              </div>
            </div>
          </div>
        </section>
      );
    }
    if (activeModule === 'review') {
      return (
        <div className="grid gap-5 xl:grid-cols-[1.02fr_0.98fr]">
          <div className="flex flex-col gap-5">
            <div className="surface px-6 py-6 lg:px-7">
              <div style={{ borderBottom: '1px solid var(--color-border)', paddingBottom: 12, marginBottom: 20 }}>
                <p className="eyebrow">评分工作台</p>
                <h2 className="mt-2 text-[24px] font-semibold tracking-[-0.03em] text-ink">主管与 HR 复核</h2>
                <p className="mt-2 text-sm leading-6 text-steel">处理评分、审核和校准。</p>
              </div>
              <ReviewPanel
                status={evaluation?.status ?? 'draft'}
                aiLevel={evaluation?.ai_level ?? '未生成'}
                aiScore={evaluation?.ai_overall_score ?? null}
                managerScore={evaluation?.manager_score ?? null}
                scoreGap={evaluation?.score_gap ?? null}
                canHrReview={canHrReview}
                dimensions={dimensions}
                isConfirming={isConfirming}
                isReturning={isReturning}
                isSubmitting={isReviewSubmitting}
                onConfirmEvaluation={handleConfirmEvaluation}
                onReturnEvaluation={handleReturnEvaluation}
                onReviewCommentChange={setReviewComment}
                onReviewLevelChange={setReviewLevel}
                onSubmitReview={handleSubmitReview}
                reviewComment={reviewComment}
                reviewLevel={reviewLevel}
              />
            </div>

            {evaluation?.used_fallback && FALLBACK_VISIBLE_STATUSES.includes(evaluation.status) && (
              <div style={{
                background: 'var(--color-warning-bg, #FFF3E8)',
                border: '1px solid var(--color-warning-border, #FFD8A8)',
                borderLeft: '3px solid var(--color-warning, #FF7D00)',
                borderRadius: '6px',
                padding: '12px 16px',
              }}>
                <div style={{ fontWeight: 500, fontSize: '13.5px', color: 'var(--color-ink)' }}>
                  当前结果为规则引擎估算
                </div>
                <p style={{ fontSize: '13.5px', fontWeight: 500, lineHeight: 1.5, color: 'var(--color-steel)', marginTop: '4px' }}>
                  DeepSeek AI 服务未配置或暂时不可用，本次评估基于规则引擎生成，结果仅供参考，不代表 AI 评估意见。
                </p>
              </div>
            )}

            {FALLBACK_VISIBLE_STATUSES.includes(evaluation?.status ?? '') && (
              <div className="surface px-6 py-6 lg:px-7">
                <div style={{ borderBottom: '1px solid var(--color-border)', paddingBottom: 12, marginBottom: 20 }}>
                  <p className="eyebrow">维度评分</p>
                  <h3 className="mt-2 text-[22px] font-semibold tracking-[-0.03em] text-ink">维度评分详情</h3>
                  <p className="mt-2 text-sm leading-6 text-steel">AI 评估的 5 个维度得分与说明。</p>
                </div>
                {evaluation?.dimension_scores && evaluation.dimension_scores.length > 0 ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    {evaluation.dimension_scores.map((ds) => (
                      <div key={ds.id} className="list-row">
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                          <div>
                            <div className="eyebrow">{ds.dimension_code}</div>
                            <div className="section-title" style={{ marginTop: '2px' }}>
                              {DIMENSION_LABELS[ds.dimension_code] ?? ds.dimension_code}
                            </div>
                            <div style={{ fontSize: '12px', color: 'var(--color-steel)', marginTop: '2px' }}>
                              权重 {Math.round(ds.weight * 100)}%
                            </div>
                          </div>
                          <div className="dashboard-value" style={{ fontSize: '26px' }}>
                            {ds.ai_raw_score.toFixed(1)}
                          </div>
                        </div>
                        {ds.ai_rationale && (
                          <p style={{ fontSize: '13px', color: 'var(--color-steel)', lineHeight: 1.65, marginTop: '8px' }}>
                            {ds.ai_rationale}
                          </p>
                        )}
                        {ds.prompt_hash && (
                          <details style={{ marginTop: '8px' }}>
                            <summary className="chip-button" style={{ cursor: 'pointer', userSelect: 'none' }}>
                              Prompt 哈希（可复现审计）
                            </summary>
                            <code style={{ fontSize: '11px', color: 'var(--color-placeholder)', fontFamily: 'monospace', display: 'block', marginTop: '4px', wordBreak: 'break-all' }}>
                              {ds.prompt_hash}
                            </code>
                          </details>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div>
                    <p style={{ fontSize: '14px', color: 'var(--color-steel)' }}>暂无维度评分数据</p>
                    <p style={{ fontSize: '13px', color: 'var(--color-placeholder)', marginTop: '4px' }}>
                      完成 AI 评估后，5 个维度得分将展示在此处。
                    </p>
                  </div>
                )}
              </div>
            )}

            <div className="surface px-6 py-6 lg:px-7">
              <DimensionScoreEditor dimensions={dimensions} onChange={setDimensions} />
            </div>
          </div>

          <div className="flex flex-col gap-5">
            <div className="surface px-6 py-6 lg:px-7">
              <div style={{ borderBottom: '1px solid var(--color-border)', paddingBottom: 12, marginBottom: 20 }}>
                <p className="eyebrow">校准对照</p>
                <h2 className="mt-2 text-[24px] font-semibold tracking-[-0.03em] text-ink">AI 与人工评分差异</h2>
                <p className="mt-2 text-sm leading-6 text-steel">查看分差和说明。</p>
              </div>
              <CalibrationCompareTable rows={calibrationRows} />
            </div>

            {integrityFlagged ? (
              <section className="surface px-6 py-6 lg:px-7" style={{ borderColor: 'var(--color-danger)', background: 'var(--color-danger-bg)' }}>
                <p className="eyebrow" style={{ color: 'var(--color-danger)' }}>诚信风险提示</p>
                <h3 className="mt-2 text-[22px] font-semibold tracking-[-0.03em]" style={{ color: 'var(--color-danger)' }}>建议在评分前先核查这些异常内容</h3>
                <p className="mt-3 text-sm leading-6" style={{ color: 'var(--color-danger)' }}>检测到 {evaluation?.integrity_issue_count ?? 0} 条风险提示，下面列出当前样例，便于 HR 或主管快速复核。</p>
                {integrityExamples.length ? (
                  <div className="mt-4 grid gap-3">
                    {integrityExamples.map((example) => (
                      <div key={example} style={{ border: '1px solid var(--color-danger)', borderRadius: 6, background: '#FFFFFF', padding: '10px 14px', fontSize: 14, lineHeight: 1.6, color: 'var(--color-danger)' }}>
                        {example}
                      </div>
                    ))}
                  </div>
                ) : null}
              </section>
            ) : null}
          </div>
        </div>
      );
    }

    return (
      <>
      {/* 考勤概览 — 仅审批参考，不影响调薪计算 */}
      {(user?.role === 'admin' || user?.role === 'hrbp' || user?.role === 'manager') && employee?.id ? (
        <AttendanceKpiCard employeeId={employee.id} />
      ) : null}
      <section className="surface px-6 py-6 lg:px-7">
        <div className="flex flex-wrap items-start justify-between gap-4" style={{ borderBottom: '1px solid var(--color-border)', paddingBottom: 12, marginBottom: 20 }}>
          <div>
            <p className="eyebrow">调薪建议</p>
            <h2 className="mt-2 text-[24px] font-semibold tracking-[-0.03em] text-ink">建议结果快照</h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-steel">查看建议薪资和审批动作。</p>
          </div>
          <div style={{ border: '1px solid var(--color-border)', borderRadius: 8, background: 'var(--color-bg-subtle)', padding: '10px 16px', textAlign: 'right' }}>
            <p style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.18em', color: 'var(--color-steel)' }}>当前状态</p>
            <p className="mt-2 text-sm font-medium text-ink">{formatRecommendationStatus(salaryRecommendation?.status)}</p>
          </div>
        </div>

        {salaryRecommendation ? (
          <>
            <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              <div className="surface-subtle px-4 py-4"><p className="text-sm text-steel">当前薪资</p><p className="mt-2 text-2xl font-semibold text-ink">{formatCurrency(salaryRecommendation.current_salary)}</p></div>
              <div className="surface-subtle px-4 py-4"><p className="text-sm text-steel">建议薪资</p><p className="mt-2 text-2xl font-semibold text-ink">{formatCurrency(salaryRecommendation.recommended_salary)}</p></div>
              <div className="surface-subtle px-4 py-4"><p className="text-sm text-steel">最终调整比例</p><p className="mt-2 text-2xl font-semibold text-ink">{formatPercent(salaryRecommendation.final_adjustment_ratio, 2)}</p></div>
              <div className="surface-subtle px-4 py-4"><p className="text-sm text-steel">建议状态</p><p className="mt-2 text-2xl font-semibold text-ink">{formatRecommendationStatus(salaryRecommendation.status)}</p></div>
            </div>

            <div className="mt-5 grid gap-3 md:grid-cols-3">
              <div className="surface-subtle px-4 py-4"><p className="text-sm text-steel">建议涨幅</p><p className="mt-2 text-lg font-semibold text-ink">{formatPercent(salaryRecommendation.recommended_ratio, 2)}</p></div>
              <div className="surface-subtle px-4 py-4"><p className="text-sm text-steel">AI 系数</p><p className="mt-2 text-lg font-semibold text-ink">{salaryRecommendation.ai_multiplier.toFixed(2)}</p></div>
              <div className="surface-subtle px-4 py-4"><p className="text-sm text-steel">认证加成</p><p className="mt-2 text-lg font-semibold text-ink">{formatPercent(salaryRecommendation.certification_bonus, 2)}</p></div>
            </div>

            {liveSalaryPreview ? (
              <div className="mt-5">
                <div className="flex flex-wrap items-start justify-between gap-3 rounded-[8px] border px-4 py-4" style={{ borderColor: recommendationNeedsRefresh ? 'var(--color-warning)' : 'var(--color-border)', background: recommendationNeedsRefresh ? 'var(--color-warning-bg)' : 'var(--color-bg-subtle)' }}>
                  <div>
                    <p className="text-sm font-semibold text-ink">最新复核分联动预览</p>
                    <p className="mt-2 text-sm leading-6 text-steel">这里显示的是按当前最终评分、等级和员工档案重新推算后的建议结果。</p>
                  </div>
                  <button
                    className="action-secondary"
                    disabled={isGeneratingSalary || !evaluation || evaluation.status !== 'confirmed'}
                    onClick={handleGenerateSalary}
                    type="button"
                  >
                    {isGeneratingSalary ? '联动中...' : '按最新评分联动'}
                  </button>
                </div>
                <div className="mt-3 grid gap-3 md:grid-cols-2 xl:grid-cols-5">
                  <div className="surface-subtle px-4 py-4"><p className="text-sm text-steel">最新复核分</p><p className="mt-2 text-lg font-semibold text-ink">{evaluation?.overall_score.toFixed(1) ?? '--'}</p></div>
                  <div className="surface-subtle px-4 py-4"><p className="text-sm text-steel">最新等级</p><p className="mt-2 text-lg font-semibold text-ink">{formatLevelLabel(evaluation?.ai_level ?? 'Level 1')}</p></div>
                  <div className="surface-subtle px-4 py-4"><p className="text-sm text-steel">联动后建议涨幅</p><p className="mt-2 text-lg font-semibold text-ink">{formatPercent(liveSalaryPreview.recommendedRatio, 2)}</p></div>
                  <div className="surface-subtle px-4 py-4"><p className="text-sm text-steel">联动后最终比例</p><p className="mt-2 text-lg font-semibold text-ink">{formatPercent(liveSalaryPreview.finalAdjustmentRatio, 2)}</p></div>
                  <div className="surface-subtle px-4 py-4"><p className="text-sm text-steel">联动后建议薪资</p><p className="mt-2 text-lg font-semibold text-ink">{formatCurrency(String(liveSalaryPreview.recommendedSalary.toFixed(2)))}</p></div>
                </div>
                {recommendationNeedsRefresh ? (
                  <p className="mt-3 text-sm" style={{ color: 'var(--color-warning)' }}>
                    当前页面展示的“建议涨幅 / AI 系数 / 认证加成 / 最终调整比例”还没有跟最新复核分同步，点击上面的“按最新评分联动”就会刷新。
                  </p>
                ) : null}
              </div>
            ) : null}

            {salaryRecommendation.explanation ? (
              <details className="mt-5" style={{ border: '1px solid var(--color-border)', borderRadius: 8, background: 'var(--color-bg-subtle)', padding: '12px 16px' }}>
                <summary className="cursor-pointer text-sm font-semibold text-ink">查看建议说明</summary>
                <p className="mt-3 text-sm leading-7 text-steel">{salaryRecommendation.explanation}</p>
              </details>
            ) : null}

            <div className="mt-5" style={{ border: '1px solid var(--color-border)', borderRadius: 8, background: '#FFFFFF', padding: '18px 20px' }}>
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <p className="text-sm font-semibold text-ink">人工调整薪资窗口</p>
                  <p className="mt-2 text-sm leading-6 text-steel">主管或 HR 可以在 AI 建议基础上手动调整最终涨幅和调整后薪资，再提交审批。</p>
                </div>
                <button
                  className="action-secondary"
                  disabled={!canEditSalaryRecommendation}
                  onClick={handleCloseSalaryEditor}
                  type="button"
                >
                  恢复当前建议
                </button>
              </div>

              {isSalaryEditorOpen ? (
                <div className="mt-5 grid gap-4 lg:grid-cols-[1.05fr_0.95fr]">
                  <div className="surface-subtle px-4 py-4">
                    <p className="text-sm font-semibold text-ink">调整参数</p>
                    <div className="mt-4 grid gap-4 md:grid-cols-2">
                      <label className="text-sm text-steel">
                        <span>人工调整比例（%）</span>
                        <input
                          className="toolbar-input mt-2 w-full"
                          max={100}
                          min={0}
                          onChange={(event) => handleManualPercentChange(event.target.value)}
                          step="0.01"
                          type="number"
                          value={manualAdjustmentPercent}
                        />
                      </label>
                      <label className="text-sm text-steel">
                        <span>调整后薪资（元）</span>
                        <input
                          className="toolbar-input mt-2 w-full"
                          min={baseSalaryAmount}
                          onChange={(event) => handleManualSalaryChange(event.target.value)}
                          step="0.01"
                          type="number"
                          value={manualRecommendedSalary}
                        />
                      </label>
                    </div>

                    <div className="mt-4 flex flex-wrap gap-3">
                      <button
                        className="action-primary"
                        disabled={!isManualPercentValid || !isManualSalaryValid || isSavingSalaryAdjustment}
                        onClick={handleSaveSalaryAdjustment}
                        type="button"
                      >
                        {isSavingSalaryAdjustment ? '保存中...' : '保存人工调整'}
                      </button>
                      <button className="action-secondary" disabled={isSavingSalaryAdjustment} onClick={handleCloseSalaryEditor} type="button">
                        取消
                      </button>
                    </div>

                    {!isManualPercentValid ? <p className="mt-3 text-sm" style={{ color: 'var(--color-danger)' }}>调整比例需要填写 0 到 100 之间的数字。</p> : null}
                    {!isManualSalaryValid ? <p className="mt-3 text-sm" style={{ color: 'var(--color-danger)' }}>调整后薪资不能低于当前薪资。</p> : null}
                  </div>

                  <div className="surface-subtle px-4 py-4">
                    <p className="text-sm font-semibold text-ink">调整预览</p>
                    <div className="mt-4 space-y-3 text-sm text-steel">
                      <div className="flex items-center justify-between gap-4">
                        <span>AI 原建议薪资</span>
                        <span className="font-medium text-ink">{formatCurrency(salaryRecommendation.recommended_salary)}</span>
                      </div>
                      <div className="flex items-center justify-between gap-4">
                        <span>人工调整后薪资</span>
                        <span className="font-medium text-ink">{isManualSalaryValid ? formatCurrency(String(manualRecommendedSalaryNumber.toFixed(2))) : '--'}</span>
                      </div>
                      <div className="flex items-center justify-between gap-4">
                        <span>人工调整比例</span>
                        <span className="font-medium text-ink">{isManualPercentValid ? `${manualAdjustmentPercent}%` : '--'}</span>
                      </div>
                      <div className="flex items-center justify-between gap-4">
                        <span>预计调薪金额</span>
                        <span className="font-medium text-ink">{manualSalaryDelta != null ? formatCurrency(String(manualSalaryDelta.toFixed(2))) : '--'}</span>
                      </div>
                    </div>
                  </div>
                </div>
              ) : null}

              {!canEditSalaryRecommendation ? (
                <p className="mt-4 text-sm" style={{ color: 'var(--color-warning)' }}>
                  当前调薪建议已进入审批或锁定状态，暂时不能再做人工调整。
                </p>
              ) : null}
            </div>

            <div className="mt-5 flex flex-wrap gap-3">
              <button
                className="action-primary"
                disabled={
                  !canSubmitApproval ||
                  isSubmittingApproval ||
                  salaryRecommendation.status === 'pending_approval' ||
                  salaryRecommendation.status === 'approved' ||
                  salaryRecommendation.status === 'locked'
                }
                onClick={handleSubmitApproval}
                type="button"
              >
                {isSubmittingApproval ? '提交中...' : '提交审批'}
              </button>
              <Link className="chip-button" to="/approvals">
                查看审批中心
              </Link>
            </div>

            {!canSubmitApproval ? <p className="mt-3 text-sm" style={{ color: 'var(--color-warning)' }}>当前账号无法发起审批，请使用主管、HRBP 或管理员账号。</p> : null}
          </>
        ) : (
          <div className="mt-5" style={{ border: '1px dashed var(--color-border)', borderRadius: 8, background: 'var(--color-bg-subtle)', padding: '16px 20px', fontSize: 14, lineHeight: 1.8, color: 'var(--color-steel)' }}>
            当前评估还没有生成调薪建议。先确认评估结果，再使用上方动作或切回概览模块生成建议。
          </div>
        )}
        {canViewSalaryHistory ? (
          <div className="mt-5">
            <SalaryHistoryPanel
              currentCycleId={selectedCycleId}
              employeeName={employee?.name}
              history={salaryHistory}
              isLoading={isSalaryHistoryLoading}
            />
          </div>
        ) : null}
      </section>
      </>
    );
  })();

  return (
    <AppShell
      title="员工评估详情"
      description="按模块处理材料、证据、复核和调薪。"
      actions={
        <>
          <Link className="chip-button" to={getRoleHomePath(user?.role)}>
            返回工作台
          </Link>
          <Link className="chip-button" to="/approvals">
            审批中心
          </Link>
        </>
      }
    >
      {isLoading ? <p className="px-2 text-sm text-steel">正在加载员工评估详情...</p> : null}
      {errorMessage ? <p className="surface px-5 py-4 text-sm" style={{ color: "var(--color-danger)" }}>{errorMessage}</p> : null}
      {successMessage ? <p className="surface px-5 py-4 text-sm" style={{ color: "var(--color-success)" }}>{successMessage}</p> : null}

      {(() => {
        const currentDuplicate = fileQueue.find((i) => i.status === 'currentDuplicate');
        if (!currentDuplicate) return null;
        return (
          <DuplicateWarningModal
            isOpen
            fileName={currentDuplicate.file.name}
            uploaderName={currentDuplicate.duplicateInfo!.uploaderName}
            uploadedAt={currentDuplicate.duplicateInfo!.uploadedAt}
            onConfirm={handleDuplicateConfirm}
            onCancel={handleDuplicateCancel}
          />
        );
      })()}

      {toastMessage ? (
        <div
          style={{
            position: 'fixed',
            right: 24,
            bottom: 24,
            zIndex: 900,
            background: 'var(--color-info-bg)',
            color: 'var(--color-info)',
            fontSize: 13,
            padding: '8px 16px',
            borderRadius: 6,
            boxShadow: '0 6px 16px rgba(0,0,0,0.08)',
          }}
        >
          {toastMessage}
        </div>
      ) : null}

      {employee ? (
        <>
          <section className="surface animate-fade-up overflow-hidden px-0 py-0">
            <div style={{ borderBottom: '1px solid var(--color-border)', background: 'var(--color-bg-subtle)', padding: '20px 24px' }}>
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <div className="flex flex-wrap items-center gap-3">
                    <h2 className="text-[24px] font-semibold tracking-[-0.03em] text-ink">{employee.name}</h2>
                    <StatusIndicator status={employee.status} />
                  </div>
                  <p className="mt-2 text-sm text-steel">员工编号 {employee.employee_no}</p>
                  <p className="mt-3 max-w-2xl text-sm leading-6 text-steel">按当前周期处理评估流程。</p>
                </div>
                <div style={{ background: 'var(--color-bg-subtle)', border: '1px solid var(--color-border)', borderRadius: 8, padding: '12px 16px', textAlign: 'right' }}>
                  <p style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.18em', color: 'var(--color-steel)' }}>当前模块</p>
                  <p className="mt-2 text-lg font-semibold text-ink">{activeModuleMeta.label}</p>
                  <p className="mt-1 text-xs text-steel">{activeModuleMeta.note}</p>
                </div>
              </div>
            </div>

            <div className="px-6 py-6 lg:px-7">
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                <div className="surface-subtle px-4 py-4"><p className="text-sm text-steel">部门</p><p className="mt-2 text-lg font-semibold text-ink">{employee.department}</p></div>
                <div className="surface-subtle px-4 py-4"><p className="text-sm text-steel">岗位族</p><p className="mt-2 text-lg font-semibold text-ink">{employee.job_family}</p></div>
                <div className="surface-subtle px-4 py-4"><p className="text-sm text-steel">岗位级别</p><p className="mt-2 text-lg font-semibold text-ink">{employee.job_level}</p></div>
                <label className="surface-subtle px-4 py-4">
                  <span className="text-sm text-steel">当前周期</span>
                  <select className="toolbar-input mt-3 w-full" onChange={(event) => setSelectedCycleId(event.target.value)} value={selectedCycleId}>
                    {cycles.map((cycle) => (
                      <option key={cycle.id} value={cycle.id}>{cycle.name}</option>
                    ))}
                  </select>
                </label>
              </div>

              <div style={{ marginTop: 20, border: '1px solid var(--color-border)', borderRadius: 8, background: '#FFFFFF', padding: '16px' }}>
                <div className="flex flex-wrap items-start justify-between gap-4">
                    <div>
                      <p className="text-sm font-semibold text-ink">模块切换</p>
                    </div>
                  <div className="cursor-help text-xs text-steel" style={{ border: '1px solid var(--color-border)', borderRadius: 6, padding: '4px 12px' }} title={activeModuleMeta.helper}>模块说明</div>
                </div>
                <div className="mt-4 flex flex-wrap gap-3">
                  {moduleTabs.map((item) => {
                    const isActive = item.key === activeModule;
                    return (
                      <button
                        key={item.key}
                        onClick={() => setActiveModule(item.key)}
                        type="button"
                        style={{
                          borderRadius: 6,
                          border: `1px solid ${isActive ? 'var(--color-primary)' : 'var(--color-border)'}`,
                          background: isActive ? 'var(--color-primary)' : '#FFFFFF',
                          color: isActive ? '#FFFFFF' : 'var(--color-ink)',
                          padding: '8px 14px',
                          textAlign: 'left',
                          cursor: 'pointer',
                        }}
                      >
                        <div className="text-sm font-semibold">{item.label}</div>
                        <div style={{ marginTop: 2, fontSize: 11, color: isActive ? 'rgba(255,255,255,0.8)' : 'var(--color-steel)' }}>{item.note}</div>
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>
          </section>

          {activeModuleContent}
        </>
      ) : null}
    </AppShell>
  );
}
