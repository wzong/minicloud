import apiClient from './client';
import type { VM, VMCreate, VMsByRack } from '../types';

export const vmsApi = {
  list: (params?: Record<string, any>) => apiClient.get<VM[]>('/vms', { params }).then(r => r.data),
  get: (id: number) => apiClient.get<VM>(`/vms/${id}`).then(r => r.data),
  create: (data: VMCreate) => apiClient.post<VM>('/vms', data).then(r => r.data),
  delete: (id: number) => apiClient.delete(`/vms/${id}`),
  start: (id: number) => apiClient.post<VM>(`/vms/${id}/start`).then(r => r.data),
  stop: (id: number) => apiClient.post<VM>(`/vms/${id}/stop`).then(r => r.data),
  refresh: (id: number) => apiClient.post<VM>(`/vms/${id}/refresh`).then(r => r.data),
  byRack: () => apiClient.get<VMsByRack[]>('/vms/by-rack').then(r => r.data),
};
