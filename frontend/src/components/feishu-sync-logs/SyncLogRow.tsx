import type { SyncLogRead, SyncLogSyncType } from '../../types/api';
import { CountersBadgeCluster } from './CountersBadgeCluster';
import { StatusBadge } from './StatusBadge';

const SYNC_TYPE_LABEL: Record<SyncLogSyncType, string> = {
  attendance: '考勤',
  performance: '绩效',
  salary_adjustments: '薪调',
  hire_info: '入职信息',
  non_statutory_leave: '社保假勤',
};

function formatTime(iso: string): string {
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function formatDuration(startedAt: string, finishedAt: string | null): string {
  if (!finishedAt) return '—';
  const start = new Date(startedAt).getTime();
  const end = new Date(finishedAt).getTime();
  const seconds = Math.max(0, Math.round((end - start) / 1000));
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  return `${minutes}m${seconds % 60}s`;
}

interface SyncLogRowProps {
  log: SyncLogRead;
  onOpenDetail: (log: SyncLogRead) => void;
  onDownloadCsv: (log: SyncLogRead) => void;
  isDownloadingCsv?: boolean;
}

export function SyncLogRow({
  log,
  onOpenDetail,
  onDownloadCsv,
  isDownloadingCsv,
}: SyncLogRowProps) {
  const canDownload = log.unmatched_count > 0;
  return (
    <tr style={{ borderBottom: '1px solid var(--color-border)' }}>
      <td className="px-3 py-3 text-sm" style={{ color: 'var(--color-ink)' }}>
        {SYNC_TYPE_LABEL[log.sync_type]}
      </td>
      <td className="px-3 py-3 text-sm">
        <StatusBadge status={log.status} />
      </td>
      <td className="px-3 py-3 text-sm" style={{ color: 'var(--color-steel)' }}>
        {log.sync_type === 'attendance' ? (
          <span
            className="inline-flex items-center rounded px-2 py-0.5 text-xs font-semibold"
            style={{
              color: 'var(--color-ink)',
              background: 'var(--color-bg-subtle)',
            }}
          >
            {log.mode === 'incremental' ? '增量' : '全量'}
          </span>
        ) : (
          <span style={{ color: 'var(--color-placeholder)' }}>—</span>
        )}
      </td>
      <td className="px-3 py-3">
        <CountersBadgeCluster
          success={log.synced_count}
          updated={log.updated_count}
          unmatched={log.unmatched_count}
          mappingFailed={log.mapping_failed_count}
          failed={log.failed_count}
          onBadgeClick={() => onOpenDetail(log)}
        />
      </td>
      <td className="px-3 py-3 text-sm" style={{ color: 'var(--color-steel)' }}>
        {formatTime(log.started_at)}
      </td>
      <td className="px-3 py-3 text-sm" style={{ color: 'var(--color-steel)' }}>
        {formatDuration(log.started_at, log.finished_at)}
      </td>
      <td className="px-3 py-3 text-sm" style={{ color: 'var(--color-steel)' }}>
        {log.triggered_by ?? '系统'}
      </td>
      <td className="px-3 py-3 text-sm">
        <button
          type="button"
          onClick={() => {
            if (canDownload) onDownloadCsv(log);
          }}
          disabled={!canDownload || isDownloadingCsv}
          title={!canDownload ? '本次同步无未匹配工号，无需下载' : undefined}
          className="mr-3 underline"
          style={{
            color: canDownload ? 'var(--color-primary)' : 'var(--color-placeholder)',
            cursor: canDownload ? 'pointer' : 'not-allowed',
            background: 'transparent',
            border: 'none',
            padding: 0,
          }}
        >
          下载未匹配工号 CSV
        </button>
        <button
          type="button"
          onClick={() => onOpenDetail(log)}
          className="underline"
          style={{
            color: 'var(--color-primary)',
            background: 'transparent',
            border: 'none',
            padding: 0,
            cursor: 'pointer',
          }}
        >
          查看详情
        </button>
      </td>
    </tr>
  );
}
