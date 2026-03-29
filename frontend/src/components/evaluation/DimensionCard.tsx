import { DIMENSION_LABELS } from '../../utils/dimensionConstants';

interface DimensionCardProps {
  dimensionCode: string;
  rawScore: number;
  weight: number;
  rationale: string;
}

export function DimensionCard({ dimensionCode, rawScore, weight, rationale }: DimensionCardProps) {
  const label = DIMENSION_LABELS[dimensionCode] ?? dimensionCode;
  const weightPct = Math.round(weight * 100);

  return (
    <div className="surface-subtle" style={{ padding: '16px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: 15, fontWeight: 600, color: 'var(--color-ink)' }}>
          {label}
        </span>
        <span style={{ fontSize: 13, color: 'var(--color-steel)' }}>
          得分 {rawScore} &middot; 权重 {weightPct}%
        </span>
      </div>
      <p style={{ marginTop: 8, fontSize: 13, color: 'var(--color-steel)', lineHeight: 1.5 }}>
        {rationale}
      </p>
    </div>
  );
}
