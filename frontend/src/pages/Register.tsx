import axios from 'axios';
import { Link, useNavigate } from 'react-router-dom';
import { useState } from 'react';

import { RegisterForm } from '../components/auth/RegisterForm';
import { useAuth } from '../hooks/useAuth';
import type { RegisterPayload } from '../types/api';

function resolveError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    return (error.response?.data as { message?: string } | undefined)?.message ?? '注册失败，请稍后重试。';
  }
  return '注册失败，请稍后重试。';
}

export function RegisterPage() {
  const navigate = useNavigate();
  const { register } = useAuth();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function handleRegister(payload: RegisterPayload) {
    setIsSubmitting(true);
    setErrorMessage(null);
    try {
      await register(payload);
      navigate('/workspace', { replace: true });
    } catch (error) {
      setErrorMessage(resolveError(error));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="min-h-screen bg-[linear-gradient(145deg,#fff7ed_0%,#ffffff_38%,#e0f2fe_100%)] px-6 py-12 text-ink">
      <div className="mx-auto grid max-w-5xl gap-10 md:grid-cols-[0.95fr_1.05fr]">
        <section className="rounded-[32px] bg-white p-8 shadow-panel">
          <h1 className="text-3xl font-bold leading-tight">创建一个新的平台账号</h1>
          <p className="mt-4 text-sm leading-7 text-slate-600">
            该页面会直接调用后端注册接口，创建完成后自动写入 access token、refresh token 和用户资料，并跳转到受保护的工作台区域。
          </p>
          <p className="mt-6 text-sm text-slate-500">
            已经有账号？
            <Link className="ml-2 font-semibold text-ember" to="/login">
              返回登录
            </Link>
          </p>
        </section>
        <section className="rounded-[32px] bg-slate-950/95 p-8 text-white shadow-panel">
          <h2 className="text-2xl font-semibold">注册账号</h2>
          <p className="mt-2 text-sm text-white/65">建议先用 `admin` 或 `employee` 角色完成开发联调。</p>
          <div className="mt-6">
            <RegisterForm errorMessage={errorMessage} isSubmitting={isSubmitting} onSubmit={handleRegister} />
          </div>
        </section>
      </div>
    </main>
  );
}
