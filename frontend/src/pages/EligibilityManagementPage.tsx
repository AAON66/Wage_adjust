import { useState } from 'react';

import { EligibilityListTab } from '../components/eligibility/EligibilityListTab';
import { OverrideRequestsTab } from '../components/eligibility/OverrideRequestsTab';
import { AppShell } from '../components/layout/AppShell';

type TabKey = 'list' | 'overrides';

const TABS: Array<{ key: TabKey; label: string }> = [
  { key: 'list', label: '调薪资格' },
  { key: 'overrides', label: '特殊申请' },
];

export function EligibilityManagementPage() {
  const [activeTab, setActiveTab] = useState<TabKey>('list');

  return (
    <AppShell
      title="调薪资格管理"
      description="查看员工调薪资格状态、筛选导出，以及处理特殊审批申请。"
    >
      <div className="space-y-5">
        <nav className="flex gap-1 border-b" style={{ borderColor: 'var(--color-border)' }}>
          {TABS.map((tab) => (
            <button
              key={tab.key}
              className="px-4 py-2.5 text-sm font-medium transition-colors"
              style={{
                color: activeTab === tab.key ? 'var(--color-primary)' : 'var(--color-steel)',
                borderBottom: activeTab === tab.key ? '2px solid var(--color-primary)' : '2px solid transparent',
              }}
              onClick={() => setActiveTab(tab.key)}
              type="button"
            >
              {tab.label}
            </button>
          ))}
        </nav>

        {activeTab === 'list' && <EligibilityListTab />}
        {activeTab === 'overrides' && <OverrideRequestsTab />}
      </div>
    </AppShell>
  );
}
