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
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
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
    <section className="rounded-[32px] bg-white p-6 shadow-panel">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-sm uppercase tracking-[0.24em] text-ember">Budget Simulation</p>
          <h2 className="mt-2 text-3xl font-bold text-ink">Salary recommendation sandbox</h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">
            Adjust filters and budget assumptions to compare proposed recommendation cost against the available cycle budget.
          </p>
        </div>
        <div className="rounded-[24px] bg-slate-50 px-5 py-4 text-right">
          <p className="text-sm text-slate-500">Remaining budget</p>
          <p className={`mt-2 text-2xl font-bold ${remainingBudget >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
            {formatCurrency(remainingBudget)}
          </p>
        </div>
      </div>

      <div className="mt-6 grid gap-4 md:grid-cols-3">
        <label className="rounded-[24px] border border-slate-200 p-4">
          <span className="text-sm text-slate-500">Cycle budget</span>
          <input
            className="mt-2 w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm text-ink"
            min={0}
            onChange={(event) => onBudgetAmountChange(Number(event.target.value))}
            type="number"
            value={budgetAmount}
          />
        </label>
        <label className="rounded-[24px] border border-slate-200 p-4">
          <span className="text-sm text-slate-500">Department filter</span>
          <input
            className="mt-2 w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm text-ink"
            onChange={(event) => onDepartmentFilterChange(event.target.value)}
            placeholder="Engineering"
            value={departmentFilter}
          />
        </label>
        <label className="rounded-[24px] border border-slate-200 p-4">
          <span className="text-sm text-slate-500">Job family filter</span>
          <input
            className="mt-2 w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm text-ink"
            onChange={(event) => onJobFamilyFilterChange(event.target.value)}
            placeholder="Platform"
            value={jobFamilyFilter}
          />
        </label>
      </div>

      <div className="mt-6 grid gap-4 md:grid-cols-3">
        {[
          ['Recommended total', formatCurrency(recommendedCost)],
          ['Budget amount', formatCurrency(budgetAmount)],
          ['In simulation', `${employees.length} employees`],
        ].map(([label, value]) => (
          <div key={label} className="rounded-[24px] bg-slate-50 p-5">
            <p className="text-sm text-slate-500">{label}</p>
            <p className="mt-2 text-2xl font-bold text-ink">{value}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
