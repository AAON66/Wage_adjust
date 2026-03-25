interface SimulationEmployee {
  id: string;
  name: string;
  department: string;
  currentSalary: number;
  suggestedIncreaseRate: number;
}

interface BudgetSimulationPanelProps {
  budgetInput: string;
  effectiveBudget: number;
  recommendedCost: number;
  employees: SimulationEmployee[];
  departmentFilter: string;
  jobFamilyFilter: string;
  scopedDepartments?: string[];
  isDepartmentScoped?: boolean;
  onBudgetAmountChange: (value: string) => void;
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
  budgetInput,
  effectiveBudget,
  recommendedCost,
  employees,
  departmentFilter,
  jobFamilyFilter,
  scopedDepartments = [],
  isDepartmentScoped = false,
  onBudgetAmountChange,
  onDepartmentFilterChange,
  onJobFamilyFilterChange,
}: BudgetSimulationPanelProps) {
  const remainingBudget = effectiveBudget - recommendedCost;
  const isUsingCycleBudget = budgetInput.trim() === '';
  const usageRate = effectiveBudget > 0 ? recommendedCost / effectiveBudget : 0;

  return (
    <section className="surface animate-fade-up px-6 py-6 lg:px-7">
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          gap: 16,
          borderBottom: '1px solid var(--color-border)',
          paddingBottom: 14,
          marginBottom: 16,
        }}
      >
        <div>
          <p className="eyebrow">Simulation</p>
          <h2 className="mt-2 text-[24px] font-semibold tracking-[-0.03em] text-ink">调薪建议沙盘</h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-steel">
            调整筛选条件和预算假设，快速比较当前建议方案和评估周期可用预算之间的差异。未手动输入预算时，会自动采用周期预算或部门分配预算。
          </p>
        </div>
        <div className="surface-subtle px-5 py-4 text-right">
          <p className="text-sm text-steel">剩余预算</p>
          <p
            style={{
              marginTop: 8,
              fontSize: 26,
              fontWeight: 600,
              letterSpacing: '-0.03em',
              color: remainingBudget >= 0 ? 'var(--color-success)' : 'var(--color-danger)',
            }}
          >
            {formatCurrency(remainingBudget)}
          </p>
          <p className="mt-2 text-xs text-steel">预算使用率 {(Math.min(Math.max(usageRate * 100, 0), 999)).toFixed(1)}%</p>
        </div>
      </div>

      <div className="mt-5 grid gap-3 md:grid-cols-3">
        <label className="surface-subtle px-4 py-4">
          <span className="text-sm text-steel">预算覆盖值</span>
          <input
            className="toolbar-input mt-3 w-full"
            min={0}
            onChange={(event) => onBudgetAmountChange(event.target.value)}
            placeholder="留空则使用周期/部门预算"
            type="number"
            value={budgetInput}
          />
          <p className="mt-3 text-xs leading-5 text-steel">
            {isUsingCycleBudget ? '当前使用系统自动预算。若周期配置了部门预算，筛选部门后会自动带入该部门预算。' : '当前使用你手动输入的预算覆盖值。'}
          </p>
        </label>
        <label className="surface-subtle px-4 py-4">
          <span className="text-sm text-steel">部门筛选</span>
          {isDepartmentScoped ? (
            <select className="toolbar-input mt-3 w-full" onChange={(event) => onDepartmentFilterChange(event.target.value)} value={departmentFilter}>
              <option value="">全部可见部门</option>
              {scopedDepartments.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          ) : (
            <input className="toolbar-input mt-3 w-full" onChange={(event) => onDepartmentFilterChange(event.target.value)} placeholder="例如：研发中心" value={departmentFilter} />
          )}
          {isDepartmentScoped ? (
            <p className="mt-3 text-xs leading-5 text-steel">当前仅可查看：{scopedDepartments.length ? scopedDepartments.join('、') : '暂无可见部门'}</p>
          ) : null}
        </label>
        <label className="surface-subtle px-4 py-4">
          <span className="text-sm text-steel">岗位族筛选</span>
          <input className="toolbar-input mt-3 w-full" onChange={(event) => onJobFamilyFilterChange(event.target.value)} placeholder="例如：平台研发" value={jobFamilyFilter} />
        </label>
      </div>

      <div className="mt-5 grid gap-3 md:grid-cols-3">
        {[
          ['建议总额', formatCurrency(recommendedCost), '当前筛选范围内的建议调薪总额。'],
          ['生效预算', formatCurrency(effectiveBudget), isUsingCycleBudget ? '来自评估周期预算或部门预算分配规则。' : '来自当前手动输入的预算覆盖值。'],
          ['模拟人数', `${employees.length} 人`, '当前纳入模拟计算的员工数。'],
        ].map(([label, value, note]) => (
          <div className="metric-tile" key={label}>
            <p className="metric-label">{label}</p>
            <p className="metric-value text-[26px]">{value}</p>
            <p className="metric-note">{note}</p>
          </div>
        ))}
      </div>

      <div className="mt-5">
        <div className="flex items-center justify-between gap-3 text-sm text-steel">
          <span>预算占用进度</span>
          <span>{formatCurrency(recommendedCost)} / {formatCurrency(effectiveBudget)}</span>
        </div>
        <div style={{ marginTop: 10, height: 8, borderRadius: 999, background: 'var(--color-border)', overflow: 'hidden' }}>
          <div
            style={{
              height: '100%',
              width: `${Math.min(Math.max(usageRate * 100, 0), 100)}%`,
              borderRadius: 999,
              background: remainingBudget >= 0 ? 'var(--color-primary)' : 'var(--color-danger)',
              transition: 'width 0.2s ease',
            }}
          />
        </div>
      </div>
    </section>
  );
}
