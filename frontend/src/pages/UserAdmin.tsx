import axios from 'axios';
import { Link } from 'react-router-dom';
import { useEffect, useMemo, useState } from 'react';

import { AppShell } from '../components/layout/AppShell';
import { useAuth } from '../hooks/useAuth';
import {
  bulkCreateUsers,
  bulkDeleteUsers,
  createManagedUser,
  deleteManagedUser,
  fetchUsers,
  updateManagedUserPassword,
} from '../services/userAdminService';
import type { AdminUserCreatePayload, BulkFailureRecord, UserProfile } from '../types/api';
import { assessPasswordStrength, generateSecurePassword } from '../utils/password';
import { getRoleLabel } from '../utils/roleAccess';

const ROLE_OPTIONS = [
  { value: 'admin', label: '管理员' },
  { value: 'hrbp', label: 'HRBP' },
  { value: 'manager', label: '主管' },
  { value: 'employee', label: '员工' },
] as const;

const ROLE_ALIAS_MAP: Record<string, string> = {
  admin: 'admin',
  管理员: 'admin',
  hrbp: 'hrbp',
  HRBP: 'hrbp',
  manager: 'manager',
  主管: 'manager',
  employee: 'employee',
  员工: 'employee',
};

const ROLE_PRIORITY: Record<string, number> = {
  employee: 1,
  hrbp: 2,
  manager: 2,
  admin: 3,
};

type PanelMode = 'single' | 'batch' | 'password';

type ValidationDetail = {
  loc?: Array<string | number>;
  msg?: string;
};

type IssuedPasswordNotice = {
  email: string;
  password: string;
  context: 'create' | 'reset';
};

function getFieldLabel(field: string): string {
  const mapping: Record<string, string> = {
    email: '邮箱',
    password: '密码',
    role: '角色',
    new_password: '新密码',
    current_password: '当前密码',
    body: '提交内容',
  };
  return mapping[field] ?? field;
}

function getAssignableRoleOptions(role: string | null | undefined) {
  const operatorPriority = role ? ROLE_PRIORITY[role] ?? 0 : 0;
  return ROLE_OPTIONS.filter((option) => (ROLE_PRIORITY[option.value] ?? 0) < operatorPriority);
}

function formatValidationDetails(details: unknown): string | null {
  if (!Array.isArray(details)) {
    return null;
  }

  const messages = details
    .map((item) => item as ValidationDetail)
    .map((item) => {
      const field = item.loc?.[item.loc.length - 1];
      const fieldLabel = typeof field === 'string' ? getFieldLabel(field) : '输入项';
      const rawMessage = item.msg ?? '输入不符合要求。';

      if (rawMessage.includes('valid email address')) {
        return `${fieldLabel}格式不正确。`;
      }
      if (rawMessage.includes('at least 8 characters')) {
        return `${fieldLabel}长度不能少于 8 位。`;
      }
      if (rawMessage.includes('Field required')) {
        return `请填写${fieldLabel}。`;
      }
      return `${fieldLabel}：${rawMessage}`;
    })
    .filter(Boolean);

  return messages.length ? messages.join(' ') : null;
}

function resolveError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const payload = error.response?.data as { message?: string; detail?: string | ValidationDetail[]; details?: ValidationDetail[] } | undefined;
    const detailMessage = typeof payload?.detail === 'string' ? payload.detail : formatValidationDetails(payload?.detail ?? payload?.details);
    return payload?.message ?? detailMessage ?? '账号管理操作失败。';
  }
  return '账号管理操作失败。';
}

function parseBatchLines(text: string, assignableRoles: string[]): AdminUserCreatePayload[] {
  return text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const parts = line.split(/[，,\t]/).map((item) => item.trim()).filter(Boolean);
      if (parts.length < 3) {
        throw new Error(`批量导入格式错误：${line}`);
      }
      const role = ROLE_ALIAS_MAP[parts[1]];
      if (!role) {
        throw new Error(`未识别的角色：${parts[1]}`);
      }
      if (!assignableRoles.includes(role)) {
        throw new Error(`当前身份不能创建角色：${parts[1]}`);
      }
      return {
        email: parts[0],
        role,
        password: parts[2],
      };
    });
}

