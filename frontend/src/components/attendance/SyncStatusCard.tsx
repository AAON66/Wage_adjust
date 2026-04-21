import type { SyncLogRead } from '../../types/api';

interface SyncStatusCardProps {
  syncStatus: SyncLogRead | null;
  onRefresh: () => void;
}

function formatSyncTime(isoString: string | null): string {
  if (!isoString) return '--';
  const d = new Date(isoString);
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  const hours = String(d.getHours()).padStart(2, '0');
  const minutes = String(d.getMinutes()).padStart(2, '0');
  return `${year}-${month}-${day} ${hours}:${minutes}`;
}

type StatusStyle = {
  bg: string;
  color: string;
  label: string;
};

function getStatusStyle(status: string | undefined): StatusStyle {
  switch (status) {
    case 'success':
      return { bg: 'var(--color-success-bg, #E8FFEA)', color: 'var(--color-success, #00B42A)', label: '成功' };
    case 'running':
      return { bg: 'var(--color-info-bg, #EBF0FE)', color: 'var(--color-info, #1456F0)', label: '同步中' };
    case 'failed':
      return { bg: 'var(--color-danger-bg, #FFECE8)', color: 'var(--color-danger, #F53F3F)', label: '失败' };
    default:
      return { bg: 'var(--color-bg-subtle)', color: 'var(--color-placeholder)', label: '未配置' };
  }
}

export function SyncStatusCard({ syncStatus, onRefresh }: SyncStatusCardProps) {
  const style = getStatusStyle(syncStatus?.status);
  const syncTime = syncStatus?.finished_at ?? syncStatus?.started_at ?? null;

  return (
    <div className="surface px-5 py-4" aria-live="polite">
      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
        <div>
          <p className="section-title" style={{ fontSize: 15, fontWeight: 600 }}>同步状态</p>
          <div className="mt-2" style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 12, fontSize: 13.5 }}>
            <span style={{ color: 'var(--color-steel)' }}>
              上次同步：{formatSyncTime(syncTime)}
            </span>
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 6,
                padding: '2px 10px',
                borderRadius: 12,
                fontSize: 12,
                fontWeight: 600,
                background: style.bg,
                color: style.color,
              }}
            >
              {syncStatus?.status === 'running' ? (
                <span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%', border: '2px solid currentColor', borderTopColor: 'transparent', animation: 'spin 0.8s linear infinite' }} />
              ) : null}
              {style.label}
            </span>
            {syncStatus && syncStatus.status === 'success' ? (
              <span style={{ color: 'var(--color-steel)', fontSize: 13 }}>
                同步 {syncStatus.synced_count} / {syncStatus.total_fetched} 条记录
              </span>
            ) : null}
          </div>
          {syncStatus?.status === 'failed' && syncStatus.error_message ? (
            <p className="mt-2 text-sm" style={{ color: 'var(--color-danger)' }}>
              {syncStatus.error_message}
            </p>
          ) : null}
          {syncStatus && syncStatus.unmatched_count > 0 ? (
            <p className="mt-2 text-sm" style={{ color: 'var(--color-warning, #FF7D00)' }} title={syncStatus.unmatched_employee_nos?.slice(0, 5).join(', ') ?? ''}>
              {syncStatus.unmatched_count} 条记录因工号不匹配被跳过
            </p>
          ) : null}
          {syncStatus && syncStatus.leading_zero_fallback_count > 0 ? (
            <p className="mt-2 text-sm" style={{ color: 'var(--color-warning, #FF7D00)' }}>
              {syncStatus.leading_zero_fallback_count} 条记录通过前导零容忍匹配成功，建议排查飞书源数据格式
            </p>
          ) : null}
        </div>
        <button className="chip-button" onClick={onRefresh} type="button">
          刷新状态
        </button>
      </div>
    </div>
  );
}
