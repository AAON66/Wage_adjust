import { Link } from 'react-router-dom';

export function SyncLogsEmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <div
        className="text-base font-semibold"
        style={{ color: 'var(--color-ink)' }}
      >
        暂无同步日志
      </div>
      <p
        className="mt-2 max-w-md text-sm"
        style={{ color: 'var(--color-steel)' }}
      >
        HR 触发飞书同步后，每次执行的结果会在此列出。可前往「飞书配置」页面手动触发一次同步。
      </p>
      <Link
        to="/feishu-config"
        className="mt-4 inline-flex items-center rounded border px-3 py-1.5 text-sm"
        style={{
          borderColor: 'var(--color-border)',
          color: 'var(--color-ink)',
        }}
      >
        前往飞书配置
      </Link>
    </div>
  );
}
