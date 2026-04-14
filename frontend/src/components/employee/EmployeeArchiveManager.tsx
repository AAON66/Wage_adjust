import { useMemo, useState } from 'react';

import { createEmployee, updateEmployee } from '../../services/employeeService';
import type { DepartmentRecord, EmployeeCreatePayload, EmployeeRecord } from '../../types/api';

const INITIAL_EMPLOYEE_FORM: EmployeeCreatePayload = {
  employee_no: '',
  name: '',
  id_card_no: null,
  company: null,
  department: '',
  sub_department: null,
  job_family: '',
  job_level: '',
  manager_id: null,
  status: 'active',
};

interface EmployeeArchiveManagerProps {
  employees: EmployeeRecord[];
  departments: DepartmentRecord[];
  onReload: () => Promise<void>;
  resolveError: (error: unknown) => string;
  onError: (message: string) => void;
  onSuccess: (message: string) => void;
}

function toFormValues(employee: EmployeeRecord): EmployeeCreatePayload {
  return {
    employee_no: employee.employee_no,
    name: employee.name,
    id_card_no: employee.id_card_no,
    company: employee.company,
    department: employee.department,
    sub_department: employee.sub_department,
    job_family: employee.job_family,
    job_level: employee.job_level,
    manager_id: employee.manager_id,
    status: employee.status,
  };
}

