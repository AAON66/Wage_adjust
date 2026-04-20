import axios from 'axios';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useState } from 'react';

import { FeishuLoginPanel } from '../components/auth/FeishuLoginPanel';
import { LoginForm } from '../components/auth/LoginForm';
import { ParticleBackground } from '../components/common/ParticleBackground';
import { useAuth } from '../hooks/useAuth';
import { getRoleHomePath } from '../utils/roleAccess';

function resolveError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    return (error.response?.data as { message?: string } | undefined)?.message ?? '登录失败，请稍后重试。';
  }
  return '登录失败，请稍后重试。';
}

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useAuth();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function handleLogin(payload: { email: string; password: string }) {
    setIsSubmitting(true);
    setErrorMessage(null);
    try {
      const profile = await login(payload);
      if (profile.must_change_password) {
        navigate('/settings', {
          replace: true,
          state: {
            forcePasswordChange: true,
            from: getRoleHomePath(profile.role),
          },
        });
        return;
      }
      const redirectTarget = (location.state as { from?: string } | null)?.from ?? getRoleHomePath(profile.role);
      navigate(redirectTarget, { replace: true });
    } catch (error) {
      setErrorMessage(resolveError(error));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <>
      <ParticleBackground />
      <main style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', padding: '24px 20px', position: 'relative', zIndex: 1 }}>
        <div style={{ margin: '0 auto', width: '100%', maxWidth: 1100, display: 'grid', gap: 20 }} className="lg:grid-cols-[1.1fr_0.9fr]">
          <section className="surface animate-fade-up" style={{ padding: '32px 32px', overflow: 'hidden' }}>
            <p className="eyebrow">账号登录</p>
            <h1 style={{ marginTop: 8, fontSize: 32, fontWeight: 700, letterSpacing: '-0.02em', color: 'var(--color-ink)', lineHeight: 1.2 }}>欢迎使用智能调薪平台</h1>
            <p style={{ marginTop: 12, fontSize: 13, lineHeight: 1.7, color: 'var(--color-steel)' }}>登录后进入对应工作区。</p>
            <div style={{ marginTop: 24, display: 'grid', gap: 10 }} className="sm:grid-cols-2">
              {[
                ['员工', '查看个人材料与评估进展'],
                ['主管', '查看团队评估与审批'],
                ['HRBP', '处理复核、预算与审批'],
                ['管理员', '处理周期、导入与全局配置'],
              ].map(([title, desc]) => (
                <div className="surface-subtle" style={{ padding: '12px 14px' }} key={title}>
                  <p style={{ fontWeight: 500, color: 'var(--color-ink)', fontSize: 14 }}>{title}</p>
                  <p style={{ marginTop: 4, fontSize: 13, lineHeight: 1.6, color: 'var(--color-steel)' }}>{desc}</p>
                </div>
              ))}
            </div>
          </section>

          <section className="surface animate-fade-up" style={{ padding: '32px 32px', animationDelay: '80ms' }}>
            <p className="eyebrow">访问入口</p>
            <h2 style={{ marginTop: 8, fontSize: 24, fontWeight: 600, letterSpacing: '-0.02em', color: 'var(--color-ink)' }}>登录平台</h2>
            <p style={{ marginTop: 4, fontSize: 13, color: 'var(--color-steel)' }}>请使用公司内部已开通账号登录。</p>
            <div style={{ marginTop: 20 }}>
              <LoginForm errorMessage={errorMessage} isSubmitting={isSubmitting} onSubmit={handleLogin} />
            </div>
            <FeishuLoginPanel />
            <div style={{ marginTop: 16, background: 'var(--color-bg-subtle)', border: '1px solid var(--color-border)', borderRadius: 6, padding: '10px 14px', fontSize: 13, lineHeight: 1.6, color: 'var(--color-steel)' }}>
              账号由管理员开通。首次登录需先改密。
            </div>
            <p style={{ marginTop: 16, fontSize: 13, color: 'var(--color-steel)' }}>
              返回平台首页
              <Link style={{ marginLeft: 8, fontWeight: 500, color: 'var(--color-primary)' }} to="/">
                查看系统说明
              </Link>
            </p>
          </section>
        </div>
      </main>
    </>
  );
}
