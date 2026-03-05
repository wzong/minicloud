import apiClient from './client';
import type { IPAllocation, IPAvailable } from '../types';

export const ipApi = {
  allocations: () => apiClient.get<IPAllocation[]>('/ip/allocations').then(r => r.data),
  available: () => apiClient.get<IPAvailable>('/ip/available').then(r => r.data),
  reserve: (ip: string, notes?: string) =>
    apiClient.post<IPAllocation>('/ip/reserve', { ip_address: ip, notes }).then(r => r.data),
  unreserve: (ip: string) => apiClient.delete(`/ip/reserve/${ip}`),
};
