import axios from 'axios';
import { Link } from 'react-router-dom';
import { useEffect, useMemo, useState } from 'react';

import { AppShell } from '../components/layout/AppShell';
import { useAuth } from '../hooks/useAuth';
import {
  bulkCreateUsers,
  bulkDeleteUsers,
  createDepartment,
  createManagedUser,
  deleteDepartment,
  deleteManagedUser,
  fetchDepartments,
  fetchUsers,
  updateDepartment,
  updateManagedUserDepartments,
  updateManagedUserPassword,
} from '../services/userAdminService';
import type { AdminUserCreatePayload, BulkFailureRecord, DepartmentRecord, UserProfile } from '../types/api';
import { assessPasswordStrength, generateSecurePassword } from '../utils/password';
import { getRoleLabel } from '../utils/roleAccess';

const ROLE_OPTIONS = [
  { value: 'admin', label: '管理员' },
  { value: 'hrbp', label: 'HRBP' },
  { value: 'manager', label: '主管' },
  { value: 'employee', label: '员工' },
] as const;

const ROLE_PRIORITY: Record<string, number> = { employee: 1, hrbp: 2, manager: 2, admin: 3 };
const ROLE_ALIAS_MAP: Record<string, string> = { admin: 'admin', hrbp: 'hrbp', manager: 'manager', employee: 'employee', 管理员: 'admin', 主管: 'manager', 员工: 'employee' };

type UserAdminTabKey = 'accounts' | 'single' | 'batch' | 'password' | 'scope' | 'department';

const USER_ADMIN_TABS: Array<{ key: UserAdminTabKey; label: string; note: string; adminOnly?: boolean }> = [
  { key: 'accounts', label: '账号列表', note: '查看、筛选和删除当前账号' },
  { key: 'single', label: '新增账号', note: '单个创建平台账号' },
  { key: 'batch', label: '批量创建', note: '批量导入账号' },
  { key: 'password', label: '重置密码', note: '更新指定账号密码' },
  { key: 'scope', label: '设置部门', note: '绑定 HRBP / 主管部门范围' },
  { key: 'department', label: '部门管理', note: '新增、编辑和删除部门', adminOnly: true },
];

function getAssignableRoleOptions(role: string | null | undefined) {
  const priority = role ? ROLE_PRIORITY[role] ?? 0 : 0;
  return ROLE_OPTIONS.filter((item) => (ROLE_PRIORITY[item.value] ?? 0) < priority);
}

function resolveError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const payload = error.response?.data as { message?: string; detail?: string } | undefined;
    return payload?.message ?? payload?.detail ?? '管理员操作失败。';
  }
  return '管理员操作失败。';
}

function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value));
}

function formatDepartmentNames(user: UserProfile): string {
  if (!user.departments.length) {
    return user.role === 'hrbp' || user.role === 'manager' ? '未绑定部门' : '不适用';
  }
  return user.departments.map((item) => item.name).join('、');
}

function parseBatchLines(text: string, assignableRoles: string[]): AdminUserCreatePayload[] {
  return text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const parts = line.split(/[,\t]/).map((item) => item.trim()).filter(Boolean);
      if (parts.length < 3) throw new Error(`批量导入格式错误：${line}`);
      const role = ROLE_ALIAS_MAP[parts[1]];
      if (!role) throw new Error(`未识别的角色：${parts[1]}`);
      if (!assignableRoles.includes(role)) throw new Error(`当前身份不能创建角色：${parts[1]}`);
      return { email: parts[0], password: parts[2], role, id_card_no: parts[3] || null, department_ids: [] };
    });
}

