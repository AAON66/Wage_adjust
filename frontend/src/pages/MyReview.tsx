import axios from 'axios';
import { Link } from 'react-router-dom';
import { useEffect, useMemo, useState } from 'react';

import { EvidenceCard } from '../components/evaluation/EvidenceCard';
import { FileList } from '../components/evaluation/FileList';
import { FileUploadPanel } from '../components/evaluation/FileUploadPanel';
import { StatusIndicator } from '../components/evaluation/StatusIndicator';
import { AppShell } from '../components/layout/AppShell';
import { useAuth } from '../hooks/useAuth';
import { fetchCycles } from '../services/cycleService';
import {
  deleteSubmissionFile,
  fetchSubmissionEvidence,
  fetchSubmissionFiles,
  importGitHubSubmissionFile,
  parseFile,
  replaceSubmissionFile,
  uploadSubmissionFiles,
} from '../services/fileService';
import { fetchEmployees } from '../services/employeeService';
import { ensureSubmission, fetchEmployeeSubmissions } from '../services/submissionService';
import type { CycleRecord, EmployeeRecord, EvidenceRecord, SubmissionRecord, UploadedFileRecord } from '../types/api';
import { findEmployeeForUser } from '../utils/employeeIdentity';
import { getRoleLabel } from '../utils/roleAccess';

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

export function MyReviewPage() {
  const { user } = useAuth();
  const [employee, setEmployee] = useState<EmployeeRecord | null>(null);
  const [cycles, setCycles] = useState<CycleRecord[]>([]);
  const [selectedCycleId, setSelectedCycleId] = useState('');
  const [submissions, setSubmissions] = useState<SubmissionRecord[]>([]);
  const [currentSubmission, setCurrentSubmission] = useState<SubmissionRecord | null>(null);
  const [files, setFiles] = useState<UploadedFileRecord[]>([]);
  const [evidenceItems, setEvidenceItems] = useState<EvidenceRecord[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [isGithubImporting, setIsGithubImporting] = useState(false);
  const [workingFileId, setWorkingFileId] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

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

  async function handleFilesSelected(selectedFiles: globalThis.FileList | null) {
    if (!selectedFiles?.length || !currentSubmission) {
      return;
    }

    setIsUploading(true);
    setErrorMessage(null);
    try {
      const uploadResponse = await uploadSubmissionFiles(currentSubmission.id, Array.from(selectedFiles));
      await Promise.all(uploadResponse.items.map((file) => parseFile(file.id)));
      await refreshCurrentWorkspace();
    } catch (error) {
      setErrorMessage(resolveError(error));
    } finally {
      setIsUploading(false);
    }
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
      await parseFile(updated.id);
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

      {!isLoading && !employee ? (
        <section className="surface px-6 py-8">
          <h2 className="text-2xl font-semibold text-ink">暂未匹配到你的员工档案</h2>
          <p className="mt-3 text-sm leading-7 text-steel">当前账号尚未绑定员工档案，请联系管理员或 HRBP。</p>
        </section>
      ) : null}

      {employee ? (
        <>
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
