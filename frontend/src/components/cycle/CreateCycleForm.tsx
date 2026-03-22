import { useEffect, useState, type FormEvent } from 'react';

import type { CycleCreatePayload } from '../../types/api';

type CreateCycleFormProps = {
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
};

export function CreateCycleForm({
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
        <input className="toolbar-input" onChange={(event) => updateField('name', event.target.value)} value={form.name} />
      </label>
      <label className="flex flex-col gap-2 text-sm font-medium text-ink">
        评估周期
        <input className="toolbar-input" onChange={(event) => updateField('review_period', event.target.value)} value={form.review_period} />
      </label>
      <label className="flex flex-col gap-2 text-sm font-medium text-ink">
        预算金额
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
      {errorMessage ? <p className="text-sm" style={{ color: 'var(--color-danger)' }}>{errorMessage}</p> : null}
      <div className="flex flex-wrap gap-3">
        <button className="action-primary" disabled={isSubmitting} type="submit">
          {isSubmitting ? (isEditing ? '保存中...' : '创建中...') : (isEditing ? '保存周期修改' : '创建评估周期')}
        </button>
        {isEditing && onCancelEdit ? (
          <button className="action-secondary" onClick={onCancelEdit} type="button">取消编辑</button>
        ) : null}
      </div>
    </form>
  );
}
