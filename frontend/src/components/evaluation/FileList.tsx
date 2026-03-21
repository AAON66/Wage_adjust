import type { UploadedFileRecord } from '../../types/api';

const PARSE_STATUS_STYLES: Record<UploadedFileRecord['parse_status'], string> = {
  pending: 'bg-slate-100 text-slate-700',
  parsing: 'bg-amber-100 text-amber-700',
  parsed: 'bg-emerald-100 text-emerald-700',
  failed: 'bg-rose-100 text-rose-700',
};

const PARSE_STATUS_LABELS: Record<UploadedFileRecord['parse_status'], string> = {
  pending: '待解析',
  parsing: '解析中',
  parsed: '已解析',
  failed: '解析失败',
};

interface FileListProps {
  files: UploadedFileRecord[];
  onDelete: (fileId: string) => void;
  onRetryParse: (fileId: string) => void;
}

export function FileList({ files, onDelete, onRetryParse }: FileListProps) {
  if (files.length === 0) {
    return (
      <section className="surface-subtle px-6 py-6">
        <div className="section-head">
          <div>
            <p className="eyebrow">材料列表</p>
            <h3 className="section-title">上传文件</h3>
          </div>
        </div>
        <p className="mt-4 text-sm text-steel">当前还没有上传任何材料。</p>
      </section>
    );
  }

  return (
    <section className="surface-subtle px-6 py-6">
      <div className="section-head">
        <div>
          <p className="eyebrow">材料列表</p>
          <h3 className="section-title">上传文件</h3>
        </div>
        <span className="text-sm text-steel">{files.length} 个文件</span>
      </div>
      <div className="mt-5 grid gap-4">
        {files.map((file) => (
          <article key={file.id} className="list-row p-4">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <h4 className="font-semibold text-ink">{file.file_name}</h4>
                <p className="mt-1 text-sm text-steel">{file.file_type.toUpperCase()} {file.size_label ? `· ${file.size_label}` : ''}</p>
              </div>
              <span className={`status-pill ${PARSE_STATUS_STYLES[file.parse_status]}`}>
                {PARSE_STATUS_LABELS[file.parse_status]}
              </span>
            </div>
            <div className="mt-4 flex flex-wrap gap-3 text-sm">
              <button className="action-secondary px-4 py-2 text-xs" disabled type="button">
                预览
              </button>
              <button className="action-secondary px-4 py-2 text-xs" onClick={() => onRetryParse(file.id)} type="button">
                重新解析
              </button>
              <button className="action-danger px-4 py-2 text-xs" onClick={() => onDelete(file.id)} type="button">
                移除
              </button>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
