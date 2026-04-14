import axios from 'axios';
import { Link } from 'react-router-dom';
import { useEffect, useMemo, useState } from 'react';

import { ImportJobTable } from '../components/import/ImportJobTable';
import { ImportResultPanel } from '../components/import/ImportResultPanel';
import { AppShell } from '../components/layout/AppShell';
import { useTaskPolling } from '../hooks/useTaskPolling';
import { createImportJob, downloadImportTemplate, exportImportJob, fetchImportJobs } from '../services/importService';
import type { ImportJobRecord, ImportRowResult } from '../types/api';

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
  const [lastImportResult, setLastImportResult] = useState<ImportJobRecord | null>(null);
  const [importTaskId, setImportTaskId] = useState<string | null>(null);
  const [importProgress, setImportProgress] = useState<{ processed: number; total: number; errors: number } | null>(null);

  useTaskPolling(importTaskId, {
    onComplete: (result) => {
      setImportTaskId(null);
      setImportProgress(null);
      setLastImportResult(result as ImportJobRecord);
      setIsUploading(false);
      void loadJobs();
    },
    onError: (error) => {
      setImportTaskId(null);
      setImportProgress(null);
      setIsUploading(false);
      setErrorMessage(error);
    },
    onProgress: (progress) => {
      setImportProgress(progress);
    },
  });

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
    setLastImportResult(null);
    setImportProgress(null);
    try {
      const triggerResponse = await createImportJob(selectedType, selectedFile);
      setImportTaskId(triggerResponse.task_id);
      setSelectedFile(null);
      const input = window.document.getElementById('import-file-input') as HTMLInputElement | null;
      if (input) {
        input.value = '';
      }
    } catch (error) {
      setErrorMessage(resolveError(error));
      setIsUploading(false);
    }
  }

  async function handleDownloadTemplate(importType: string, format: 'xlsx' | 'csv' = 'xlsx') {
    try {
      const blob = await downloadImportTemplate(importType, format);
      const ext = format === 'xlsx' ? 'xlsx' : 'csv';
      saveBlob(blob, `${importType}_template.${ext}`);
    } catch (error) {
      setErrorMessage(resolveError(error));
    }
  }

  async function handleExportXlsx(jobId: string) {
    try {
      const blob = await exportImportJob(jobId, 'xlsx');
      saveBlob(blob, `import_${jobId}_report.xlsx`);
    } catch (error) {
      setErrorMessage(resolveError(error));
    }
  }

  return (
    <AppShell
      title="批量导入中心"
      description="下载模板、导入文件、查看结果。"
      actions={
        <>
          <Link className="chip-button" to="/workspace">返回工作台</Link>
          <Link className="action-primary" to="/dashboard">打开组织看板</Link>
        </>
      }
    >
      {errorMessage ? <p className="surface px-5 py-4 text-sm" style={{ color: "var(--color-danger)" }}>{errorMessage}</p> : null}

      <section className="metric-strip animate-fade-up">
        <article className="metric-tile" key="员工模板">
          <p className="metric-label">员工模板</p>
          <p className="metric-value">Excel / CSV</p>
          <p className="metric-note">下载员工导入模板并按列填充数据。</p>
          <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
            <button className="chip-button" onClick={() => void handleDownloadTemplate('employees', 'xlsx')} type="button">下载 Excel</button>
            <button className="chip-button" onClick={() => void handleDownloadTemplate('employees', 'csv')} type="button">下载 CSV</button>
          </div>
        </article>
        <article className="metric-tile" key="认证模板">
          <p className="metric-label">认证模板</p>
          <p className="metric-value">Excel / CSV</p>
          <p className="metric-note">下载认证导入模板并导入历史认证记录。</p>
          <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
            <button className="chip-button" onClick={() => void handleDownloadTemplate('certifications', 'xlsx')} type="button">下载 Excel</button>
            <button className="chip-button" onClick={() => void handleDownloadTemplate('certifications', 'csv')} type="button">下载 CSV</button>
          </div>
        </article>
        <article className="metric-tile" key="处理中任务">
          <p className="metric-label">处理中任务</p>
          <p className="metric-value">{stats.processing}</p>
          <p className="metric-note">正在排队或处理中，需等待结果回写。</p>
        </article>
        <article className="metric-tile" key="任务总数">
          <p className="metric-label">任务总数</p>
          <p className="metric-value">{jobs.length}</p>
          <p className="metric-note">已完成 {stats.completed}，失败 {stats.failed}。</p>
        </article>
      </section>

      <section className="surface" style={{ padding: '16px 20px' }}>
        <div className="section-head">
          <div>
            <p className="eyebrow">上传任务</p>
            <h2 className="section-title">创建导入任务</h2>
            <p className="mt-2 text-sm leading-6 text-steel">在这里选择类型、文件和模板。</p>
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
          <div className="flex flex-col items-end justify-end">
            <button className="action-primary w-full lg:w-auto" disabled={isUploading} onClick={() => void handleUpload()} type="button">
              {isUploading ? '导入中...' : '开始导入'}
            </button>
            {isUploading && (
              <div className="text-sm text-gray-500 animate-pulse mt-2">
                {importProgress
                  ? `导入中 ${importProgress.processed}/${importProgress.total} 行${importProgress.errors > 0 ? `（${importProgress.errors} 行失败）` : ''}`
                  : '导入中...'}
              </div>
            )}
          </div>
        </div>
      </section>

      {lastImportResult ? (
        <ImportResultPanel
          totalRows={lastImportResult.total_rows}
          successRows={lastImportResult.success_rows}
          failedRows={lastImportResult.failed_rows}
          rows={(lastImportResult.result_summary as { rows?: ImportRowResult[] })?.rows ?? []}
          onDownloadErrorReport={() => {
            void handleExportXlsx(lastImportResult.id);
          }}
        />
      ) : null}

      {isLoading ? <p className="px-2 text-sm text-steel">正在加载导入任务...</p> : null}
      <ImportJobTable
        onExport={(jobId) => {
          void handleExportXlsx(jobId);
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
