interface SalaryResultCardProps {
  adjustmentRatio: number;
}

export function SalaryResultCard({ adjustmentRatio }: SalaryResultCardProps) {
  const pct = adjustmentRatio * 100;
  const sign = pct >= 0 ? '+' : '';
  const formatted = `${sign}${pct.toFixed(2)}%`;

  return (
    <div className="surface" style={{ padding: '24px' }}>
      <div
        style={{
          fontSize: 12,
          fontWeight: 600,
          letterSpacing: '0.10em',
          textTransform: 'uppercase',
          color: 'var(--color-primary)',
          marginBottom: 4,
        }}
      >
        调薪建议
      </div>
      <div style={{ fontSize: 15, fontWeight: 600, color: 'var(--color-ink)', marginBottom: 12 }}>
        最终调薪幅度
      </div>
      <div
        style={{
          fontSize: 26,
          fontWeight: 600,
          letterSpacing: '-0.02em',
          color: 'var(--color-primary)',
          marginBottom: 8,
        }}
      >
        {formatted}
      </div>
      <p style={{ fontSize: 13, color: 'var(--color-steel)' }}>
        以下为审批通过后的最终调整比例。
      </p>
    </div>
  );
}
