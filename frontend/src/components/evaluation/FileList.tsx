import type { UploadedFileRecord } from '../../types/api';

const PARSE_STATUS_STYLES: Record<UploadedFileRecord['parse_status'], string> = {
  pending: 'bg-slate-100 text-slate-700',
  parsing: 'bg-amber-100 text-amber-700',
  parsed: 'bg-emerald-100 text-emerald-700',
  failed: 'bg-rose-100 text-rose-700',
};

interface FileListProps {
  files: UploadedFileRecord[];
  onDelete: (fileId: string) => void;
  onRetryParse: (fileId: string) => void;
}

export function FileList({ files, onDelete, onRetryParse }: FileListProps) {
  if (files.length === 0) {
    return (
      <section className="rounded-[28px] bg-white p-6 shadow-panel">
        <h3 className="text-xl font-semibold text-ink">File list</h3>
        <p className="mt-3 text-sm text-slate-500">No materials have been staged yet.</p>
      </section>
    );
  }

  return (
    <section className="rounded-[28px] bg-white p-6 shadow-panel">
      <div className="flex items-center justify-between gap-3">
        <h3 className="text-xl font-semibold text-ink">File list</h3>
        <span className="text-sm text-slate-500">{files.length} items</span>
      </div>
      <div className="mt-5 grid gap-4">
        {files.map((file) => (
          <article key={file.id} className="rounded-[24px] border border-slate-200 p-4">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <h4 className="font-semibold text-ink">{file.file_name}</h4>
                <p className="mt-1 text-sm text-slate-500">{file.file_type.toUpperCase()} {file.size_label ? `· ${file.size_label}` : ''}</p>
              </div>
              <span className={`rounded-full px-3 py-1 text-xs font-semibold ${PARSE_STATUS_STYLES[file.parse_status]}`}>
                {file.parse_status}
              </span>
            </div>
            <div className="mt-4 flex flex-wrap gap-3 text-sm">
              <button className="rounded-full border border-slate-200 px-4 py-2 font-medium text-slate-600" disabled type="button">
                Preview
              </button>
              <button className="rounded-full border border-ink/15 px-4 py-2 font-medium text-ink" onClick={() => onRetryParse(file.id)} type="button">
                Retry parse
              </button>
              <button className="rounded-full border border-rose-200 px-4 py-2 font-medium text-rose-600" onClick={() => onDelete(file.id)} type="button">
                Remove
              </button>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
