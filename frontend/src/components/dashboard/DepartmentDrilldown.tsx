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

interface DepartmentDrilldownProps {
  department: string;
  levelData: DashboardDistributionItem[];
  avgAdjustment: number;
  employeeCount: number;
}

export function DepartmentDrilldown({
  department,
  levelData,
  avgAdjustment,
  employeeCount,
}: DepartmentDrilldownProps) {
  const labels = levelData.map((item) => LEVEL_LABEL_MAP[item.label] ?? item.label);
  const colors = levelData.map((item) => LEVEL_COLORS[item.label] ?? '#C9CDD4');

  const option = {
    textStyle: {
      fontFamily: '"PingFang SC", "Microsoft YaHei", "Segoe UI", Inter, sans-serif',
      color: '#646A73',
    },
    tooltip: {
      trigger: 'axis' as const,
      backgroundColor: '#FFFFFF',
      borderColor: '#E0E4EA',
      borderWidth: 1,
      textStyle: { color: '#1F2329', fontSize: 12 },
      padding: [6, 10] as [number, number],
      extraCssText: 'box-shadow: 0 4px 16px rgba(0,0,0,0.10);',
    },
    grid: { left: 8, right: 8, top: 16, bottom: 4, containLabel: true },
    xAxis: {
      type: 'category' as const,
      data: labels,
      axisLabel: { fontSize: 11 },
      axisTick: { show: false },
      axisLine: { lineStyle: { color: '#E0E4EA' } },
    },
    yAxis: {
      type: 'value' as const,
      splitLine: { lineStyle: { color: '#F0F1F3' } },
      axisLabel: { fontSize: 10 },
    },
    series: [
      {
        type: 'bar' as const,
        data: levelData.map((item, i) => ({
          value: item.value,
          itemStyle: { color: colors[i], borderRadius: [4, 4, 0, 0] },
        })),
        barMaxWidth: 32,
      },
    ],
  };

  return (
    <div style={{ padding: 20, background: 'var(--color-bg-subtle)', borderRadius: 12 }}>
      <h4 style={{ fontSize: 14, fontWeight: 600, color: 'var(--color-ink)', marginBottom: 12 }}>
        {department} - 部门下钻
      </h4>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        <div style={{ height: 200 }}>
          <ReactECharts option={option} style={{ height: '100%', width: '100%' }} />
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 12 }}>
          <div>
            <p style={{ fontSize: 12, color: 'var(--color-steel)' }}>平均调薪幅度</p>
            <p style={{ fontSize: 20, fontWeight: 700, color: 'var(--color-ink)' }}>
              {(avgAdjustment * 100).toFixed(1)}%
            </p>
          </div>
          <div>
            <p style={{ fontSize: 12, color: 'var(--color-steel)' }}>部门员工数</p>
            <p style={{ fontSize: 20, fontWeight: 700, color: 'var(--color-ink)' }}>{employeeCount}</p>
          </div>
        </div>
      </div>
    </div>
  );
}
