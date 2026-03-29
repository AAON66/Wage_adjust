import ReactECharts from 'echarts-for-react';
import { DIMENSION_LABELS, DIMENSION_ORDER } from '../../utils/dimensionConstants';

interface DimensionScore {
  dimension_code: string;
  raw_score: number;
  weight: number;
}

interface DimensionRadarChartProps {
  scores: DimensionScore[];
}

const BASE_TEXT_STYLE = {
  fontFamily: '"PingFang SC", "Microsoft YaHei", "Segoe UI", Inter, sans-serif',
  color: '#646A73',
};

export function DimensionRadarChart({ scores }: DimensionRadarChartProps) {
  const scoreMap = new Map(scores.map((s) => [s.dimension_code, s]));

  const indicator = DIMENSION_ORDER.map((code) => ({
    name: DIMENSION_LABELS[code] ?? code,
    max: 100,
  }));

  const values = DIMENSION_ORDER.map((code) => scoreMap.get(code)?.raw_score ?? 0);

  const option = {
    textStyle: BASE_TEXT_STYLE,
    tooltip: {
      trigger: 'item' as const,
      backgroundColor: '#FFFFFF',
      borderColor: '#E0E4EA',
      borderWidth: 1,
      textStyle: { color: '#1F2329', fontSize: 13 },
      padding: [8, 12] as [number, number],
      extraCssText: 'box-shadow: 0 4px 16px rgba(0,0,0,0.10);',
      formatter() {
        const lines = DIMENSION_ORDER.map((code) => {
          const s = scoreMap.get(code);
          const label = DIMENSION_LABELS[code] ?? code;
          const score = s?.raw_score ?? 0;
          const weight = s?.weight ?? 0;
          return `${label}: <b>${score}</b> (权重 ${Math.round(weight * 100)}%)`;
        });
        return lines.join('<br/>');
      },
    },
    radar: {
      indicator,
      splitLine: { lineStyle: { color: '#E0E4EA' } },
      splitArea: { show: false },
      axisLine: { lineStyle: { color: '#E0E4EA' } },
      axisName: { color: '#646A73', fontSize: 13 },
    },
    series: [
      {
        type: 'radar' as const,
        data: [
          {
            value: values,
            areaStyle: { color: 'rgba(20, 86, 240, 0.18)' },
            lineStyle: { color: '#1456F0', width: 2 },
            itemStyle: { color: '#1456F0' },
            symbolSize: 4,
          },
        ],
      },
    ],
  };

  return (
    <div style={{ height: 320 }}>
      <ReactECharts option={option} style={{ height: '100%', width: '100%' }} />
    </div>
  );
}
