import { useCallback } from 'react';
import { usePolling } from '../../hooks/usePolling';
import { fetchKpiSummary } from '../../services/dashboardService';
import type { KpiSummaryResponse } from '../../types/api';

interface KpiCardsProps {
  cycleId: string | undefined;
}

function topLevelLabel(data: KpiSummaryResponse): string {
  if (!data.level_summary.length) return '--';
  const sorted = [...data.level_summary].sort((a, b) => b.value - a.value);
  return sorted[0].label;
}

export function KpiCards({ cycleId }: KpiCardsProps) {
  const fetcher = useCallback(() => fetchKpiSummary(cycleId), [cycleId]);
  const { data, isServiceUnavailable } = usePolling<KpiSummaryResponse>(fetcher, 30000);

  return (
    <div>
      {isServiceUnavailable ? (
        <div
          style={{
            padding: '8px 16px',
            marginBottom: 12,
            borderRadius: 8,
            background: 'var(--color-bg-subtle)',
            border: '1px solid var(--color-border)',
            fontSize: 13,
            color: 'var(--color-warning)',
          }}
        >
          缓存服务暂时不可用，KPI 数据可能更新较慢。
        </div>
      ) : null}
      <div className="kpi-cards-grid">
        <article className="metric-tile">
          <p className="metric-label">待审批数</p>
          <p
            className="metric-value"
            style={
              data && data.pending_approvals > 0
                ? { color: '#FF7D00' }
                : undefined
            }
          >
            {data ? data.pending_approvals : '--'}
          </p>
        </article>
        <article className="metric-tile">
          <p className="metric-label">已评估 / 总人数</p>
          <p className="metric-value">
            {data ? `${data.evaluated_employees} / ${data.total_employees}` : '--'}
          </p>
        </article>
        <article className="metric-tile">
          <p className="metric-label">平均调薪幅度</p>
          <p className="metric-value">
            {data ? `${(data.avg_adjustment_ratio * 100).toFixed(1)}%` : '--'}
          </p>
        </article>
        <article className="metric-tile">
          <p className="metric-label">AI 等级概览</p>
          <p className="metric-value">{data ? topLevelLabel(data) : '--'}</p>
        </article>
      </div>
      <style>{`
        .kpi-cards-grid {
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          gap: 16px;
        }
        @media (max-width: 1279px) {
          .kpi-cards-grid {
            grid-template-columns: repeat(2, 1fr);
          }
        }
        @media (max-width: 767px) {
          .kpi-cards-grid {
            grid-template-columns: 1fr;
          }
        }
      `}</style>
    </div>
  );
}
