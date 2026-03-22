import axios from 'axios';
import { useLocation, useNavigate } from 'react-router-dom';
import { useMemo, useState } from 'react';

import { AppShell } from '../components/layout/AppShell';
import { useAuth } from '../hooks/useAuth';
import { changePassword } from '../services/auth';
import { assessPasswordStrength } from '../utils/password';
import { getRoleHomePath, getRoleLabel } from '../utils/roleAccess';

function resolveError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    return (error.response?.data as { message?: string; detail?: string } | undefined)?.message ??
      (error.response?.data as { message?: string; detail?: string } | undefined)?.detail ??
      '密码修改失败。';
  }
  return '密码修改失败。';
}

export function SettingsPage() {
  const { user, refreshProfile } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const mustChangePassword = Boolean(user?.must_change_password || (location.state as { forcePasswordChange?: boolean } | null)?.forcePasswordChange);
  const passwordStrength = useMemo(() => assessPasswordStrength(newPassword), [newPassword]);

  async function handleSubmit() {
    setErrorMessage(null);
    setSuccessMessage(null);

    if (!currentPassword || !newPassword || !confirmPassword) {
      setErrorMessage('请完整填写当前密码、新密码和确认密码。');
      return;
    }
    if (newPassword !== confirmPassword) {
      setErrorMessage('两次输入的新密码不一致。');
      return;
    }
    if (newPassword.length < 8) {
      setErrorMessage('新密码长度不能少于 8 位。');
      return;
    }

    setIsSubmitting(true);
    try {
      const response = await changePassword({
        current_password: currentPassword,
        new_password: newPassword,
      });
      const profile = await refreshProfile();
      setSuccessMessage(mustChangePassword ? '密码已更新，已解除首次登录限制。' : response.message);
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');

      if (mustChangePassword && profile) {
        navigate(getRoleHomePath(profile.role), { replace: true });
      }
    } catch (error) {
      setErrorMessage(resolveError(error));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <AppShell
      title="账号设置"
      description="查看账号并修改密码。"
    >
      <section className="grid gap-5 xl:grid-cols-[0.88fr_1.12fr]">
        <section className="surface px-6 py-6 lg:px-7">
          <div className="section-head">
            <div>
              <p className="eyebrow">当前账号</p>
              <h2 className="section-title">账号信息</h2>
            </div>
          </div>
          <div className="mt-5 grid gap-4">
            <div className="surface-subtle px-4 py-4">
              <p className="text-sm text-steel">邮箱</p>
              <p className="mt-2 text-lg font-semibold text-ink">{user?.email}</p>
            </div>
            <div className="surface-subtle px-4 py-4">
              <p className="text-sm text-steel">角色</p>
              <p className="mt-2 text-lg font-semibold text-ink">{getRoleLabel(user?.role)}</p>
            </div>
            <div className="surface-subtle px-4 py-4">
              <p className="text-sm text-steel">安全说明</p>
              <p className="mt-2 text-sm leading-6 text-steel">密码修改后立即生效。请使用强密码。</p>
            </div>
          </div>
        </section>

        <section className="surface px-6 py-6 lg:px-7">
          <div className="section-head">
            <div>
              <p className="eyebrow">密码管理</p>
              <h2 className="section-title">修改登录密码</h2>
              <p className="mt-2 text-sm leading-6 text-steel">仅修改当前账号密码。</p>
            </div>
          </div>

          {mustChangePassword ? (
            <div style={{ marginTop: 16, background: 'var(--color-warning-bg)', border: '1px solid #FFD8A8', borderRadius: 6, padding: '10px 14px', fontSize: 13, lineHeight: 1.6, color: 'var(--color-warning)' }}>
              当前账号仍在使用初始密码，请先完成改密。
            </div>
          ) : null}

          {errorMessage ? <p style={{ marginTop: 16, background: 'var(--color-danger-bg)', border: '1px solid #FFCDD0', borderRadius: 6, padding: '10px 14px', fontSize: 13, color: 'var(--color-danger)' }}>{errorMessage}</p> : null}
          {successMessage ? <p style={{ marginTop: 16, background: 'var(--color-success-bg)', border: '1px solid #B7F5C2', borderRadius: 6, padding: '10px 14px', fontSize: 13, color: 'var(--color-success)' }}>{successMessage}</p> : null}

          <div className="mt-5 grid gap-4">
            <label className="grid gap-2 text-sm font-medium text-ink">
              当前密码
              <input className="toolbar-input" onChange={(event) => setCurrentPassword(event.target.value)} type="password" value={currentPassword} />
            </label>
            <label className="grid gap-2 text-sm font-medium text-ink">
              新密码
              <input className="toolbar-input" onChange={(event) => setNewPassword(event.target.value)} type="password" value={newPassword} />
            </label>
            <div className="surface-subtle px-4 py-4">
              <div className="flex items-center justify-between gap-3">
                <p className="text-sm font-medium text-ink">密码强度</p>
                <span className={`rounded-full px-3 py-1 text-xs font-medium ${passwordStrength.toneClass}`}>{passwordStrength.label}</span>
              </div>
              <div style={{ marginTop: 10, height: 6, borderRadius: 3, background: 'var(--color-bg-subtle)' }}>
                <div style={{ height: 6, borderRadius: 3, background: 'var(--color-primary)', transition: 'width 0.2s', width: `${Math.max(passwordStrength.score, 1) * 20}%` }} />
              </div>
              <p className="mt-3 text-sm leading-6 text-steel">{passwordStrength.hint}</p>
            </div>
            <label className="grid gap-2 text-sm font-medium text-ink">
              确认新密码
              <input className="toolbar-input" onChange={(event) => setConfirmPassword(event.target.value)} type="password" value={confirmPassword} />
            </label>
            <div className="flex flex-wrap gap-3 pt-2">
              <button className="action-primary" disabled={isSubmitting} onClick={() => void handleSubmit()} type="button">
                {isSubmitting ? '提交中...' : '更新密码'}
              </button>
            </div>
          </div>
        </section>
      </section>
    </AppShell>
  );
}
