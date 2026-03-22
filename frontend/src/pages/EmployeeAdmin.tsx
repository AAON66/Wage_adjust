import axios from 'axios';
import { useEffect, useMemo, useState } from 'react';

import { ImportJobTable } from '../components/import/ImportJobTable';
import { AppShell } from '../components/layout/AppShell';
import { useAuth } from '../hooks/useAuth';
import { createEmployee, fetchEmployees } from '../services/employeeService';
import { deleteHandbook, fetchHandbooks, uploadHandbook } from '../services/handbookService';
import { bulkDeleteImportJobs, createImportJob, downloadImportTemplate, exportImportJob, fetchImportJobs } from '../services/importService';
import { fetchUsers, updateManagedUserEmployeeBinding } from '../services/userAdminService';
import type { EmployeeCreatePayload, EmployeeHandbookRecord, EmployeeRecord, ImportJobRecord, UserProfile } from '../types/api';
import { getRoleLabel } from '../utils/roleAccess';

const IMPORT_TYPES = [
  { value: 'employees', label: '员工档案' },
  { value: 'certifications', label: '认证信息' },
];

const INITIAL_EMPLOYEE_FORM: EmployeeCreatePayload = {
  employee_no: '',
  name: '',
  department: '',
  job_family: '',
  job_level: '',
  manager_id: null,
  status: 'active',
};

type EmployeeAdminTabKey = 'employee' | 'binding' | 'import' | 'handbook';

const TAB_ITEMS: Array<{ key: EmployeeAdminTabKey; label: string; description: string }> = [
  { key: 'employee', label: '新增档案', description: '单个创建员工档案' },
  { key: 'binding', label: '账号绑定', description: '处理账号与员工档案对应' },
  { key: 'import', label: '批量导入', description: '处理模板下载和导入记录' },
  { key: 'handbook', label: '员工手册', description: '上传并维护制度文档' },
];

function resolveError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const data = error.response?.data as { detail?: string; message?: string; details?: Array<{ loc?: Array<string | number>; msg?: string }> } | undefined;
    const firstDetail = data?.details?.[0];
    if (firstDetail?.loc?.includes('page_size')) {
      return '请求数量超过系统允许范围，请缩小查询数量后重试。';
    }
    return data?.detail ?? data?.message ?? firstDetail?.msg ?? '员工档案管理操作失败。';
  }
  return '员工档案管理操作失败。';
}

function formatBindingKeyword(employee: EmployeeRecord | null | undefined): string {
  if (!employee) {
    return '';
  }
  return `${employee.name}${employee.employee_no ? ` ${employee.employee_no}` : ''}`.trim();
}

function formatEmployeeOption(employee: EmployeeRecord): string {
  return `${employee.name} · ${employee.employee_no} · ${employee.department} / ${employee.job_family}`;
}

