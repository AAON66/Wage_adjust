interface TierChipProps {
  /** 圆点 + 边框颜色（hex） */
  color: string;
  label: string;
  count: number;
  /** 0–1 的小数 */
  pct: number;
}

interface UnTieredChipProps {
  count: number;
}

/**
 * Phase 34 UI-SPEC §6.4：单档计数 chip。
 * 不可点击（用 `<span>` 替换 `<button>`），无 hover 态。
 */
export function TierChip({ color, label, count, pct }: TierChipProps) {
  return (
    <span
      className="status-pill"
      style={{
        padding: '4px 10px',
        fontSize: 13,
        background: '#FFFFFF',
        border: `1px solid ${color}`,
        color: 'var(--color-ink)',
        gap: 6,
      }}
    >
      <span
        style={{
          display: 'inline-block',
          width: 8,
          height: 8,
          borderRadius: '50%',
          background: color,
          flexShrink: 0,
          marginRight: 4,
        }}
      />
      {label} <strong style={{ fontWeight: 600, marginLeft: 4 }}>{count}</strong> 人 ({(pct * 100).toFixed(0)}%)
    </span>
  );
}

/** 未分档 chip（边框 + 圆点用 placeholder/border 灰，与三档区分） */
export function UnTieredChip({ count }: UnTieredChipProps) {
  return (
    <span
      className="status-pill"
      style={{
        padding: '4px 10px',
        fontSize: 13,
        background: '#FFFFFF',
        border: '1px solid var(--color-border)',
        color: 'var(--color-ink)',
        gap: 6,
      }}
    >
      <span
        style={{
          display: 'inline-block',
          width: 8,
          height: 8,
          borderRadius: '50%',
          background: 'var(--color-placeholder)',
          flexShrink: 0,
          marginRight: 4,
        }}
      />
      未分档 <strong style={{ fontWeight: 600, marginLeft: 4 }}>{count}</strong> 人
    </span>
  );
}
