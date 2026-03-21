import axios from 'axios';
import { Link } from 'react-router-dom';
import { useEffect, useMemo, useState } from 'react';

import { AppShell } from '../components/layout/AppShell';
import { StatusIndicator } from '../components/evaluation/StatusIndicator';
import { useAuth } from '../hooks/useAuth';
import { fetchCycles } from '../services/cycleService';
import { fetchEmployees } from '../services/employeeService';
import { fetchSubmissionEvidence, fetchSubmissionFiles } from '../services/fileService';
import { fetchEmployeeSubmissions } from '../services/submissionService';
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

export function MyReviewPage() {
  const { user } = useAuth();
  const [employee, setEmployee] = useState<EmployeeRecord | null>(null);
  const [cycles, setCycles] = useState<CycleRecord[]>([]);
  const [submissions, setSubmissions] = useState<SubmissionRecord[]>([]);
  const [files, setFiles] = useState<UploadedFileRecord[]>([]);
  const [evidenceItems, setEvidenceItems] = useState<EvidenceRecord[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadPortal() {
      setIsLoading(true);
      setErrorMessage(null);
      try {
        const [employeeResponse, cycleResponse] = await Promise.all([
          fetchEmployees({ page: 1, page_size: 100 }),
          fetchCycles(),
        ]);
        if (cancelled) return;

        const matchedEmployee = findEmployeeForUser(user, employeeResponse.items);
        setCycles(cycleResponse.items);
        setEmployee(matchedEmployee);

        if (!matchedEmployee) {
          setSubmissions([]);
          setFiles([]);
          setEvidenceItems([]);
          return;
        }

        const submissionResponse = await fetchEmployeeSubmissions(matchedEmployee.id);
        if (cancelled) return;
        setSubmissions(submissionResponse.items);

        const latestSubmission = submissionResponse.items[0];
        if (!latestSubmission) {
          setFiles([]);
          setEvidenceItems([]);
          return;
        }

        const [fileResponse, evidenceResponse] = await Promise.all([
          fetchSubmissionFiles(latestSubmission.id),
          fetchSubmissionEvidence(latestSubmission.id),
        ]);
        if (cancelled) return;
        setFiles(fileResponse.items);
        setEvidenceItems(evidenceResponse.items);
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

    void loadPortal();
    return () => {
      cancelled = true;
    };
  }, [user]);

  const latestSubmission = submissions[0] ?? null;
  const cycleNameById = useMemo(() => Object.fromEntries(cycles.map((cycle) => [cycle.id, cycle.name])), [cycles]);

  return (
    <AppShell
      title="个人评估中心"
      description="围绕个人评估周期查看提交状态、材料进展和 AI 提取出的证据摘要。"
      actions={<span className="rounded-full bg-[#edf3ff] px-4 py-2 text-sm text-[#2750b6]">当前角色：{getRoleLabel(user?.role)}</span>}
    >
      {errorMessage ? <p className="surface px-5 py-4 text-sm text-red-600">{errorMessage}</p> : null}
      {isLoading ? <p className="px-2 text-sm text-steel">正在加载个人评估中心...</p> : null}

      {!isLoading && !employee ? (
        <section className="surface px-6 py-8">
          <h2 className="text-2xl font-semibold text-ink">暂未匹配到你的员工档案</h2>
          <p className="mt-3 text-sm leading-7 text-steel">当前账号已经是员工角色，但系统里还没有与你绑定的员工档案。请联系系统管理员或 HRBP 完成账号与员工档案绑定。</p>
        </section>
      ) : null}

      {employee ? (
        <>
          <section className="metric-strip animate-fade-up">
            {[
              ['所属部门', employee.department, '当前所属组织单元。'],
              ['岗位族', employee.job_family, '当前岗位序列。'],
              ['最近提交状态', latestSubmission?.status ?? '未提交', '当前周期最近一次提交状态。'],
              ['已提取证据', `${evidenceItems.length} 条`, '系统已整理出的证据摘要数量。'],
            ].map(([label, value, note]) => (
              <article className="metric-tile" key={label}>
                <p className="metric-label">{label}</p>
                <p className="metric-value text-[26px]">{value}</p>
                <p className="metric-note">{note}</p>
              </article>
            ))}
          </section>

          <section className="grid gap-5 lg:grid-cols-[1.1fr_0.9fr]">
            <article className="surface px-6 py-6 lg:px-7">
              <div className="flex items-center justify-between gap-3 border-b border-[#e6eef9] pb-4">
                <div>
                  <p className="eyebrow">我的周期</p>
                  <h2 className="mt-2 text-[24px] font-semibold tracking-[-0.03em] text-ink">提交记录</h2>
                </div>
                {latestSubmission ? <StatusIndicator status={latestSubmission.status} /> : null}
              </div>
              {submissions.length ? (
                <div className="mt-5 space-y-4">
                  {submissions.map((submission) => (
                    <div className="surface-subtle px-5 py-5" key={submission.id}>
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div>
                          <h3 className="text-base font-semibold text-ink">{cycleNameById[submission.cycle_id] ?? submission.cycle_id}</h3>
                          <p className="mt-1 text-sm text-steel">提交时间：{formatDate(submission.submitted_at)}</p>
                        </div>
                        <StatusIndicator status={submission.status} />
                      </div>
                      <p className="mt-4 text-sm leading-6 text-steel">员工自述：{submission.self_summary ?? '暂未填写'}</p>
                      <p className="mt-2 text-sm leading-6 text-steel">主管评语：{submission.manager_summary ?? '暂未填写'}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="mt-4 text-sm text-steel">当前还没有你的提交记录。</p>
              )}
            </article>

            <div className="flex flex-col gap-5">
              <article className="surface px-6 py-6 lg:px-7">
                <div className="border-b border-[#e6eef9] pb-4">
                  <p className="eyebrow">我的材料</p>
                  <h2 className="mt-2 text-[24px] font-semibold tracking-[-0.03em] text-ink">上传文件</h2>
                </div>
                <div className="mt-5 space-y-3">
                  {files.length ? (
                    files.map((file) => (
                      <div className="surface-subtle px-4 py-4" key={file.id}>
                        <div className="flex items-center justify-between gap-3">
                          <p className="font-medium text-ink">{file.file_name}</p>
                          <StatusIndicator status={file.parse_status} />
                        </div>
                      </div>
                    ))
                  ) : (
                    <p className="text-sm text-steel">当前没有上传材料。</p>
                  )}
                </div>
              </article>

              <article className="surface px-6 py-6 lg:px-7">
                <div className="border-b border-[#e6eef9] pb-4">
                  <p className="eyebrow">证据摘要</p>
                  <h2 className="mt-2 text-[24px] font-semibold tracking-[-0.03em] text-ink">AI 提取结果</h2>
                </div>
                <div className="mt-5 space-y-3">
                  {evidenceItems.length ? (
                    evidenceItems.map((item) => (
                      <div className="surface-subtle px-4 py-4" key={item.id}>
                        <p className="font-medium text-ink">{item.title}</p>
                        <p className="mt-2 text-sm leading-6 text-steel">{item.content}</p>
                      </div>
                    ))
                  ) : (
                    <p className="text-sm text-steel">当前还没有证据摘要。</p>
                  )}
                </div>
              </article>
            </div>
          </section>
        </>
      ) : null}
    </AppShell>
  );
}



