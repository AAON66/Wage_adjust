export interface CalibrationCompareRow {
  code: string;
  label: string;
  aiScore: number;
  manualScore: number | null;
  note: string;
  status: 'waiting' | 'completed';
}

interface CalibrationCompareTableProps {
  rows: CalibrationCompareRow[];
}

function formatScore(value: number | null): string {
  if (value == null) {
    return '--';
  }
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}

export function CalibrationCompareTable({ rows }: CalibrationCompareTableProps) {
  return (
    <section className="table-shell animate-fade-up">
      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12, padding: '14px 16px', borderBottom: '1px solid var(--color-border)' }}>
        <div>
          <p className="eyebrow">校准对比</p>
          <h3 className="section-title">AI 与人工评分对照</h3>
          <p style={{ marginTop: 4, fontSize: 13, color: 'var(--color-steel)' }}>现在会固定保留 AI 原始分，不会再被人工复核分覆盖。</p>
        </div>
        <span style={{ fontSize: 13, color: 'var(--color-steel)' }}>{rows.length} 条记录</span>
      </div>
      <div className="overflow-x-auto">
        <table className="table-lite">
          <thead>
            <tr>
              <th>维度</th>
              <th>AI 原始分</th>
              <th>人工复核分</th>
              <th>差值</th>
              <th style={{ width: 136, textAlign: 'center' }}>当前状态</th>
              <th>复核说明</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const delta = row.manualScore == null ? null : row.manualScore - row.aiScore;
              const deltaColor = delta == null ? 'var(--color-steel)' : delta === 0 ? 'var(--color-steel)' : delta > 0 ? 'var(--color-success)' : 'var(--color-danger)';
              const statusLabel = row.status === 'completed' ? '已完成对比' : '待人工复核';
              return (
                <tr key={row.code}>
                  <td>
                    <div className="font-semibold text-ink">{row.label}</div>
                    <div className="mt-1 text-xs uppercase tracking-[0.18em] text-steel">{row.code}</div>
                  </td>
                  <td>{formatScore(row.aiScore)}</td>
                  <td>{formatScore(row.manualScore)}</td>
                  <td style={{ fontWeight: 600, color: deltaColor }}>
                    {delta == null ? '--' : delta > 0 ? `+${formatScore(delta)}` : formatScore(delta)}
                  </td>
                  <td style={{ width: 136 }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 32 }}>
                      <span
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          minHeight: 28,
                          borderRadius: 999,
                          padding: '0 12px',
                          fontSize: 12,
                          fontWeight: 600,
                          lineHeight: 1,
                          whiteSpace: 'nowrap',
                          background: row.status === 'completed' ? 'var(--color-success-bg)' : 'var(--color-bg-subtle)',
                          color: row.status === 'completed' ? 'var(--color-success)' : 'var(--color-steel)',
                        }}
                      >
                        {statusLabel}
                      </span>
                    </div>
                  </td>
                  <td>{row.note || '暂无补充说明'}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
