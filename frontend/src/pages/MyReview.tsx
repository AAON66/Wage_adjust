import axios from 'axios';
import { Link } from 'react-router-dom';
import { useEffect, useMemo, useState } from 'react';

import { DimensionCard } from '../components/evaluation/DimensionCard';
import { DuplicateWarningModal } from '../components/evaluation/DuplicateWarningModal';
import { DimensionRadarChart } from '../components/evaluation/DimensionRadarChart';
import { EvaluationStepBar } from '../components/evaluation/EvaluationStepBar';
import { EvidenceCard } from '../components/evaluation/EvidenceCard';
import { FileList } from '../components/evaluation/FileList';
import { FileUploadPanel } from '../components/evaluation/FileUploadPanel';
import { SalaryResultCard } from '../components/evaluation/SalaryResultCard';
import { StatusIndicator } from '../components/evaluation/StatusIndicator';
import { AppShell } from '../components/layout/AppShell';
import { useAuth } from '../hooks/useAuth';
import { fetchApprovalHistory } from '../services/approvalService';
import { fetchCycles } from '../services/cycleService';
import { fetchEmployees } from '../services/employeeService';
import { fetchEvaluationBySubmission } from '../services/evaluationService';
import {
  deleteSubmissionFile,
  fetchSubmissionEvidence,
  fetchSubmissionFiles,
  importGitHubSubmissionFile,
  parseFile,
  replaceSubmissionFile,
  uploadSubmissionFiles,
  uploadSubmissionFilesWithDuplicate,
} from '../services/fileService';
import { checkDuplicate } from '../services/sharingService';
import { computeFileSHA256 } from '../utils/fileHash';
import { fetchSalaryRecommendationByEvaluation } from '../services/salaryService';
import { ensureSubmission, fetchEmployeeSubmissions } from '../services/submissionService';
import type {
  ApprovalRecord,
  CycleRecord,
  EmployeeRecord,
  EvaluationRecord,
  EvidenceRecord,
  SalaryRecommendationRecord,
  SubmissionRecord,
  UploadedFileRecord,
} from '../types/api';
import { findEmployeeForUser } from '../utils/employeeIdentity';
import { getRoleLabel } from '../utils/roleAccess';

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

function resolveError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    return (error.response?.data as { detail?: string; message?: string } | undefined)?.detail ??
      (error.response?.data as { detail?: string; message?: string } | undefined)?.message ??
      '加载个人评估中心失败。';
  }
  return '加载个人评估中心失败。';
}

function formatDate(value: string | null): string {
  if (!value) return '待提交';
  return new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium' }).format(new Date(value));
}

function mapEvidence(item: EvidenceRecord): EvidenceRecord {
  const tags = Object.entries(item.metadata_json ?? {}).map(([key, value]) => `${key}:${String(value)}`);
  return { ...item, tags };
}

function resolveCurrentStep(
  salaryStatus: string | null,
  approvals: ApprovalRecord[],
): number {
  // Step 3: completed
  if (salaryStatus === 'approved') return 3;

  // Determine from approval records
  const currentPending = approvals.find(
    (r) => r.is_current_step && r.decision === 'pending',
  );
  if (currentPending) {
    if (currentPending.step_order === 1) return 1;
    if (currentPending.step_order >= 2) return 2;
  }

  // Default: submitted
  return 0;
}

