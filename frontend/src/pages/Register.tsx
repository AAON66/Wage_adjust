import axios from 'axios';
import { Link, useNavigate } from 'react-router-dom';
import { useState } from 'react';

import { RegisterForm } from '../components/auth/RegisterForm';
import { useAuth } from '../hooks/useAuth';
import type { RegisterPayload } from '../types/api';
import { getRoleHomePath } from '../utils/roleAccess';

function resolveError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const data = error.response?.data as { message?: string; detail?: string } | undefined;
    return data?.message ?? data?.detail ?? error.message ?? '注册失败，请稍后重试。';
  }
  if (error instanceof Error) {
    return error.message;
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
      const profile = await register(payload);
      navigate(getRoleHomePath(profile.role), { replace: true });
    } catch (error) {
      setErrorMessage(resolveError(error));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="app-shell flex min-h-screen items-center px-4 py-4 text-ink lg:px-5">
      <div className="mx-auto grid w-full max-w-[1320px] gap-5 lg:grid-cols-[1.06fr_0.94fr]">
        <section className="surface animate-fade-up overflow-hidden px-6 py-8 lg:px-8">
          <p className="eyebrow">创建账号</p>
          <h1 className="mt-3 text-[40px] font-semibold leading-[1.06] tracking-[-0.05em] text-ink lg:text-[54px]">先确定角色，再进入对应工作区</h1>
          <p className="mt-5 max-w-xl text-sm leading-7 text-steel">创建后按角色进入对应工作区。</p>
          <div className="mt-8 space-y-3">
            {[
              ['管理员', '处理系统配置与导入'],
              ['HRBP', '处理预算、复核与审批'],
              ['主管', '处理团队评估与审批'],
              ['员工', '查看个人评估与材料'],
            ].map(([title, desc]) => (
              <div className="surface-subtle px-4 py-4" key={title}>
                <p className="font-medium text-ink">{title}</p>
                <p className="mt-2 text-sm leading-6 text-steel">{desc}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="surface animate-fade-up px-6 py-8 lg:px-8" style={{ animationDelay: '80ms' }}>
          <p className="eyebrow">注册入口</p>
          <h2 className="mt-3 text-[30px] font-semibold tracking-[-0.04em] text-ink">创建平台账号</h2>
          <p className="mt-2 text-sm text-steel">请选择对应角色。</p>
          <div className="mt-6">
            <RegisterForm errorMessage={errorMessage} isSubmitting={isSubmitting} onSubmit={handleRegister} />
          </div>
          <p className="mt-6 text-sm text-steel">
            已经有账号？
            <Link className="ml-2 font-medium text-[#2d5cff]" to="/login">
              返回登录
            </Link>
          </p>
        </section>
      </div>
    </main>
  );
}
