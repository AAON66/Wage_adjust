import api from './api';
import type { EmployeeCreatePayload, EmployeeListResponse, EmployeeQuery, EmployeeRecord, EmployeeUpdatePayload } from '../types/api';

export async function fetchEmployees(params: EmployeeQuery): Promise<EmployeeListResponse> {
  const response = await api.get<EmployeeListResponse>('/employees', { params });
  return response.data;
}

export async function fetchEmployee(employeeId: string): Promise<EmployeeRecord> {
  const response = await api.get<EmployeeRecord>(`/employees/${employeeId}`);
  return response.data;
}

export async function createEmployee(payload: EmployeeCreatePayload): Promise<EmployeeRecord> {
  const response = await api.post<EmployeeRecord>('/employees', payload);
  return response.data;
}

export async function updateEmployee(employeeId: string, payload: EmployeeUpdatePayload): Promise<EmployeeRecord> {
  const response = await api.patch<EmployeeRecord>(`/employees/${employeeId}`, payload);
  return response.data;
}
