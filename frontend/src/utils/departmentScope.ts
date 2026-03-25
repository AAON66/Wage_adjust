import type { UserProfile } from '../types/api';

export function isDepartmentScopedRole(role: string | null | undefined): boolean {
  return role === 'hrbp' || role === 'manager';
}

export function getScopedDepartmentNames(user: UserProfile | null | undefined): string[] {
  if (!isDepartmentScopedRole(user?.role)) {
    return [];
  }

  return Array.from(
    new Set(
      (user?.departments ?? [])
        .filter((department) => department.status !== 'inactive')
        .map((department) => department.name.trim())
        .filter(Boolean),
    ),
  ).sort((left, right) => left.localeCompare(right, 'zh-CN'));
}

export function canAccessDepartment(user: UserProfile | null | undefined, departmentName: string): boolean {
  if (!departmentName) {
    return true;
  }
  const scopedDepartments = getScopedDepartmentNames(user);
  if (!scopedDepartments.length) {
    return !isDepartmentScopedRole(user?.role);
  }
  return scopedDepartments.includes(departmentName);
}
