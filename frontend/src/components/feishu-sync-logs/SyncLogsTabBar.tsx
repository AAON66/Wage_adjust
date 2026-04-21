import type { SyncLogSyncType } from '../../types/api';

export type TabKey = 'all' | SyncLogSyncType;

interface SyncLogsTabBarProps {
  activeTab: TabKey;
  onChange: (tab: TabKey) => void;
}

const TAB_ITEMS: { key: TabKey; label: string }[] = [
  { key: 'all', label: '全部' },
  { key: 'attendance', label: '考勤' },
  { key: 'performance', label: '绩效' },
  { key: 'salary_adjustments', label: '薪调' },
  { key: 'hire_info', label: '入职信息' },
  { key: 'non_statutory_leave', label: '社保假勤' },
];

export function SyncLogsTabBar({ activeTab, onChange }: SyncLogsTabBarProps) {
  return (
    <div
      role="tablist"
      className="flex items-center gap-2"
      style={{ borderBottom: '1px solid var(--color-border)' }}
    >
      {TAB_ITEMS.map((item) => {
        const active = item.key === activeTab;
        return (
          <button
            key={item.key}
            type="button"
            role="tab"
            aria-selected={active}
            onClick={() => onChange(item.key)}
            className="px-3 py-2 text-sm font-medium transition-colors"
            style={{
              color: active ? 'var(--color-primary)' : 'var(--color-steel)',
              borderBottom: active
                ? '2px solid var(--color-primary)'
                : '2px solid transparent',
              background: 'transparent',
            }}
          >
            {item.label}
          </button>
        );
      })}
    </div>
  );
}
