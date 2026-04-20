import axios from 'axios';
import { useLocation, useNavigate } from 'react-router-dom';
import { useEffect, useMemo, useState } from 'react';

import { AppShell } from '../components/layout/AppShell';
import { useAuth } from '../hooks/useAuth';
import { authorizeFeishu, changePassword, selfBindConfirm, selfBindPreview, unbindFeishu } from '../services/auth';
import { assessPasswordStrength } from '../utils/password';
import { resolveFeishuError } from '../utils/feishuErrors';
import { getRoleHomePath, getRoleLabel } from '../utils/roleAccess';
import type { SelfBindPreviewResult } from '../types/api';

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
  const [bindIdCardNo, setBindIdCardNo] = useState('');
  const [bindPreview, setBindPreview] = useState<SelfBindPreviewResult | null>(null);
  const [bindStep, setBindStep] = useState<'input' | 'preview' | 'done'>('input');
  const [bindError, setBindError] = useState<string | null>(null);
  const [isBinding, setIsBinding] = useState(false);
  const [feishuError, setFeishuError] = useState<string | null>(null);
  const [feishuSuccess, setFeishuSuccess] = useState<string | null>(null);
  const [isFeishuProcessing, setIsFeishuProcessing] = useState(false);

  // 监听 FeishuBindCallbackPage 跳回时携带的 state: { bindSuccess: true }
  useEffect(() => {
    const navState = location.state as { bindSuccess?: boolean } | null;
    if (navState?.bindSuccess) {
      setFeishuSuccess('飞书账号已绑定');
      // 清除 history state 避免刷新重复显示
      window.history.replaceState({}, '');
    }
  }, [location.state]);

  const mustChangePassword = Boolean(user?.must_change_password || (location.state as { forcePasswordChange?: boolean } | null)?.forcePasswordChange);
  const passwordStrength = useMemo(() => assessPasswordStrength(newPassword), [newPassword]);

  async function handleBindPreview() {
    setBindError(null);
    if (!bindIdCardNo.trim()) {
      setBindError('请输入身份证号。');
      return;
    }
    setIsBinding(true);
    try {
      const result = await selfBindPreview(bindIdCardNo.trim());
      setBindPreview(result);
      setBindStep('preview');
    } catch (error) {
      if (axios.isAxiosError(error)) {
        const payload = error.response?.data as { message?: string; detail?: string } | undefined;
        setBindError(payload?.message ?? payload?.detail ?? '查询匹配失败。');
      } else {
        setBindError('查询匹配失败。');
      }
    } finally {
      setIsBinding(false);
    }
  }

  async function handleBindConfirm() {
    setBindError(null);
    setIsBinding(true);
    try {
      await selfBindConfirm(bindIdCardNo.trim());
      await refreshProfile();
      setBindStep('done');
      setBindPreview(null);
      setBindIdCardNo('');
    } catch (error) {
      if (axios.isAxiosError(error)) {
        const payload = error.response?.data as { message?: string; detail?: string } | undefined;
        setBindError(payload?.message ?? payload?.detail ?? '绑定失败。');
      } else {
        setBindError('绑定失败。');
      }
    } finally {
      setIsBinding(false);
    }
  }

  async function handleFeishuBind() {
    setFeishuError(null);
    setFeishuSuccess(null);
    setIsFeishuProcessing(true);
    try {
      const { authorize_url } = await authorizeFeishu('bind');
      window.location.href = authorize_url;
      // 整页跳转，后续代码不会执行；setIsFeishuProcessing 无需 reset
    } catch (err) {
      setFeishuError(resolveFeishuError('backend', err).message);
      setIsFeishuProcessing(false);
    }
  }

  async function handleFeishuUnbind() {
    // D-10: 解绑二次确认
    const confirmed = window.confirm('解绑后你将无法再使用飞书账号登录，需重新绑定。确认解绑？');
    if (!confirmed) return;

    setFeishuError(null);
    setFeishuSuccess(null);
    setIsFeishuProcessing(true);
    try {
      await unbindFeishu();
      await refreshProfile();
      setFeishuSuccess('已解除飞书绑定');
    } catch (err) {
      setFeishuError(resolveFeishuError('backend', err).message);
    } finally {
      setIsFeishuProcessing(false);
    }
  }

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
      <section className="surface px-6 py-6 lg:px-7">
        <div className="section-head">
          <div>
            <p className="eyebrow">员工绑定</p>
            <h2 className="section-title">账号与员工关联</h2>
          </div>
        </div>
        <div className="mt-5 grid gap-4">
          {user?.employee_id ? (
            <div className="surface-subtle px-4 py-4">
              <p className="text-sm text-steel">已绑定员工</p>
              <p className="mt-2 text-lg font-semibold text-ink">{user.employee_name}（{user.employee_no}）</p>
            </div>
          ) : (
            <>
              {bindError ? <p style={{ background: 'var(--color-danger-bg)', border: '1px solid #FFCDD0', borderRadius: 6, padding: '10px 14px', fontSize: 13, color: 'var(--color-danger)' }}>{bindError}</p> : null}
              {bindStep === 'done' ? <p style={{ background: 'var(--color-success-bg)', border: '1px solid #B7F5C2', borderRadius: 6, padding: '10px 14px', fontSize: 13, color: 'var(--color-success)' }}>绑定成功。</p> : null}
              {bindStep === 'input' ? (
                <div className="grid gap-3">
                  <p className="text-sm text-steel">请输入您的身份证号以查询匹配的员工档案。</p>
                  <input className="toolbar-input" placeholder="身份证号" value={bindIdCardNo} onChange={(event) => setBindIdCardNo(event.target.value)} />
                  <button className="action-primary" disabled={isBinding} onClick={() => void handleBindPreview()} type="button">{isBinding ? '查询中...' : '查询匹配'}</button>
                </div>
              ) : null}
              {bindStep === 'preview' && bindPreview ? (
                <div className="grid gap-3">
                  <div className="surface-subtle px-4 py-4">
                    <p className="text-sm text-steel">匹配到员工</p>
                    <p className="mt-2 text-lg font-semibold text-ink">{bindPreview.name}（{bindPreview.employee_no}）</p>
                    <p className="mt-1 text-sm text-steel">部门：{bindPreview.department}</p>
                  </div>
                  <div className="flex gap-3">
                    <button className="action-primary" disabled={isBinding} onClick={() => void handleBindConfirm()} type="button">{isBinding ? '绑定中...' : '确认绑定'}</button>
                    <button className="action-secondary" onClick={() => { setBindStep('input'); setBindPreview(null); setBindError(null); }} type="button">取消</button>
                  </div>
                </div>
              ) : null}
            </>
          )}
        </div>
      </section>

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
              <p className="mt-2 text-sm leading-6 text-steel">仅修改当前账号密码。密码需至少 8 位，且包含大写字母、小写字母和数字或特殊字符。</p>
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
                <span style={{ borderRadius: 4, padding: '2px 8px', fontSize: 12, fontWeight: 500, ...passwordStrength.toneStyle }}>{passwordStrength.label}</span>
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

      <section className="surface px-6 py-6 lg:px-7">
        <div className="section-head">
          <div>
            <p className="eyebrow">登录方式</p>
            <h2 className="section-title">飞书账号</h2>
            <p className="mt-2 text-sm leading-6 text-steel">
              {user?.feishu_open_id
                ? '你的飞书账号已绑定到系统账号，可在登录页使用飞书扫码登录。'
                : '绑定飞书账号后，可用飞书扫码快速登录。'}
            </p>
          </div>
        </div>

        {feishuError ? (
          <p style={{ marginTop: 16, background: 'var(--color-danger-bg)', border: '1px solid #FFCDD0', borderRadius: 6, padding: '10px 14px', fontSize: 13, color: 'var(--color-danger)' }}>
            {feishuError}
          </p>
        ) : null}
        {feishuSuccess ? (
          <p style={{ marginTop: 16, background: 'var(--color-success-bg)', border: '1px solid #B7F5C2', borderRadius: 6, padding: '10px 14px', fontSize: 13, color: 'var(--color-success)' }}>
            {feishuSuccess}
          </p>
        ) : null}

        <div className="mt-5 flex items-center gap-3">
          {user?.feishu_open_id ? (
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                borderRadius: 999,
                background: 'var(--color-success-bg)',
                color: 'var(--color-success)',
                padding: '4px 12px',
                fontSize: 13,
                fontWeight: 500,
              }}
            >
              已绑定
            </span>
          ) : (
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                borderRadius: 999,
                background: 'var(--color-bg-subtle)',
                color: 'var(--color-steel)',
                padding: '4px 12px',
                fontSize: 13,
                fontWeight: 500,
              }}
            >
              未绑定
            </span>
          )}
        </div>

        <div className="mt-5 flex flex-wrap gap-3">
          {user?.feishu_open_id ? (
            <button
              className="action-secondary"
              disabled={isFeishuProcessing}
              onClick={() => void handleFeishuUnbind()}
              type="button"
            >
              {isFeishuProcessing ? '处理中…' : '解除飞书绑定'}
            </button>
          ) : (
            <button
              className="action-primary"
              disabled={isFeishuProcessing}
              onClick={() => void handleFeishuBind()}
              type="button"
            >
              {isFeishuProcessing ? '处理中…' : '使用飞书绑定'}
            </button>
          )}
        </div>
      </section>
    </AppShell>
  );
}
