import axios from 'axios';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useState } from 'react';

import { LoginForm } from '../components/auth/LoginForm';
import { useAuth } from '../hooks/useAuth';

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
      await login(payload);
      const redirectTarget = (location.state as { from?: string } | null)?.from ?? '/workspace';
      navigate(redirectTarget, { replace: true });
    } catch (error) {
      setErrorMessage(resolveError(error));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,#fff7ed,transparent_35%),linear-gradient(135deg,#f5efe6_0%,#fff_48%,#fde68a_100%)] px-6 py-12 text-ink">
      <div className="mx-auto grid max-w-5xl gap-10 md:grid-cols-[1.1fr_0.9fr]">
        <section className="rounded-[32px] bg-ink p-8 text-white shadow-panel">
          <p className="text-sm font-semibold uppercase tracking-[0.3em] text-amber-300">Sign In</p>
          <h1 className="mt-5 text-4xl font-bold leading-tight">接入公司综合调薪平台</h1>
          <p className="mt-4 max-w-lg text-sm leading-7 text-white/75">
            当前前端认证链路已连接后端 auth API。登录后将进入受保护的工作台区域，后续会继续接入员工评估、周期配置与审批页面。
          </p>
        </section>
        <section className="rounded-[32px] bg-white p-8 shadow-panel">
          <h2 className="text-2xl font-semibold text-ink">欢迎回来</h2>
          <p className="mt-2 text-sm text-slate-500">使用已注册账号登录系统。</p>
          <div className="mt-6">
            <LoginForm errorMessage={errorMessage} isSubmitting={isSubmitting} onSubmit={handleLogin} />
          </div>
          <p className="mt-6 text-sm text-slate-500">
            还没有账号？
            <Link className="ml-2 font-semibold text-ember" to="/register">
              去注册
            </Link>
          </p>
        </section>
      </div>
    </main>
  );
}
