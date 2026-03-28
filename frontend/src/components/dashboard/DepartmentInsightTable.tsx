import { useEffect, useState } from 'react';

import { fetchDepartmentDrilldown } from '../../services/dashboardService';
import type { DashboardDepartmentInsight, DepartmentDrilldownResponse } from '../../types/api';
import { DepartmentDrilldown } from './DepartmentDrilldown';

interface DepartmentInsightTableProps {
  rows: DashboardDepartmentInsight[];
  cycleId?: string;
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

export function DepartmentInsightTable({ rows, cycleId }: DepartmentInsightTableProps) {
  const [expandedDept, setExpandedDept] = useState<string | null>(null);
  const [drilldownData, setDrilldownData] = useState<DepartmentDrilldownResponse | null>(null);
  const [drilldownLoading, setDrilldownLoading] = useState(false);

  // Reset drilldown state when cycle changes
  useEffect(() => {
    setExpandedDept(null);
    setDrilldownData(null);
  }, [cycleId]);

  async function handleToggleDrilldown(department: string) {
    if (expandedDept === department) {
      setExpandedDept(null);
      setDrilldownData(null);
      return;
    }

    setExpandedDept(department);
    setDrilldownData(null);
    setDrilldownLoading(true);

    try {
      const response = await fetchDepartmentDrilldown(department, cycleId);
      setDrilldownData(response);
    } catch {
      setDrilldownData(null);
    } finally {
      setDrilldownLoading(false);
    }
  }

  const columnCount = 9; // 8 data columns + 1 action column

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
              <th style={{ textAlign: 'center', width: 100 }}>操作</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <>
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
                    ) : <span style={{ color: 'var(--color-steel)' }}>--</span>}
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    {row.pending_review_count > 0 ? (
                      <span style={{ fontWeight: 600, color: 'var(--color-warning)' }}>{row.pending_review_count}</span>
                    ) : <span style={{ color: 'var(--color-steel)' }}>--</span>}
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
                  <td style={{ textAlign: 'center' }}>
                    <button
                      className="chip-button"
                      style={{ fontSize: 12, padding: '2px 10px' }}
                      onClick={() => void handleToggleDrilldown(row.department)}
                    >
                      {expandedDept === row.department ? '收起' : '查看详情'}
                    </button>
                  </td>
                </tr>
                {expandedDept === row.department ? (
                  <tr key={`${row.department}-drilldown`}>
                    <td colSpan={columnCount} style={{ padding: 0 }}>
                      {drilldownLoading ? (
                        <div style={{ padding: 20, textAlign: 'center', color: 'var(--color-steel)', fontSize: 13 }}>
                          加载中...
                        </div>
                      ) : drilldownData ? (
                        <DepartmentDrilldown
                          department={drilldownData.department}
                          levelData={drilldownData.level_distribution}
                          avgAdjustment={drilldownData.avg_adjustment_ratio}
                          employeeCount={drilldownData.employee_count}
                        />
                      ) : (
                        <div style={{ padding: 20, textAlign: 'center', color: 'var(--color-steel)', fontSize: 13 }}>
                          加载下钻数据失败。
                        </div>
                      )}
                    </td>
                  </tr>
                ) : null}
              </>
            ))}
          </tbody>
        </table>
      </div>
      {!rows.length ? <p className="px-5 py-4 text-sm text-steel">当前周期还没有可展示的部门洞察数据。</p> : null}
    </section>
  );
}
