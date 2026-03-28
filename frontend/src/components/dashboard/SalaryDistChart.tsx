import ReactECharts from 'echarts-for-react';
import type { DashboardDistributionItem } from '../../types/api';
import { ServiceUnavailableBanner } from './AILevelChart';

const ALPHA_STEPS = [0.4, 0.55, 0.7, 0.85, 1.0];

function alphaColor(alpha: number): string {
  const r = 20, g = 86, b = 240;
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

const BASE_TEXT_STYLE = {
  fontFamily: '"PingFang SC", "Microsoft YaHei", "Segoe UI", Inter, sans-serif',
  color: '#646A73',
};

const BASE_TOOLTIP = {
  trigger: 'axis' as const,
  backgroundColor: '#FFFFFF',
  borderColor: '#E0E4EA',
  borderWidth: 1,
  textStyle: { color: '#1F2329', fontSize: 13 },
  padding: [8, 12] as [number, number],
  extraCssText: 'box-shadow: 0 4px 16px rgba(0,0,0,0.10);',
};

const BASE_GRID = { left: 16, right: 16, top: 24, bottom: 8, containLabel: true };

interface SalaryDistChartProps {
  data: DashboardDistributionItem[];
  isServiceUnavailable?: boolean;
}

export function SalaryDistChart({ data, isServiceUnavailable }: SalaryDistChartProps) {
  if (isServiceUnavailable) {
    return <ServiceUnavailableBanner />;
  }

  if (!data.length) {
    return (
      <div
        className="surface"
        style={{ height: 300, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
      >
        <span style={{ color: 'var(--color-steel)', fontSize: 13 }}>当前周期暂无数据</span>
      </div>
    );
  }

  const labels = data.map((item) => item.label);

  const option = {
    textStyle: BASE_TEXT_STYLE,
    tooltip: BASE_TOOLTIP,
    grid: BASE_GRID,
    xAxis: {
      type: 'category' as const,
      data: labels,
      axisLabel: { fontSize: 12 },
      axisTick: { show: false },
      axisLine: { lineStyle: { color: '#E0E4EA' } },
    },
    yAxis: {
      type: 'value' as const,
      name: '人数',
      nameTextStyle: { fontSize: 11, color: '#646A73' },
      splitLine: { lineStyle: { color: '#F0F1F3' } },
    },
    series: [
      {
        type: 'bar' as const,
        data: data.map((item, i) => ({
          value: item.value,
          itemStyle: {
            color: alphaColor(ALPHA_STEPS[i] ?? 1.0),
            borderRadius: [4, 4, 0, 0],
          },
        })),
        barMaxWidth: 48,
      },
    ],
  };

  return (
    <div style={{ height: 300 }}>
      <ReactECharts option={option} style={{ height: '100%', width: '100%' }} />
    </div>
  );
}