export function EmployeeArchiveManager({
  employees,
  departments,
  onReload,
  resolveError,
  onError,
  onSuccess,
}: EmployeeArchiveManagerProps) {
  const [form, setForm] = useState<EmployeeCreatePayload>(INITIAL_EMPLOYEE_FORM);
  const [editingEmployeeId, setEditingEmployeeId] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const activeDepartments = useMemo(() => departments.filter((item) => item.status === 'active'), [departments]);
  const sortedEmployees = useMemo(
    () => [...employees].sort((left, right) => (left.created_at < right.created_at ? 1 : -1)),
    [employees],
  );
  const unboundEmployees = useMemo(() => employees.filter((employee) => !employee.bound_user_id), [employees]);

  function updateForm<K extends keyof EmployeeCreatePayload>(field: K, value: EmployeeCreatePayload[K]) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  function resetForm() {
    setForm(INITIAL_EMPLOYEE_FORM);
    setEditingEmployeeId(null);
  }

  async function handleSubmit() {
    if (!form.employee_no || !form.name || !form.department || !form.job_family || !form.job_level) {
      onError('请完整填写员工工号、姓名、所属部门、岗位族和岗位级别。');
      return;
    }
    if (!activeDepartments.some((item) => item.name === form.department)) {
      onError('请选择已创建且启用中的所属部门。');
      return;
    }

    setIsSubmitting(true);
    try {
      if (editingEmployeeId) {
        await updateEmployee(editingEmployeeId, form);
        onSuccess('员工档案已更新。');
      } else {
        await createEmployee(form);
        onSuccess('新的员工档案已创建。');
      }
      resetForm();
      await onReload();
    } catch (error) {
      onError(resolveError(error));
    } finally {
      setIsSubmitting(false);
    }
  }

  function handleStartEdit(employee: EmployeeRecord) {
    setEditingEmployeeId(employee.id);
    setForm(toFormValues(employee));
    onSuccess(`正在编辑员工档案：${employee.name}`);
  }

  return (
    <section className="grid gap-5 xl:grid-cols-[1.05fr_0.95fr]">
      <section className="surface px-6 py-6 lg:px-7">
        <div className="section-head">
          <div>
            <p className="eyebrow">{editingEmployeeId ? '编辑档案' : '单个录入'}</p>
            <h2 className="section-title">{editingEmployeeId ? '修改员工档案' : '新增员工档案'}</h2>
            <p className="section-note mt-2">
              {editingEmployeeId ? '修改后会直接覆盖当前员工档案，并继续保留原有绑定关系与历史记录。' : '录入完成后可继续做账号绑定或批量导入。'}
            </p>
          </div>
          {editingEmployeeId ? (
            <button className="action-secondary" onClick={resetForm} type="button">
              退出编辑
            </button>
          ) : null}
        </div>

        <div className="mt-5 grid gap-4 md:grid-cols-2">
          <label className="surface-subtle px-4 py-4">
            <span className="text-sm text-steel">员工工号</span>
            <input className="toolbar-input mt-3 w-full" onChange={(event) => updateForm('employee_no', event.target.value)} placeholder="例如 EMP-CN-201" value={form.employee_no} />
          </label>
          <label className="surface-subtle px-4 py-4">
            <span className="text-sm text-steel">员工姓名</span>
            <input className="toolbar-input mt-3 w-full" onChange={(event) => updateForm('name', event.target.value)} placeholder="请输入员工姓名" value={form.name} />
          </label>
          <label className="surface-subtle px-4 py-4">
            <span className="text-sm text-steel">身份证号</span>
            <input className="toolbar-input mt-3 w-full" onChange={(event) => updateForm('id_card_no', event.target.value || null)} placeholder="用于自动匹配平台账号，可留空" value={form.id_card_no ?? ''} />
          </label>
          <label className="surface-subtle px-4 py-4">
            <span className="text-sm text-steel">所属公司</span>
            <input className="toolbar-input mt-3 w-full" onChange={(event) => updateForm('company', event.target.value || null)} placeholder="例如 华东区域公司，可留空" value={form.company ?? ''} />
          </label>
          <label className="surface-subtle px-4 py-4">
            <span className="text-sm text-steel">所属部门</span>
            <select className="toolbar-input mt-3 w-full" onChange={(event) => updateForm('department', event.target.value)} value={form.department}>
              <option value="">{activeDepartments.length ? '请选择已创建部门' : '暂无可选部门'}</option>
              {activeDepartments.map((item) => (
                <option key={item.id} value={item.name}>
                  {item.name}
                </option>
              ))}
            </select>
            <p className="mt-3 text-xs leading-5 text-steel">
              {activeDepartments.length ? '只能从已创建且启用中的部门里选择。' : '请先到部门管理里创建并启用部门。'}
            </p>
          </label>
          <label className="surface-subtle px-4 py-4">
            <span className="text-sm text-steel">下属部门</span>
            <input
              className="toolbar-input mt-3 w-full"
              disabled={!form.department}
              onChange={(event) => updateForm('sub_department', event.target.value || null)}
              placeholder={form.department ? '例如 后端平台组 / 销售一部' : '请先选择所属部门'}
              value={form.sub_department ?? ''}
            />
          </label>
          <label className="surface-subtle px-4 py-4">
            <span className="text-sm text-steel">岗位族</span>
            <input className="toolbar-input mt-3 w-full" onChange={(event) => updateForm('job_family', event.target.value)} placeholder="例如 平台研发" value={form.job_family} />
          </label>
          <label className="surface-subtle px-4 py-4">
            <span className="text-sm text-steel">岗位级别</span>
            <input className="toolbar-input mt-3 w-full" onChange={(event) => updateForm('job_level', event.target.value)} placeholder="例如 P6" value={form.job_level} />
          </label>
          <label className="surface-subtle px-4 py-4">
            <span className="text-sm text-steel">在职状态</span>
            <select className="toolbar-input mt-3 w-full" onChange={(event) => updateForm('status', event.target.value)} value={form.status}>
              <option value="active">在职</option>
              <option value="inactive">停用</option>
            </select>
          </label>
        </div>

        <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-[var(--color-border)] pt-4">
          <p className="text-sm text-steel">
            {editingEmployeeId ? '保存后，右侧档案列表会自动刷新。' : '新建完成后，员工档案会立即出现在员工档案列表中。'}
          </p>
          <div className="flex flex-wrap gap-3">
            <button className="action-secondary" onClick={resetForm} type="button">
              {editingEmployeeId ? '取消编辑' : '清空表单'}
            </button>
            <button className="action-primary" disabled={isSubmitting} onClick={() => void handleSubmit()} type="button">
              {isSubmitting ? '保存中...' : editingEmployeeId ? '保存员工档案' : '新增员工档案'}
            </button>
          </div>
        </div>
      </section>

      <section className="surface px-6 py-6 lg:px-7">
        <div className="section-head">
          <div>
            <p className="eyebrow">档案列表</p>
            <h2 className="section-title">员工档案与快速编辑</h2>
            <p className="section-note mt-2">点击某条员工档案的“编辑档案”即可把数据回填到左侧表单。</p>
          </div>
          <div className="flex flex-wrap gap-2 text-xs text-steel">
            <span className="chip-button">总档案 {employees.length}</span>
            <span className="chip-button">待绑定 {unboundEmployees.length}</span>
          </div>
        </div>

        <div className="mt-5 grid gap-3">
          {sortedEmployees.map((employee) => (
            <article className="surface-subtle px-4 py-4" key={employee.id}>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="text-sm font-semibold text-ink">{employee.name}</h3>
                    <span
                      className="status-pill"
                      style={{
                        background: employee.status === 'active' ? 'var(--color-success-bg)' : 'var(--color-bg-subtle)',
                        color: employee.status === 'active' ? 'var(--color-success)' : 'var(--color-steel)',
                      }}
                    >
                      {employee.status === 'active' ? '在职' : '停用'}
                    </span>
                    {employee.bound_user_id ? (
                      <span className="status-pill" style={{ background: 'var(--color-primary-light)', color: 'var(--color-primary)' }}>
                        已绑定账号
                      </span>
                    ) : null}
                  </div>
                  <p className="mt-2 text-sm text-steel">{employee.employee_no} · {employee.department}{employee.sub_department ? ` / ${employee.sub_department}` : ''}</p>
                  <p className="mt-1 text-sm text-steel">{employee.job_family} · {employee.job_level}</p>
                  <p className="mt-1 text-xs text-steel">身份证号：{employee.id_card_no ?? '未填写'}{employee.bound_user_email ? ` · 账号 ${employee.bound_user_email}` : ''}</p>
                </div>
                <button className="action-secondary shrink-0" onClick={() => handleStartEdit(employee)} type="button">
                  编辑档案
                </button>
              </div>
            </article>
          ))}
          {!sortedEmployees.length ? <p className="text-sm text-steel">当前还没有员工档案。</p> : null}
        </div>
      </section>
    </section>
  );
}
