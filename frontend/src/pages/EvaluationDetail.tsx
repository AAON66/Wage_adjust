import axios from 'axios';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { useEffect, useMemo, useState } from 'react';

import { EvidenceCard } from '../components/evaluation/EvidenceCard';
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
import { confirmEvaluation, fetchEvaluationBySubmission, generateEvaluation, submitManualReview } from '../services/evaluationService';
import { fetchSubmissionEvidence, fetchSubmissionFiles, parseFile, uploadSubmissionFiles } from '../services/fileService';
import { fetchEmployee } from '../services/employeeService';
import { fetchSalaryRecommendationByEvaluation, recommendSalary } from '../services/salaryService';
import { ensureSubmission } from '../services/submissionService';
import type { CycleRecord, EmployeeRecord, EvaluationRecord, EvidenceRecord, SalaryRecommendationRecord, SubmissionRecord, UploadedFileRecord } from '../types/api';

const FLOW = ['collecting', 'submitted', 'parsing', 'evaluated', 'reviewing', 'calibrated', 'approved', 'published'];

function resolveError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    return (error.response?.data as { detail?: string; message?: string } | undefined)?.detail ??
      (error.response?.data as { detail?: string; message?: string } | undefined)?.message ??
      '加载员工详情失败。';
  }
  return '加载员工详情失败。';
}

function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value));
}

