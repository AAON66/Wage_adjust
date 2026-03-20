import api from './api';
import type { EmployeeListResponse, EmployeeQuery, EmployeeRecord } from '../types/api';

export async function fetchEmployees(params: EmployeeQuery): Promise<EmployeeListResponse> {
  const response = await api.get<EmployeeListResponse>('/employees', { params });
  return response.data;
}

export async function fetchEmployee(employeeId: string): Promise<EmployeeRecord> {
  const response = await api.get<EmployeeRecord>(`/employees/${employeeId}`);
  return response.data;
}