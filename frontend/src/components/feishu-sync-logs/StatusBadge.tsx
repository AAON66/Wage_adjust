import type { SyncLogStatus } from '../../types/api';

interface StatusBadgeProps {
  status: SyncLogStatus;
}

const STATUS_MAP: Record<SyncLogStatus, { label: string; color: string; bg: string }> = {
  success: { label: '成功', color: 'var(--color-success)', bg: 'var(--color-success-bg)' },
  partial: { label: '部分成功', color: 'var(--color-warning)', bg: 'var(--color-warning-bg)' },
  failed: { label: '失败', color: 'var(--color-danger)', bg: 'var(--color-danger-bg)' },
  running: { label: '同步中', color: 'var(--color-info)', bg: 'var(--color-info-bg)' },
};

export function StatusBadge({ status }: StatusBadgeProps) {
  const { label, color, bg } = STATUS_MAP[status];
  return (
    <span
      className="inline-flex items-center gap-1 rounded px-2 py-0.5 text-xs font-semibold"
      style={{ color, background: bg }}
    >
      {status === 'running' ? (
        <span
          aria-hidden
          className="inline-block h-3 w-3 animate-spin rounded-full"
          style={{
            border: `2px solid ${color}`,
            borderTopColor: 'transparent',
          }}
        />
      ) : null}
      {label}
    </span>
  );
}