function saveBlob(blob: Blob, fileName: string): void {
  const url = window.URL.createObjectURL(blob);
  const link = window.document.createElement('a');
  link.href = url;
  link.download = fileName;
  window.document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

export function EmployeeAdminPage() {
  const { user } = useAuth();
  const [users, setUsers] = useState<UserProfile[]>([]);
  const [employees, setEmployees] = useState<EmployeeRecord[]>([]);
  const [handbooks, setHandbooks] = useState<EmployeeHandbookRecord[]>([]);
  const [importJobs, setImportJobs] = useState<ImportJobRecord[]>([]);
  const [selectedImportJobIds, setSelectedImportJobIds] = useState<string[]>([]);
  const [keyword, setKeyword] = useState('');
  const [activeTab, setActiveTab] = useState<EmployeeAdminTabKey>('employee');
  const [bindingDrafts, setBindingDrafts] = useState<Record<string, string>>({});
  const [bindingSearchDrafts, setBindingSearchDrafts] = useState<Record<string, string>>({});
  const [activeBindingPickerId, setActiveBindingPickerId] = useState<string | null>(null);
  const [expandedBindingIds, setExpandedBindingIds] = useState<string[]>([]);
  const [employeeForm, setEmployeeForm] = useState<EmployeeCreatePayload>(INITIAL_EMPLOYEE_FORM);
  const [selectedImportType, setSelectedImportType] = useState('employees');
  const [selectedImportFile, setSelectedImportFile] = useState<File | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isCreatingEmployee, setIsCreatingEmployee] = useState(false);
  const [isUploadingHandbook, setIsUploadingHandbook] = useState(false);
  const [isUploadingImport, setIsUploadingImport] = useState(false);
  const [isDeletingImportJobs, setIsDeletingImportJobs] = useState(false);
  const [workingUserId, setWorkingUserId] = useState<string | null>(null);
  const [deletingHandbookId, setDeletingHandbookId] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  async function loadPageData() {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const [userResponse, employeeResponse, handbookResponse, importResponse] = await Promise.all([
        fetchUsers({ page: 1, page_size: 100 }),
        fetchEmployees({ page: 1, page_size: 100 }),
        fetchHandbooks(),
        fetchImportJobs(),
      ]);
      setUsers(userResponse.items);
      setEmployees(employeeResponse.items);
      setHandbooks(handbookResponse.items);
      setImportJobs(importResponse.items);
      setSelectedImportJobIds((current) => current.filter((jobId) => importResponse.items.some((job) => job.id === jobId)));
      setBindingDrafts(Object.fromEntries(userResponse.items.map((item) => [item.id, item.employee_id ?? ''])));
      setBindingSearchDrafts(
        Object.fromEntries(
          userResponse.items.map((item) => [
            item.id,
            item.employee_id ? `${item.employee_name ?? ''}${item.employee_no ? ` ${item.employee_no}` : ''}`.trim() : '',
          ]),
        ),
      );
    } catch (error) {
      setErrorMessage(resolveError(error));
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadPageData();
  }, []);

  const filteredUsers = useMemo(() => {
    const loweredKeyword = keyword.trim().toLowerCase();
    return users
      .filter((item) => item.id !== user?.id)
      .filter((item) => {
        if (!loweredKeyword) {
          return true;
        }
        return [item.email, item.employee_name ?? '', item.employee_no ?? ''].some((value) => value.toLowerCase().includes(loweredKeyword));
      });
  }, [keyword, user?.id, users]);

  const boundManageableUsers = useMemo(() => filteredUsers.filter((item) => Boolean(item.employee_id)), [filteredUsers]);
  const unboundManageableUsers = useMemo(() => filteredUsers.filter((item) => !item.employee_id), [filteredUsers]);
  const unboundEmployees = useMemo(() => employees.filter((employee) => !employee.bound_user_id), [employees]);
  const boundUsersCount = useMemo(() => users.filter((item) => item.employee_id).length, [users]);
  const importStats = useMemo(() => ({
    total: importJobs.length,
    processing: importJobs.filter((job) => job.status === 'pending' || job.status === 'queued' || job.status === 'processing').length,
    completed: importJobs.filter((job) => job.status === 'completed').length,
  }), [importJobs]);

  function getEmployeeOptionsForUser(targetUser: UserProfile): EmployeeRecord[] {
    return employees.filter((employee) => !employee.bound_user_id || employee.bound_user_id === targetUser.id);
  }

  function getFilteredEmployeeOptions(targetUser: UserProfile): EmployeeRecord[] {
    const searchValue = (bindingSearchDrafts[targetUser.id] ?? '').trim().toLowerCase();
    const options = getEmployeeOptionsForUser(targetUser);
    if (!searchValue) {
      return options;
    }
    return options.filter((employee) =>
      [employee.name, employee.employee_no, employee.department, employee.job_family]
        .filter(Boolean)
        .some((value) => value.toLowerCase().includes(searchValue)),
    );
  }

  function selectEmployeeForBinding(userId: string, employee: EmployeeRecord | null) {
    setBindingDrafts((current) => ({ ...current, [userId]: employee?.id ?? '' }));
    setBindingSearchDrafts((current) => ({ ...current, [userId]: formatBindingKeyword(employee) }));
    setActiveBindingPickerId(null);
  }

  function updateEmployeeForm<K extends keyof EmployeeCreatePayload>(field: K, value: EmployeeCreatePayload[K]) {
    setEmployeeForm((current) => ({ ...current, [field]: value }));
  }

  async function handleCreateEmployee() {
    if (!employeeForm.employee_no || !employeeForm.name || !employeeForm.department || !employeeForm.job_family || !employeeForm.job_level) {
      setErrorMessage('请完整填写员工工号、姓名、部门、岗位族和岗位级别。');
      return;
    }

    setIsCreatingEmployee(true);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      await createEmployee(employeeForm);
      setEmployeeForm(INITIAL_EMPLOYEE_FORM);
      setSuccessMessage('新的员工档案已创建，可继续做账号绑定或批量导入。');
      await loadPageData();
    } catch (error) {
      setErrorMessage(resolveError(error));
    } finally {
      setIsCreatingEmployee(false);
    }
  }

  async function handleSaveBinding(targetUser: UserProfile) {
    const nextEmployeeId = bindingDrafts[targetUser.id] || null;
    setWorkingUserId(targetUser.id);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      const updatedUser = await updateManagedUserEmployeeBinding(targetUser.id, nextEmployeeId);
      setUsers((current) => current.map((item) => item.id === updatedUser.id ? updatedUser : item));
      setEmployees((current) => current.map((employee) => {
        if (employee.id === updatedUser.employee_id) {
          return {
            ...employee,
            bound_user_id: updatedUser.id,
            bound_user_email: updatedUser.email,
          };
        }
        if (employee.bound_user_id === updatedUser.id && employee.id !== updatedUser.employee_id) {
          return {
            ...employee,
            bound_user_id: null,
            bound_user_email: null,
          };
        }
        return employee;
      }));
      setBindingSearchDrafts((current) => ({
        ...current,
        [targetUser.id]: nextEmployeeId ? formatBindingKeyword(employees.find((employee) => employee.id === nextEmployeeId)) : '',
      }));
      setSuccessMessage(nextEmployeeId ? '员工档案绑定已更新。' : '员工档案绑定已解除。');
      await loadPageData();
    } catch (error) {
      setErrorMessage(resolveError(error));
    } finally {
      setWorkingUserId(null);
    }
  }

  async function handleUploadHandbook(fileList: globalThis.FileList | null) {
    const file = fileList?.[0];
    if (!file) {
      return;
    }

    setIsUploadingHandbook(true);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      await uploadHandbook(file);
      setSuccessMessage('员工手册已上传并完成解析。');
      await loadPageData();
    } catch (error) {
      setErrorMessage(resolveError(error));
    } finally {
      setIsUploadingHandbook(false);
    }
  }

  async function handleDeleteHandbook(handbook: EmployeeHandbookRecord) {
    if (!window.confirm(`确认删除手册《${handbook.title}》吗？`)) {
      return;
    }

    setDeletingHandbookId(handbook.id);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      await deleteHandbook(handbook.id);
      setSuccessMessage('员工手册已删除。');
      setHandbooks((current) => current.filter((item) => item.id !== handbook.id));
    } catch (error) {
      setErrorMessage(resolveError(error));
    } finally {
      setDeletingHandbookId(null);
    }
  }

  async function handleUploadImport() {
    if (!selectedImportFile) {
      setErrorMessage('请先选择需要导入的文件。');
      return;
    }

    setIsUploadingImport(true);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      await createImportJob(selectedImportType, selectedImportFile);
      setSelectedImportFile(null);
      const input = window.document.getElementById('employee-admin-import-input') as HTMLInputElement | null;
      if (input) {
        input.value = '';
      }
      setSuccessMessage('批量导入任务已创建，请在下方查看处理结果。');
      await loadPageData();
    } catch (error) {
      setErrorMessage(resolveError(error));
    } finally {
      setIsUploadingImport(false);
    }
  }

  async function handleDownloadTemplate(importType: string) {
    try {
      const blob = await downloadImportTemplate(importType);
      saveBlob(blob, `${importType}_template.csv`);
    } catch (error) {
      setErrorMessage(resolveError(error));
    }
  }

  async function handleExport(jobId: string) {
    try {
      const blob = await exportImportJob(jobId);
      saveBlob(blob, `import_${jobId}_report.csv`);
    } catch (error) {
      setErrorMessage(resolveError(error));
    }
  }

  function toggleImportSelection(jobId: string) {
    setSelectedImportJobIds((current) =>
      current.includes(jobId) ? current.filter((id) => id !== jobId) : [...current, jobId],
    );
  }

  function toggleAllImportSelections() {
    setSelectedImportJobIds((current) =>
      current.length === importJobs.length ? [] : importJobs.map((job) => job.id),
    );
  }

  async function handleDeleteSelectedImportJobs() {
    if (!selectedImportJobIds.length) {
      return;
    }

    if (!window.confirm(`确认删除已选中的 ${selectedImportJobIds.length} 条导入记录吗？`)) {
      return;
    }

    setIsDeletingImportJobs(true);
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      const response = await bulkDeleteImportJobs(selectedImportJobIds);
      setImportJobs((current) => current.filter((job) => !response.deleted_job_ids.includes(job.id)));
      setSelectedImportJobIds([]);
      setSuccessMessage(`已删除 ${response.deleted_job_ids.length} 条导入记录。`);
    } catch (error) {
      setErrorMessage(resolveError(error));
    } finally {
      setIsDeletingImportJobs(false);
    }
  }

  function renderBindingCard(item: UserProfile) {
    const options = getFilteredEmployeeOptions(item).slice(0, 8);
    const selectedEmployee = employees.find((employee) => employee.id === (bindingDrafts[item.id] ?? '')) ?? null;
    const isWorking = workingUserId === item.id;
    const isPickerOpen = activeBindingPickerId === item.id;
    const isExpanded = expandedBindingIds.includes(item.id);

    return (
      <article className="list-row p-5" key={item.id}>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-3">
              <h3 className="break-all text-base font-semibold text-ink">{item.email}</h3>
              <span className="status-pill" style={{ background: 'var(--color-primary-light)', color: 'var(--color-primary)' }}>{getRoleLabel(item.role)}</span>
              {item.employee_id ? <span className="status-pill" style={{ background: 'var(--color-success-bg)', color: 'var(--color-success)' }}>已绑定</span> : <span className="status-pill" style={{ background: 'var(--color-warning-bg)', color: 'var(--color-warning)' }}>待绑定</span>}
            </div>
            <p className="mt-2 text-sm text-steel">
              {item.employee_id ? `当前绑定：${item.employee_name ?? '未命名员工'}${item.employee_no ? `（${item.employee_no}）` : ''}` : '当前尚未绑定员工档案。'}
            </p>
          </div>
          <button
            className="action-secondary shrink-0"
            onClick={() => {
              setExpandedBindingIds((current: string[]) => current.includes(item.id) ? current.filter((id: string) => id !== item.id) : [...current, item.id]);
              setActiveBindingPickerId((current) => (current === item.id ? null : current));
            }}
            type="button"
          >
            {isExpanded ? '收起详情' : '展开详情'}
          </button>
        </div>

        {isExpanded ? (
          <div style={{ marginTop: 12, borderTop: '1px solid var(--color-border)', paddingTop: 12 }}>
            <div className="grid gap-2 text-sm text-ink">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <span>搜索并选择员工档案</span>
                <button className="action-primary shrink-0" disabled={isWorking} onClick={() => void handleSaveBinding(item)} type="button">
                  {isWorking ? '保存中...' : '保存绑定'}
                </button>
              </div>
              <div className="flex flex-wrap gap-2">
                <input
                  className="toolbar-input min-w-[220px] flex-1"
                  disabled={isWorking}
                  onBlur={() => {
                    window.setTimeout(() => setActiveBindingPickerId((current) => (current === item.id ? null : current)), 120);
                  }}
                  onChange={(event) => {
                    const nextValue = event.target.value;
                    setBindingSearchDrafts((current) => ({ ...current, [item.id]: nextValue }));
                    setBindingDrafts((current) => ({ ...current, [item.id]: '' }));
                    setActiveBindingPickerId(item.id);
                  }}
                  onFocus={() => setActiveBindingPickerId(item.id)}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter' && options[0]) {
                      event.preventDefault();
                      selectEmployeeForBinding(item.id, options[0]);
                    }
                  }}
                  placeholder="输入姓名、工号、部门或岗位"
                  value={bindingSearchDrafts[item.id] ?? ''}
                />
                <button
                  className="action-secondary shrink-0"
                  disabled={isWorking}
                  onMouseDown={(event) => event.preventDefault()}
                  onClick={() => {
                    setBindingSearchDrafts((current) => ({ ...current, [item.id]: '' }));
                    setBindingDrafts((current) => ({ ...current, [item.id]: '' }));
                    setActiveBindingPickerId(item.id);
                  }}
                  type="button"
                >
                  清空
                </button>
              </div>

              {isPickerOpen ? (
                <div style={{ marginTop: 8, overflow: 'hidden', borderRadius: 8, border: '1px solid var(--color-border)', background: '#FFFFFF', boxShadow: 'var(--shadow-dropdown)' }}>
                  <button
                    style={{ display: 'flex', width: '100%', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--color-border)', padding: '10px 14px', textAlign: 'left', fontSize: 13, color: 'var(--color-ink)', background: 'none', cursor: 'pointer' }}
                    onMouseDown={(event) => event.preventDefault()}
                    onClick={() => selectEmployeeForBinding(item.id, null)}
                    type="button"
                  >
                    <span>暂不绑定</span>
                    <span className="text-xs text-steel">清空当前选择</span>
                  </button>
                  <div className="max-h-64 overflow-y-auto py-1">
                    {options.length ? (
                      options.map((employee) => (
                        <button
                          className="flex w-full items-start justify-between gap-3 px-4 py-3 text-left transition hover:bg-[var(--color-bg-hover)]"
                          key={employee.id}
                          onMouseDown={(event) => event.preventDefault()}
                          onClick={() => selectEmployeeForBinding(item.id, employee)}
                          type="button"
                        >
                          <div className="min-w-0">
                            <p className="text-sm font-medium text-ink">{employee.name}</p>
                            <p className="mt-1 break-words text-xs leading-5 text-steel">{employee.employee_no} · {employee.department} · {employee.job_family}</p>
                          </div>
                          {selectedEmployee?.id === employee.id ? <span className="shrink-0 text-xs font-medium" style={{ color: 'var(--color-primary)' }}>已选</span> : null}
                        </button>
                      ))
                    ) : (
                      <div className="px-4 py-4 text-sm text-steel">没有找到匹配的员工档案，请换个关键词试试。</div>
                    )}
                  </div>
                </div>
              ) : null}

              <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-steel">
                <span className="min-w-0 break-words">{selectedEmployee ? `已选：${formatEmployeeOption(selectedEmployee)}` : '尚未选择员工档案'}</span>
                <span className="shrink-0">最多展示 8 条联想结果</span>
              </div>
            </div>
          </div>
        ) : null}
      </article>
    );
  }

  function renderTabButton(item: { key: EmployeeAdminTabKey; label: string; description: string }) {
    const isActive = activeTab === item.key;
    return (
      <button
        key={item.key}
        title={item.description}
        style={{
          borderRadius: 6,
          border: `1px solid ${isActive ? 'var(--color-primary)' : 'var(--color-border)'}`,
          background: isActive ? 'var(--color-primary-light)' : '#FFFFFF',
          padding: '10px 16px',
          textAlign: 'left',
          cursor: 'pointer',
          transition: 'background 0.15s, border-color 0.15s',
        }}
        onClick={() => setActiveTab(item.key)}
        type="button"
      >
        <p style={{ fontSize: 14, fontWeight: 500, color: isActive ? 'var(--color-primary)' : 'var(--color-ink)' }}>{item.label}</p>
        <p style={{ marginTop: 4, fontSize: 12, color: 'var(--color-steel)' }}>{item.description}</p>
      </button>
    );
  }

  return (
    <AppShell
      title="员工档案与手册"
      description="处理员工档案、账号绑定、批量导入和员工手册。"
      actions={<span className="status-pill" style={{ background: 'var(--color-primary-light)', color: 'var(--color-primary)' }}>当前身份：{getRoleLabel(user?.role)}</span>}
    >
      <section className="metric-strip animate-fade-up">
        {[
          ['员工档案', String(employees.length), '系统内现有员工档案总数，可用于单个维护和批量接入。'],
          ['已完成绑定', String(boundUsersCount), '已有平台账号与正式员工档案建立绑定关系。'],
          ['待绑定档案', String(unboundEmployees.length), '当前还未与平台账号建立绑定的员工档案数量。'],
          ['导入任务', String(importStats.total), `处理中 ${importStats.processing} 个，已完成 ${importStats.completed} 个。`],
        ].map(([label, value, note]) => (
          <article className="metric-tile" key={label}>
            <p className="metric-label">{label}</p>
            <p className="metric-value text-[26px]">{value}</p>
            <p className="metric-note">{note}</p>
          </article>
        ))}
      </section>

      {errorMessage ? <p className="surface px-5 py-4 text-sm" style={{ color: "var(--color-danger)" }}>{errorMessage}</p> : null}
      {successMessage ? <p className="surface px-5 py-4 text-sm" style={{ color: "var(--color-success)" }}>{successMessage}</p> : null}
      {isLoading ? <p className="surface px-5 py-4 text-sm text-steel">正在加载员工档案管理数据...</p> : null}

      <section className="surface" style={{ padding: '20px 24px' }}>
        <h2 className="section-title">按任务切换当前工作面</h2>
        <div className="mt-5 grid gap-3 lg:grid-cols-4">
          {TAB_ITEMS.map((item) => renderTabButton(item))}
        </div>
      </section>

      {activeTab === 'employee' ? (
        <section className="grid gap-5 xl:grid-cols-[1.02fr_0.98fr]">
          <section className="surface px-6 py-6 lg:px-7">
            <div className="section-head">
              <div>
                <p className="eyebrow">单个录入</p>
                <h2 className="section-title">新增员工档案</h2>
                <p className="section-note mt-2">录入档案后可继续账号绑定。</p>
              </div>
            </div>
            <div className="mt-5 grid gap-4 md:grid-cols-2">
              <label className="surface-subtle px-4 py-4"><span className="text-sm text-steel">员工工号</span><input className="toolbar-input mt-3 w-full" onChange={(event) => updateEmployeeForm('employee_no', event.target.value)} placeholder="例如 EMP-CN-201" value={employeeForm.employee_no} /></label>
              <label className="surface-subtle px-4 py-4"><span className="text-sm text-steel">员工姓名</span><input className="toolbar-input mt-3 w-full" onChange={(event) => updateEmployeeForm('name', event.target.value)} placeholder="请输入员工姓名" value={employeeForm.name} /></label>
              <label className="surface-subtle px-4 py-4"><span className="text-sm text-steel">所属部门</span><input className="toolbar-input mt-3 w-full" onChange={(event) => updateEmployeeForm('department', event.target.value)} placeholder="例如 研发中心" value={employeeForm.department} /></label>
              <label className="surface-subtle px-4 py-4"><span className="text-sm text-steel">岗位族</span><input className="toolbar-input mt-3 w-full" onChange={(event) => updateEmployeeForm('job_family', event.target.value)} placeholder="例如 平台研发" value={employeeForm.job_family} /></label>
              <label className="surface-subtle px-4 py-4"><span className="text-sm text-steel">岗位级别</span><input className="toolbar-input mt-3 w-full" onChange={(event) => updateEmployeeForm('job_level', event.target.value)} placeholder="例如 P6" value={employeeForm.job_level} /></label>
              <label className="surface-subtle px-4 py-4"><span className="text-sm text-steel">在职状态</span><select className="toolbar-input mt-3 w-full" onChange={(event) => updateEmployeeForm('status', event.target.value)} value={employeeForm.status}><option value="active">在职</option><option value="inactive">停用</option></select></label>
            </div>
            <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-[var(--color-border)] pt-4">
              <p className="text-sm text-steel">新建完成后，员工档案会立即出现在绑定区和批量管理范围内。</p>
              <div className="flex flex-wrap gap-3">
                <button className="action-secondary" onClick={() => setEmployeeForm(INITIAL_EMPLOYEE_FORM)} type="button">清空表单</button>
                <button className="action-primary" disabled={isCreatingEmployee} onClick={() => void handleCreateEmployee()} type="button">{isCreatingEmployee ? '创建中...' : '新增员工档案'}</button>
              </div>
            </div>
          </section>
          <section className="surface px-6 py-6 lg:px-7">
            <div className="section-head"><div><p className="eyebrow">录入说明</p><h2 className="section-title">先建档，再继续后续运营</h2></div></div>
            <div className="mt-5 grid gap-4">
              <div className="surface-subtle px-5 py-5"><p className="text-sm font-semibold text-ink">当前未绑定档案</p><p className="mt-2 text-3xl font-semibold tracking-[-0.04em] text-ink">{unboundEmployees.length}</p><p className="mt-3 text-sm leading-6 text-steel">新增后可继续账号绑定。</p></div>
              <div className="surface-subtle px-5 py-5"><p className="text-sm font-semibold text-ink">推荐操作顺序</p><div className="mt-4 grid gap-3 text-sm leading-6 text-steel"><div>1. 先录入正式员工档案，保证工号、部门和岗位信息完整。</div><div>2. 切换到账号绑定，把平台账号与员工档案完成对应。</div><div>3. 如需一次性导入大量数据，再切换到批量导入处理。</div></div></div>
            </div>
          </section>
        </section>
      ) : null}

      {activeTab === 'binding' ? (
        <section className="surface px-6 py-6 lg:px-7">
          <div className="section-head"><div><p className="eyebrow">档案绑定</p><h2 className="section-title">平台账号与员工档案</h2><p className="section-note mt-2">处理平台账号与员工档案对应。</p></div></div>
          <div className="mt-5 grid gap-3 lg:grid-cols-[minmax(0,1fr)_260px]">
            <input className="toolbar-input" onChange={(event) => setKeyword(event.target.value)} placeholder="按邮箱、员工姓名或工号搜索" value={keyword} />
            <div className="surface-subtle px-4 py-4 text-sm text-steel">已绑定账号 {boundManageableUsers.length} 个，待绑定账号 {unboundManageableUsers.length} 个。</div>
          </div>
          <div className="mt-5 space-y-5">
            <section className="surface-subtle px-5 py-5"><div className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--color-border)] pb-3"><div><p className="text-sm font-semibold text-ink">已绑定账号</p><p className="mt-1 text-sm text-steel">默认展示已经完成绑定的账号，方便直接查看和调整当前绑定关系。</p></div><span className="chip-button">{boundManageableUsers.length} 个</span></div><div className="mt-4 grid gap-4">{boundManageableUsers.length ? boundManageableUsers.map((item) => renderBindingCard(item)) : <p className="text-sm text-steel">当前还没有已绑定的账号。</p>}</div></section>
            <section className="surface-subtle px-5 py-5"><div className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--color-border)] pb-3"><div><p className="text-sm font-semibold text-ink">待绑定账号</p><p className="mt-1 text-sm text-steel">这里保留还没有关联员工档案的平台账号，适合逐个完成绑定。</p></div><span className="chip-button">{unboundManageableUsers.length} 个</span></div><div className="mt-4 grid gap-4">{unboundManageableUsers.length ? unboundManageableUsers.map((item) => renderBindingCard(item)) : <p className="text-sm text-steel">当前没有待绑定账号。</p>}</div></section>
          </div>
        </section>
      ) : null}

      {activeTab === 'import' ? (
        <div className="flex flex-col gap-5">
          <section className="surface px-6 py-6 lg:px-7">
            <div className="section-head"><div><p className="eyebrow">批量导入</p><h2 className="section-title">员工档案批量导入</h2><p className="section-note mt-2">下载模板、导入文件、查看结果。</p></div><div className="flex flex-wrap gap-2"><button className="chip-button" onClick={() => void handleDownloadTemplate('employees')} type="button">下载员工模板</button></div></div>
            <div className="mt-5 grid gap-4 lg:grid-cols-[220px_1fr]">
              <label className="surface-subtle px-4 py-4"><span className="text-sm text-steel">导入类型</span><select className="toolbar-input mt-3 w-full" onChange={(event) => setSelectedImportType(event.target.value)} value={selectedImportType}>{IMPORT_TYPES.map((item) => (<option key={item.value} value={item.value}>{item.label}</option>))}</select></label>
              <label className="surface-subtle px-4 py-4"><span className="text-sm text-steel">选择文件</span><input accept=".csv,.xlsx,.xls" className="toolbar-input mt-3 w-full" id="employee-admin-import-input" onChange={(event) => setSelectedImportFile(event.target.files?.[0] ?? null)} style={{ height: 'auto', padding: '6px 10px' }} type="file" /><p className="mt-3 text-xs leading-5 text-steel">建议先下载模板后再导入，系统会返回任务处理结果和可导出的报告。</p></label>
            </div>
            <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-[var(--color-border)] pt-4"><div className="flex flex-wrap gap-3 text-sm text-steel"><span className="chip-button">处理中 {importStats.processing}</span><span className="chip-button">已完成 {importStats.completed}</span><span className="chip-button">总任务 {importStats.total}</span></div><button className="action-primary" disabled={isUploadingImport} onClick={() => void handleUploadImport()} type="button">{isUploadingImport ? '上传中...' : '创建导入任务'}</button></div>
          </section>
          <ImportJobTable onDeleteSelected={() => { void handleDeleteSelectedImportJobs(); }} onExport={(jobId) => { void handleExport(jobId); }} onToggleAll={toggleAllImportSelections} onToggleRow={toggleImportSelection} rows={importJobs.map((job) => ({ id: job.id, fileName: job.file_name, importType: job.import_type, status: job.status, totalRows: job.total_rows, successRows: job.success_rows, failedRows: job.failed_rows }))} selectedIds={selectedImportJobIds} />
          {isDeletingImportJobs ? <p className="surface px-5 py-4 text-sm text-steel">正在删除已选导入记录...</p> : null}
        </div>
      ) : null}

      {activeTab === 'handbook' ? (
        <section className="surface px-6 py-6 lg:px-7">
          <div className="section-head"><div><p className="eyebrow">员工手册</p><h2 className="section-title">上传并解析制度文档</h2><p className="section-note mt-2">上传制度文档并查看解析结果。</p></div></div>
          <div className="surface-subtle mt-5 px-5 py-5"><div className="flex flex-wrap items-start justify-between gap-4"><div><p className="text-sm font-medium text-ink">上传新手册</p><p className="mt-2 text-sm leading-6 text-steel">支持 PDF、Markdown、TXT。上传后自动解析。</p></div><label className={isUploadingHandbook ? 'action-secondary cursor-pointer' : 'action-primary cursor-pointer'}>{isUploadingHandbook ? '上传中...' : '选择手册文件'}<input accept=".pdf,.md,.txt" className="sr-only" onChange={(event) => { void handleUploadHandbook(event.target.files); event.currentTarget.value = ''; }} type="file" /></label></div></div>
          <div className="mt-5 grid gap-4">{handbooks.map((handbook) => (<article className="list-row p-5" key={handbook.id}><div className="flex flex-wrap items-start justify-between gap-3"><div><h3 className="text-base font-semibold text-ink">{handbook.title}</h3><p className="mt-1 text-sm text-steel">{handbook.file_name} · {handbook.file_type.toUpperCase()} · {new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(handbook.created_at))}</p></div><div className="flex flex-wrap items-center gap-2"><span className="status-pill" style={{ background: 'var(--color-success-bg)', color: 'var(--color-success)' }}>{handbook.parse_status === 'parsed' ? '已解析' : handbook.parse_status}</span><button className="action-danger px-4 py-2 text-xs" disabled={deletingHandbookId === handbook.id} onClick={() => void handleDeleteHandbook(handbook)} type="button">{deletingHandbookId === handbook.id ? '删除中...' : '删除'}</button></div></div><p className="mt-4 text-sm leading-6 text-steel">{handbook.summary ?? '当前尚未生成摘要。'}</p>{handbook.key_points_json.length ? (<div className="mt-4 grid gap-2">{handbook.key_points_json.map((point) => (<div className="surface-subtle px-4 py-3 text-sm leading-6 text-ink" key={point}>{point}</div>))}</div>) : null}{handbook.tags_json.length ? (<div className="mt-4 flex flex-wrap gap-2">{handbook.tags_json.map((tag) => (<span className="chip-button" key={tag}>{tag}</span>))}</div>) : null}</article>))}{!handbooks.length ? <p className="text-sm text-steel">当前还没有上传员工手册。</p> : null}</div>
        </section>
      ) : null}
    </AppShell>
  );
}


