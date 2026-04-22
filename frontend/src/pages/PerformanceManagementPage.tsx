import { AppShell } from '../components/layout/AppShell';

/**
 * Phase 34 D-13：HR 独立「绩效管理」页面占位 stub。
 * Task 2 / Task 3 会用真实的 3 section（档次分布 / 绩效记录导入 / 绩效记录列表）替换此 stub。
 */
export function PerformanceManagementPage() {
  return (
    <AppShell
      title="绩效管理"
      description="HR 端：导入绩效记录、查看档次分布、手动触发档次重算"
    >
      <div className="surface" style={{ padding: 24 }}>
        <p className="section-note">页面框架就绪，组件 Wave 3 后续 Task 接入。</p>
      </div>
    </AppShell>
  );
}
