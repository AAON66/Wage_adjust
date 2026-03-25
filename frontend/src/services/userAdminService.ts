import api from './api';
import type {
  AdminUserCreatePayload,
  BulkUserCreateResponse,
  BulkUserDeleteResponse,
  DepartmentCreatePayload,
  DepartmentListResponse,
  DepartmentRecord,
  DepartmentUpdatePayload,
  UserListResponse,
  UserProfile,
  UserQuery,
} from '../types/api';

export async function fetchUsers(params: UserQuery): Promise<UserListResponse> {
  const response = await api.get<UserListResponse>('/users', { params });
  return response.data;
}

export async function fetchDepartments(): Promise<DepartmentListResponse> {
  const response = await api.get<DepartmentListResponse>('/departments');
  return response.data;
}

export async function createDepartment(payload: DepartmentCreatePayload): Promise<DepartmentRecord> {
  const response = await api.post<DepartmentRecord>('/departments', payload);
  return response.data;
}

export async function updateDepartment(departmentId: string, payload: DepartmentUpdatePayload): Promise<DepartmentRecord> {
  const response = await api.patch<DepartmentRecord>(`/departments/${departmentId}`, payload);
  return response.data;
}

export async function deleteDepartment(departmentId: string): Promise<{ deleted_department_id: string }> {
  const response = await api.delete<{ deleted_department_id: string }>(`/departments/${departmentId}`);
  return response.data;
}

export async function createManagedUser(payload: AdminUserCreatePayload): Promise<UserProfile> {
  const response = await api.post<UserProfile>('/users', payload);
  return response.data;
}

export async function bulkCreateUsers(items: AdminUserCreatePayload[]): Promise<BulkUserCreateResponse> {
  const response = await api.post<BulkUserCreateResponse>('/users/bulk-create', { items });
  return response.data;
}

export async function updateManagedUserEmployeeBinding(userId: string, employeeId: string | null): Promise<UserProfile> {
  const response = await api.patch<UserProfile>(`/users/${userId}/binding`, { employee_id: employeeId });
  return response.data;
}

export async function updateManagedUserPassword(userId: string, newPassword: string): Promise<{ updated_user_id: string; message: string }> {
  const response = await api.patch<{ updated_user_id: string; message: string }>(`/users/${userId}/password`, { new_password: newPassword });
  return response.data;
}

export async function updateManagedUserDepartments(userId: string, departmentIds: string[]): Promise<UserProfile> {
  const response = await api.patch<UserProfile>(`/users/${userId}/departments`, { department_ids: departmentIds });
  return response.data;
}

export async function deleteManagedUser(userId: string): Promise<{ deleted_user_id: string }> {
  const response = await api.delete<{ deleted_user_id: string }>(`/users/${userId}`);
  return response.data;
}

export async function bulkDeleteUsers(userIds: string[]): Promise<BulkUserDeleteResponse> {
  const response = await api.post<BulkUserDeleteResponse>('/users/bulk-delete', { user_ids: userIds });
  return response.data;
}
