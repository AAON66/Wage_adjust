import ReactECharts from 'echarts-for-react';
import type { DashboardDistributionItem } from '../../types/api';

const LEVEL_LABEL_MAP: Record<string, string> = {
  'Level 1': '一级',
  'Level 2': '二级',
  'Level 3': '三级',
  'Level 4': '四级',
  'Level 5': '五级',
};

const LEVEL_COLORS: Record<string, string> = {
  'Level 1': '#C9CDD4',
  'Level 2': '#BAE6FD',
  'Level 3': '#38BDF8',
  'Level 4': '#1456F0',
  'Level 5': '#00B42A',
};

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

interface AILevelChartProps {
  data: DashboardDistributionItem[];
  error?: string | null;
  isServiceUnavailable?: boolean;
}

function ServiceUnavailableBanner() {
  return (
    <div
      className="surface"
      style={{
        height: 300,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexDirection: 'column',
        gap: 8,
      }}
    >
      <span style={{ color: 'var(--color-warning)', fontSize: 15, fontWeight: 600 }}>
        缓存服务暂时不可用
      </span>
      <span style={{ color: 'var(--color-steel)', fontSize: 13 }}>
        数据加载可能较慢。请联系管理员检查 Redis 服务状态。
      </span>
    </div>
  );
}

export function AILevelChart({ data, isServiceUnavailable }: AILevelChartProps) {
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

  const total = data.reduce((sum, item) => sum + item.value, 0);

  const labels = data.map((item) => LEVEL_LABEL_MAP[item.label] ?? item.label);
  const colors = data.map((item) => LEVEL_COLORS[item.label] ?? '#C9CDD4');

  const option = {
    textStyle: BASE_TEXT_STYLE,
    tooltip: {
      ...BASE_TOOLTIP,
      formatter(params: { name: string; value: number }[]) {
        const p = params[0];
        const pct = total > 0 ? ((p.value / total) * 100).toFixed(1) : '0.0';
        return `${p.name}<br/>人数: <b>${p.value}</b> (${pct}%)`;
      },
    },
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
          itemStyle: { color: colors[i], borderRadius: [4, 4, 0, 0] },
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

export { ServiceUnavailableBanner };
