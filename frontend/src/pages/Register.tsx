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
    <main style={{ minHeight: '100vh', background: 'var(--color-bg-page)', display: 'flex', alignItems: 'center', padding: '24px 20px' }}>
      <div style={{ margin: '0 auto', width: '100%', maxWidth: 1100, display: 'grid', gap: 20 }} className="lg:grid-cols-[1.06fr_0.94fr]">
        <section className="surface animate-fade-up" style={{ padding: '32px', overflow: 'hidden' }}>
          <p className="eyebrow">创建账号</p>
          <h1 style={{ marginTop: 8, fontSize: 32, fontWeight: 700, letterSpacing: '-0.02em', color: 'var(--color-ink)', lineHeight: 1.2 }}>先确定角色，再进入对应工作区</h1>
          <p style={{ marginTop: 12, fontSize: 13, lineHeight: 1.7, color: 'var(--color-steel)' }}>创建后按角色进入对应工作区。</p>
          <div style={{ marginTop: 20, display: 'flex', flexDirection: 'column', gap: 8 }}>
            {[
              ['管理员', '处理系统配置与导入'],
              ['HRBP', '处理预算、复核与审批'],
              ['主管', '处理团队评估与审批'],
              ['员工', '查看个人评估与材料'],
            ].map(([title, desc]) => (
              <div className="surface-subtle" style={{ padding: '12px 14px' }} key={title}>
                <p style={{ fontWeight: 500, color: 'var(--color-ink)', fontSize: 14 }}>{title}</p>
                <p style={{ marginTop: 4, fontSize: 13, lineHeight: 1.6, color: 'var(--color-steel)' }}>{desc}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="surface animate-fade-up" style={{ padding: '32px', animationDelay: '80ms' }}>
          <p className="eyebrow">注册入口</p>
          <h2 style={{ marginTop: 8, fontSize: 24, fontWeight: 600, letterSpacing: '-0.02em', color: 'var(--color-ink)' }}>创建平台账号</h2>
          <p style={{ marginTop: 4, fontSize: 13, color: 'var(--color-steel)' }}>请选择对应角色。</p>
          <div style={{ marginTop: 20 }}>
            <RegisterForm errorMessage={errorMessage} isSubmitting={isSubmitting} onSubmit={handleRegister} />
          </div>
          <p style={{ marginTop: 16, fontSize: 13, color: 'var(--color-steel)' }}>
            已经有账号？
            <Link style={{ marginLeft: 8, fontWeight: 500, color: 'var(--color-primary)' }} to="/login">
              返回登录
            </Link>
          </p>
        </section>
      </div>
    </main>
  );
}
