import { useEffect } from 'react';
import type { SyncLogRead } from '../../types/api';

interface SyncLogDetailDrawerProps {
  open: boolean;
  log: SyncLogRead | null;
  onClose: () => void;
}

export function SyncLogDetailDrawer({ open, log, onClose }: SyncLogDetailDrawerProps) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  if (!open || !log) return null;

  const logIdShort = log.id.slice(0, 8);

  return (
    <>
      <div
        onClick={onClose}
        className="fixed inset-0 z-40"
        style={{ background: 'rgba(0,0,0,0.4)' }}
      />
      <aside
        role="dialog"
        aria-modal="true"
        aria-labelledby={`drawer-title-${log.id}`}
        className="fixed right-0 top-0 z-50 h-full overflow-y-auto shadow-xl"
        style={{ width: '480px', background: 'var(--color-bg-surface)' }}
      >
        <div
          className="px-5 py-4"
          style={{
            borderBottom: '1px solid var(--color-border)',
            borderLeft: '4px solid var(--color-primary)',
          }}
        >
          <h2
            id={`drawer-title-${log.id}`}
            className="text-base font-semibold"
            style={{ color: 'var(--color-ink)' }}
          >
            同步明细 #{logIdShort}
          </h2>
        </div>
        <div
          className="px-5 py-4 space-y-4 text-sm"
          style={{ color: 'var(--color-ink)' }}
        >
          {log.leading_zero_fallback_count > 0 && (
            <div style={{ color: 'var(--color-warning)' }}>
              {log.leading_zero_fallback_count} 条记录通过前导零容忍匹配成功，建议排查飞书源数据格式
            </div>
          )}
          {log.error_message && (
            <div>
              <div
                className="text-xs font-semibold"
                style={{ color: 'var(--color-steel)' }}
              >
                错误信息
              </div>
              <pre
                className="whitespace-pre-wrap text-sm"
                style={{ color: 'var(--color-danger)' }}
              >
                {log.error_message}
              </pre>
            </div>
          )}
          <div>
            <div
              className="text-xs font-semibold"
              style={{ color: 'var(--color-steel)' }}
            >
              未匹配工号
            </div>
            {log.unmatched_employee_nos && log.unmatched_employee_nos.length > 0 ? (
              <ul className="mt-1 list-disc pl-5">
                {log.unmatched_employee_nos.map((no) => (
                  <li key={no}>{no}</li>
                ))}
              </ul>
            ) : (
              <div style={{ color: 'var(--color-steel)' }}>本次同步无未匹配工号</div>
            )}
          </div>
          {log.status === 'partial' && (
            <div className="text-xs" style={{ color: 'var(--color-steel)' }}>
              同步完成但存在未匹配 / 映射失败 / 写库失败条目，请点击详情查看根因。
            </div>
          )}
        </div>
      </aside>
    </>
  );
}
