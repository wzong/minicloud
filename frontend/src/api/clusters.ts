import apiClient from './client';
import type { Cluster, ClusterCreate, ClusterPreview, ClusterNode, ClusterStatus } from '../types';

export const clustersApi = {
  list: () => apiClient.get<Cluster[]>('/clusters').then(r => r.data),
  get: (id: number) => apiClient.get<Cluster>(`/clusters/${id}`).then(r => r.data),
  create: (data: ClusterCreate) => apiClient.post<Cluster>('/clusters', data).then(r => r.data),
  delete: (id: number) => apiClient.delete(`/clusters/${id}`),
  preview: (data: ClusterCreate) => apiClient.post<ClusterPreview>('/clusters/preview', data).then(r => r.data),
  getNodes: (id: number) => apiClient.get<ClusterNode[]>(`/clusters/${id}/nodes`).then(r => r.data),
  addNodes: (id: number, data: { role: string; count: number; host_id?: number }) =>
    apiClient.post(`/clusters/${id}/nodes`, data).then(r => r.data),
  removeNode: (clusterId: number, nodeId: number) =>
    apiClient.delete(`/clusters/${clusterId}/nodes/${nodeId}`),
  getKubeconfig: (id: number) => apiClient.get<string>(`/clusters/${id}/kubeconfig`).then(r => r.data),
  getStatus: (id: number) => apiClient.get<ClusterStatus>(`/clusters/${id}/status`).then(r => r.data),
};
