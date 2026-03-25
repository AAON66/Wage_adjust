import { useEffect, useMemo, useState, type FormEvent } from 'react';

import type { CycleCreatePayload, CycleDepartmentBudgetPayload, DepartmentRecord } from '../../types/api';

type CreateCycleFormProps = {
  departments: DepartmentRecord[];
  initialValues?: CycleCreatePayload;
  isEditing?: boolean;
  isSubmitting: boolean;
  errorMessage: string | null;
  onSubmit: (payload: CycleCreatePayload) => Promise<void>;
  onCancelEdit?: () => void;
};

const DEFAULT_FORM: CycleCreatePayload = {
  name: '2026 年度评估',
  review_period: '2026',
  budget_amount: '250000.00',
  status: 'draft',
  department_budgets: [],
};

function toNumber(value: string): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function normalizeDepartmentBudgets(items: CycleDepartmentBudgetPayload[]): CycleDepartmentBudgetPayload[] {
  return items
    .map((item) => ({
      department_id: item.department_id,
      budget_amount: item.budget_amount.trim(),
    }))
    .filter((item) => item.department_id && item.budget_amount !== '' && toNumber(item.budget_amount) > 0);
}

export function CreateCycleForm({
  departments,
  initialValues,
  isEditing = false,
  isSubmitting,
  errorMessage,
  onSubmit,
  onCancelEdit,
}: CreateCycleFormProps) {
  const [form, setForm] = useState<CycleCreatePayload>(initialValues ?? DEFAULT_FORM);

  useEffect(() => {
    setForm(initialValues ?? DEFAULT_FORM);
  }, [initialValues]);

  const activeDepartments = useMemo(
    () => departments.filter((item) => item.status === 'active').sort((left, right) => left.name.localeCompare(right.name, 'zh-CN')),
    [departments],
  );

  const allocationMap = useMemo(() => new Map(form.department_budgets.map((item) => [item.department_id, item.budget_amount])), [form.department_budgets]);
  const totalBudget = toNumber(form.budget_amount);
  const allocatedBudget = useMemo(
    () => normalizeDepartmentBudgets(form.department_budgets).reduce((sum, item) => sum + toNumber(item.budget_amount), 0),
    [form.department_budgets],
  );
  const remainingBudget = totalBudget - allocatedBudget;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await onSubmit({
      ...form,
      department_budgets: normalizeDepartmentBudgets(form.department_budgets),
    });
  }

  function updateField<K extends keyof CycleCreatePayload>(key: K, value: CycleCreatePayload[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  function updateDepartmentBudget(departmentId: string, budgetAmount: string) {
    setForm((current) => {
      const nextBudgets = current.department_budgets.filter((item) => item.department_id !== departmentId);
      if (budgetAmount.trim() !== '') {
        nextBudgets.push({ department_id: departmentId, budget_amount: budgetAmount });
      }
      return {
        ...current,
        department_budgets: nextBudgets,
      };
    });
  }

  function fillEvenly() {
    if (!activeDepartments.length) {
      return;
    }

    const evenAmount = (totalBudget / activeDepartments.length).toFixed(2);
    updateField(
      'department_budgets',
      activeDepartments.map((department) => ({
        department_id: department.id,
        budget_amount: evenAmount,
      })),
    );
  }

  function clearAllocations() {
    updateField('department_budgets', []);
  }

  return (
    <form className="flex flex-col gap-4" onSubmit={(event) => void handleSubmit(event)}>
      <label className="flex flex-col gap-2 text-sm font-medium text-ink">
        周期名称
        <input className="toolbar-input" onChange={(event) => updateField('name', event.target.value)} value={form.name} />
      </label>
      <label className="flex flex-col gap-2 text-sm font-medium text-ink">
        评估周期
        <input className="toolbar-input" onChange={(event) => updateField('review_period', event.target.value)} value={form.review_period} />
      </label>
      <label className="flex flex-col gap-2 text-sm font-medium text-ink">
        总预算金额
        <input className="toolbar-input" onChange={(event) => updateField('budget_amount', event.target.value)} value={form.budget_amount} />
      </label>
      <label className="flex flex-col gap-2 text-sm font-medium text-ink">
        状态
        <select className="toolbar-input" onChange={(event) => updateField('status', event.target.value)} value={form.status}>
          <option value="draft">草稿</option>
          <option value="collecting">收集中</option>
          {isEditing ? <option value="published">已发布</option> : null}
        </select>
      </label>

      <section className="surface-subtle px-4 py-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-sm font-semibold text-ink">部门预算分配</p>
            <p className="mt-2 text-sm leading-6 text-steel">
              可以为部分或全部部门单独指定预算。未设置的部门会自动参与剩余预算平分；如果一个部门都没设置，则默认按全部启用部门平均分配。
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button className="action-secondary px-4 py-2 text-xs" onClick={fillEvenly} type="button">
              按当前总预算平均填充
            </button>
            <button className="action-secondary px-4 py-2 text-xs" onClick={clearAllocations} type="button">
              清空部门分配
            </button>
          </div>
        </div>

        <div className="mt-4 grid gap-3 md:grid-cols-3">
          <article className="metric-tile">
            <p className="metric-label">已单独分配</p>
            <p className="metric-value text-[24px]">{allocatedBudget.toFixed(2)}</p>
            <p className="metric-note">已经录入明确预算的部门金额合计。</p>
          </article>
          <article className="metric-tile">
            <p className="metric-label">待默认分摊</p>
            <p className="metric-value text-[24px]" style={{ color: remainingBudget >= 0 ? 'var(--color-ink)' : 'var(--color-danger)' }}>
              {remainingBudget.toFixed(2)}
            </p>
            <p className="metric-note">剩余金额会在未设置的部门之间自动平分。</p>
          </article>
          <article className="metric-tile">
            <p className="metric-label">启用部门数</p>
            <p className="metric-value text-[24px]">{activeDepartments.length}</p>
            <p className="metric-note">只有状态为启用的部门会参与预算分配。</p>
          </article>
        </div>

        <div className="mt-4 space-y-3">
          {activeDepartments.map((department) => (
            <label className="flex flex-col gap-2 rounded-2xl border border-[var(--color-border)] bg-white px-4 py-4 text-sm text-ink" key={department.id}>
              <span className="flex items-center justify-between gap-3">
                <span className="font-medium">{department.name}</span>
                <span className="text-xs text-steel">留空则参与默认平分</span>
              </span>
              <input
                className="toolbar-input"
                min={0}
                onChange={(event) => updateDepartmentBudget(department.id, event.target.value)}
                placeholder="例如：50000.00"
                type="number"
                value={allocationMap.get(department.id) ?? ''}
              />
            </label>
          ))}
          {activeDepartments.length === 0 ? <p className="text-sm text-steel">当前还没有启用中的部门，暂时无法设置部门预算。</p> : null}
        </div>
      </section>

      {errorMessage ? (
        <p className="text-sm" style={{ color: 'var(--color-danger)' }}>
          {errorMessage}
        </p>
      ) : null}

      <div className="flex flex-wrap gap-3">
        <button className="action-primary" disabled={isSubmitting} type="submit">
          {isSubmitting ? (isEditing ? '保存中...' : '创建中...') : isEditing ? '保存周期修改' : '创建评估周期'}
        </button>
        {isEditing && onCancelEdit ? (
          <button className="action-secondary" onClick={onCancelEdit} type="button">
            取消编辑
          </button>
        ) : null}
      </div>
    </form>
  );
}
