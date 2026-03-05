import apiClient from './client';
import type { Host, HostCreate, HypervisorCheck } from '../types';

export const hostsApi = {
  list: () => apiClient.get<Host[]>('/hosts').then(r => r.data),
  get: (id: number) => apiClient.get<Host>(`/hosts/${id}`).then(r => r.data),
  create: (data: HostCreate) => apiClient.post<Host>('/hosts', data).then(r => r.data),
  delete: (id: number) => apiClient.delete(`/hosts/${id}`),
  detect: (id: number) => apiClient.post<Host>(`/hosts/${id}/detect`).then(r => r.data),
  checkHypervisor: (id: number) => apiClient.post<HypervisorCheck>(`/hosts/${id}/check-hypervisor`).then(r => r.data),
  updateRackName: (id: number, rackName: string) => apiClient.put<Host>(`/hosts/${id}/rack-name`, { rack_name: rackName }).then(r => r.data),
};
