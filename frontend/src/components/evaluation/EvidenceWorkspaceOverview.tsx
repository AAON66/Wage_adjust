import type { EvidenceRecord } from '../../types/api';

interface EvidenceWorkspaceOverviewProps {
  evidenceItems: EvidenceRecord[];
}

type OverviewMetric = {
  label: string;
  shortLabel: string;
  value: number;
  tone: string;
};

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

function polygonPoints(values: number[], radius: number, center: number): string {
  return values
    .map((value, index) => {
      const angle = -Math.PI / 2 + (Math.PI * 2 * index) / values.length;
      const pointRadius = (radius * value) / 100;
      const x = center + Math.cos(angle) * pointRadius;
      const y = center + Math.sin(angle) * pointRadius;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(' ');
}

function gridPolygonPoints(sides: number, radius: number, center: number): string {
  return Array.from({ length: sides }, (_, index) => {
    const angle = -Math.PI / 2 + (Math.PI * 2 * index) / sides;
    const x = center + Math.cos(angle) * radius;
    const y = center + Math.sin(angle) * radius;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(' ');
}

function axisEndPoint(index: number, sides: number, radius: number, center: number) {
  const angle = -Math.PI / 2 + (Math.PI * 2 * index) / sides;
  return {
    x: center + Math.cos(angle) * radius,
    y: center + Math.sin(angle) * radius,
    labelX: center + Math.cos(angle) * (radius + 18),
    labelY: center + Math.sin(angle) * (radius + 18),
  };
}

function buildMetrics(evidenceItems: EvidenceRecord[]): OverviewMetric[] {
  const count = evidenceItems.length;
  const averageConfidence = count
    ? evidenceItems.reduce((sum, item) => sum + item.confidence_score * 100, 0) / count
    : 0;
  const averageContentLength = count
    ? evidenceItems.reduce((sum, item) => sum + item.content.trim().length, 0) / count
    : 0;
  const uniqueSourceTypes = new Set(evidenceItems.map((item) => item.source_type)).size;
  const averageMetadataCount = count
    ? evidenceItems.reduce((sum, item) => sum + Object.keys(item.metadata_json ?? {}).length, 0) / count
    : 0;
  const taggedCount = evidenceItems.filter((item) => (item.tags?.length ?? 0) > 0).length;
  const riskCount = evidenceItems.filter((item) => Boolean(item.metadata_json?.prompt_manipulation_detected)).length;
  const keywordHits = evidenceItems.reduce((sum, item) => {
    const text = `${item.title} ${item.content}`.toLowerCase();
    const keywords = ['提升', '优化', '交付', '上线', '增长', '节省', '自动化', '效率', 'impact', 'improve', 'deliver', 'launch'];
    return sum + keywords.reduce((inner, keyword) => inner + (text.includes(keyword.toLowerCase()) ? 1 : 0), 0);
  }, 0);

  return [
    { label: '置信度', shortLabel: '置信', value: clamp(Math.round(averageConfidence), 0, 100), tone: 'text-[#2958c7]' },
    { label: '信息量', shortLabel: '信息', value: clamp(Math.round(34 + Math.min(averageContentLength, 360) / 5.8), 18, 96), tone: 'text-[#2c6b57]' },
    { label: '覆盖面', shortLabel: '覆盖', value: clamp(28 + uniqueSourceTypes * 18 + Math.round(taggedCount * 6 / Math.max(count, 1)), 20, 96), tone: 'text-[#5a56b2]' },
    { label: '可追溯', shortLabel: '追溯', value: clamp(Math.round(32 + averageMetadataCount * 12), 18, 96), tone: 'text-[#7a5b23]' },
    { label: '影响力', shortLabel: '影响', value: clamp(38 + keywordHits * 4, 24, 96), tone: 'text-[#b24c32]' },
    { label: '安全度', shortLabel: '安全', value: clamp(94 - Math.round((riskCount / Math.max(count, 1)) * 72), 18, 96), tone: 'text-[#9d385f]' },
  ];
}

export function EvidenceWorkspaceOverview({ evidenceItems }: EvidenceWorkspaceOverviewProps) {
  const metrics = buildMetrics(evidenceItems);
  const radarValues = metrics.map((item) => item.value);
  const center = 86;
  const radius = 56;
  const averageScore = Math.round(metrics.reduce((sum, item) => sum + item.value, 0) / metrics.length);
  const riskCount = evidenceItems.filter((item) => Boolean(item.metadata_json?.prompt_manipulation_detected)).length;
  const sourceTypes = new Set(evidenceItems.map((item) => item.source_type)).size;
  const latestEvidence = evidenceItems.length
    ? [...evidenceItems].sort((left, right) => new Date(right.created_at).getTime() - new Date(left.created_at).getTime())[0]
    : null;

  return (
    <section className="sticky top-6 rounded-[28px] border border-[#d7e4fa] bg-[linear-gradient(180deg,rgba(250,252,255,0.98),rgba(243,247,255,0.98))] px-5 py-5 shadow-[0_20px_46px_rgba(15,23,42,0.05)] lg:px-6">
      <div className="border-b border-[#e6eef9] pb-4">
        <p className="eyebrow">证据总览</p>
        <h3 className="mt-2 text-[24px] font-semibold tracking-[-0.03em] text-ink">把雷达图单独看</h3>
        <p className="mt-2 text-sm leading-6 text-steel">先看总览，再看单条证据。</p>
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-3 xl:grid-cols-1">
        <div className="rounded-[22px] border border-white/80 bg-white/82 px-4 py-4">
          <p className="text-xs uppercase tracking-[0.18em] text-[#6f8ecc]">证据数量</p>
          <p className="mt-2 text-[30px] font-semibold tracking-[-0.05em] text-ink">{evidenceItems.length}</p>
        </div>
        <div className="rounded-[22px] border border-white/80 bg-white/82 px-4 py-4">
          <p className="text-xs uppercase tracking-[0.18em] text-[#6f8ecc]">总体评分</p>
          <p className="mt-2 text-[30px] font-semibold tracking-[-0.05em] text-ink">{averageScore}</p>
        </div>
        <div className={`rounded-[22px] border px-4 py-4 ${riskCount > 0 ? 'border-rose-200 bg-rose-50' : 'border-white/80 bg-white/82'}`}>
          <p className="text-xs uppercase tracking-[0.18em] text-[#6f8ecc]">风险证据</p>
          <p className={`mt-2 text-[30px] font-semibold tracking-[-0.05em] ${riskCount > 0 ? 'text-rose-700' : 'text-ink'}`}>{riskCount}</p>
        </div>
      </div>

      <div className="mt-5 rounded-[26px] border border-[#dce6f5] bg-white px-4 py-5">
        <div className="flex items-center justify-between">
          <p className="text-sm font-semibold text-ink">证据雷达</p>
          <span className="text-xs text-steel">6 个维度</span>
        </div>

        <div className="mt-4 flex justify-center">
          <svg
            aria-label="证据总览雷达图"
            className="h-[210px] w-[210px] overflow-visible"
            style={{ fontFamily: '"PingFang SC", "Microsoft YaHei", "Segoe UI", sans-serif' }}
            viewBox="0 0 172 172"
          >
            {[1, 0.75, 0.5, 0.25].map((ratio) => (
              <polygon
                key={ratio}
                fill="none"
                points={gridPolygonPoints(metrics.length, radius * ratio, center)}
                stroke={ratio === 1 ? '#bfd0f6' : '#dbe6fb'}
                strokeWidth={ratio === 1 ? 1.4 : 1}
              />
            ))}
            {metrics.map((metric, index) => {
              const axis = axisEndPoint(index, metrics.length, radius, center);
              return (
                <g key={metric.label}>
                  <line stroke="#d4e0f8" strokeWidth="1" x1={center} x2={axis.x} y1={center} y2={axis.y} />
                  <text
                    fill="#5873a5"
                    fontSize="10"
                    textAnchor={Math.abs(axis.labelX - center) < 8 ? 'middle' : axis.labelX < center ? 'end' : 'start'}
                    x={axis.labelX}
                    y={axis.labelY}
                  >
                    {metric.shortLabel}
                  </text>
                </g>
              );
            })}
            <polygon fill="rgba(55,109,255,0.16)" points={polygonPoints(radarValues, radius, center)} stroke="#376dff" strokeWidth="2.2" />
            {radarValues.map((value, index) => {
              const angle = -Math.PI / 2 + (Math.PI * 2 * index) / radarValues.length;
              const pointRadius = (radius * value) / 100;
              const x = center + Math.cos(angle) * pointRadius;
              const y = center + Math.sin(angle) * pointRadius;
              return <circle key={`${metrics[index].label}-${value}`} cx={x} cy={y} fill="#ffffff" r="4.2" stroke="#376dff" strokeWidth="2" />;
            })}
            <circle cx={center} cy={center} fill="#ffffff" r="18" stroke="#d6e2fa" />
            <text fill="#18305d" fontSize="17" fontWeight="700" textAnchor="middle" x={center} y={center + 6}>{averageScore}</text>
          </svg>
        </div>

        <div className="mt-4 grid gap-2">
          {metrics.map((metric) => (
            <div className="flex items-center justify-between rounded-[18px] border border-[#dce6f5] bg-[#f8fbff] px-3 py-2.5" key={metric.label}>
              <span className="text-sm text-steel">{metric.label}</span>
              <span className={`text-sm font-semibold ${metric.tone}`}>{metric.value}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="mt-5 rounded-[24px] border border-[#dce6f5] bg-white px-4 py-4 text-sm text-steel">
        <div className="flex items-center justify-between gap-4">
          <span>来源类型</span>
          <span className="font-medium text-ink">{sourceTypes} 种</span>
        </div>
        <div className="mt-3 flex items-center justify-between gap-4">
          <span>最近一条</span>
          <span className="max-w-[58%] truncate font-medium text-ink">{latestEvidence?.title ?? '暂无'}</span>
        </div>
      </div>
    </section>
  );
}