export function UserAdminPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin';
  const [activeTab, setActiveTab] = useState<UserAdminTabKey>('accounts');
  const [users, setUsers] = useState<UserProfile[]>([]);
  const [departments, setDepartments] = useState<DepartmentRecord[]>([]);
  const [keyword, setKeyword] = useState('');
  const [roleFilter, setRoleFilter] = useState('');
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [singleForm, setSingleForm] = useState<AdminUserCreatePayload>({ email: '', password: '', role: 'employee', id_card_no: null, department_ids: [] });
  const [batchInput, setBatchInput] = useState('');
  const [passwordTargetId, setPasswordTargetId] = useState('');
  const [scopeTargetId, setScopeTargetId] = useState('');
  const [scopeDepartmentIds, setScopeDepartmentIds] = useState<string[]>([]);
  const [newPassword, setNewPassword] = useState('');
  const [confirmNewPassword, setConfirmNewPassword] = useState('');
  const [departmentId, setDepartmentId] = useState<string | null>(null);
  const [departmentName, setDepartmentName] = useState('');
  const [departmentDescription, setDepartmentDescription] = useState('');
  const [departmentStatus, setDepartmentStatus] = useState('active');
  const [isLoading, setIsLoading] = useState(true);
  const [busyKey, setBusyKey] = useState('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [operationFailures, setOperationFailures] = useState<BulkFailureRecord[]>([]);

  const assignableRoleOptions = useMemo(() => getAssignableRoleOptions(user?.role), [user?.role]);
  const assignableRoles = useMemo(() => assignableRoleOptions.map((item) => item.value as string), [assignableRoleOptions]);
  const passwordStrength = useMemo(() => assessPasswordStrength(newPassword), [newPassword]);
  const singlePasswordStrength = useMemo(() => assessPasswordStrength(singleForm.password), [singleForm.password]);
  const manageableUsers = useMemo(() => users.filter((item) => item.id !== user?.id), [users, user?.id]);
  const scopeUsers = useMemo(() => manageableUsers.filter((item) => item.role === 'hrbp' || item.role === 'manager'), [manageableUsers]);
  const visibleTabs = useMemo(() => USER_ADMIN_TABS.filter((item) => !item.adminOnly || isAdmin), [isAdmin]);
  const activeTabMeta = useMemo(() => visibleTabs.find((item) => item.key === activeTab) ?? visibleTabs[0], [activeTab, visibleTabs]);

  async function loadData() {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const [userResponse, departmentResponse] = await Promise.all([
        fetchUsers({ page: 1, page_size: 100, keyword: keyword || undefined, role: roleFilter || undefined }),
        fetchDepartments(),
      ]);
      setUsers(userResponse.items);
      setDepartments(departmentResponse.items);
    } catch (error) {
      setErrorMessage(resolveError(error));
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => { void loadData(); }, [keyword, roleFilter]);
  useEffect(() => {
    if (assignableRoleOptions.length && !assignableRoles.includes(singleForm.role)) {
      setSingleForm((current) => ({ ...current, role: assignableRoleOptions[0].value, department_ids: [], id_card_no: current.id_card_no ?? null }));
    }
  }, [assignableRoleOptions, assignableRoles, singleForm.role]);

  function clearFeedback() {
    setErrorMessage(null);
    setSuccessMessage(null);
    setOperationFailures([]);
  }

  function resetDepartmentForm() {
    setDepartmentId(null);
    setDepartmentName('');
    setDepartmentDescription('');
    setDepartmentStatus('active');
  }

  function toggleSingleDepartment(departmentIdValue: string) {
    setSingleForm((current) => ({
      ...current,
      department_ids: current.department_ids?.includes(departmentIdValue)
        ? current.department_ids.filter((item) => item !== departmentIdValue)
        : [...(current.department_ids ?? []), departmentIdValue],
    }));
  }

  function toggleScopeDepartment(departmentIdValue: string) {
    setScopeDepartmentIds((current) => current.includes(departmentIdValue) ? current.filter((item) => item !== departmentIdValue) : [...current, departmentIdValue]);
  }

  async function handleCreateUser() {
    clearFeedback();
    if (!singleForm.email.trim()) return setErrorMessage('请填写登录邮箱。');
    if (singleForm.password.length < 8) return setErrorMessage('初始密码长度不能少于 8 位。');
    if ((singleForm.role === 'hrbp' || singleForm.role === 'manager') && !(singleForm.department_ids?.length ?? 0)) {
      return setErrorMessage('新增 HRBP 或主管账号时，至少需要绑定一个部门。');
    }
    setBusyKey('create');
    try {
      await createManagedUser({
        ...singleForm,
        email: singleForm.email.trim(),
        id_card_no: singleForm.id_card_no?.trim() ? singleForm.id_card_no.trim() : null,
        department_ids: singleForm.department_ids ?? [],
      });
      setSuccessMessage('账号已创建。');
      setSingleForm({ email: '', password: '', role: assignableRoleOptions[0]?.value ?? 'employee', id_card_no: null, department_ids: [] });
      await loadData();
    } catch (error) {
      setErrorMessage(resolveError(error));
    } finally {
      setBusyKey('');
    }
  }

  async function handleBatchCreate() {
    clearFeedback();
    setBusyKey('batch');
    try {
      const response = await bulkCreateUsers(parseBatchLines(batchInput, assignableRoles));
      setOperationFailures(response.failed);
      setSuccessMessage(`批量创建完成，成功 ${response.created.length} 个，失败 ${response.failed.length} 个。`);
      setBatchInput('');
      await loadData();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : resolveError(error));
    } finally {
      setBusyKey('');
    }
  }

  async function handleUpdatePassword() {
    clearFeedback();
    if (!passwordTargetId) return setErrorMessage('请先选择目标账号。');
    if (newPassword.length < 8) return setErrorMessage('新密码长度不能少于 8 位。');
    if (newPassword !== confirmNewPassword) return setErrorMessage('两次输入的新密码不一致。');
    setBusyKey('password');
    try {
      await updateManagedUserPassword(passwordTargetId, newPassword);
      setSuccessMessage('密码已重置。');
      setNewPassword('');
      setConfirmNewPassword('');
      await loadData();
    } catch (error) {
      setErrorMessage(resolveError(error));
    } finally {
      setBusyKey('');
    }
  }

  async function handleSaveScope() {
    clearFeedback();
    if (!scopeTargetId) return setErrorMessage('请先选择目标账号。');
    if (!scopeDepartmentIds.length) return setErrorMessage('请至少选择一个部门。');
    setBusyKey('scope');
    try {
      await updateManagedUserDepartments(scopeTargetId, scopeDepartmentIds);
      setSuccessMessage('账号部门绑定已更新。');
      await loadData();
    } catch (error) {
      setErrorMessage(resolveError(error));
    } finally {
      setBusyKey('');
    }
  }

  async function handleSaveDepartment() {
    clearFeedback();
    if (!departmentName.trim()) return setErrorMessage('请填写部门名称。');
    setBusyKey('department');
    try {
      const payload = { name: departmentName.trim(), description: departmentDescription.trim(), status: departmentStatus };
      if (departmentId) await updateDepartment(departmentId, payload);
      else await createDepartment(payload);
      setSuccessMessage(departmentId ? '部门已更新。' : '部门已新增。');
      resetDepartmentForm();
      await loadData();
    } catch (error) {
      setErrorMessage(resolveError(error));
    } finally {
      setBusyKey('');
    }
  }

  async function handleDeleteDepartment(target: DepartmentRecord) {
    if (!window.confirm(`确认删除部门“${target.name}”吗？`)) return;
    clearFeedback();
    setBusyKey(`department-delete-${target.id}`);
    try {
      await deleteDepartment(target.id);
      setSuccessMessage('部门已删除。');
      if (departmentId === target.id) resetDepartmentForm();
      await loadData();
    } catch (error) {
      setErrorMessage(resolveError(error));
    } finally {
      setBusyKey('');
    }
  }

  async function handleDeleteUser(target: UserProfile) {
    if (!window.confirm(`确认删除账号 ${target.email} 吗？`)) return;
    clearFeedback();
    setBusyKey(`delete-${target.id}`);
    try {
      await deleteManagedUser(target.id);
      setSuccessMessage('账号已删除。');
      setSelectedIds((current) => current.filter((item) => item !== target.id));
      await loadData();
    } catch (error) {
      setErrorMessage(resolveError(error));
    } finally {
      setBusyKey('');
    }
  }

  async function handleBulkDelete() {
    if (!selectedIds.length) return setErrorMessage('请先选择要删除的账号。');
    if (!window.confirm(`确认删除已选中的 ${selectedIds.length} 个账号吗？`)) return;
    clearFeedback();
    setBusyKey('bulk-delete');
    try {
      const response = await bulkDeleteUsers(selectedIds);
      setOperationFailures(response.failed);
      setSuccessMessage(`批量删除完成，成功 ${response.deleted_user_ids.length} 个，失败 ${response.failed.length} 个。`);
      setSelectedIds([]);
      await loadData();
    } catch (error) {
      setErrorMessage(resolveError(error));
    } finally {
      setBusyKey('');
    }
  }

  return (
    <AppShell
      title="平台账号与部门管理"
      description="按模块切换处理账号、部门和部门范围。"
      actions={<><Link className="chip-button" to="/workspace">返回工作台</Link><button className="action-secondary" onClick={() => void loadData()} type="button">刷新数据</button></>}
    >
      {errorMessage ? <p className="surface px-5 py-4 text-sm" style={{ color: 'var(--color-danger)' }}>{errorMessage}</p> : null}
      {successMessage ? <p className="surface px-5 py-4 text-sm" style={{ color: 'var(--color-success)' }}>{successMessage}</p> : null}
      {operationFailures.length ? <section className="surface px-6 py-6 lg:px-7">{operationFailures.map((item) => <p className="text-sm text-steel" key={`${item.identifier}-${item.message}`}>{item.identifier}：{item.message}</p>)}</section> : null}

      <section className="surface px-6 py-6 lg:px-7">
        <div className="section-head">
          <div>
            <p className="eyebrow">模块切换</p>
            <h2 className="section-title">平台账号与部门管理</h2>
          </div>
          <div className="cursor-help text-xs text-steel" style={{ border: '1px solid var(--color-border)', borderRadius: 6, padding: '4px 12px' }} title={activeTabMeta?.note}>模块说明</div>
        </div>
        <div className="mt-5 flex flex-wrap gap-2">
          {visibleTabs.map((item) => (
            <button className={activeTab === item.key ? 'chip-button chip-button-active' : 'chip-button'} key={item.key} onClick={() => setActiveTab(item.key)} type="button">
              {item.label}
            </button>
          ))}
        </div>
      </section>

      {activeTab === 'department' && isAdmin ? (
        <section className="grid gap-5 xl:grid-cols-[380px_minmax(0,1fr)]">
          <aside className="surface px-6 py-6 lg:px-7">
            <div className="section-head"><div><p className="eyebrow">部门管理</p><h2 className="section-title">新增 / 修改 / 删除部门</h2></div></div>
            <div className="mt-5 grid gap-4">
              <input className="toolbar-input" onChange={(event) => setDepartmentName(event.target.value)} placeholder="部门名称" value={departmentName} />
              <textarea className="toolbar-textarea w-full" onChange={(event) => setDepartmentDescription(event.target.value)} placeholder="部门说明（可选）" value={departmentDescription} />
              <select className="toolbar-input" onChange={(event) => setDepartmentStatus(event.target.value)} value={departmentStatus}><option value="active">启用</option><option value="inactive">停用</option></select>
              <div className="flex gap-3"><button className="action-primary" disabled={busyKey === 'department'} onClick={() => void handleSaveDepartment()} type="button">{busyKey === 'department' ? '保存中...' : departmentId ? '保存修改' : '新增部门'}</button><button className="action-secondary" onClick={resetDepartmentForm} type="button">清空</button></div>
            </div>
          </aside>
          <section className="surface px-6 py-6 lg:px-7">
            <div className="section-head"><div><p className="eyebrow">部门列表</p><h2 className="section-title">当前已配置部门</h2></div></div>
            <div className="mt-5 grid gap-3">
              {departments.map((item) => (
                <div className="surface-subtle px-4 py-4" key={item.id}>
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div><p className="font-semibold text-ink">{item.name}</p><p className="mt-1 text-sm text-steel">{item.description || '暂无说明'}</p></div>
                    <div className="flex gap-2">
                      <button className="action-secondary px-4 py-2 text-xs" onClick={() => { setDepartmentId(item.id); setDepartmentName(item.name); setDepartmentDescription(item.description ?? ''); setDepartmentStatus(item.status); }} type="button">编辑</button>
                      <button className="action-danger px-4 py-2 text-xs" disabled={busyKey === `department-delete-${item.id}`} onClick={() => void handleDeleteDepartment(item)} type="button">{busyKey === `department-delete-${item.id}` ? '删除中...' : '删除'}</button>
                    </div>
                  </div>
                </div>
              ))}
              {!departments.length ? <p className="text-sm text-steel">当前还没有部门，请先新增部门。</p> : null}
            </div>
          </section>
        </section>
      ) : null}

      <section className={activeTab === 'accounts' ? 'grid gap-5' : 'grid gap-5 xl:max-w-[760px]'}>
        {activeTab !== 'accounts' ? (
        <aside className="surface px-6 py-6 lg:px-7">
          <div className="section-head">
            <div>
              <p className="eyebrow">账号操作</p>
              <h2 className="section-title">{activeTabMeta?.label ?? '账号操作'}</h2>
            </div>
          </div>

          {activeTab === 'single' ? (
            <div className="mt-5 grid gap-4">
              <input className="toolbar-input" onChange={(event) => setSingleForm((current) => ({ ...current, email: event.target.value }))} placeholder="登录邮箱" value={singleForm.email} />
              <input className="toolbar-input" onChange={(event) => setSingleForm((current) => ({ ...current, id_card_no: event.target.value || null }))} placeholder="身份证号，用于自动匹配员工档案" value={singleForm.id_card_no ?? ''} />
              <div className="flex gap-2">
                <input className="toolbar-input flex-1" onChange={(event) => setSingleForm((current) => ({ ...current, password: event.target.value }))} placeholder="初始密码" value={singleForm.password} />
                <button className="action-secondary px-4" onClick={() => setSingleForm((current) => ({ ...current, password: generateSecurePassword() }))} type="button">生成密码</button>
              </div>
              <div className="surface-subtle px-4 py-4"><p className="text-sm text-steel">密码强度：{singlePasswordStrength.label}</p><p className="mt-2 text-xs text-steel">{singlePasswordStrength.hint}</p></div>
              <select className="toolbar-input" onChange={(event) => setSingleForm((current) => ({ ...current, role: event.target.value, department_ids: [] }))} value={singleForm.role}>
                {assignableRoleOptions.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
              </select>
              {(singleForm.role === 'hrbp' || singleForm.role === 'manager') ? (
                <div className="surface-subtle px-4 py-4">
                  <p className="text-sm font-medium text-ink">绑定部门</p>
                  <div className="mt-3 grid gap-2">
                    {departments.map((item) => (
                      <label className="flex items-center gap-3 text-sm text-ink" key={item.id}>
                        <input checked={singleForm.department_ids?.includes(item.id) ?? false} onChange={() => toggleSingleDepartment(item.id)} type="checkbox" />
                        <span>{item.name}</span>
                      </label>
                    ))}
                    {!departments.length ? <p className="text-sm text-steel">没有可选部门，请先新增部门。</p> : null}
                  </div>
                </div>
              ) : null}
              <button className="action-primary" disabled={busyKey === 'create'} onClick={() => void handleCreateUser()} type="button">{busyKey === 'create' ? '创建中...' : '创建账号'}</button>
            </div>
          ) : null}

          {activeTab === 'batch' ? (
            <div className="mt-5 grid gap-4">
              <textarea className="toolbar-textarea w-full" onChange={(event) => setBatchInput(event.target.value)} placeholder={'a@company.com,employee,Password123!,310101199001010123\nb@company.com,employee,Password123!'} value={batchInput} />
              <p className="text-sm text-steel">批量格式支持：邮箱,角色,密码,身份证号。第四列可留空，批量模式默认不带部门绑定。</p>
              <button className="action-primary" disabled={busyKey === 'batch'} onClick={() => void handleBatchCreate()} type="button">{busyKey === 'batch' ? '创建中...' : '执行批量创建'}</button>
            </div>
          ) : null}

          {activeTab === 'password' ? (
            <div className="mt-5 grid gap-4">
              <select className="toolbar-input" onChange={(event) => setPasswordTargetId(event.target.value)} value={passwordTargetId}>
                <option value="">请选择目标账号</option>
                {manageableUsers.map((item) => <option key={item.id} value={item.id}>{item.email} · {getRoleLabel(item.role)}</option>)}
              </select>
              <div className="flex gap-2">
                <input className="toolbar-input flex-1" onChange={(event) => setNewPassword(event.target.value)} placeholder="新密码" value={newPassword} />
                <button className="action-secondary px-4" onClick={() => { const password = generateSecurePassword(); setNewPassword(password); setConfirmNewPassword(password); }} type="button">生成密码</button>
              </div>
              <div className="surface-subtle px-4 py-4"><p className="text-sm text-steel">密码强度：{passwordStrength.label}</p><p className="mt-2 text-xs text-steel">{passwordStrength.hint}</p></div>
              <input className="toolbar-input" onChange={(event) => setConfirmNewPassword(event.target.value)} placeholder="确认新密码" value={confirmNewPassword} />
              <button className="action-primary" disabled={busyKey === 'password'} onClick={() => void handleUpdatePassword()} type="button">{busyKey === 'password' ? '更新中...' : '更新密码'}</button>
            </div>
          ) : null}

          {activeTab === 'scope' ? (
            <div className="mt-5 grid gap-4">
              <select className="toolbar-input" onChange={(event) => { const target = scopeUsers.find((item) => item.id === event.target.value); setScopeTargetId(event.target.value); setScopeDepartmentIds(target?.departments.map((item) => item.id) ?? []); }} value={scopeTargetId}>
                <option value="">请选择 HRBP 或主管账号</option>
                {scopeUsers.map((item) => <option key={item.id} value={item.id}>{item.email} · {getRoleLabel(item.role)}</option>)}
              </select>
              <div className="surface-subtle px-4 py-4">
                <p className="text-sm font-medium text-ink">绑定部门</p>
                <div className="mt-3 grid gap-2">
                  {departments.map((item) => (
                    <label className="flex items-center gap-3 text-sm text-ink" key={item.id}>
                      <input checked={scopeDepartmentIds.includes(item.id)} onChange={() => toggleScopeDepartment(item.id)} type="checkbox" />
                      <span>{item.name}</span>
                    </label>
                  ))}
                </div>
              </div>
              <button className="action-primary" disabled={busyKey === 'scope'} onClick={() => void handleSaveScope()} type="button">{busyKey === 'scope' ? '保存中...' : '保存部门绑定'}</button>
            </div>
          ) : null}
        </aside>
        ) : null}

        {activeTab === 'accounts' ? (
        <section className="surface px-6 py-6 lg:px-7">
          <div className="section-head">
            <div><p className="eyebrow">账号列表</p><h2 className="section-title">当前可管理账号</h2></div>
            <div className="flex flex-wrap gap-2"><span className="chip-button">当前登录：{user?.email}</span><button className="action-danger" disabled={busyKey === 'bulk-delete' || !selectedIds.length} onClick={() => void handleBulkDelete()} type="button">{busyKey === 'bulk-delete' ? '删除中...' : `批量删除${selectedIds.length ? `（${selectedIds.length}）` : ''}`}</button></div>
          </div>
          <div className="mt-5 grid gap-3 lg:grid-cols-[minmax(0,1fr)_220px_auto]">
            <input className="toolbar-input" onChange={(event) => setKeyword(event.target.value)} placeholder="按邮箱搜索账号" value={keyword} />
            <select className="toolbar-input" onChange={(event) => setRoleFilter(event.target.value)} value={roleFilter}>
              <option value="">全部角色</option>
              {[{ value: user?.role ?? '', label: user?.role ? getRoleLabel(user.role) : '' }, ...assignableRoleOptions].filter((item, index, array) => item.value && array.findIndex((x) => x.value === item.value) === index).map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
            </select>
            <div className="flex items-center justify-end text-sm text-steel">已选 {selectedIds.length} 个账号</div>
          </div>

          {isLoading ? <p className="mt-5 text-sm text-steel">正在加载账号与部门数据...</p> : null}

          <div className="table-shell mt-5">
            <div className="overflow-x-auto">
              <table className="table-lite">
                <thead><tr><th className="w-12"><input checked={manageableUsers.length > 0 && selectedIds.length === manageableUsers.length} onChange={(event) => setSelectedIds(event.target.checked ? manageableUsers.map((item) => item.id) : [])} type="checkbox" /></th><th>账号信息</th><th>角色</th><th>绑定部门</th><th>创建时间</th><th>安全状态</th><th className="min-w-[220px]">操作</th></tr></thead>
                <tbody>
                  {users.map((item) => {
                    const isCurrentUser = item.id === user?.id;
                    const canEditScope = isAdmin && !isCurrentUser && (item.role === 'hrbp' || item.role === 'manager');
                    return (
                      <tr key={item.id}>
                        <td><input checked={selectedIds.includes(item.id)} disabled={isCurrentUser} onChange={() => setSelectedIds((current) => current.includes(item.id) ? current.filter((x) => x !== item.id) : [...current, item.id])} type="checkbox" /></td>
                        <td><div className="font-medium text-ink">{item.email}</div><div className="mt-1 text-xs text-steel">{item.id_card_no ? `身份证号：${item.id_card_no}` : (isCurrentUser ? '当前登录账号' : '可管理账号')}</div></td>
                        <td>{getRoleLabel(item.role)}</td>
                        <td><span className="text-sm text-ink">{formatDepartmentNames(item)}</span></td>
                        <td>{formatDateTime(item.created_at)}</td>
                        <td>{item.must_change_password ? <span className="status-pill" style={{ background: 'var(--color-warning-bg)', color: 'var(--color-warning)' }}>首次登录需改密</span> : <span className="status-pill" style={{ background: 'var(--color-success-bg)', color: 'var(--color-success)' }}>正常</span>}</td>
                        <td>{isCurrentUser ? <span className="text-xs text-steel">请到账号设置修改自己的密码。</span> : <div className="flex flex-wrap gap-2"><button className="action-secondary px-4 py-2 text-xs" onClick={() => { setPasswordTargetId(item.id); setActiveTab('password'); }} type="button">重置密码</button>{canEditScope ? <button className="action-secondary px-4 py-2 text-xs" onClick={() => { setScopeTargetId(item.id); setScopeDepartmentIds(item.departments.map((department) => department.id)); setActiveTab('scope'); }} type="button">设置部门</button> : null}<button className="action-danger px-4 py-2 text-xs" disabled={busyKey === `delete-${item.id}`} onClick={() => void handleDeleteUser(item)} type="button">{busyKey === `delete-${item.id}` ? '删除中...' : '删除账号'}</button></div>}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </section>
        ) : null}
      </section>
    </AppShell>
  );
}
