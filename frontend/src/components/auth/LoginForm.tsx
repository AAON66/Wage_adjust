import { useState, type FormEvent } from 'react';

import type { LoginPayload } from '../../types/api';

type LoginFormProps = {
  isSubmitting: boolean;
  errorMessage: string | null;
  onSubmit: (payload: LoginPayload) => Promise<void>;
};

export function LoginForm({ isSubmitting, errorMessage, onSubmit }: LoginFormProps) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await onSubmit({ email, password });
  }

  return (
    <form className="flex flex-col gap-4" onSubmit={(event) => void handleSubmit(event)}>
      <label className="flex flex-col gap-2 text-sm font-medium text-ink">
        邮箱
        <input
          className="toolbar-input"
          onChange={(event) => setEmail(event.target.value)}
          placeholder="请输入邮箱"
          type="email"
          value={email}
        />
      </label>
      <label className="flex flex-col gap-2 text-sm font-medium text-ink">
        密码
        <input
          className="toolbar-input"
          onChange={(event) => setPassword(event.target.value)}
          placeholder="请输入密码"
          type="password"
          value={password}
        />
      </label>
      {errorMessage ? <p className="text-sm" style={{ color: 'var(--color-danger)' }}>{errorMessage}</p> : null}
      <button className="action-primary w-full" disabled={isSubmitting} type="submit">
        {isSubmitting ? '登录中...' : '登录系统'}
      </button>
    </form>
  );
}
