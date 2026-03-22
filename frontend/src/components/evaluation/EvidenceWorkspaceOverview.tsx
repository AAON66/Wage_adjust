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
    { label: '置信度', shortLabel: '置信', value: clamp(Math.round(averageConfidence), 0, 100), tone: 'var(--color-primary)' },
    { label: '信息量', shortLabel: '信息', value: clamp(Math.round(34 + Math.min(averageContentLength, 360) / 5.8), 18, 96), tone: 'var(--color-success)' },
    { label: '覆盖面', shortLabel: '覆盖', value: clamp(28 + uniqueSourceTypes * 18 + Math.round(taggedCount * 6 / Math.max(count, 1)), 20, 96), tone: '#7C3AED' },
    { label: '可追溯', shortLabel: '追溯', value: clamp(Math.round(32 + averageMetadataCount * 12), 18, 96), tone: 'var(--color-warning)' },
    { label: '影响力', shortLabel: '影响', value: clamp(38 + keywordHits * 4, 24, 96), tone: '#EA580C' },
    { label: '安全度', shortLabel: '安全', value: clamp(94 - Math.round((riskCount / Math.max(count, 1)) * 72), 18, 96), tone: riskCount > 0 ? 'var(--color-danger)' : 'var(--color-success)' },
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
    ? [...evidenceItems].sort((l, r) => new Date(r.created_at).getTime() - new Date(l.created_at).getTime())[0]
    : null;

  return (
    <section style={{ position: 'sticky', top: 24, background: '#FFFFFF', border: '1px solid var(--color-border)', borderRadius: 8, padding: '16px 20px', boxShadow: 'var(--shadow-card)' }}>
      <div style={{ borderBottom: '1px solid var(--color-border)', paddingBottom: 12, marginBottom: 16 }}>
        <p className="eyebrow">证据总览</p>
        <h3 style={{ marginTop: 4, fontSize: 15, fontWeight: 600, color: 'var(--color-ink)' }}>证据雷达</h3>
        <p style={{ marginTop: 4, fontSize: 13, color: 'var(--color-steel)' }}>先看总览，再看单条证据。</p>
      </div>

      {/* Stats */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8, marginBottom: 16 }}>
        <div style={{ background: 'var(--color-bg-subtle)', border: '1px solid var(--color-border)', borderRadius: 6, padding: '10px 12px' }}>
          <p style={{ fontSize: 11, color: 'var(--color-steel)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>证据数</p>
          <p style={{ marginTop: 4, fontSize: 22, fontWeight: 600, color: 'var(--color-ink)' }}>{evidenceItems.length}</p>
        </div>
        <div style={{ background: 'var(--color-bg-subtle)', border: '1px solid var(--color-border)', borderRadius: 6, padding: '10px 12px' }}>
          <p style={{ fontSize: 11, color: 'var(--color-steel)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>总体评分</p>
          <p style={{ marginTop: 4, fontSize: 22, fontWeight: 600, color: 'var(--color-ink)' }}>{averageScore}</p>
        </div>
        <div style={{ background: riskCount > 0 ? 'var(--color-danger-bg)' : 'var(--color-bg-subtle)', border: `1px solid ${riskCount > 0 ? '#FFCDD0' : 'var(--color-border)'}`, borderRadius: 6, padding: '10px 12px' }}>
          <p style={{ fontSize: 11, color: 'var(--color-steel)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>风险证据</p>
          <p style={{ marginTop: 4, fontSize: 22, fontWeight: 600, color: riskCount > 0 ? 'var(--color-danger)' : 'var(--color-ink)' }}>{riskCount}</p>
        </div>
      </div>

      {/* Radar */}
      <div style={{ background: 'var(--color-bg-subtle)', border: '1px solid var(--color-border)', borderRadius: 6, padding: '14px 16px', marginBottom: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
          <p style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-ink)' }}>六维雷达</p>
          <span style={{ fontSize: 12, color: 'var(--color-steel)' }}>6 个维度</span>
        </div>

        <div style={{ display: 'flex', justifyContent: 'center' }}>
          <svg
            aria-label="证据总览雷达图"
            style={{ height: 200, width: 200, overflow: 'visible', fontFamily: '"PingFang SC", "Microsoft YaHei", sans-serif' }}
            viewBox="0 0 172 172"
          >
            {[1, 0.75, 0.5, 0.25].map((ratio) => (
              <polygon
                key={ratio}
                fill="none"
                points={gridPolygonPoints(metrics.length, radius * ratio, center)}
                stroke={ratio === 1 ? 'var(--color-border-strong)' : 'var(--color-border)'}
                strokeWidth={ratio === 1 ? 1.2 : 0.8}
              />
            ))}
            {metrics.map((metric, index) => {
              const axis = axisEndPoint(index, metrics.length, radius, center);
              return (
                <g key={metric.label}>
                  <line stroke="var(--color-border)" strokeWidth="1" x1={center} x2={axis.x} y1={center} y2={axis.y} />
                  <text
                    fill="var(--color-steel)"
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
            <polygon fill="rgba(20,86,240,0.1)" points={polygonPoints(radarValues, radius, center)} stroke="#1456F0" strokeWidth="2" />
            {radarValues.map((value, index) => {
              const angle = -Math.PI / 2 + (Math.PI * 2 * index) / radarValues.length;
              const pointRadius = (radius * value) / 100;
              const x = center + Math.cos(angle) * pointRadius;
              const y = center + Math.sin(angle) * pointRadius;
              return <circle key={`${metrics[index].label}-${value}`} cx={x} cy={y} fill="#ffffff" r="3.5" stroke="#1456F0" strokeWidth="1.8" />;
            })}
            <circle cx={center} cy={center} fill="#ffffff" r="18" stroke="var(--color-border)" />
            <text fill="var(--color-ink)" fontSize="16" fontWeight="700" textAnchor="middle" x={center} y={center + 6}>{averageScore}</text>
          </svg>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 4, marginTop: 8 }}>
          {metrics.map((metric) => (
            <div key={metric.label} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '5px 8px', background: '#FFFFFF', borderRadius: 4, fontSize: 13 }}>
              <span style={{ color: 'var(--color-steel)' }}>{metric.label}</span>
              <span style={{ fontWeight: 600, color: metric.tone }}>{metric.value}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Footer info */}
      <div style={{ background: 'var(--color-bg-subtle)', border: '1px solid var(--color-border)', borderRadius: 6, padding: '10px 14px', fontSize: 13, color: 'var(--color-steel)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span>来源类型</span>
          <span style={{ fontWeight: 500, color: 'var(--color-ink)' }}>{sourceTypes} 种</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 8 }}>
          <span>最近一条</span>
          <span style={{ maxWidth: '58%', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontWeight: 500, color: 'var(--color-ink)' }}>
            {latestEvidence?.title ?? '暂无'}
          </span>
        </div>
      </div>
    </section>
  );
}
