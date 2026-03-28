import ReactECharts from 'echarts-for-react';
import type { DashboardDistributionItem } from '../../types/api';
import { ServiceUnavailableBanner } from './AILevelChart';

const STATUS_LABEL_MAP: Record<string, string> = {
  draft: '草稿',
  submitted: '已提交',
  pending_approval: '审批中',
  approved: '已批准',
  rejected: '已拒绝',
  recommended: '已推荐',
  adjusted: '已调整',
  locked: '已锁定',
};

const STATUS_COLOR_MAP: Record<string, string> = {
  draft: '#C9CDD4',
  submitted: '#38BDF8',
  pending_approval: '#1456F0',
  approved: '#00B42A',
  rejected: '#F53F3F',
};

const DEFAULT_STATUS_COLOR = '#7C3AED';

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

interface ApprovalPipelineChartProps {
  data: DashboardDistributionItem[];
  isServiceUnavailable?: boolean;
}

export function ApprovalPipelineChart({ data, isServiceUnavailable }: ApprovalPipelineChartProps) {
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

  const labels = data.map((item) => STATUS_LABEL_MAP[item.label] ?? item.label);

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
        data: data.map((item) => ({
          value: item.value,
          itemStyle: {
            color: STATUS_COLOR_MAP[item.label] ?? DEFAULT_STATUS_COLOR,
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
