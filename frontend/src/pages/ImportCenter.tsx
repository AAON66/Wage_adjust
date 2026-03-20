import axios from 'axios';
import { Link } from 'react-router-dom';
import { useEffect, useMemo, useState } from 'react';

import { ImportJobTable } from '../components/import/ImportJobTable';
import { createImportJob, downloadImportTemplate, exportImportJob, fetchImportJobs } from '../services/importService';
import type { ImportJobRecord } from '../types/api';

const IMPORT_TYPES = [
  { value: 'employees', label: 'Employees' },
  { value: 'certifications', label: 'Certifications' },
];

function resolveError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    return (error.response?.data as { detail?: string; message?: string } | undefined)?.detail ??
      (error.response?.data as { detail?: string; message?: string } | undefined)?.message ??
      'Failed to complete import action.';
  }
  return 'Failed to complete import action.';
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
      setErrorMessage('Please choose a CSV file before uploading.');
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
    <main className="min-h-screen bg-sand px-6 py-10 text-ink">
      <div className="mx-auto flex max-w-6xl flex-col gap-6">
        <header className="flex flex-wrap items-start justify-between gap-4 rounded-[32px] bg-white p-6 shadow-panel">
          <div>
            <p className="text-sm uppercase tracking-[0.24em] text-ember">Import Center</p>
            <h1 className="mt-2 text-4xl font-bold">Batch import workspace</h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-500">
              This page now runs live import jobs, downloads CSV templates, and exports row-level result reports from the backend import APIs.
            </p>
          </div>
          <div className="flex gap-3">
            <Link className="rounded-full border border-ink/15 px-5 py-3 text-sm font-semibold text-ink" to="/workspace">
              Back to workspace
            </Link>
            <Link className="rounded-full bg-ink px-5 py-3 text-sm font-semibold text-white" to="/dashboard">
              Open dashboard
            </Link>
          </div>
        </header>

        {errorMessage ? <p className="rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-600">{errorMessage}</p> : null}

        <section className="grid gap-4 md:grid-cols-3">
          <article className="rounded-[28px] bg-white p-5 shadow-panel">
            <p className="text-sm text-slate-500">Employee template</p>
            <p className="mt-3 text-3xl font-bold text-ink">csv</p>
            <button className="mt-4 rounded-full border border-ink/15 px-4 py-2 text-sm font-semibold text-ink" onClick={() => handleDownloadTemplate('employees')} type="button">
              Download
            </button>
          </article>
          <article className="rounded-[28px] bg-white p-5 shadow-panel">
            <p className="text-sm text-slate-500">Certification template</p>
            <p className="mt-3 text-3xl font-bold text-ink">csv</p>
            <button className="mt-4 rounded-full border border-ink/15 px-4 py-2 text-sm font-semibold text-ink" onClick={() => handleDownloadTemplate('certifications')} type="button">
              Download
            </button>
          </article>
          <article className="rounded-[28px] bg-white p-5 shadow-panel">
            <p className="text-sm text-slate-500">Current jobs</p>
            <p className="mt-3 text-3xl font-bold text-ink">{jobs.length}</p>
            <p className="mt-2 text-sm text-slate-500">Completed {stats.completed} · Processing {stats.processing} · Failed {stats.failed}</p>
          </article>
        </section>

        <section className="rounded-[28px] bg-white p-6 shadow-panel">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-sm uppercase tracking-[0.24em] text-ember">Upload</p>
              <h3 className="mt-2 text-2xl font-bold text-ink">Create import job</h3>
            </div>
            <span className="text-sm text-slate-500">CSV is the stable format in this environment</span>
          </div>
          <div className="mt-6 grid gap-4 md:grid-cols-[220px_1fr_auto]">
            <label className="rounded-[20px] border border-slate-200 p-4">
              <span className="text-sm text-slate-500">Import type</span>
              <select className="mt-2 w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm text-ink" onChange={(event) => setSelectedType(event.target.value)} value={selectedType}>
                {IMPORT_TYPES.map((item) => (
                  <option key={item.value} value={item.value}>{item.label}</option>
                ))}
              </select>
            </label>
            <label className="rounded-[20px] border border-dashed border-slate-300 p-4">
              <span className="text-sm text-slate-500">CSV file</span>
              <input accept=".csv,.xlsx,.xls" className="mt-2 block w-full text-sm text-slate-600" id="import-file-input" onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)} type="file" />
              <p className="mt-2 text-xs text-slate-500">Excel uploads currently return a clear error because `openpyxl` is not installed.</p>
            </label>
            <button className="rounded-full bg-ink px-5 py-3 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-40" disabled={isUploading} onClick={() => void handleUpload()} type="button">
              {isUploading ? 'Uploading...' : 'Start import'}
            </button>
          </div>
        </section>

        {isLoading ? <p className="text-sm text-slate-500">Loading import jobs...</p> : null}
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
      </div>
    </main>
  );
}
