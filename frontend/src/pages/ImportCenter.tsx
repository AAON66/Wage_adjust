import axios from 'axios';
import { Link } from 'react-router-dom';
import { useEffect, useMemo, useState } from 'react';

import { ImportJobTable } from '../components/import/ImportJobTable';
import { AppShell } from '../components/layout/AppShell';
import { createImportJob, downloadImportTemplate, exportImportJob, fetchImportJobs } from '../services/importService';
import type { ImportJobRecord } from '../types/api';

const IMPORT_TYPES = [
  { value: 'employees', label: '员工' },
  { value: 'certifications', label: '认证' },
];

function resolveError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    return (error.response?.data as { detail?: string; message?: string } | undefined)?.detail ??
      (error.response?.data as { detail?: string; message?: string } | undefined)?.message ??
      '导入操作失败。';
  }
  return '导入操作失败。';
}

function saveBlob(blob: Blob, fileName: string): void {
  const url = window.URL.createObjectURL(blob);
  const link = window.document.createElement('a');
  link.href = url;
  link.download = fileName;
  window.document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

export function ImportCenterPage() {
  const [jobs, setJobs] = useState<ImportJobRecord[]>([]);
  const [selectedType, setSelectedType] = useState('employees');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function loadJobs() {
    const response = await fetchImportJobs();
    setJobs(response.items);
  }

  useEffect(() => {
    let cancelled = false;
    async function bootstrap() {
      setIsLoading(true);
      setErrorMessage(null);
      try {
        const response = await fetchImportJobs();
        if (!cancelled) {
          setJobs(response.items);
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
    void bootstrap();
    return () => {
      cancelled = true;
    };
  }, []);

  const stats = useMemo(() => ({
    completed: jobs.filter((job) => job.status === 'completed').length,
    failed: jobs.filter((job) => job.status === 'failed').length,
    processing: jobs.filter((job) => job.status === 'processing' || job.status === 'queued' || job.status === 'pending').length,
  }), [jobs]);

  async function handleUpload() {
    if (!selectedFile) {
      setErrorMessage('请先选择需要上传的文件。');
      return;
    }
    setIsUploading(true);
    setErrorMessage(null);
    try {
      await createImportJob(selectedType, selectedFile);
      setSelectedFile(null);
      const input = window.document.getElementById('import-file-input') as HTMLInputElement | null;
      if (input) {
        input.value = '';
      }
      await loadJobs();
    } catch (error) {
      setErrorMessage(resolveError(error));
    } finally {
      setIsUploading(false);
    }
  }

  async function handleDownloadTemplate(importType: string) {
    try {
      const blob = await downloadImportTemplate(importType);
      saveBlob(blob, `${importType}_template.csv`);
    } catch (error) {
      setErrorMessage(resolveError(error));
    }
  }

  async function handleExport(jobId: string) {
    try {
      const blob = await exportImportJob(jobId);
      saveBlob(blob, `import_${jobId}_report.csv`);
    } catch (error) {
      setErrorMessage(resolveError(error));
    }
  }

  return (
    <AppShell
      title="批量导入中心"
      description="下载模板、导入文件、导出结果。"
      actions={
        <>
          <Link className="chip-button" to="/workspace">返回工作台</Link>
          <Link className="action-primary" to="/dashboard">打开组织看板</Link>
        </>
      }
    >
      {errorMessage ? <p className="surface px-5 py-4 text-sm" style={{ color: "var(--color-danger)" }}>{errorMessage}</p> : null}

      <section className="metric-strip animate-fade-up">
        {[
          ['员工模板', 'CSV', '下载员工导入模板并按列填充数据。'],
          ['认证模板', 'CSV', '下载认证导入模板并导入历史认证记录。'],
          ['处理中任务', String(stats.processing), '正在排队或处理中，需等待结果回写。'],
          ['任务总数', String(jobs.length), `已完成 ${stats.completed}，失败 ${stats.failed}。`],
        ].map(([label, value, note]) => (
          <article className="metric-tile" key={label}>
            <p className="metric-label">{label}</p>
            <p className="metric-value">{value}</p>
            <p className="metric-note">{note}</p>
          </article>
        ))}
      </section>

      <section className="surface" style={{ padding: '16px 20px' }}>
        <div className="section-head">
          <div>
            <p className="eyebrow">上传任务</p>
            <h2 className="section-title">创建导入任务</h2>
            <p className="mt-2 text-sm leading-6 text-steel">在这里选择类型、文件和模板。</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button className="chip-button" onClick={() => void handleDownloadTemplate('employees')} type="button">下载员工模板</button>
            <button className="chip-button" onClick={() => void handleDownloadTemplate('certifications')} type="button">下载认证模板</button>
          </div>
        </div>

        <div className="mt-5 grid gap-4 lg:grid-cols-[240px_1fr_auto]">
          <label className="surface-subtle px-4 py-4">
            <span className="text-sm text-steel">导入类型</span>
            <select className="toolbar-input mt-3 w-full" onChange={(event) => setSelectedType(event.target.value)} value={selectedType}>
              {IMPORT_TYPES.map((item) => (
                <option key={item.value} value={item.value}>{item.label}</option>
              ))}
            </select>
          </label>
          <label className="surface-subtle px-4 py-4">
            <span className="text-sm text-steel">上传文件</span>
            <input accept=".csv,.xlsx,.xls" className="toolbar-input mt-3 w-full" id="import-file-input" onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)} style={{ height: 'auto', padding: '6px 10px' }} type="file" />
            <p className="mt-3 text-xs leading-5 text-steel">请根据模板要求准备文件后再导入，系统会按任务结果返回成功与失败明细。</p>
          </label>
          <div className="flex items-end">
            <button className="action-primary w-full lg:w-auto" disabled={isUploading} onClick={() => void handleUpload()} type="button">
              {isUploading ? '上传中...' : '开始导入'}
            </button>
          </div>
        </div>
      </section>

      {isLoading ? <p className="px-2 text-sm text-steel">正在加载导入任务...</p> : null}
      <ImportJobTable
        onExport={(jobId) => {
          void handleExport(jobId);
        }}
        rows={jobs.map((job) => ({
          id: job.id,
          fileName: job.file_name,
          importType: job.import_type,
          status: job.status,
          totalRows: job.total_rows,
          successRows: job.success_rows,
          failedRows: job.failed_rows,
        }))}
      />
    </AppShell>
  );
}