function validateSingleForm(form: AdminUserCreatePayload, assignableRoles: string[]): string | null {
  const email = form.email.trim();
  const password = form.password;
  const role = form.role.trim().toLowerCase();

  if (!email) {
    return '请填写登录邮箱。';
  }
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    return '请输入正确的邮箱格式。';
  }
  if (!password) {
    return '请填写初始密码。';
  }
  if (password.length < 8) {
    return '初始密码长度不能少于 8 位。';
  }
  if (!assignableRoles.includes(role)) {
    return '当前身份不能创建该角色账号。';
  }
  return null;
}

export function UserAdminPage() {
  const { user } = useAuth();
  const [items, setItems] = useState<UserProfile[]>([]);
  const [total, setTotal] = useState(0);
  const [keyword, setKeyword] = useState('');
  const [roleFilter, setRoleFilter] = useState('');
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [panelMode, setPanelMode] = useState<PanelMode>('single');
  const [singleForm, setSingleForm] = useState<AdminUserCreatePayload>({
    email: '',
    password: '',
    role: 'employee',
  });
  const [batchInput, setBatchInput] = useState('');
  const [passwordTargetId, setPasswordTargetId] = useState('');
  const [passwordTargetLabel, setPasswordTargetLabel] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmNewPassword, setConfirmNewPassword] = useState('');
  const [issuedPasswordNotice, setIssuedPasswordNotice] = useState<IssuedPasswordNotice | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isCreating, setIsCreating] = useState(false);
  const [isBatchCreating, setIsBatchCreating] = useState(false);
  const [isPasswordUpdating, setIsPasswordUpdating] = useState(false);
  const [isDeleting, setIsDeleting] = useState<string | null>(null);
  const [isBulkDeleting, setIsBulkDeleting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [operationFailures, setOperationFailures] = useState<BulkFailureRecord[]>([]);

  const assignableRoleOptions = useMemo(() => getAssignableRoleOptions(user?.role), [user?.role]);
  const assignableRoles = useMemo(() => assignableRoleOptions.map((option) => option.value as string), [assignableRoleOptions]);

  async function loadUsers() {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const response = await fetchUsers({
        page: 1,
        page_size: 100,
        keyword: keyword || undefined,
        role: roleFilter || undefined,
      });
      setItems(response.items);
      setTotal(response.total);
      setPasswordTargetLabel((current) => {
        if (!passwordTargetId) return current;
        const matched = response.items.find((item) => item.id === passwordTargetId);
        if (!matched) {
          setPasswordTargetId('');
          return '';
        }
        return matched.email;
      });
    } catch (error) {
      setErrorMessage(resolveError(error));
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    void loadUsers();
  }, [keyword, roleFilter]);

  useEffect(() => {
    if (assignableRoleOptions.length > 0 && !assignableRoles.some((role) => role === singleForm.role)) {
      setSingleForm((current) => ({ ...current, role: assignableRoleOptions[0].value }));
    }
  }, [assignableRoleOptions, assignableRoles, singleForm.role]);

  const metrics = useMemo(() => {
    const adminCount = items.filter((item) => item.role === 'admin').length;
    const hrbpCount = items.filter((item) => item.role === 'hrbp').length;
    const managerCount = items.filter((item) => item.role === 'manager').length;
    const employeeCount = items.filter((item) => item.role === 'employee').length;
    const passwordUpdatePendingCount = items.filter((item) => item.must_change_password).length;
    return { adminCount, hrbpCount, managerCount, employeeCount, passwordUpdatePendingCount };
  }, [items]);

  const manageableUsers = useMemo(() => items.filter((item) => item.id !== user?.id), [items, user?.id]);
  const singlePasswordStrength = useMemo(() => assessPasswordStrength(singleForm.password), [singleForm.password]);
  const resetPasswordStrength = useMemo(() => assessPasswordStrength(newPassword), [newPassword]);

  const panelMeta = useMemo(() => {
    return {
      single: {
        eyebrow: '新增账号',
        title: '开通单个账号',
        note: user?.role === 'admin'
          ? '可创建 HRBP、主管和员工账号。'
          : '当前身份只能创建员工账号。',
      },
      batch: {
        eyebrow: '批量开通',
        title: '导入多名账号',
        note: '系统会校验可创建角色。',
      },
      password: {
        eyebrow: '密码管理',
        title: '重置用户密码',
        note: '只能重置低权限账号密码。',
      },
    } as const;
  }, [user?.role]);

  function clearFeedback() {
    setErrorMessage(null);
    setSuccessMessage(null);
    setOperationFailures([]);
  }

  function toggleSelection(userId: string) {
    setSelectedIds((current) => current.includes(userId) ? current.filter((item) => item !== userId) : [...current, userId]);
  }

  function selectPasswordTarget(targetUser: UserProfile) {
    setPanelMode('password');
    setPasswordTargetId(targetUser.id);
    setPasswordTargetLabel(targetUser.email);
    setNewPassword('');
    setConfirmNewPassword('');
    clearFeedback();
  }

  function applyGeneratedSinglePassword() {
    const generatedPassword = generateSecurePassword();
    setSingleForm((current) => ({ ...current, password: generatedPassword }));
    clearFeedback();
  }

  function applyGeneratedResetPassword() {
    const generatedPassword = generateSecurePassword();
    setNewPassword(generatedPassword);
    setConfirmNewPassword(generatedPassword);
    clearFeedback();
  }

  async function handleCreateUser() {
    clearFeedback();
    const normalizedForm = {
      ...singleForm,
      email: singleForm.email.trim(),
      role: singleForm.role.trim().toLowerCase(),
    };
    const validationMessage = validateSingleForm(normalizedForm, assignableRoles);
    if (validationMessage) {
      setErrorMessage(validationMessage);
      return;
    }

    setIsCreating(true);
    try {
      const createdUser = await createManagedUser(normalizedForm);
      setSuccessMessage('账号已创建。请安全告知初始密码，并提醒用户首次登录后立即修改密码。');
      setIssuedPasswordNotice({ email: createdUser.email, password: normalizedForm.password, context: 'create' });
      setSingleForm({ email: '', password: '', role: assignableRoleOptions[0]?.value ?? 'employee' });
      await loadUsers();
    } catch (error) {
      setErrorMessage(resolveError(error));
    } finally {
      setIsCreating(false);
    }
  }

  async function handleBatchCreate() {
    clearFeedback();
    setIsBatchCreating(true);
    try {
      const payloads = parseBatchLines(batchInput, assignableRoles);
      const response = await bulkCreateUsers(payloads);
      setOperationFailures(response.failed);
      setSuccessMessage(`批量创建完成，成功 ${response.created.length} 个，失败 ${response.failed.length} 个。已创建账号首次登录都需要先修改密码。`);
      if (response.created.length > 0) {
        setBatchInput('');
      }
      setIssuedPasswordNotice(null);
      await loadUsers();
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : resolveError(error));
    } finally {
      setIsBatchCreating(false);
    }
  }

  async function handleUpdatePassword() {
    clearFeedback();
    if (!passwordTargetId) {
      setErrorMessage('请先选择需要修改密码的账号。');
      return;
    }
    if (!newPassword || !confirmNewPassword) {
      setErrorMessage('请填写新密码和确认密码。');
      return;
    }
    if (newPassword !== confirmNewPassword) {
      setErrorMessage('两次输入的新密码不一致。');
      return;
    }
    if (newPassword.length < 8) {
      setErrorMessage('新密码长度不能少于 8 位。');
      return;
    }

    setIsPasswordUpdating(true);
    try {
      await updateManagedUserPassword(passwordTargetId, newPassword);
      setSuccessMessage('密码已重置。请将新密码安全告知用户，系统会要求其下次登录后立即修改密码。');
      setIssuedPasswordNotice({ email: passwordTargetLabel || '目标账号', password: newPassword, context: 'reset' });
      setNewPassword('');
      setConfirmNewPassword('');
      await loadUsers();
    } catch (error) {
      setErrorMessage(resolveError(error));
    } finally {
      setIsPasswordUpdating(false);
    }
  }

  async function handleDeleteUser(targetUser: UserProfile) {
    if (!window.confirm(`确认删除账号 ${targetUser.email} 吗？此操作不可撤销。`)) {
      return;
    }
    clearFeedback();
    setIsDeleting(targetUser.id);
    try {
      await deleteManagedUser(targetUser.id);
      setSuccessMessage('账号已删除。');
      setSelectedIds((current) => current.filter((item) => item !== targetUser.id));
      if (passwordTargetId === targetUser.id) {
        setPasswordTargetId('');
        setPasswordTargetLabel('');
        setNewPassword('');
        setConfirmNewPassword('');
      }
      await loadUsers();
    } catch (error) {
      setErrorMessage(resolveError(error));
    } finally {
      setIsDeleting(null);
    }
  }

  async function handleBulkDelete() {
    if (selectedIds.length === 0) {
      setErrorMessage('请先选择需要批量删除的账号。');
      return;
    }
    if (!window.confirm(`确认批量删除已选中的 ${selectedIds.length} 个账号吗？`)) {
      return;
    }
    clearFeedback();
    setIsBulkDeleting(true);
    try {
      const response = await bulkDeleteUsers(selectedIds);
      setOperationFailures(response.failed);
      setSuccessMessage(`批量删除完成，成功 ${response.deleted_user_ids.length} 个，失败 ${response.failed.length} 个。`);
      if (passwordTargetId && response.deleted_user_ids.includes(passwordTargetId)) {
        setPasswordTargetId('');
        setPasswordTargetLabel('');
        setNewPassword('');
        setConfirmNewPassword('');
      }
      setSelectedIds([]);
      await loadUsers();
    } catch (error) {
      setErrorMessage(resolveError(error));
    } finally {
      setIsBulkDeleting(false);
    }
  }

  const panel = panelMeta[panelMode];

  return (
    <AppShell
      title="平台账号管理"
      description="按权限管理账号与密码。"
      actions={
        <>
          <Link className="chip-button" to="/workspace">返回工作台</Link>
          <button className="action-secondary" onClick={() => void loadUsers()} type="button">刷新列表</button>
        </>
      }
    >
      <section className="metric-strip animate-fade-up">
        {[
          ['可见账号', String(total), '当前权限范围内可查看的账号数量。'],
          ['管理员', String(metrics.adminCount), '仅管理员可管理更低级角色。'],
          ['HRBP/主管', String(metrics.hrbpCount + metrics.managerCount), '两者同级，不能互相更改。'],
          ['待改密账号', String(metrics.passwordUpdatePendingCount), '这些账号下次登录必须先修改密码。'],
        ].map(([label, value, note]) => (
          <article className="metric-tile" key={label}>
            <p className="metric-label">{label}</p>
            <p className="metric-value">{value}</p>
            <p className="metric-note">{note}</p>
          </article>
        ))}
      </section>

      {errorMessage ? <p className="surface px-5 py-4 text-sm" style={{ color: "var(--color-danger)" }}>{errorMessage}</p> : null}
      {successMessage ? <p className="surface px-5 py-4 text-sm" style={{ color: "var(--color-success)" }}>{successMessage}</p> : null}

      {issuedPasswordNotice ? (
        <section className="surface px-6 py-6 lg:px-7">
          <div className="section-head">
            <div>
              <p className="eyebrow">密码交付提醒</p>
              <h2 className="section-title">请安全传达本次密码</h2>
              <p className="section-note mt-2">请通过安全渠道单独发送密码。</p>
            </div>
          </div>
          <div className="mt-5 grid gap-3 md:grid-cols-[1fr_1fr_auto]">
            <div className="surface-subtle px-4 py-4">
              <p className="text-xs text-steel">账号邮箱</p>
              <p className="mt-2 text-sm font-medium text-ink">{issuedPasswordNotice.email}</p>
            </div>
            <div className="surface-subtle px-4 py-4">
              <p className="text-xs text-steel">{issuedPasswordNotice.context === 'create' ? '初始密码' : '重置后密码'}</p>
              <p className="mt-2 break-all font-mono text-sm font-semibold text-ink">{issuedPasswordNotice.password}</p>
            </div>
            <button className="action-secondary self-end" onClick={() => setIssuedPasswordNotice(null)} type="button">已记录</button>
          </div>
        </section>
      ) : null}

      {operationFailures.length ? (
        <section className="surface px-6 py-6 lg:px-7">
          <div className="section-head">
            <div>
              <p className="eyebrow">异常结果</p>
              <h2 className="section-title">未完成项</h2>
              <p className="section-note mt-2">按失败原因重新处理。</p>
            </div>
          </div>
          <div className="mt-5 grid gap-3">
            {operationFailures.map((failure) => (
              <div className="surface-subtle px-4 py-4" key={`${failure.identifier}-${failure.message}`}>
                <p className="font-medium text-ink">{failure.identifier}</p>
                <p className="mt-1 text-sm text-steel">{failure.message}</p>
              </div>
            ))}
          </div>
        </section>
      ) : null}

      <section className="grid gap-5 xl:grid-cols-[380px_minmax(0,1fr)]">
        <aside className="surface px-6 py-6 lg:px-7 xl:sticky xl:top-5 xl:self-start">
          <div className="section-head">
            <div>
              <p className="eyebrow">操作中心</p>
              <h2 className="section-title">集中处理账号操作</h2>
              <p className="section-note mt-2">仅显示可操作角色。</p>
            </div>
          </div>

          <div className="mt-5 grid grid-cols-1 gap-2 sm:grid-cols-3 xl:grid-cols-1">
            {([
              ['single', '新增账号', '单个开通'],
              ['batch', '批量开通', '多人导入'],
              ['password', '修改密码', '重置账号密码'],
            ] as const).map(([value, label, note]) => {
              const active = panelMode === value;
              return (
                <button
                  className={active ? 'chip-button chip-button-active w-full text-left' : 'chip-button w-full text-left'}
                  key={value}
                  onClick={() => setPanelMode(value)}
                  type="button"
                >
                  <span className="block text-sm font-medium text-ink">{label}</span>
                  <span className="mt-1 block text-xs text-steel">{note}</span>
                </button>
              );
            })}
          </div>

          <div className="surface-subtle mt-5 px-5 py-5">
            <p className="eyebrow">{panel.eyebrow}</p>
            <h3 className="mt-2 text-xl font-semibold tracking-[-0.03em] text-ink">{panel.title}</h3>
            <p className="mt-2 text-sm leading-6 text-steel">{panel.note}</p>
          </div>

          {panelMode === 'single' ? (
            <div className="mt-5 grid gap-4">
              <label className="grid gap-2 text-sm font-medium text-ink">
                登录邮箱
                <input className="toolbar-input" onChange={(event) => setSingleForm((current) => ({ ...current, email: event.target.value }))} placeholder="name@company.com" type="email" value={singleForm.email} />
              </label>
              <label className="grid gap-2 text-sm font-medium text-ink">
                初始密码
                <div className="flex gap-2">
                  <input className="toolbar-input flex-1" onChange={(event) => setSingleForm((current) => ({ ...current, password: event.target.value }))} placeholder="至少 8 位" type="text" value={singleForm.password} />
                  <button className="action-secondary shrink-0 px-4" onClick={applyGeneratedSinglePassword} type="button">生成安全密码</button>
                </div>
              </label>
              <div className="surface-subtle px-4 py-4">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-medium text-ink">密码强度</p>
                  <span style={{ borderRadius: 4, padding: '2px 8px', fontSize: 12, fontWeight: 500, ...singlePasswordStrength.toneStyle }}>{singlePasswordStrength.label}</span>
                </div>
                <div style={{ marginTop: 10, height: 6, borderRadius: 3, background: 'var(--color-bg-subtle)' }}>
                  <div style={{ height: 6, borderRadius: 3, background: 'var(--color-primary)', transition: 'width 0.2s', width: `${Math.max(singlePasswordStrength.score, 1) * 20}%` }} />
                </div>
                <p className="mt-3 text-sm leading-6 text-steel">{singlePasswordStrength.hint}</p>
              </div>
              <label className="grid gap-2 text-sm font-medium text-ink">
                角色
                <select className="toolbar-input" onChange={(event) => setSingleForm((current) => ({ ...current, role: event.target.value }))} value={singleForm.role}>
                  {assignableRoleOptions.map((option) => (
                    <option key={option.value} value={option.value}>{option.label}</option>
                  ))}
                </select>
              </label>
              <p className="text-xs leading-6 text-steel">新账号首次登录需改密。</p>
              <button className="action-primary w-full" disabled={isCreating || assignableRoleOptions.length === 0} onClick={() => void handleCreateUser()} type="button">
                {isCreating ? '创建中...' : '创建账号'}
              </button>
            </div>
          ) : null}

          {panelMode === 'batch' ? (
            <div className="mt-5 grid gap-4">
              <textarea
                className="toolbar-textarea w-full"
                onChange={(event) => setBatchInput(event.target.value)}
                placeholder={'zhangsan@company.com,employee,Password123!\nlihua@company.com,员工,Password123!'}
                value={batchInput}
              />
              <div className="flex flex-wrap gap-2">
                {assignableRoleOptions.map((option) => (
                  <span className="chip-button" key={option.value}>{option.label}</span>
                ))}
              </div>
              <div className="surface-subtle px-4 py-4 text-sm leading-6 text-steel">
                每行格式：邮箱，角色，密码。
              </div>
              <button className="action-primary w-full" disabled={isBatchCreating || assignableRoleOptions.length === 0} onClick={() => void handleBatchCreate()} type="button">
                {isBatchCreating ? '批量创建中...' : '执行批量创建'}
              </button>
            </div>
          ) : null}

          {panelMode === 'password' ? (
            <div className="mt-5 grid gap-4">
              <label className="grid gap-2 text-sm font-medium text-ink">
                目标账号
                <select className="toolbar-input" onChange={(event) => {
                  const targetUser = items.find((item) => item.id === event.target.value);
                  setPasswordTargetId(event.target.value);
                  setPasswordTargetLabel(targetUser?.email ?? '');
                }} value={passwordTargetId}>
                  <option value="">请选择账号</option>
                  {manageableUsers.map((item) => (
                    <option key={item.id} value={item.id}>{item.email} · {getRoleLabel(item.role)}</option>
                  ))}
                </select>
              </label>
              <div className="surface-subtle px-4 py-4">
                <p className="text-xs text-steel">当前目标</p>
                <p className="mt-2 text-sm font-medium text-ink">{passwordTargetLabel || '未选择账号'}</p>
              </div>
              <label className="grid gap-2 text-sm font-medium text-ink">
                新密码
                <div className="flex gap-2">
                  <input className="toolbar-input flex-1" onChange={(event) => setNewPassword(event.target.value)} type="text" value={newPassword} />
                  <button className="action-secondary shrink-0 px-4" onClick={applyGeneratedResetPassword} type="button">生成安全密码</button>
                </div>
              </label>
              <div className="surface-subtle px-4 py-4">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-medium text-ink">密码强度</p>
                  <span style={{ borderRadius: 4, padding: '2px 8px', fontSize: 12, fontWeight: 500, ...resetPasswordStrength.toneStyle }}>{resetPasswordStrength.label}</span>
                </div>
                <div style={{ marginTop: 10, height: 6, borderRadius: 3, background: 'var(--color-bg-subtle)' }}>
                  <div style={{ height: 6, borderRadius: 3, background: 'var(--color-primary)', transition: 'width 0.2s', width: `${Math.max(resetPasswordStrength.score, 1) * 20}%` }} />
                </div>
                <p className="mt-3 text-sm leading-6 text-steel">{resetPasswordStrength.hint}</p>
              </div>
              <label className="grid gap-2 text-sm font-medium text-ink">
                确认新密码
                <input className="toolbar-input" onChange={(event) => setConfirmNewPassword(event.target.value)} type="text" value={confirmNewPassword} />
              </label>
              <button className="action-primary w-full" disabled={isPasswordUpdating} onClick={() => void handleUpdatePassword()} type="button">
                {isPasswordUpdating ? '更新中...' : '更新用户密码'}
              </button>
            </div>
          ) : null}
        </aside>

        <section className="surface px-6 py-6 lg:px-7">
          <div className="section-head">
            <div>
              <p className="eyebrow">账号总览</p>
              <h2 className="section-title">当前可管理账号</h2>
              <p className="section-note mt-2">仅显示你本人和可管理账号。</p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="chip-button">当前登录：{user?.email}</span>
              <button className="action-danger" disabled={isBulkDeleting || selectedIds.length === 0} onClick={() => void handleBulkDelete()} type="button">
                {isBulkDeleting ? '删除中...' : `批量删除${selectedIds.length ? `（${selectedIds.length}）` : ''}`}
              </button>
            </div>
          </div>

          <div className="mt-5 grid gap-3 lg:grid-cols-[minmax(0,1fr)_220px_auto]">
            <input className="toolbar-input" onChange={(event) => setKeyword(event.target.value)} placeholder="按邮箱搜索账号" value={keyword} />
            <select className="toolbar-input" onChange={(event) => setRoleFilter(event.target.value)} value={roleFilter}>
              <option value="">全部角色</option>
              {[{ value: user?.role ?? '', label: user?.role ? getRoleLabel(user.role) : '' }, ...assignableRoleOptions]
                .filter((option, index, array) => option.value && array.findIndex((item) => item.value === option.value) === index)
                .map((option) => (
                  <option key={option.value} value={option.value}>{option.label}</option>
                ))}
            </select>
            <div className="flex items-center justify-end text-sm text-steel">
              已选 {selectedIds.length} 个账号
            </div>
          </div>

          <div className="mt-5 grid gap-3 md:grid-cols-3">
            <div className="surface-subtle px-4 py-4">
              <p className="text-xs text-steel">管理员</p>
              <p className="mt-2 text-lg font-semibold text-ink">{metrics.adminCount}</p>
            </div>
            <div className="surface-subtle px-4 py-4">
              <p className="text-xs text-steel">流程角色</p>
              <p className="mt-2 text-lg font-semibold text-ink">{metrics.hrbpCount + metrics.managerCount}</p>
            </div>
            <div className="surface-subtle px-4 py-4">
              <p className="text-xs text-steel">员工账号</p>
              <p className="mt-2 text-lg font-semibold text-ink">{metrics.employeeCount}</p>
            </div>
          </div>

          {isLoading ? <p className="mt-5 text-sm text-steel">正在加载账号列表...</p> : null}

          <div className="table-shell mt-5">
            <div className="overflow-x-auto">
              <table className="table-lite">
                <thead>
                  <tr>
                    <th className="w-12">
                      <input
                        checked={manageableUsers.length > 0 && selectedIds.length === manageableUsers.length}
                        onChange={(event) => setSelectedIds(event.target.checked ? manageableUsers.map((item) => item.id) : [])}
                        type="checkbox"
                      />
                    </th>
                    <th>账号信息</th>
                    <th>角色</th>
                    <th>创建时间</th>
                    <th>安全状态</th>
                    <th className="min-w-[180px]">操作</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item) => {
                    const isCurrentUser = item.id === user?.id;
                    return (
                      <tr key={item.id}>
                        <td>
                          <input checked={selectedIds.includes(item.id)} disabled={isCurrentUser} onChange={() => toggleSelection(item.id)} type="checkbox" />
                        </td>
                        <td>
                          <div className="font-medium text-ink">{item.email}</div>
                          <div className="mt-1 text-xs text-steel">{isCurrentUser ? '当前登录账号' : '可管理的下级账号'}</div>
                        </td>
                        <td>{getRoleLabel(item.role)}</td>
                        <td>{new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(item.created_at))}</td>
                        <td>
                          {item.must_change_password ? (
                            <span className="status-pill" style={{ background: 'var(--color-warning-bg)', color: 'var(--color-warning)' }}>首次登录需改密</span>
                          ) : (
                            <span className="status-pill" style={{ background: 'var(--color-success-bg)', color: 'var(--color-success)' }}>密码状态正常</span>
                          )}
                        </td>
                        <td>
                          {isCurrentUser ? (
                            <span className="text-xs text-steel">请到账号设置修改自己的密码</span>
                          ) : (
                            <div className="flex flex-wrap gap-2">
                              <button className="action-secondary px-4 py-2 text-xs" onClick={() => selectPasswordTarget(item)} type="button">
                                修改密码
                              </button>
                              <button className="action-danger px-4 py-2 text-xs" disabled={isDeleting === item.id} onClick={() => void handleDeleteUser(item)} type="button">
                                {isDeleting === item.id ? '删除中...' : '删除账号'}
                              </button>
                            </div>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </section>
      </section>
    </AppShell>
  );
}
