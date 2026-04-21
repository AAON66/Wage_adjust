export type BadgeKey = 'success' | 'updated' | 'unmatched' | 'mapping_failed' | 'failed';

interface CountersBadgeClusterProps {
  success: number;
  updated: number;
  unmatched: number;
  mappingFailed: number;
  failed: number;
  onBadgeClick?: (key: BadgeKey) => void;
}

interface BadgeDef {
  key: BadgeKey;
  label: string;
  color: string;
  bg: string;
}

const BADGES: BadgeDef[] = [
  { key: 'success', label: '成功', color: 'var(--color-success)', bg: 'var(--color-success-bg)' },
  { key: 'updated', label: '更新', color: 'var(--color-info)', bg: 'var(--color-info-bg)' },
  { key: 'unmatched', label: '未匹配', color: 'var(--color-warning)', bg: 'var(--color-warning-bg)' },
  { key: 'mapping_failed', label: '映射失败', color: 'var(--color-violet)', bg: 'var(--color-violet-bg)' },
  { key: 'failed', label: '写库失败', color: 'var(--color-danger)', bg: 'var(--color-danger-bg)' },
];

export function CountersBadgeCluster({
  success,
  updated,
  unmatched,
  mappingFailed,
  failed,
  onBadgeClick,
}: CountersBadgeClusterProps) {
  const values: Record<BadgeKey, number> = {
    success,
    updated,
    unmatched,
    mapping_failed: mappingFailed,
    failed,
  };
  return (
    <div className="flex items-center gap-2">
      {BADGES.map((badge) => {
        const value = values[badge.key];
        const muted = value === 0;
        const style = muted
          ? { color: 'var(--color-placeholder)', background: 'var(--color-bg-subtle)' }
          : { color: badge.color, background: badge.bg };
        return (
          <button
            key={badge.key}
            type="button"
            role="button"
            tabIndex={0}
            aria-label={`查看${badge.label} ${value} 条明细`}
            title={muted ? `${badge.label}类计数为 0` : undefined}
            onClick={() => {
              if (!muted) onBadgeClick?.(badge.key);
            }}
            className="flex items-center gap-1 rounded px-2 py-1 text-xs font-semibold transition-opacity"
            style={{
              ...style,
              cursor: muted ? 'default' : 'pointer',
              opacity: muted ? 0.7 : 1,
              border: 'none',
            }}
          >
            <span>{badge.label}</span>
            <span>{value}</span>
          </button>
        );
      })}
    </div>
  );
}
