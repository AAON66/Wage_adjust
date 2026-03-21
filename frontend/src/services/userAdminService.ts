import api from './api';
import type {
  AdminUserCreatePayload,
  BulkUserCreateResponse,
  BulkUserDeleteResponse,
  UserListResponse,
  UserProfile,
  UserQuery,
} from '../types/api';

export async function fetchUsers(params: UserQuery): Promise<UserListResponse> {
  const response = await api.get<UserListResponse>('/users', { params });
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

export async function updateManagedUserPassword(userId: string, newPassword: string): Promise<{ updated_user_id: string; message: string }> {
  const response = await api.patch<{ updated_user_id: string; message: string }>(`/users/${userId}/password`, { new_password: newPassword });
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
