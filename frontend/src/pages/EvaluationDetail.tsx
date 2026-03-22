import axios from 'axios';
import { useEffect, useMemo, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';

import { EvidenceCard } from '../components/evaluation/EvidenceCard';
import { EvidenceWorkspaceOverview } from '../components/evaluation/EvidenceWorkspaceOverview';
import { FileList } from '../components/evaluation/FileList';
import { FileUploadPanel } from '../components/evaluation/FileUploadPanel';
import { StatusIndicator } from '../components/evaluation/StatusIndicator';
import { AppShell } from '../components/layout/AppShell';
import { CalibrationCompareTable } from '../components/review/CalibrationCompareTable';
import { DimensionScoreEditor, type DimensionScoreDraft } from '../components/review/DimensionScoreEditor';
import { ReviewPanel } from '../components/review/ReviewPanel';
import { useAuth } from '../hooks/useAuth';
import { submitApproval } from '../services/approvalService';
import { fetchCycles } from '../services/cycleService';
import { confirmEvaluation, fetchEvaluationBySubmission, generateEvaluation, submitHrReview, submitManualReview } from '../services/evaluationService';
import {
  deleteSubmissionFile,
  fetchSubmissionEvidence,
  fetchSubmissionFiles,
  importGitHubSubmissionFile,
  parseAllSubmissionFiles,
  parseFile,
  replaceSubmissionFile,
  uploadSubmissionFiles,
} from '../services/fileService';
import { fetchEmployee } from '../services/employeeService';
import { fetchSalaryRecommendationByEvaluation, recommendSalary } from '../services/salaryService';
import { ensureSubmission } from '../services/submissionService';
import type {
  CycleRecord,
  EmployeeRecord,
  EvaluationRecord,
  EvidenceRecord,
  SalaryRecommendationRecord,
  SubmissionRecord,
  UploadedFileRecord,
} from '../types/api';
import { getRoleHomePath } from '../utils/roleAccess';

const FLOW = ['collecting', 'submitted', 'parsing', 'evaluated', 'reviewing', 'calibrated', 'approved', 'published'] as const;
const MODULE_KEYS = ['overview', 'parse', 'evidence', 'review', 'salary'] as const;

type DetailModuleKey = (typeof MODULE_KEYS)[number];

type ModuleTab = {
  key: DetailModuleKey;
  label: string;
  note: string;
  helper: string;
};

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
    { code: 'TOOL', label: 'AI 工具掌握度', score: 70, rationale: '等待评估结果。' },
    { code: 'DEPTH', label: 'AI 应用深度', score: 70, rationale: '等待评估结果。' },
    { code: 'LEARN', label: 'AI 学习速度', score: 70, rationale: '等待评估结果。' },
    { code: 'SHARE', label: '知识分享', score: 70, rationale: '等待评估结果。' },
    { code: 'IMPACT', label: '业务影响力', score: 70, rationale: '等待评估结果。' },
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
  return evaluation.dimension_scores.map((dimension) => ({
    code: dimension.dimension_code,
    label: formatDimensionLabel(dimension.dimension_code),
    score: dimension.raw_score,
    rationale: localizeDimensionRationale(dimension.dimension_code, dimension.rationale),
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
  if (!dimensions.length) {
    return 0;
  }
  return Number((dimensions.reduce((sum, dimension) => sum + dimension.score, 0) / dimensions.length).toFixed(1));
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

  const [employee, setEmployee] = useState<EmployeeRecord | null>(null);
  const [cycles, setCycles] = useState<CycleRecord[]>([]);
  const [selectedCycleId, setSelectedCycleId] = useState('');
  const [activeModule, setActiveModule] = useState<DetailModuleKey>(() => normalizeModuleKey(searchParams.get('tab')));
  const [submission, setSubmission] = useState<SubmissionRecord | null>(null);
  const [files, setFiles] = useState<UploadedFileRecord[]>([]);
  const [evidenceItems, setEvidenceItems] = useState<EvidenceRecord[]>([]);
  const [evaluation, setEvaluation] = useState<EvaluationRecord | null>(null);
  const [salaryRecommendation, setSalaryRecommendation] = useState<SalaryRecommendationRecord | null>(null);
  const [dimensions, setDimensions] = useState<DimensionScoreDraft[]>(() => createInitialDimensions());
  const [reviewLevel, setReviewLevel] = useState('Level 3');
  const [reviewComment, setReviewComment] = useState('请填写主管评分依据；如进入 HR 审核，请填写同意或打回原因。');
  const [isUploading, setIsUploading] = useState(false);
  const [isGithubImporting, setIsGithubImporting] = useState(false);
  const [isParsingAll, setIsParsingAll] = useState(false);
  const [workingFileId, setWorkingFileId] = useState<string | null>(null);
  const [isReviewSubmitting, setIsReviewSubmitting] = useState(false);
  const [isConfirming, setIsConfirming] = useState(false);
  const [isReturning, setIsReturning] = useState(false);
  const [isGeneratingEvaluation, setIsGeneratingEvaluation] = useState(false);
  const [isGeneratingSalary, setIsGeneratingSalary] = useState(false);
  const [isSubmittingApproval, setIsSubmittingApproval] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const canSubmitApproval = user?.role === 'admin' || user?.role === 'hrbp' || user?.role === 'manager';
  const canHrReview = user?.role === 'admin' || user?.role === 'hrbp';

  async function refreshSubmissionData(targetSubmissionId: string) {
    const [filesResponse, evidenceResponse] = await Promise.all([
      fetchSubmissionFiles(targetSubmissionId),
      fetchSubmissionEvidence(targetSubmissionId),
    ]);

    setFiles(filesResponse.items);
    setEvidenceItems(evidenceResponse.items.map(mapEvidence));

    try {
      const evaluationResponse = await fetchEvaluationBySubmission(targetSubmissionId);
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
    } catch {
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

        const requestedCycleId = searchParams.get('cycleId');
        const fallbackCycleId = cycleResponse.items[0]?.id ?? '';
        const nextCycleId = requestedCycleId && cycleResponse.items.some((cycle) => cycle.id === requestedCycleId)
          ? requestedCycleId
          : fallbackCycleId;
        setSelectedCycleId(nextCycleId);
        setActiveModule(normalizeModuleKey(searchParams.get('tab')));
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
  }, [employeeId, searchParams]);

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
  const reviewAverage = averageDimensionScore(dimensions);

  const calibrationRows = useMemo(
    () =>
      dimensions.map((dimension, index) => ({
        code: dimension.code,
        label: dimension.label,
        aiScore: evaluation?.dimension_scores[index]?.raw_score ?? dimension.score,
        manualScore: dimension.score,
        note: dimension.rationale,
      })),
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
    ? 'AI 正在批量解析材料'
    : parseInProgressCount > 0
      ? '材料解析进行中'
      : parseFailedCount > 0
        ? '有材料等待重新解析'
        : parseCompletedCount > 0
          ? '证据工作区已准备就绪'
          : '等待上传或导入材料';

  const parseStatusDescription = isParsingAll
    ? '系统正在解析当前材料。'
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

  const activeModuleMeta = moduleTabs.find((item) => item.key === activeModule) ?? moduleTabs[0];

  async function reloadCurrentCycleData() {
    if (!employeeId || !selectedCycleId) {
      return;
    }
    await loadCycleSubmission(employeeId, selectedCycleId);
  }

  async function handleFilesSelected(selectedFiles: globalThis.FileList | null) {
    if (!selectedFiles?.length || !submission) {
      return;
    }

    setIsUploading(true);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      const uploadResponse = await uploadSubmissionFiles(submission.id, Array.from(selectedFiles));
      await Promise.all(uploadResponse.items.map((file) => parseFile(file.id)));
      await reloadCurrentCycleData();
      setSuccessMessage('材料已上传，系统正在自动解析。');
    } catch (error) {
      setErrorMessage(resolveError(error));
    } finally {
      setIsUploading(false);
    }
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
      await parseFile(updated.id);
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

    setIsParsingAll(true);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      await parseAllSubmissionFiles(submission.id);
      await reloadCurrentCycleData();
      setSuccessMessage('已启动当前周期的批量解析。');
    } catch (error) {
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
        await parseAllSubmissionFiles(submission.id);
      }
      const nextEvaluation = await generateEvaluation(submission.id);
      setEvaluation(nextEvaluation);
      setSalaryRecommendation(null);
      setDimensions(mapEvaluationToDrafts(nextEvaluation));
      setReviewLevel(nextEvaluation.ai_level);
      setReviewComment(localizeEvaluationNarrative(nextEvaluation.explanation));
      await reloadCurrentCycleData();
      setSuccessMessage('AI 评分已生成，可以继续主管复核。');
    } catch (error) {
      setErrorMessage(resolveError(error));
    } finally {
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
      setSuccessMessage('主管评分已提交。');
      setActiveModule('review');
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
      if (evaluation.status === 'pending_hr') {
        await submitHrReview(evaluation.id, { decision: 'approved', comment: reviewComment });
      } else {
        await confirmEvaluation(evaluation.id);
      }
      await reloadCurrentCycleData();
      setSuccessMessage('评估结果已确认。');
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

  async function handleGenerateSalary() {
    if (!evaluation) {
      return;
    }

    setIsGeneratingSalary(true);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      const recommendation = await recommendSalary(evaluation.id);
      setSalaryRecommendation(recommendation);
      setSuccessMessage('调薪建议已生成。');
      setActiveModule('salary');
    } catch (error) {
      setErrorMessage(resolveError(error));
    } finally {
      setIsGeneratingSalary(false);
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
      await submitApproval({
        recommendationId: salaryRecommendation.id,
        steps: [
          {
            step_name: '发起审批',
            approver_id: user.id,
            comment: '从员工评估详情页提交审批。',
          },
        ],
      });
      setSalaryRecommendation((current) => (current ? { ...current, status: 'pending_approval' } : current));
      setSuccessMessage('调薪建议已提交审批。');
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
                <h3 className="font-medium text-ink">{isGeneratingEvaluation ? '生成中...' : '生成 AI 评分'}</h3>
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
                  <h2 className="mt-2 text-[24px] font-semibold tracking-[-0.03em] text-ink">{parseStatusTitle}</h2>
                  <p className="mt-2 max-w-3xl text-sm leading-6 text-steel">{parseStatusDescription}</p>
                </div>
                <div style={{ background: '#FFFFFF', border: '1px solid var(--color-border)', borderRadius: 8, padding: '12px 16px', textAlign: 'right' }}>
                  <p style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.18em', color: 'var(--color-steel)' }}>完成度</p>
                  <p className="mt-2 text-[34px] font-semibold tracking-[-0.05em] text-ink">{parseProgressPercent}%</p>
                  <p className="text-xs text-steel">{parseCompletedCount}/{files.length || 0} 份材料已完成解析</p>
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
                    width: `${parseProgressPercent}%`,
                    background: parseFailedCount > 0 ? 'var(--color-danger)' : 'var(--color-primary)',
                  }}
                />
              </div>

              <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                <div className="surface-subtle px-4 py-4"><p className="text-sm text-steel">已完成</p><p className="mt-2 text-2xl font-semibold" style={{ color: 'var(--color-success)' }}>{parseCompletedCount}</p></div>
                <div className="surface-subtle px-4 py-4"><p className="text-sm text-steel">进行中</p><p className="mt-2 text-2xl font-semibold" style={{ color: 'var(--color-warning)' }}>{isParsingAll ? Math.max(parseInProgressCount, 1) : parseInProgressCount}</p></div>
                <div className="surface-subtle px-4 py-4"><p className="text-sm text-steel">待处理</p><p className="mt-2 text-2xl font-semibold text-ink">{parsePendingCount}</p></div>
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
              <div style={{ border: '1px solid var(--color-border)', borderRadius: 8, background: 'var(--color-bg-subtle)', padding: '10px 16px', textAlign: 'right' }}>
                <p style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.18em', color: 'var(--color-steel)' }}>阅读方式</p>
                <p className="mt-2 text-sm font-medium text-ink">先看总览，再看单条证据</p>
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

            {salaryRecommendation.explanation ? (
              <details className="mt-5" style={{ border: '1px solid var(--color-border)', borderRadius: 8, background: 'var(--color-bg-subtle)', padding: '12px 16px' }}>
                <summary className="cursor-pointer text-sm font-semibold text-ink">查看建议说明</summary>
                <p className="mt-3 text-sm leading-7 text-steel">{salaryRecommendation.explanation}</p>
              </details>
            ) : null}

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
      </section>
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
                    <p className="mt-1 text-sm text-steel">切换后只显示当前模块。</p>
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