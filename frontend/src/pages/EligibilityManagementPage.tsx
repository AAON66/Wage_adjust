import { useState } from 'react';

import { EligibilityListTab } from '../components/eligibility/EligibilityListTab';
import { OverrideRequestsTab } from '../components/eligibility/OverrideRequestsTab';
import { ImportTabContent } from '../components/eligibility-import/ImportTabContent';
import { AppShell } from '../components/layout/AppShell';
import type { EligibilityImportType } from '../services/eligibilityImportService';

type TabKey = 'list' | 'overrides' | 'performance_grades' | 'salary_adjustments' | 'hire_info' | 'non_statutory_leave';

const IMPORT_TAB_KEYS: EligibilityImportType[] = ['performance_grades', 'salary_adjustments', 'hire_info', 'non_statutory_leave'];

const TABS: Array<{ key: TabKey; label: string }> = [
  { key: 'list', label: '调薪资格' },
  { key: 'overrides', label: '特殊申请' },
  { key: 'performance_grades', label: '绩效等级' },
  { key: 'salary_adjustments', label: '调薪历史' },
  { key: 'hire_info', label: '入职信息' },
  { key: 'non_statutory_leave', label: '非法定假期' },
];

function isImportTab(key: TabKey): key is EligibilityImportType {
  return (IMPORT_TAB_KEYS as string[]).includes(key);
}

export function EligibilityManagementPage() {
  const [activeTab, setActiveTab] = useState<TabKey>('list');

  const activeTabMeta = TABS.find((t) => t.key === activeTab);

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
        {isImportTab(activeTab) && activeTabMeta && (
          <ImportTabContent importType={activeTab} label={activeTabMeta.label} />
        )}
      </div>
    </AppShell>
  );
}
