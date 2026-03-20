import { useState, type FormEvent } from 'react';

import type { CycleCreatePayload } from '../../types/api';

type CreateCycleFormProps = {
  isSubmitting: boolean;
  errorMessage: string | null;
  onSubmit: (payload: CycleCreatePayload) => Promise<void>;
};

export function CreateCycleForm({ isSubmitting, errorMessage, onSubmit }: CreateCycleFormProps) {
  const [form, setForm] = useState<CycleCreatePayload>({
    name: '2026 Annual Review',
    review_period: '2026',
    budget_amount: '250000.00',
    status: 'draft',
  });

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await onSubmit(form);
  }

  function updateField<K extends keyof CycleCreatePayload>(key: K, value: CycleCreatePayload[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  return (
    <form className="flex flex-col gap-4" onSubmit={(event) => void handleSubmit(event)}>
      <label className="flex flex-col gap-2 text-sm font-medium text-ink">
        周期名称
        <input className="rounded-2xl border border-slate-200 px-4 py-3" onChange={(event) => updateField('name', event.target.value)} value={form.name} />
      </label>
      <label className="flex flex-col gap-2 text-sm font-medium text-ink">
        评估周期
        <input className="rounded-2xl border border-slate-200 px-4 py-3" onChange={(event) => updateField('review_period', event.target.value)} value={form.review_period} />
      </label>
      <label className="flex flex-col gap-2 text-sm font-medium text-ink">
        预算金额
        <input className="rounded-2xl border border-slate-200 px-4 py-3" onChange={(event) => updateField('budget_amount', event.target.value)} value={form.budget_amount} />
      </label>
      <label className="flex flex-col gap-2 text-sm font-medium text-ink">
        状态
        <select className="rounded-2xl border border-slate-200 px-4 py-3" onChange={(event) => updateField('status', event.target.value)} value={form.status}>
          <option value="draft">draft</option>
          <option value="collecting">collecting</option>
        </select>
      </label>
      {errorMessage ? <p className="text-sm text-red-600">{errorMessage}</p> : null}
      <button className="rounded-full bg-ink px-5 py-3 text-sm font-semibold text-white disabled:opacity-60" disabled={isSubmitting} type="submit">
        {isSubmitting ? '创建中...' : '创建评估周期'}
      </button>
    </form>
  );
}
