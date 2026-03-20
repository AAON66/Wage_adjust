interface ImportJobRow {
  id: string;
  fileName: string;
  importType: string;
  status: 'pending' | 'queued' | 'processing' | 'completed' | 'failed';
  totalRows: number;
  successRows: number;
  failedRows: number;
}

interface ImportJobTableProps {
  rows: ImportJobRow[];
  onExport?: (jobId: string) => void;
}

const STATUS_STYLES: Record<ImportJobRow['status'], string> = {
  pending: 'bg-slate-100 text-slate-700',
  queued: 'bg-slate-100 text-slate-700',
  processing: 'bg-amber-100 text-amber-700',
  completed: 'bg-emerald-100 text-emerald-700',
  failed: 'bg-rose-100 text-rose-700',
};

export function ImportJobTable({ rows, onExport }: ImportJobTableProps) {
  return (
    <section className="rounded-[28px] bg-white p-6 shadow-panel">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-sm uppercase tracking-[0.24em] text-ember">Import Jobs</p>
          <h3 className="mt-2 text-2xl font-bold text-ink">Batch import runs</h3>
        </div>
        <span className="text-sm text-slate-500">{rows.length} jobs</span>
      </div>
      <div className="mt-5 overflow-x-auto">
        <table className="min-w-full border-separate border-spacing-y-3 text-sm">
          <thead>
            <tr className="text-left text-slate-500">
              <th className="px-4">File</th>
              <th className="px-4">Type</th>
              <th className="px-4">Status</th>
              <th className="px-4">Rows</th>
              <th className="px-4">Success</th>
              <th className="px-4">Failed</th>
              <th className="px-4">Export</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id} className="bg-slate-50 text-slate-700">
                <td className="rounded-l-[20px] px-4 py-4 font-semibold text-ink">{row.fileName}</td>
                <td className="px-4 py-4">{row.importType}</td>
                <td className="px-4 py-4">
                  <span className={`rounded-full px-3 py-1 text-xs font-semibold ${STATUS_STYLES[row.status]}`}>{row.status}</span>
                </td>
                <td className="px-4 py-4">{row.totalRows}</td>
                <td className="px-4 py-4">{row.successRows}</td>
                <td className="px-4 py-4">{row.failedRows}</td>
                <td className="rounded-r-[20px] px-4 py-4">
                  <button
                    className="rounded-full border border-ink/15 px-4 py-2 text-xs font-semibold text-ink disabled:cursor-not-allowed disabled:opacity-40"
                    disabled={!onExport}
                    onClick={() => onExport?.(row.id)}
                    type="button"
                  >
                    Export report
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