export function MyReviewPage() {
  const { user } = useAuth();
  const [employee, setEmployee] = useState<EmployeeRecord | null>(null);
  const [cycles, setCycles] = useState<CycleRecord[]>([]);
  const [selectedCycleId, setSelectedCycleId] = useState('');
  const [submissions, setSubmissions] = useState<SubmissionRecord[]>([]);
  const [currentSubmission, setCurrentSubmission] = useState<SubmissionRecord | null>(null);
  const [files, setFiles] = useState<UploadedFileRecord[]>([]);
  const [evidenceItems, setEvidenceItems] = useState<EvidenceRecord[]>([]);
  const [evaluation, setEvaluation] = useState<EvaluationRecord | null>(null);
  const [salaryRecommendation, setSalaryRecommendation] = useState<SalaryRecommendationRecord | null>(null);
  const [approvalRecords, setApprovalRecords] = useState<ApprovalRecord[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [isGithubImporting, setIsGithubImporting] = useState(false);
  const [workingFileId, setWorkingFileId] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [fileQueue, setFileQueue] = useState<FileQueueItem[]>([]);
  const [hashCheckStatus, setHashCheckStatus] = useState<'idle' | 'checking' | 'error'>('idle');
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  async function loadCycleWorkspace(targetEmployeeId: string, cycleId: string) {
    const submissionResponse = await ensureSubmission(targetEmployeeId, cycleId);
    const [submissionListResponse, fileResponse, evidenceResponse] = await Promise.all([
      fetchEmployeeSubmissions(targetEmployeeId),
      fetchSubmissionFiles(submissionResponse.id),
      fetchSubmissionEvidence(submissionResponse.id),
    ]);

    setCurrentSubmission(submissionResponse);
    setSubmissions(submissionListResponse.items);
    setFiles(fileResponse.items);
    setEvidenceItems(evidenceResponse.items.map(mapEvidence));

    // Fetch evaluation (404 = no evaluation yet, not an error)
    let evalData: EvaluationRecord | null = null;
    try {
      evalData = await fetchEvaluationBySubmission(submissionResponse.id);
    } catch (err) {
      if (axios.isAxiosError(err) && err.response?.status === 404) {
        evalData = null;
      } else {
        throw err;
      }
    }
    setEvaluation(evalData);

    // When evaluation exists, fetch salary recommendation, then approval history
    let salaryData: SalaryRecommendationRecord | null = null;
    if (evalData) {
      try {
        salaryData = await fetchSalaryRecommendationByEvaluation(evalData.id);
      } catch (err) {
        if (axios.isAxiosError(err) && err.response?.status === 404) {
          salaryData = null;
        } else {
          throw err;
        }
      }
    }
    setSalaryRecommendation(salaryData);

    let approvalItems: ApprovalRecord[] = [];
    if (salaryData) {
      try {
        const historyResponse = await fetchApprovalHistory(salaryData.id);
        approvalItems = historyResponse.items;
      } catch {
        approvalItems = [];
      }
    }
    setApprovalRecords(approvalItems);
  }

  useEffect(() => {
    let cancelled = false;

    async function loadBase() {
      setIsLoading(true);
      setErrorMessage(null);
      try {
        const [employeeResponse, cycleResponse] = await Promise.all([
          fetchEmployees({ page: 1, page_size: 100 }),
          fetchCycles(),
        ]);
        if (cancelled) return;

        const matchedEmployee = findEmployeeForUser(user, employeeResponse.items);
        setEmployee(matchedEmployee);
        setCycles(cycleResponse.items);
        setSelectedCycleId(cycleResponse.items[0]?.id ?? '');

        if (!matchedEmployee) {
          setCurrentSubmission(null);
          setSubmissions([]);
          setFiles([]);
          setEvidenceItems([]);
          setEvaluation(null);
          setSalaryRecommendation(null);
          setApprovalRecords([]);
        }
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
  }, [user]);

  useEffect(() => {
    let cancelled = false;

    async function loadWorkspace() {
      if (!employee || !selectedCycleId) {
        return;
      }

      setIsLoading(true);
      setErrorMessage(null);
      try {
        await loadCycleWorkspace(employee.id, selectedCycleId);
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

    void loadWorkspace();
    return () => {
      cancelled = true;
    };
  }, [employee, selectedCycleId]);

  const cycleNameById = useMemo(() => Object.fromEntries(cycles.map((cycle) => [cycle.id, cycle.name])), [cycles]);
  const currentCycle = useMemo(() => cycles.find((cycle) => cycle.id === selectedCycleId) ?? null, [cycles, selectedCycleId]);

  async function refreshCurrentWorkspace() {
    if (!employee || !selectedCycleId) {
      return;
    }
    await loadCycleWorkspace(employee.id, selectedCycleId);
  }

  function showToast(message: string) {
    setToastMessage(message);
    setTimeout(() => setToastMessage(null), 4000);
  }

  async function finishQueueAndUpload(queue: FileQueueItem[]) {
    if (!currentSubmission) return;
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
      const uploadedFileIds: string[] = [];
      if (cleanFiles.length > 0) {
        const resp = await uploadSubmissionFiles(currentSubmission.id, cleanFiles);
        uploadedFileIds.push(...resp.items.map((f) => f.id));
      }
      for (const item of duplicateItems) {
        const resp = await uploadSubmissionFilesWithDuplicate(
          currentSubmission.id,
          item.file,
          item.duplicateInfo!.originalFileId,
        );
        uploadedFileIds.push(...resp.items.map((f) => f.id));
        showToast(`文件已上传，共享申请已发送给 ${item.duplicateInfo!.uploaderName}`);
      }

      await refreshCurrentWorkspace();
      const parseResults = await Promise.allSettled(uploadedFileIds.map((id) => parseFile(id)));
      await refreshCurrentWorkspace();
      const failedCount = parseResults.filter((result) => result.status === 'rejected').length;
      if (failedCount > 0) {
        setErrorMessage(`文件已上传，但有 ${failedCount} 个文件解析失败，可在列表中点击"重新解析"。`);
      }
    } catch (error) {
      setErrorMessage(resolveError(error));
    } finally {
      setIsUploading(false);
      setFileQueue([]);
    }
  }

  async function processQueue(queue: FileQueueItem[]) {
    if (!currentSubmission) return;
    const nextQueue = queue.map((i) => ({ ...i }));
    for (let idx = 0; idx < nextQueue.length; idx++) {
      const item = nextQueue[idx];
      if (item.status !== 'pending') continue;
      item.status = 'checking';
      setHashCheckStatus('checking');
      setFileQueue([...nextQueue]);
      try {
        const hash = await computeFileSHA256(item.file);
        const result = await checkDuplicate(hash, currentSubmission.id);
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
        setHashCheckStatus('error');
        item.status = 'clean';
        setFileQueue([...nextQueue]);
      }
    }
    await finishQueueAndUpload(nextQueue);
  }

  async function handleFilesSelected(selectedFiles: globalThis.FileList | null) {
    if (!selectedFiles?.length || !currentSubmission) {
      return;
    }
    setErrorMessage(null);
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
    if (!currentSubmission) {
      return;
    }

    setIsGithubImporting(true);
    setErrorMessage(null);
    try {
      await importGitHubSubmissionFile(currentSubmission.id, url);
      await refreshCurrentWorkspace();
    } catch (error) {
      setErrorMessage(resolveError(error));
    } finally {
      setIsGithubImporting(false);
    }
  }

  async function handleRetryParse(fileId: string) {
    setWorkingFileId(fileId);
    setErrorMessage(null);
    try {
      await parseFile(fileId);
      await refreshCurrentWorkspace();
    } catch (error) {
      setErrorMessage(resolveError(error));
    } finally {
      setWorkingFileId(null);
    }
  }

  async function handleReplaceFile(fileId: string, nextFile: File) {
    setWorkingFileId(fileId);
    setErrorMessage(null);
    try {
      const updated = await replaceSubmissionFile(fileId, nextFile);
      await refreshCurrentWorkspace();
      try {
        await parseFile(updated.id);
      } catch (error) {
        await refreshCurrentWorkspace();
        setErrorMessage(`文件已替换，但重新解析失败：${resolveError(error)}`);
        return;
      }
      await refreshCurrentWorkspace();
    } catch (error) {
      setErrorMessage(resolveError(error));
    } finally {
      setWorkingFileId(null);
    }
  }

  async function handleDeleteFile(fileId: string) {
    setWorkingFileId(fileId);
    setErrorMessage(null);
    try {
      await deleteSubmissionFile(fileId);
      await refreshCurrentWorkspace();
    } catch (error) {
      setErrorMessage(resolveError(error));
    } finally {
      setWorkingFileId(null);
    }
  }

  return (
    <AppShell
      title="个人评估中心"
      description="维护个人材料并查看评估进展。"
      actions={
        <div className="flex flex-wrap items-center gap-3">
          <span className="status-pill" style={{ background: 'var(--color-primary-light)', color: 'var(--color-primary)' }}>当前角色：{getRoleLabel(user?.role)}</span>
          <Link className="chip-button" to="/settings">账号设置</Link>
        </div>
      }
    >
      {errorMessage ? <p className="surface px-5 py-4 text-sm" style={{ color: "var(--color-danger)" }}>{errorMessage}</p> : null}
      {isLoading ? <p className="px-2 text-sm text-steel">正在加载个人评估中心...</p> : null}

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
            bottom: 24,
            right: 24,
            background: 'var(--color-surface)',
            color: 'var(--color-ink)',
            padding: '12px 16px',
            borderRadius: 8,
            boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
            fontSize: 13.5,
            zIndex: 1000,
          }}
        >
          {toastMessage}
        </div>
      ) : null}

      {!isLoading && !employee ? (
        <section className="surface px-6 py-8">
          <h2 className="text-2xl font-semibold text-ink">暂未匹配到你的员工档案</h2>
          <p className="mt-3 text-sm leading-7 text-steel">当前账号尚未绑定员工档案，请联系管理员或 HRBP。</p>
        </section>
      ) : null}

      {employee ? (
        <>
          {currentSubmission && currentSubmission.status !== 'collecting' ? (
            <section className="surface px-6 py-5 animate-fade-up">
              <EvaluationStepBar
                currentStep={resolveCurrentStep(
                  salaryRecommendation?.status ?? null,
                  approvalRecords,
                )}
              />
            </section>
          ) : currentSubmission && currentSubmission.status === 'collecting' && !evaluation ? (
            <section className="surface px-6 py-8 text-center animate-fade-up">
              <h3 className="text-lg font-semibold text-ink">暂无评估记录</h3>
              <p className="mt-2 text-sm text-steel">您当前没有进行中的评估。请上传材料开始评估流程。</p>
            </section>
          ) : null}

          <section className="metric-strip animate-fade-up">
            {[
              ['所属部门', employee.department, '当前所属组织单元。'],
              ['岗位族', employee.job_family, '当前岗位序列。'],
              ['当前周期状态', currentSubmission?.status ?? '未开始', '当前选中周期的提交状态。'],
              ['已提取证据', `${evidenceItems.length} 条`, '系统已整理出的证据摘要数量。'],
            ].map(([label, value, note]) => (
              <article className="metric-tile" key={label}>
                <p className="metric-label">{label}</p>
                <p className="metric-value text-[26px]">{value}</p>
                <p className="metric-note">{note}</p>
              </article>
            ))}
          </section>

          {evaluation && (evaluation.status === 'confirmed' || salaryRecommendation?.status === 'approved') && evaluation.dimension_scores.length > 0 ? (
            <section className="surface px-6 py-6 animate-fade-up">
              <p className="eyebrow">评估结果</p>
              <h2 className="mt-2 section-title text-ink">AI 能力五维评估</h2>
              <div className="mt-4 grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
                <DimensionRadarChart
                  scores={evaluation.dimension_scores.map((d) => ({
                    dimension_code: d.dimension_code,
                    raw_score: d.raw_score,
                    weight: d.weight,
                  }))}
                />
                <div className="surface-subtle px-5 py-5 flex flex-col items-center justify-center gap-3">
                  <p className="text-sm text-steel">综合得分</p>
                  <p className="text-[26px] font-semibold text-ink">{Math.round(evaluation.overall_score)}</p>
                  <p className="text-sm text-steel">AI 能力等级</p>
                  <p className="text-lg font-semibold" style={{ color: 'var(--color-primary)' }}>{evaluation.ai_level}</p>
                </div>
              </div>
              <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                {evaluation.dimension_scores.map((d) => (
                  <DimensionCard
                    key={d.dimension_code}
                    dimensionCode={d.dimension_code}
                    rawScore={d.raw_score}
                    weight={d.weight}
                    rationale={d.rationale || d.ai_rationale}
                  />
                ))}
              </div>
            </section>
          ) : evaluation === null && currentSubmission && currentSubmission.status !== 'collecting' ? (
            <section className="surface px-6 py-8 text-center animate-fade-up">
              <h3 className="text-lg font-semibold text-ink">评估审核中</h3>
              <p className="mt-2 text-sm text-steel">您的评估正在审核中，请耐心等待。评估完成后结果将在此处展示。</p>
            </section>
          ) : null}

          {salaryRecommendation && salaryRecommendation.status === 'approved' ? (
            <SalaryResultCard adjustmentRatio={salaryRecommendation.final_adjustment_ratio} />
          ) : salaryRecommendation && salaryRecommendation.status !== 'approved' ? (
            <section className="surface px-6 py-8 text-center animate-fade-up">
              <h3 className="text-lg font-semibold text-ink">调薪建议审核中</h3>
              <p className="mt-2 text-sm text-steel">调薪建议正在审批流程中。审批通过后，您将在此处看到最终调整幅度。</p>
            </section>
          ) : null}

          <section className="grid gap-5 lg:grid-cols-[1.08fr_0.92fr]">
            <article className="surface px-6 py-6 lg:px-7">
              <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'flex-end', justifyContent: 'space-between', gap: 16, borderBottom: '1px solid var(--color-border)', paddingBottom: 12, marginBottom: 16 }}>
                <div>
                  <p className="eyebrow">当前周期</p>
                  <h2 className="mt-2 text-[24px] font-semibold tracking-[-0.03em] text-ink">材料与提交概览</h2>
                </div>
                <label className="min-w-[240px]">
                  <span className="text-sm text-steel">切换评估周期</span>
                  <select className="toolbar-input mt-3 w-full" onChange={(event) => setSelectedCycleId(event.target.value)} value={selectedCycleId}>
                    {cycles.map((cycle) => (
                      <option key={cycle.id} value={cycle.id}>{cycle.name}</option>
                    ))}
                  </select>
                </label>
              </div>

              <div className="mt-5 grid gap-3 md:grid-cols-2">
                <div className="surface-subtle px-4 py-4">
                  <p className="text-sm text-steel">当前周期</p>
                  <p className="mt-2 text-lg font-semibold text-ink">{currentCycle?.name ?? '未选择'}</p>
                </div>
                <div className="surface-subtle px-4 py-4">
                  <p className="text-sm text-steel">提交状态</p>
                  <div className="mt-2">
                    {currentSubmission ? <StatusIndicator status={currentSubmission.status} /> : <span className="text-sm text-steel">未生成</span>}
                  </div>
                </div>
                <div className="surface-subtle px-4 py-4">
                  <p className="text-sm text-steel">最近提交时间</p>
                  <p className="mt-2 text-lg font-semibold text-ink">{formatDate(currentSubmission?.submitted_at ?? null)}</p>
                </div>
                <div className="surface-subtle px-4 py-4">
                  <p className="text-sm text-steel">当前提交 ID</p>
                  <p className="mt-2 break-all text-sm font-medium text-ink">{currentSubmission?.id ?? '尚未创建'}</p>
                </div>
              </div>

              <div className="mt-5 space-y-4">
                <div className="surface-subtle px-5 py-5">
                  <p className="text-sm text-steel">员工自述</p>
                  <p className="mt-2 text-sm leading-6 text-ink">{currentSubmission?.self_summary ?? '当前还没有填写员工自述。'}</p>
                </div>
                <div className="surface-subtle px-5 py-5">
                  <p className="text-sm text-steel">主管评语</p>
                  <p className="mt-2 text-sm leading-6 text-ink">{currentSubmission?.manager_summary ?? '当前还没有主管评语。'}</p>
                </div>
              </div>
            </article>

            <article className="surface px-6 py-6 lg:px-7">
              <div style={{ borderBottom: '1px solid var(--color-border)', paddingBottom: 12, marginBottom: 16 }}>
                <p className="eyebrow">我的历史提交</p>
                <h2 className="mt-2 text-[24px] font-semibold tracking-[-0.03em] text-ink">周期提交记录</h2>
              </div>
              <div className="mt-5 space-y-4">
                {submissions.length ? (
                  submissions.map((submission) => (
                    <div className="surface-subtle px-5 py-5" key={submission.id}>
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div>
                          <h3 className="text-base font-semibold text-ink">{cycleNameById[submission.cycle_id] ?? submission.cycle_id}</h3>
                          <p className="mt-1 text-sm text-steel">提交时间：{formatDate(submission.submitted_at)}</p>
                        </div>
                        <StatusIndicator status={submission.status} />
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="text-sm text-steel">当前还没有你的提交记录。</p>
                )}
              </div>
            </article>
          </section>

          <section className="grid gap-5 xl:grid-cols-[1.02fr_0.98fr]">
            <div className="flex flex-col gap-5">
              <div className="surface px-6 py-6 lg:px-7">
                <FileUploadPanel
                  isGithubImporting={isGithubImporting}
                  isUploading={isUploading}
                  onFilesSelected={handleFilesSelected}
                  onGitHubImport={handleGitHubImport}
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

            <article className="surface px-6 py-6 lg:px-7">
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, borderBottom: '1px solid var(--color-border)', paddingBottom: 12, marginBottom: 16 }}>
                <div>
                  <p className="eyebrow">证据摘要</p>
                  <h2 className="mt-2 text-[24px] font-semibold tracking-[-0.03em] text-ink">AI 提取结果</h2>
                </div>
                <span className="text-sm text-steel">{evidenceItems.length} 条</span>
              </div>
              <div className="mt-5 grid gap-4">
                {evidenceItems.length ? (
                  evidenceItems.map((item) => <EvidenceCard evidence={item} key={item.id} />)
                ) : (
                  <p className="text-sm text-steel">当前还没有证据摘要。上传文件后，系统会自动解析并整理关键证据。</p>
                )}
              </div>
            </article>
          </section>
        </>
      ) : null}
    </AppShell>
  );
}
