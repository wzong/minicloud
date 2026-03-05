import apiClient from './client';
import type { WGStatus, WGPeer, WGPeerCreate } from '../types';

export const wireguardApi = {
  status: () => apiClient.get<WGStatus>('/wireguard/status').then(r => r.data),
  publicKey: () => apiClient.get<{ public_key: string }>('/wireguard/public-key').then(r => r.data),
  listPeers: () => apiClient.get<WGPeer[]>('/wireguard/peers').then(r => r.data),
  addPeer: (data: WGPeerCreate) => apiClient.post<WGPeer>('/wireguard/peers', data).then(r => r.data),
  removePeer: (dc: string) => apiClient.delete(`/wireguard/peers/${dc}`),
  reload: () => apiClient.post('/wireguard/reload'),
};
