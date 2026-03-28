import type { ImportRowResult } from '../../types/api';

interface ImportErrorTableProps {
  rows: ImportRowResult[];
  maxDisplay?: number;
}

export function ImportErrorTable({ rows, maxDisplay = 50 }: ImportErrorTableProps) {
  const failedRows = rows.filter((r) => r.status === 'failed');
  const displayRows = failedRows.slice(0, maxDisplay);
  const remaining = failedRows.length - displayRows.length;

  return (
    <div className="table-shell" style={{ marginTop: 12 }}>
      <div style={{ overflowX: 'auto' }}>
        <table className="table-lite">
          <thead>
            <tr>
              <th style={{ width: 80, textAlign: 'center' }}>行号</th>
              <th style={{ width: 80, textAlign: 'center' }}>状态</th>
              <th style={{ width: 120, textAlign: 'left' }}>错误字段</th>
              <th style={{ textAlign: 'left' }}>错误原因</th>
            </tr>
          </thead>
          <tbody>
            {displayRows.map((row, idx) => (
              <tr key={row.row_index ?? idx}>
                <td style={{ textAlign: 'center' }}>{row.row_index ?? '--'}</td>
                <td style={{ textAlign: 'center' }}>
                  <span
                    className="status-pill"
                    style={{ background: 'var(--color-danger-bg)', color: 'var(--color-danger)' }}
                  >
                    失败
                  </span>
                </td>
                <td>{row.error_column ?? '--'}</td>
                <td>{row.message}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {remaining > 0 ? (
        <div
          style={{
            padding: '12px 14px',
            fontSize: 13,
            color: 'var(--color-steel)',
            textAlign: 'center',
            background: 'var(--color-bg-subtle)',
          }}
        >
          还有 {remaining} 条错误未显示，请下载完整错误报告查看。
        </div>
      ) : null}
    </div>
  );
}
