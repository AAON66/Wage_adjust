import ReactECharts from 'echarts-for-react';

import type { ActualDistribution, TierCounts } from '../../types/api';

interface TierStackedBarProps {
  tiersCount: TierCounts;
  actualDistribution: ActualDistribution;
}

interface BarPoint {
  value: number;
  count: number;
}

interface FormatterParams {
  seriesName: string;
  value: number;
  data: BarPoint;
}

/**
 * Phase 34 D-11 / UI-SPEC §6.3：水平堆叠条
 * - 高度固定 32px，宽度 100%
 * - 1 档 #10b981 / 2 档 #f59e0b / 3 档 #ef4444（D-11 锁定）
 * - tooltip：「{seriesName}：{count} 人 ({pct}%)」（1 位小数）
 */
export function TierStackedBar({ tiersCount, actualDistribution }: TierStackedBarProps) {
  const option = {
    grid: { left: 0, right: 0, top: 0, bottom: 0, containLabel: false },
    tooltip: {
      trigger: 'item' as const,
      backgroundColor: '#FFFFFF',
      borderColor: '#E0E4EA',
      borderWidth: 1,
      textStyle: { color: '#1F2329', fontSize: 13 },
      padding: [6, 10] as [number, number],
      formatter: (p: FormatterParams) =>
        `${p.seriesName}：${p.data.count} 人 (${(p.value * 100).toFixed(1)}%)`,
    },
    xAxis: { type: 'value' as const, show: false, max: 1 },
    yAxis: { type: 'category' as const, show: false, data: [''] },
    series: [
      {
        name: '1 档',
        type: 'bar' as const,
        stack: 'total',
        data: [{ value: actualDistribution['1'], count: tiersCount['1'] }],
        itemStyle: { color: '#10b981', borderRadius: [4, 0, 0, 4] as [number, number, number, number] },
        barWidth: '100%',
      },
      {
        name: '2 档',
        type: 'bar' as const,
        stack: 'total',
        data: [{ value: actualDistribution['2'], count: tiersCount['2'] }],
        itemStyle: { color: '#f59e0b' },
        barWidth: '100%',
      },
      {
        name: '3 档',
        type: 'bar' as const,
        stack: 'total',
        data: [{ value: actualDistribution['3'], count: tiersCount['3'] }],
        itemStyle: { color: '#ef4444', borderRadius: [0, 4, 4, 0] as [number, number, number, number] },
        barWidth: '100%',
      },
    ],
  };

  return (
    <div style={{ height: 32, width: '100%', marginBottom: 12 }}>
      <ReactECharts option={option} style={{ height: '100%', width: '100%' }} />
    </div>
  );
}
