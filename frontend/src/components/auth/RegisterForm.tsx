import { useState, type FormEvent } from 'react';

import type { RegisterPayload } from '../../types/api';

type RegisterFormProps = {
  isSubmitting: boolean;
  errorMessage: string | null;
  onSubmit: (payload: RegisterPayload) => Promise<void>;
};

const ROLE_OPTIONS = [
  { value: 'employee', label: '员工' },
  { value: 'manager', label: '主管' },
  { value: 'hrbp', label: 'HRBP' },
  { value: 'admin', label: '管理员' },
];

export function RegisterForm({ isSubmitting, errorMessage, onSubmit }: RegisterFormProps) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
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
          className="toolbar-input"
          onChange={(event) => setEmail(event.target.value)}
          placeholder="name@company.com"
          type="email"
          value={email}
        />
      </label>
      <label className="flex flex-col gap-2 text-sm font-medium text-ink">
        密码
        <input
          className="toolbar-input"
          onChange={(event) => setPassword(event.target.value)}
          placeholder="至少 8 位密码"
          type="password"
          value={password}
        />
      </label>
      <label className="flex flex-col gap-2 text-sm font-medium text-ink">
        角色
        <select className="toolbar-input" onChange={(event) => setRole(event.target.value)} value={role}>
          {ROLE_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>{option.label}</option>
          ))}
        </select>
      </label>
      {errorMessage ? <p className="text-sm text-red-600">{errorMessage}</p> : null}
      <button className="action-primary w-full" disabled={isSubmitting} type="submit">
        {isSubmitting ? '注册中...' : '创建账号'}
      </button>
    </form>
  );
}
