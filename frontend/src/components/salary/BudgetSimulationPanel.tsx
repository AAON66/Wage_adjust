interface SimulationEmployee {
  id: string;
  name: string;
  department: string;
  currentSalary: number;
  suggestedIncreaseRate: number;
}

interface BudgetSimulationPanelProps {
  budgetAmount: number;
  recommendedCost: number;
  employees: SimulationEmployee[];
  departmentFilter: string;
  jobFamilyFilter: string;
  onBudgetAmountChange: (value: number) => void;
  onDepartmentFilterChange: (value: string) => void;
  onJobFamilyFilterChange: (value: string) => void;
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('zh-CN', {
    style: 'currency',
    currency: 'CNY',
    maximumFractionDigits: 0,
  }).format(value);
}

export function BudgetSimulationPanel({
  budgetAmount,
  recommendedCost,
  employees,
  departmentFilter,
  jobFamilyFilter,
  onBudgetAmountChange,
  onDepartmentFilterChange,
  onJobFamilyFilterChange,
}: BudgetSimulationPanelProps) {
  const remainingBudget = budgetAmount - recommendedCost;

  return (
    <section className="surface animate-fade-up px-6 py-6 lg:px-7">
      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'flex-start', justifyContent: 'space-between', gap: 16, borderBottom: '1px solid var(--color-border)', paddingBottom: 14, marginBottom: 16 }}>
        <div>
          <p className="eyebrow">Simulation</p>
          <h2 className="mt-2 text-[24px] font-semibold tracking-[-0.03em] text-ink">调薪建议沙盘</h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-steel">调整筛选条件和预算假设，快速比较当前建议方案和评估周期可用预算之间的差异。</p>
        </div>
        <div className="surface-subtle px-5 py-4 text-right">
          <p className="text-sm text-steel">剩余预算</p>
          <p style={{ marginTop: 8, fontSize: 26, fontWeight: 600, letterSpacing: '-0.03em', color: remainingBudget >= 0 ? 'var(--color-success)' : 'var(--color-danger)' }}>
            {formatCurrency(remainingBudget)}
          </p>
        </div>
      </div>

      <div className="mt-5 grid gap-3 md:grid-cols-3">
        <label className="surface-subtle px-4 py-4">
          <span className="text-sm text-steel">周期预算</span>
          <input className="toolbar-input mt-3 w-full" min={0} onChange={(event) => onBudgetAmountChange(Number(event.target.value))} type="number" value={budgetAmount} />
        </label>
        <label className="surface-subtle px-4 py-4">
          <span className="text-sm text-steel">部门筛选</span>
          <input className="toolbar-input mt-3 w-full" onChange={(event) => onDepartmentFilterChange(event.target.value)} placeholder="例如：研发中心" value={departmentFilter} />
        </label>
        <label className="surface-subtle px-4 py-4">
          <span className="text-sm text-steel">岗位族筛选</span>
          <input className="toolbar-input mt-3 w-full" onChange={(event) => onJobFamilyFilterChange(event.target.value)} placeholder="例如：平台研发" value={jobFamilyFilter} />
        </label>
      </div>

      <div className="mt-5 grid gap-3 md:grid-cols-3">
        {[
          ['建议总额', formatCurrency(recommendedCost), '当前筛选范围内的建议调薪总额。'],
          ['预算金额', formatCurrency(budgetAmount), '本次模拟采用的预算假设。'],
          ['模拟人数', `${employees.length} 人`, '当前纳入模拟计算的员工数。'],
        ].map(([label, value, note]) => (
          <div className="metric-tile" key={label}>
            <p className="metric-label">{label}</p>
            <p className="metric-value text-[26px]">{value}</p>
            <p className="metric-note">{note}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
