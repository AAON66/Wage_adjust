import type { SalaryHistoryRecord } from '../../types/api';

interface SalaryHistoryPanelProps {
  employeeName?: string;
  currentCycleId?: string;
  history: SalaryHistoryRecord[];
  isLoading: boolean;
}

const STATUS_LABELS: Record<string, string> = {
  draft: '草稿',
  recommended: '已建议',
  adjusted: '已人工调整',
  pending_approval: '审批中',
  approved: '已审批',
  locked: '已锁定',
};

function formatCurrency(value: string): string {
  return new Intl.NumberFormat('zh-CN', {
    style: 'currency',
    currency: 'CNY',
    maximumFractionDigits: 0,
  }).format(Number(value));
}

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(2)}%`;
}

function formatStatus(status: string): string {
  return STATUS_LABELS[status] ?? status;
}

function buildPath(points: Array<{ x: number; y: number }>): string {
  return points.map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.x} ${point.y}`).join(' ');
}

export function SalaryHistoryPanel({ employeeName, currentCycleId, history, isLoading }: SalaryHistoryPanelProps) {
  if (isLoading) {
    return (
      <section className="surface px-6 py-6 lg:px-7">
        <div className="section-head">
          <div>
            <p className="eyebrow">历史调薪</p>
            <h3 className="section-title">加薪记录走势</h3>
          </div>
        </div>
        <p className="mt-4 text-sm text-steel">正在加载该员工的历史加薪记录...</p>
      </section>
    );
  }

  if (!history.length) {
    return (
      <section className="surface px-6 py-6 lg:px-7">
        <div className="section-head">
          <div>
            <p className="eyebrow">历史调薪</p>
            <h3 className="section-title">加薪记录走势</h3>
            <p className="section-note mt-2">当前员工还没有可展示的历史调薪记录。</p>
          </div>
        </div>
        <div
          className="mt-5"
          style={{ border: '1px dashed var(--color-border)', borderRadius: 8, background: 'var(--color-bg-subtle)', padding: '16px 20px', fontSize: 14, lineHeight: 1.8, color: 'var(--color-steel)' }}
        >
          等当前员工生成并保留跨周期调薪建议后，这里会自动显示趋势图和历史明细。
        </div>
      </section>
    );
  }

  const historyInOrder = [...history].sort((left, right) => new Date(left.created_at).getTime() - new Date(right.created_at).getTime());
  const historyLatestFirst = [...historyInOrder].reverse();
  const latestRecord = historyInOrder[historyInOrder.length - 1];
  const totalIncrease = historyInOrder.reduce((sum, item) => sum + Number(item.adjustment_amount), 0);
  const maxSalary = Math.max(...historyInOrder.flatMap((item) => [Number(item.current_salary), Number(item.recommended_salary)]));
  const minSalary = Math.min(...historyInOrder.flatMap((item) => [Number(item.current_salary), Number(item.recommended_salary)]));
  const salarySpan = Math.max(maxSalary - minSalary, 1);
  const chartWidth = 720;
  const chartHeight = 240;
  const paddingX = 42;
  const paddingTop = 20;
  const paddingBottom = 54;
  const plotWidth = chartWidth - paddingX * 2;
  const plotHeight = chartHeight - paddingTop - paddingBottom;
  const getX = (index: number) => paddingX + (historyInOrder.length === 1 ? plotWidth / 2 : (plotWidth / Math.max(historyInOrder.length - 1, 1)) * index);
  const getY = (value: number) => paddingTop + ((maxSalary - value) / salarySpan) * plotHeight;
  const currentSalaryPoints = historyInOrder.map((item, index) => ({ x: getX(index), y: getY(Number(item.current_salary)) }));
  const recommendedSalaryPoints = historyInOrder.map((item, index) => ({ x: getX(index), y: getY(Number(item.recommended_salary)) }));
  const currentSalaryPath = buildPath(currentSalaryPoints);
  const recommendedSalaryPath = buildPath(recommendedSalaryPoints);
  const yAxisValues = Array.from({ length: 4 }, (_, index) => {
    const ratio = index / 3;
    const value = maxSalary - (maxSalary - minSalary) * ratio;
    return {
      label: formatCurrency(String(Math.round(value))),
      y: paddingTop + plotHeight * ratio,
    };
  });

  return (
    <section className="surface px-6 py-6 lg:px-7">
      <div className="section-head">
        <div>
          <p className="eyebrow">历史调薪</p>
          <h3 className="section-title">加薪记录走势</h3>
          <p className="section-note mt-2">{employeeName ? `${employeeName} 的跨周期调薪建议与最终调幅变化。` : '按周期查看薪资基线、建议薪资与最终调幅。'}</p>
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <span className="status-pill" style={{ background: 'rgba(20,86,240,0.12)', color: 'var(--color-primary)' }}>当前记录 {history.length} 条</span>
          <span className="status-pill" style={{ background: 'var(--color-success-bg)', color: 'var(--color-success)' }}>最近调幅 {formatPercent(latestRecord.final_adjustment_ratio)}</span>
        </div>
      </div>

      <div className="mt-5 grid gap-3 md:grid-cols-3">
        <div className="surface-subtle px-4 py-4">
          <p className="text-sm text-steel">累计调薪金额</p>
          <p className="mt-2 text-2xl font-semibold text-ink">{formatCurrency(String(totalIncrease.toFixed(2)))}</p>
        </div>
        <div className="surface-subtle px-4 py-4">
          <p className="text-sm text-steel">最近建议薪资</p>
          <p className="mt-2 text-2xl font-semibold text-ink">{formatCurrency(latestRecord.recommended_salary)}</p>
        </div>
        <div className="surface-subtle px-4 py-4">
          <p className="text-sm text-steel">最近 AI 等级</p>
          <p className="mt-2 text-2xl font-semibold text-ink">{latestRecord.ai_level}</p>
        </div>
      </div>

      <div className="mt-5 grid gap-5 xl:grid-cols-[1.15fr_0.85fr]">
        <div className="surface-subtle px-4 py-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-sm font-semibold text-ink">薪资趋势图</p>
              <p className="mt-1 text-xs leading-5 text-steel">蓝线代表当期薪资基线，绿色线代表建议或最终调后薪资。</p>
            </div>
            <div className="flex flex-wrap gap-3 text-xs text-steel">
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                <span style={{ width: 10, height: 10, borderRadius: 999, background: 'var(--color-primary)' }} />
                当前薪资
              </span>
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                <span style={{ width: 10, height: 10, borderRadius: 999, background: 'var(--color-success)' }} />
                建议薪资
              </span>
            </div>
          </div>

          <div className="mt-4 overflow-x-auto">
            <svg
              aria-label="历史加薪趋势图"
              style={{ minWidth: 640, width: '100%', height: 280, overflow: 'visible', fontFamily: '"PingFang SC", "Microsoft YaHei", sans-serif' }}
              viewBox={`0 0 ${chartWidth} ${chartHeight}`}
            >
              {yAxisValues.map((tick) => (
                <g key={tick.y}>
                  <line x1={paddingX} x2={chartWidth - paddingX} y1={tick.y} y2={tick.y} stroke="var(--color-border)" strokeDasharray="4 6" />
                  <text x={8} y={tick.y + 4} fill="var(--color-steel)" fontSize="11">
                    {tick.label}
                  </text>
                </g>
              ))}

              <path d={currentSalaryPath} fill="none" stroke="var(--color-primary)" strokeWidth="3" />
              <path d={recommendedSalaryPath} fill="none" stroke="var(--color-success)" strokeWidth="3" />

              {historyInOrder.map((item, index) => {
                const currentPoint = currentSalaryPoints[index];
                const recommendedPoint = recommendedSalaryPoints[index];
                const isCurrentCycle = currentCycleId != null && item.cycle_id === currentCycleId;
                return (
                  <g key={item.recommendation_id}>
                    <line
                      x1={currentPoint.x}
                      x2={currentPoint.x}
                      y1={chartHeight - paddingBottom + 2}
                      y2={chartHeight - paddingBottom + 10}
                      stroke="var(--color-border-strong)"
                    />
                    <circle cx={currentPoint.x} cy={currentPoint.y} fill="#FFFFFF" r="5" stroke="var(--color-primary)" strokeWidth="2.5" />
                    <circle cx={recommendedPoint.x} cy={recommendedPoint.y} fill="#FFFFFF" r="5" stroke="var(--color-success)" strokeWidth="2.5" />
                    {isCurrentCycle ? <circle cx={recommendedPoint.x} cy={recommendedPoint.y} fill="rgba(17,160,88,0.12)" r="11" stroke="none" /> : null}
                    <text x={currentPoint.x} y={chartHeight - 18} fill={isCurrentCycle ? 'var(--color-primary)' : 'var(--color-steel)'} fontSize="11" textAnchor="middle">
                      {item.cycle_name}
                    </text>
                  </g>
                );
              })}
            </svg>
          </div>
        </div>

        <div className="surface-subtle px-4 py-4">
          <p className="text-sm font-semibold text-ink">历史明细</p>
          <div className="mt-4 space-y-3">
            {historyLatestFirst.map((item) => {
              const isCurrentCycle = currentCycleId != null && item.cycle_id === currentCycleId;
              return (
                <div
                  key={item.recommendation_id}
                  style={{
                    border: `1px solid ${isCurrentCycle ? 'rgba(20,86,240,0.24)' : 'var(--color-border)'}`,
                    borderRadius: 8,
                    background: isCurrentCycle ? 'rgba(20,86,240,0.04)' : '#FFFFFF',
                    padding: '12px 14px',
                  }}
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-ink">{item.cycle_name}</p>
                      <p className="mt-1 text-xs text-steel">{item.review_period} · AI 等级 {item.ai_level} · 综合分 {item.overall_score.toFixed(1)}</p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {isCurrentCycle ? <span className="status-pill" style={{ background: 'rgba(20,86,240,0.12)', color: 'var(--color-primary)' }}>当前周期</span> : null}
                      <span className="status-pill" style={{ background: 'var(--color-bg-subtle)', color: 'var(--color-ink)' }}>{formatStatus(item.status)}</span>
                    </div>
                  </div>
                  <div className="mt-3 grid gap-2 text-sm text-steel">
                    <div className="flex items-center justify-between gap-4">
                      <span>薪资变动</span>
                      <span className="font-medium text-ink">{formatCurrency(item.current_salary)} → {formatCurrency(item.recommended_salary)}</span>
                    </div>
                    <div className="flex items-center justify-between gap-4">
                      <span>最终调幅</span>
                      <span className="font-medium text-ink">{formatPercent(item.final_adjustment_ratio)}</span>
                    </div>
                    <div className="flex items-center justify-between gap-4">
                      <span>调薪金额</span>
                      <span className="font-medium" style={{ color: 'var(--color-success)' }}>{formatCurrency(item.adjustment_amount)}</span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}
