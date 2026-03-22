import type React from 'react';
import type { UploadedFileRecord } from '../../types/api';

const PARSE_STATUS_STYLES: Record<UploadedFileRecord['parse_status'], React.CSSProperties> = {
  pending:  { background: 'var(--color-bg-subtle)',  color: 'var(--color-steel)' },
  parsing:  { background: 'var(--color-warning-bg)', color: 'var(--color-warning)' },
  parsed:   { background: 'var(--color-success-bg)', color: 'var(--color-success)' },
  failed:   { background: 'var(--color-danger-bg)',  color: 'var(--color-danger)' },
};

const PARSE_STATUS_LABELS: Record<UploadedFileRecord['parse_status'], string> = {
  pending: '待解析',
  parsing: '解析中',
  parsed:  '已解析',
  failed:  '解析失败',
};

interface FileListProps {
  files: UploadedFileRecord[];
  onDelete: (fileId: string) => void;
  onReplace: (fileId: string, nextFile: File) => void;
  onRetryParse: (fileId: string) => void;
  workingFileId?: string | null;
}

export function FileList({ files, onDelete, onReplace, onRetryParse, workingFileId = null }: FileListProps) {
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
      <div className="mt-4 grid gap-3">
        {files.map((file) => {
          const replaceInputId = `replace-${file.id}`;
          const isWorking = workingFileId === file.id;
          const parseActionLabel = file.parse_status === 'pending' ? '开始解析' : '重新解析';

          return (
            <article key={file.id} className="list-row">
              <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'flex-start', justifyContent: 'space-between', gap: 10 }}>
                <div style={{ minWidth: 0, flex: 1 }}>
                  <h4 style={{ fontSize: 13.5, fontWeight: 600, color: 'var(--color-ink)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{file.file_name}</h4>
                  <p style={{ marginTop: 3, fontSize: 12, color: 'var(--color-steel)' }}>{file.file_type.toUpperCase()}{file.size_label ? ` · ${file.size_label}` : ''}</p>
                </div>
                <span className="status-pill" style={PARSE_STATUS_STYLES[file.parse_status]}>
                  {PARSE_STATUS_LABELS[file.parse_status]}
                </span>
              </div>
              <div style={{ marginTop: 10, display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                <label className="action-secondary cursor-pointer" style={{ fontSize: 12, height: 28, padding: '0 10px' }} htmlFor={replaceInputId}>
                  {isWorking ? '处理中...' : '替换文件'}
                </label>
                <input
                  className="sr-only"
                  id={replaceInputId}
                  onChange={(event) => {
                    const nextFile = event.target.files?.[0];
                    if (nextFile) onReplace(file.id, nextFile);
                    event.currentTarget.value = '';
                  }}
                  type="file"
                />
                <button className="action-secondary" style={{ fontSize: 12, height: 28, padding: '0 10px' }} disabled={isWorking} onClick={() => onRetryParse(file.id)} type="button">
                  {isWorking ? '处理中...' : parseActionLabel}
                </button>
                <button className="action-danger" style={{ fontSize: 12, height: 28, padding: '0 10px' }} disabled={isWorking} onClick={() => onDelete(file.id)} type="button">
                  {isWorking ? '处理中...' : '移除'}
                </button>
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
