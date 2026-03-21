import type { EmployeeRecord, UserProfile } from '../types/api';

const DEMO_EMPLOYEE_NAME_BY_PREFIX: Record<string, string> = {
  chenxi: '陈曦',
  yutong: '李雨桐',
  haoran: '王浩然',
  jingyi: '赵静怡',
};

export function getEmployeeNameForUser(user: UserProfile | null): string | null {
  if (!user) return null;
  if (user.employee_name) return user.employee_name;
  const prefix = user.email.split('@')[0]?.toLowerCase();
  if (!prefix) return null;
  return DEMO_EMPLOYEE_NAME_BY_PREFIX[prefix] ?? null;
}

export function findEmployeeForUser(user: UserProfile | null, employees: EmployeeRecord[]): EmployeeRecord | null {
  if (!user) return null;
  if (user.employee_id) {
    return employees.find((employee) => employee.id === user.employee_id) ?? null;
  }
  const expectedName = getEmployeeNameForUser(user);
  if (!expectedName) return null;
  return employees.find((employee) => employee.name === expectedName) ?? null;
}
