import { useState, type FormEvent } from 'react';

import type { RegisterPayload } from '../../types/api';

type RegisterFormProps = {
  isSubmitting: boolean;
  errorMessage: string | null;
  onSubmit: (payload: RegisterPayload) => Promise<void>;
};

export function RegisterForm({ isSubmitting, errorMessage, onSubmit }: RegisterFormProps) {
  const [email, setEmail] = useState('new.user@example.com');
  const [password, setPassword] = useState('Password123');
  const [role, setRole] = useState('employee');

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await onSubmit({ email, password, role });
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
      <label className="flex flex-col gap-2 text-sm font-medium text-ink">
        角色
        <select
          className="rounded-2xl border border-slate-200 bg-white px-4 py-3 outline-none transition focus:border-ember"
          onChange={(event) => setRole(event.target.value)}
          value={role}
        >
          <option value="employee">employee</option>
          <option value="manager">manager</option>
          <option value="hrbp">hrbp</option>
          <option value="admin">admin</option>
        </select>
      </label>
      {errorMessage ? <p className="text-sm text-red-600">{errorMessage}</p> : null}
      <button
        className="rounded-full bg-ember px-5 py-3 text-sm font-semibold text-white transition hover:bg-amber-600 disabled:cursor-not-allowed disabled:opacity-60"
        disabled={isSubmitting}
        type="submit"
      >
        {isSubmitting ? '注册中...' : '创建账号'}
      </button>
    </form>
  );
}
