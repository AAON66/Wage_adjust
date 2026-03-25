interface DepartmentInsightRow {
  department: string;
  employee_count: number;
  avg_score: number;
  high_potential_count: number;
  pending_review_count: number;
  approved_count: number;
  budget_used: string;
  avg_increase_ratio: number;
}

interface DepartmentInsightTableProps {
  rows: DepartmentInsightRow[];
}

function formatCurrency(value: string): string {
  return new Intl.NumberFormat('zh-CN', {
    style: 'currency',
    currency: 'CNY',
    maximumFractionDigits: 0,
  }).format(Number(value));
}

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

export function DepartmentInsightTable({ rows }: DepartmentInsightTableProps) {
  return (
    <section className="table-shell animate-fade-up">
      <div className="section-head dashboard-table-head">
        <div>
          <p className="eyebrow">部门明细</p>
          <h3 className="section-title">部门表现与调薪执行</h3>
          <p className="section-note">从覆盖人数、评估均分、审批进度和预算执行率判断部门是否需要专项跟进。</p>
        </div>
        <p className="dashboard-summary-inline">{rows.length} 个部门</p>
      </div>
      <div className="overflow-x-auto">
        <table className="table-lite">
          <thead>
            <tr>
              <th>部门</th>
              <th style={{ textAlign: 'right' }}>覆盖员工</th>
              <th style={{ textAlign: 'right' }}>平均分</th>
              <th style={{ textAlign: 'right' }}>高潜人数</th>
              <th style={{ textAlign: 'right' }}>待复核</th>
              <th style={{ textAlign: 'right' }}>已审批</th>
              <th style={{ textAlign: 'right' }}>已用预算</th>
              <th style={{ textAlign: 'right' }}>平均涨幅</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.department}>
                <td style={{ fontWeight: 600, color: 'var(--color-ink)', whiteSpace: 'nowrap' }}>{row.department}</td>
                <td style={{ textAlign: 'right' }}>{row.employee_count}</td>
                <td style={{ textAlign: 'right' }}>
                  <span style={{
                    display: 'inline-block',
                    padding: '2px 8px',
                    borderRadius: 999,
                    fontSize: 12,
                    fontWeight: 600,
                    background: row.avg_score >= 80 ? 'var(--color-success-bg)' : row.avg_score >= 60 ? 'var(--color-primary-light)' : 'var(--color-bg-subtle)',
                    color: row.avg_score >= 80 ? 'var(--color-success)' : row.avg_score >= 60 ? 'var(--color-primary)' : 'var(--color-steel)',
                  }}>
                    {row.avg_score.toFixed(1)}
                  </span>
                </td>
                <td style={{ textAlign: 'right' }}>
                  {row.high_potential_count > 0 ? (
                    <span style={{ fontWeight: 600, color: 'var(--color-success)' }}>{row.high_potential_count}</span>
                  ) : <span style={{ color: 'var(--color-steel)' }}>—</span>}
                </td>
                <td style={{ textAlign: 'right' }}>
                  {row.pending_review_count > 0 ? (
                    <span style={{ fontWeight: 600, color: 'var(--color-warning)' }}>{row.pending_review_count}</span>
                  ) : <span style={{ color: 'var(--color-steel)' }}>—</span>}
                </td>
                <td style={{ textAlign: 'right' }}>{row.approved_count}</td>
                <td style={{ textAlign: 'right', whiteSpace: 'nowrap' }}>{formatCurrency(row.budget_used)}</td>
                <td style={{ textAlign: 'right' }}>
                  <span style={{
                    display: 'inline-block',
                    padding: '2px 8px',
                    borderRadius: 999,
                    fontSize: 12,
                    fontWeight: 600,
                    background: 'var(--color-primary-light)',
                    color: 'var(--color-primary)',
                  }}>
                    {formatPercent(row.avg_increase_ratio)}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {!rows.length ? <p className="px-5 py-4 text-sm text-steel">当前周期还没有可展示的部门洞察数据。</p> : null}
    </section>
  );
}
