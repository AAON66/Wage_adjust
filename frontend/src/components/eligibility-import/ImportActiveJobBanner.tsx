import type { ActiveJobResponse } from '../../types/api';

interface ImportActiveJobBannerProps {
  activeJob: ActiveJobResponse;
}

const STATUS_LABELS: Record<NonNullable<ActiveJobResponse['status']>, string> = {
  previewing: '预览待确认',
  processing: '落库中',
};

/**
 * D-18 + UI-SPEC §「并发锁与 409 提示」
 *
 * Tab 顶部活跃 job 提示条：当 GET /excel/active 返回 active=true 时显示。
 * 提示 HR 当前类型导入正在进行，建议等待或查看进度。
 *
 * 文案不暴露内部 status 字面量（previewing/processing），只展示中文标签。
 */
export function ImportActiveJobBanner({ activeJob }: ImportActiveJobBannerProps) {
  if (!activeJob.active || !activeJob.status) return null;
  const statusLabel = STATUS_LABELS[activeJob.status];
  const startedAt = activeJob.created_at
    ? new Date(activeJob.created_at).toLocaleString('zh-CN')
    : '';
  return (
    <div
      role="status"
      style={{
        background: 'var(--color-warning-bg)',
        color: 'var(--color-warning)',
        border: '1px solid var(--color-warning)',
        borderRadius: 8,
        padding: '8px 12px',
        fontSize: 14,
        marginBottom: 16,
      }}
    >
      <strong>该类型导入正在进行中</strong>（{statusLabel}
      {startedAt && `，开始于 ${startedAt}`}
      {activeJob.file_name && `，文件：${activeJob.file_name}`}
      ）。请等待完成，或在「同步日志」查看进度。
    </div>
  );
}
