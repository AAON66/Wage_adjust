import axios from 'axios';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useState } from 'react';

import { LoginForm } from '../components/auth/LoginForm';
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
    <main className="app-shell flex min-h-screen items-center px-4 py-4 text-ink lg:px-5">
      <div className="mx-auto grid w-full max-w-[1320px] gap-5 lg:grid-cols-[1.1fr_0.9fr]">
        <section className="surface animate-fade-up overflow-hidden px-6 py-8 lg:px-8">
          <p className="eyebrow">账号登录</p>
          <h1 className="mt-3 text-[40px] font-semibold leading-[1.06] tracking-[-0.05em] text-ink lg:text-[54px]">欢迎使用智能调薪平台</h1>
          <p className="mt-5 max-w-xl text-sm leading-7 text-steel">登录后进入对应工作区。</p>
          <div className="mt-8 grid gap-3 sm:grid-cols-2">
            {[
              ['员工', '查看个人材料与评估进展'],
              ['主管', '查看团队评估与审批'],
              ['HRBP', '处理复核、预算与审批'],
              ['管理员', '处理周期、导入与全局配置'],
            ].map(([title, desc]) => (
              <div className="surface-subtle px-4 py-4" key={title}>
                <p className="font-medium text-ink">{title}</p>
                <p className="mt-2 text-sm leading-6 text-steel">{desc}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="surface animate-fade-up px-6 py-8 lg:px-8" style={{ animationDelay: '80ms' }}>
          <p className="eyebrow">访问入口</p>
          <h2 className="mt-3 text-[30px] font-semibold tracking-[-0.04em] text-ink">登录平台</h2>
          <p className="mt-2 text-sm text-steel">请使用公司内部已开通账号登录。</p>
          <div className="mt-6">
            <LoginForm errorMessage={errorMessage} isSubmitting={isSubmitting} onSubmit={handleLogin} />
          </div>
          <div className="mt-6 rounded-[22px] bg-[#f6f9ff] px-4 py-4 text-sm leading-6 text-steel">
            账号由管理员开通。首次登录需先改密。
          </div>
          <p className="mt-6 text-sm text-steel">
            返回平台首页
            <Link className="ml-2 font-medium text-[#2d5cff]" to="/">
              查看系统说明
            </Link>
          </p>
        </section>
      </div>
    </main>
  );
}
