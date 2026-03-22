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
  selectedIds?: string[];
  onToggleRow?: (jobId: string) => void;
  onToggleAll?: () => void;
  onDeleteSelected?: () => void;
  onExport?: (jobId: string) => void;
}

const STATUS_STYLES: Record<ImportJobRow['status'], string> = {
  pending: 'bg-slate-100 text-slate-700',
  queued: 'bg-slate-100 text-slate-700',
  processing: 'bg-amber-100 text-amber-700',
  completed: 'bg-emerald-100 text-emerald-700',
  failed: 'bg-rose-100 text-rose-700',
};

const STATUS_LABELS: Record<ImportJobRow['status'], string> = {
  pending: '待处理',
  queued: '排队中',
  processing: '处理中',
  completed: '已完成',
  failed: '失败',
};

function formatImportType(importType: string): string {
  return {
    employees: '员工',
    certifications: '认证',
  }[importType] ?? importType;
}

export function ImportJobTable({
  rows,
  selectedIds = [],
  onToggleRow,
  onToggleAll,
  onDeleteSelected,
  onExport,
}: ImportJobTableProps) {
  const allSelected = rows.length > 0 && selectedIds.length === rows.length;

  return (
    <section className="table-shell animate-fade-up">
      <div className="section-head px-6 py-5">
        <div>
          <p className="eyebrow">导入任务</p>
          <h3 className="section-title">批量导入记录</h3>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          {onDeleteSelected ? (
            <button className="action-danger px-4 py-2 text-xs" disabled={!selectedIds.length} onClick={onDeleteSelected} type="button">
              删除所选{selectedIds.length ? `（${selectedIds.length}）` : ''}
            </button>
          ) : null}
          <span className="text-sm text-steel">{rows.length} 个任务</span>
        </div>
      </div>
      <div className="overflow-x-auto">
        <table className="table-lite">
          <thead>
            <tr>
              <th>
                <label className="flex items-center gap-2 text-xs font-semibold text-steel">
                  <input checked={allSelected} onChange={() => onToggleAll?.()} type="checkbox" />
                  <span>全选</span>
                </label>
              </th>
              <th>文件</th>
              <th>类型</th>
              <th>状态</th>
              <th>总行数</th>
              <th>成功</th>
              <th>失败</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const isSelected = selectedIds.includes(row.id);
              return (
                <tr key={row.id}>
                  <td>
                    <input checked={isSelected} onChange={() => onToggleRow?.(row.id)} type="checkbox" />
                  </td>
                  <td>
                    <div className="font-medium text-ink">{row.fileName}</div>
                    <div className="mt-1 text-xs text-steel">任务编号 {row.id.slice(0, 8)}</div>
                  </td>
                  <td>{formatImportType(row.importType)}</td>
                  <td>
                    <span className={`status-pill ${STATUS_STYLES[row.status]}`}>{STATUS_LABELS[row.status]}</span>
                  </td>
                  <td>{row.totalRows}</td>
                  <td className="text-emerald-700">{row.successRows}</td>
                  <td className={row.failedRows > 0 ? 'text-rose-600' : 'text-steel'}>{row.failedRows}</td>
                  <td>
                    <button className="action-secondary px-4 py-2 text-xs" disabled={!onExport} onClick={() => onExport?.(row.id)} type="button">
                      导出报告
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