function formatCurrency(value: string): string {
  return new Intl.NumberFormat('zh-CN', { style: 'currency', currency: 'CNY', maximumFractionDigits: 0 }).format(Number(value));
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

function mapEvaluationToDrafts(evaluation: EvaluationRecord | null): DimensionScoreDraft[] {
  if (!evaluation) {
    return createInitialDimensions();
  }
  return evaluation.dimension_scores.map((dimension) => ({
    code: dimension.dimension_code,
    label: formatDimensionLabel(dimension.dimension_code),
    score: dimension.raw_score,
    rationale: dimension.rationale,
  }));
}

function mapEvidence(item: EvidenceRecord): EvidenceRecord {
  const tags = Object.entries(item.metadata_json ?? {}).map(([key, value]) => `${key}:${String(value)}`);
  return { ...item, tags };
}

function inferStatus(submission: SubmissionRecord | null, files: UploadedFileRecord[], evaluation: EvaluationRecord | null, recommendation: SalaryRecommendationRecord | null): string {
  if (recommendation?.status === 'locked' || recommendation?.status === 'approved') {
    return 'approved';
  }
  if (recommendation?.status === 'pending_approval') {
    return 'reviewing';
  }
  if (evaluation?.status === 'confirmed') {
    return 'calibrated';
  }
  if (evaluation?.status === 'reviewed') {
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

export function EvaluationDetailPage() {
  const { employeeId } = useParams<{ employeeId: string }>();
  const [searchParams] = useSearchParams();
  const { user } = useAuth();
  const [employee, setEmployee] = useState<EmployeeRecord | null>(null);
  const [cycles, setCycles] = useState<CycleRecord[]>([]);
  const [selectedCycleId, setSelectedCycleId] = useState('');
  const [submission, setSubmission] = useState<SubmissionRecord | null>(null);
  const [files, setFiles] = useState<UploadedFileRecord[]>([]);
  const [evidenceItems, setEvidenceItems] = useState<EvidenceRecord[]>([]);
  const [evaluation, setEvaluation] = useState<EvaluationRecord | null>(null);
  const [salaryRecommendation, setSalaryRecommendation] = useState<SalaryRecommendationRecord | null>(null);
  const [dimensions, setDimensions] = useState<DimensionScoreDraft[]>(() => createInitialDimensions());
  const [reviewLevel, setReviewLevel] = useState('Level 3');
  const [reviewComment, setReviewComment] = useState('已开启人工复核，请记录分歧点、判断依据和需要升级处理的说明。');
  const [isUploading, setIsUploading] = useState(false);
  const [isReviewSubmitting, setIsReviewSubmitting] = useState(false);
  const [isConfirming, setIsConfirming] = useState(false);
  const [isGeneratingEvaluation, setIsGeneratingEvaluation] = useState(false);
  const [isGeneratingSalary, setIsGeneratingSalary] = useState(false);
  const [isSubmittingApproval, setIsSubmittingApproval] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const canSubmitApproval = user?.role === 'admin' || user?.role === 'hrbp' || user?.role === 'manager';

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
        setSelectedCycleId(requestedCycleId && cycleResponse.items.some((cycle) => cycle.id === requestedCycleId) ? requestedCycleId : fallbackCycleId);
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
        const submissionResponse = await ensureSubmission(employeeId, selectedCycleId);
        if (cancelled) {
          return;
        }
        setSubmission(submissionResponse);

        const [filesResponse, evidenceResponse] = await Promise.all([
          fetchSubmissionFiles(submissionResponse.id),
          fetchSubmissionEvidence(submissionResponse.id),
        ]);
        if (cancelled) {
          return;
        }
        setFiles(filesResponse.items);
        setEvidenceItems(evidenceResponse.items.map(mapEvidence));

        try {
          const evaluationResponse = await fetchEvaluationBySubmission(submissionResponse.id);
          if (cancelled) {
            return;
          }
          setEvaluation(evaluationResponse);
          setDimensions(mapEvaluationToDrafts(evaluationResponse));
          setReviewLevel(evaluationResponse.ai_level);
          setReviewComment(evaluationResponse.explanation);
          try {
            const recommendationResponse = await fetchSalaryRecommendationByEvaluation(evaluationResponse.id);
            if (!cancelled) {
              setSalaryRecommendation(recommendationResponse);
            }
          } catch {
            if (!cancelled) {
              setSalaryRecommendation(null);
            }
          }
        } catch {
          if (!cancelled) {
            setEvaluation(null);
            setSalaryRecommendation(null);
            setDimensions(createInitialDimensions());
          }
        }
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
  const activeIndex = FLOW.indexOf(currentStatus);
  const calibrationRows = useMemo(
    () => dimensions.map((dimension, index) => ({
      code: dimension.code,
      label: dimension.label,
      aiScore: evaluation?.dimension_scores[index]?.raw_score ?? dimension.score,
      manualScore: dimension.score,
      note: dimension.rationale,
    })),
    [dimensions, evaluation],
  );

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
      setReviewComment(evaluationResponse.explanation);
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
    }
  }

  async function handleFilesSelected(selectedFiles: FileList | null) {
    if (!selectedFiles?.length || !submission) {
      return;
    }
    setIsUploading(true);
    try {
      await uploadSubmissionFiles(submission.id, Array.from(selectedFiles));
      await refreshSubmissionData(submission.id);
    } catch (error) {
      setErrorMessage(resolveError(error));
    } finally {
      setIsUploading(false);
    }
  }

  async function handleRetryParse(fileId: string) {
    if (!submission) {
      return;
    }
    try {
      await parseFile(fileId);
      await refreshSubmissionData(submission.id);
    } catch (error) {
      setErrorMessage(resolveError(error));
    }
  }

  function handleDeleteFile(fileId: string) {
    setFiles((current) => current.filter((file) => file.id !== fileId));
  }

  async function handleGenerateEvaluation() {
    if (!submission) {
      return;
    }
    setIsGeneratingEvaluation(true);
    try {
      const nextEvaluation = await generateEvaluation(submission.id);
      setEvaluation(nextEvaluation);
      setSalaryRecommendation(null);
      setDimensions(mapEvaluationToDrafts(nextEvaluation));
      setReviewLevel(nextEvaluation.ai_level);
      setReviewComment(nextEvaluation.explanation);
      await refreshSubmissionData(submission.id);
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
    try {
      const reviewed = await submitManualReview(evaluation.id, {
        ai_level: reviewLevel,
        explanation: reviewComment,
        dimension_scores: dimensions.map((dimension) => ({
          dimension_code: dimension.code,
          raw_score: dimension.score,
          rationale: dimension.rationale,
        })),
      });
      setEvaluation(reviewed);
      setDimensions(mapEvaluationToDrafts(reviewed));
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
    try {
      await confirmEvaluation(evaluation.id);
      await refreshSubmissionData(submission.id);
    } catch (error) {
      setErrorMessage(resolveError(error));
    } finally {
      setIsConfirming(false);
    }
  }

  async function handleGenerateSalary() {
    if (!evaluation) {
      return;
    }
    setIsGeneratingSalary(true);
    try {
      const recommendation = await recommendSalary(evaluation.id);
      setSalaryRecommendation(recommendation);
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
    try {
      await submitApproval({
        recommendationId: salaryRecommendation.id,
        steps: [
          {
            step_name: '当前审批',
            approver_id: user.id,
            comment: '由评估详情页提交审批。',
          },
        ],
      });
      setSalaryRecommendation((current) => current ? { ...current, status: 'pending_approval' } : current);
    } catch (error) {
      setErrorMessage(resolveError(error));
    } finally {
      setIsSubmittingApproval(false);
    }
  }

  return (
    <AppShell
      title="员工评估详情"
      description="围绕单个员工查看材料、证据、AI 评估、人工复核和调薪建议。"
      actions={
        <>
          <Link className="chip-button" to="/employees">返回列表</Link>
          <Link className="chip-button" to="/cycles/create">创建周期</Link>
        </>
      }
    >
      {isLoading ? <p className="px-2 text-sm text-steel">正在加载员工详情...</p> : null}
      {errorMessage ? <p className="surface px-5 py-4 text-sm text-red-600">{errorMessage}</p> : null}

      {employee ? (
        <>
          <section className="grid gap-5 lg:grid-cols-[1.24fr_0.76fr]">
            <article className="surface animate-fade-up px-6 py-6 lg:px-7">
              <div className="flex flex-wrap items-start justify-between gap-4 border-b border-[#e6eef9] pb-4">
                <div>
                  <div className="flex flex-wrap items-center gap-3">
                    <h2 className="text-[28px] font-semibold tracking-[-0.04em] text-ink">{employee.name}</h2>
                    <StatusIndicator status={employee.status} />
                  </div>
                  <p className="mt-2 text-sm text-steel">员工编号 {employee.employee_no}</p>
                </div>
                <div className="surface-subtle px-4 py-4 text-right">
                  <p className="text-sm text-steel">更新时间</p>
                  <p className="mt-2 text-sm font-medium text-ink">{formatDateTime(employee.updated_at)}</p>
                </div>
              </div>

              <dl className="mt-5 grid gap-3 md:grid-cols-2">
                <div className="surface-subtle px-4 py-4">
                  <dt className="text-sm text-steel">部门</dt>
                  <dd className="mt-2 text-lg font-semibold text-ink">{employee.department}</dd>
                </div>
                <div className="surface-subtle px-4 py-4">
                  <dt className="text-sm text-steel">岗位族</dt>
                  <dd className="mt-2 text-lg font-semibold text-ink">{employee.job_family}</dd>
                </div>
                <div className="surface-subtle px-4 py-4">
                  <dt className="text-sm text-steel">岗位级别</dt>
                  <dd className="mt-2 text-lg font-semibold text-ink">{employee.job_level}</dd>
                </div>
                <label className="surface-subtle px-4 py-4">
                  <span className="text-sm text-steel">当前周期</span>
                  <select className="toolbar-input mt-3 w-full" onChange={(event) => setSelectedCycleId(event.target.value)} value={selectedCycleId}>
                    {cycles.map((cycle) => (
                      <option key={cycle.id} value={cycle.id}>{cycle.name}</option>
                    ))}
                  </select>
                </label>
              </dl>
            </article>

            <aside className="surface animate-fade-up px-6 py-6 lg:px-7" style={{ animationDelay: '60ms' }}>
              <div className="border-b border-[#e6eef9] pb-4">
                <p className="eyebrow">实时操作</p>
                <h2 className="mt-2 text-[24px] font-semibold tracking-[-0.03em] text-ink">实时操作</h2>
              </div>
              <div className="mt-5 grid gap-3">
                <button className="surface-subtle px-4 py-4 text-left disabled:opacity-60" disabled={isGeneratingEvaluation || !submission} onClick={handleGenerateEvaluation} type="button">
                  <h3 className="font-medium text-ink">{isGeneratingEvaluation ? '评估生成中...' : '生成 AI 评估'}</h3>
                  <p className="mt-2 text-sm leading-6 text-steel">为当前 submission 创建或刷新 AI 评估结果。</p>
                </button>
                <button className="surface-subtle px-4 py-4 text-left disabled:opacity-60" disabled={isGeneratingSalary || !evaluation} onClick={handleGenerateSalary} type="button">
                  <h3 className="font-medium text-ink">{isGeneratingSalary ? '调薪建议生成中...' : '生成调薪建议'}</h3>
                  <p className="mt-2 text-sm leading-6 text-steel">基于当前评估结果运行调薪建议引擎。</p>
                </button>
                <div className="surface-subtle px-4 py-4">
                  <h3 className="font-medium text-ink">提交上下文</h3>
                  <p className="mt-3 text-sm leading-6 text-steel">提交记录：{submission?.id ?? '未就绪'}</p>
                  <p className="text-sm leading-6 text-steel">周期：{currentCycle?.name ?? '未选择周期'}</p>
                  <p className="text-sm leading-6 text-steel">评估：{evaluation?.status ?? '尚未生成'}</p>
                  <p className="text-sm leading-6 text-steel">审批：{salaryRecommendation?.status ?? '尚未提交'}</p>
                </div>
              </div>
            </aside>
          </section>

          <section className="surface animate-fade-up px-6 py-6 lg:px-7">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#e6eef9] pb-4">
              <div>
                <p className="eyebrow">流程状态</p>
                <h2 className="mt-2 text-[24px] font-semibold tracking-[-0.03em] text-ink">评估生命周期</h2>
              </div>
              <StatusIndicator status={currentStatus} />
            </div>
            <div className="mt-5 grid gap-3 md:grid-cols-4 xl:grid-cols-8">
              {FLOW.map((status, index) => {
                const isDone = activeIndex >= index;
                return (
                  <div className={`rounded-[22px] border px-4 py-4 text-center ${isDone ? 'border-[#2d5cff] bg-[#2d5cff] text-white' : 'border-[#dce6f5] bg-[#f8fbff] text-steel'}`} key={status}>
                    <div className="text-xs uppercase tracking-[0.18em]">步骤 {index + 1}</div>
                    <div className="mt-3 flex justify-center">
                      <StatusIndicator status={status} />
                    </div>
                  </div>
                );
              })}
            </div>
          </section>

          <section className="grid gap-5 xl:grid-cols-[1.02fr_0.98fr]">
            <div className="flex flex-col gap-5">
              <div className="surface px-6 py-6 lg:px-7">
                <FileUploadPanel isUploading={isUploading} onFilesSelected={handleFilesSelected} />
              </div>
              <div className="surface px-6 py-6 lg:px-7">
                <FileList files={files} onDelete={handleDeleteFile} onRetryParse={handleRetryParse} />
              </div>
            </div>
            <section className="surface px-6 py-6 lg:px-7">
              <div className="flex items-center justify-between gap-3 border-b border-[#e6eef9] pb-4">
                <div>
                  <p className="eyebrow">证据提取</p>
                  <h2 className="mt-2 text-[24px] font-semibold tracking-[-0.03em] text-ink">提取出的证据卡片</h2>
                </div>
                <span className="text-sm text-steel">{evidenceItems.length} 张卡片</span>
              </div>
              <div className="mt-5 grid gap-4">
                {evidenceItems.map((item) => (
                  <EvidenceCard evidence={item} key={item.id} />
                ))}
              </div>
            </section>
          </section>

          <section className="grid gap-5 xl:grid-cols-[1.02fr_0.98fr]">
            <div className="flex flex-col gap-5">
              <div className="surface px-6 py-6 lg:px-7">
                <ReviewPanel
                  aiLevel={evaluation?.ai_level ?? '未生成'}
                  dimensions={dimensions}
                  isConfirming={isConfirming}
                  isSubmitting={isReviewSubmitting}
                  onConfirmEvaluation={handleConfirmEvaluation}
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
                <CalibrationCompareTable rows={calibrationRows} />
              </div>
              <section className="surface px-6 py-6 lg:px-7">
                <div className="border-b border-[#e6eef9] pb-4">
                  <p className="eyebrow">调薪建议</p>
                  <h3 className="mt-2 text-[24px] font-semibold tracking-[-0.03em] text-ink">建议结果快照</h3>
                </div>
                {salaryRecommendation ? (
                  <>
                    <dl className="mt-5 space-y-3 text-sm text-steel">
                      <div className="flex justify-between gap-4"><dt>状态</dt><dd className="text-ink">{salaryRecommendation.status}</dd></div>
                      <div className="flex justify-between gap-4"><dt>当前薪资</dt><dd className="text-ink">{formatCurrency(salaryRecommendation.current_salary)}</dd></div>
                      <div className="flex justify-between gap-4"><dt>建议薪资</dt><dd className="text-ink">{formatCurrency(salaryRecommendation.recommended_salary)}</dd></div>
                      <div className="flex justify-between gap-4"><dt>最终调整比例</dt><dd className="text-ink">{(salaryRecommendation.final_adjustment_ratio * 100).toFixed(2)}%</dd></div>
                    </dl>
                    <div className="mt-5 flex flex-wrap gap-3">
                      <button
                        className="rounded-full bg-[#2d5cff] px-5 py-3 text-sm font-semibold text-white shadow-float disabled:opacity-60"
                        disabled={!canSubmitApproval || isSubmittingApproval || salaryRecommendation.status === 'pending_approval' || salaryRecommendation.status === 'approved' || salaryRecommendation.status === 'locked'}
                        onClick={handleSubmitApproval}
                        type="button"
                      >
                        {isSubmittingApproval ? '提交中...' : '提交审批'}
                      </button>
                      <Link className="chip-button" to="/approvals">
                        查看审批中心
                      </Link>
                    </div>
                    {!canSubmitApproval ? <p className="mt-3 text-sm text-amber-700">当前账号角色无法发起审批，请使用主管、HRBP 或管理员账号。</p> : null}
                  </>
                ) : (
                  <p className="mt-4 text-sm text-steel">当前评估尚未生成调薪建议。</p>
                )}
              </section>
            </div>
          </section>
        </>
      ) : null}
    </AppShell>
  );
}


