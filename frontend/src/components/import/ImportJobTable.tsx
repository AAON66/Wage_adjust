import type React from 'react';

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

const STATUS_STYLES: Record<ImportJobRow['status'], React.CSSProperties> = {
  pending:    { background: 'var(--color-bg-subtle)', color: 'var(--color-steel)' },
  queued:     { background: 'var(--color-bg-subtle)', color: 'var(--color-steel)' },
  processing: { background: 'var(--color-warning-bg)', color: 'var(--color-warning)' },
  completed:  { background: 'var(--color-success-bg)', color: 'var(--color-success)' },
  failed:     { background: 'var(--color-danger-bg)', color: 'var(--color-danger)' },
};

const STATUS_LABELS: Record<ImportJobRow['status'], string> = {
  pending: '待处理',
  queued: '排队中',
  processing: '处理中',
  completed: '已完成',
  failed: '失败',
};

function formatImportType(importType: string): string {
  return { employees: '员工', certifications: '认证' }[importType] ?? importType;
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
    <section className="table-shell">
      <div className="section-head" style={{ padding: '16px 20px' }}>
        <div>
          <p className="eyebrow">导入任务</p>
          <h3 className="section-title">批量导入记录</h3>
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 8 }}>
          {onDeleteSelected ? (
            <button className="action-danger" disabled={!selectedIds.length} onClick={onDeleteSelected} type="button">
              删除所选{selectedIds.length ? `（${selectedIds.length}）` : ''}
            </button>
          ) : null}
          <span style={{ fontSize: 13, color: 'var(--color-steel)' }}>{rows.length} 个任务</span>
        </div>
      </div>
      <div style={{ overflowX: 'auto' }}>
        <table className="table-lite">
          <thead>
            <tr>
              <th>
                <label style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
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
                    <div style={{ fontWeight: 500, color: 'var(--color-ink)' }}>{row.fileName}</div>
                    <div style={{ marginTop: 2, fontSize: 12, color: 'var(--color-steel)' }}>任务编号 {row.id.slice(0, 8)}</div>
                  </td>
                  <td>{formatImportType(row.importType)}</td>
                  <td>
                    <span className="status-pill" style={STATUS_STYLES[row.status]}>{STATUS_LABELS[row.status]}</span>
                  </td>
                  <td>{row.totalRows}</td>
                  <td style={{ color: 'var(--color-success)' }}>{row.successRows}</td>
                  <td style={{ color: row.failedRows > 0 ? 'var(--color-danger)' : 'var(--color-steel)' }}>{row.failedRows}</td>
                  <td>
                    <button className="action-secondary" style={{ height: 30, padding: '0 12px', fontSize: 13 }} disabled={!onExport} onClick={() => onExport?.(row.id)} type="button">
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
