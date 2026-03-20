import { useState, type FormEvent } from 'react';

import type { LoginPayload } from '../../types/api';

type LoginFormProps = {
  isSubmitting: boolean;
  errorMessage: string | null;
  onSubmit: (payload: LoginPayload) => Promise<void>;
};

export function LoginForm({ isSubmitting, errorMessage, onSubmit }: LoginFormProps) {
  const [email, setEmail] = useState('owner@example.com');
  const [password, setPassword] = useState('Password123');

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await onSubmit({ email, password });
  }

  return (
    <form className="flex flex-col gap-4" onSubmit={(event) => void handleSubmit(event)}>
      <label className="flex flex-col gap-2 text-sm font-medium text-ink">
        邮箱
        <input
          className="rounded-2xl border border-slate-200 bg-white px-4 py-3 outline-none transition focus:border-ember"
          onChange={(event) => setEmail(event.target.value)}
          type="email"
          value={email}
        />
      </label>
      <label className="flex flex-col gap-2 text-sm font-medium text-ink">
        密码
        <input
          className="rounded-2xl border border-slate-200 bg-white px-4 py-3 outline-none transition focus:border-ember"
          onChange={(event) => setPassword(event.target.value)}
          type="password"
          value={password}
        />
      </label>
      {errorMessage ? <p className="text-sm text-red-600">{errorMessage}</p> : null}
      <button
        className="rounded-full bg-ink px-5 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
        disabled={isSubmitting}
        type="submit"
      >
        {isSubmitting ? '登录中...' : '登录系统'}
      </button>
    </form>
  );
}
