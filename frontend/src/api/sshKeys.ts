import apiClient from './client';
import type { SSHKey } from '../types';

export const sshKeysApi = {
  list: () => apiClient.get<SSHKey[]>('/ssh-keys').then(r => r.data),
  generate: (name: string) => apiClient.post<SSHKey>('/ssh-keys/generate', { name }).then(r => r.data),
  import: (name: string, privateKey: string) =>
    apiClient.post<SSHKey>('/ssh-keys/import', { name, private_key: privateKey }).then(r => r.data),
  delete: (id: number) => apiClient.delete(`/ssh-keys/${id}`),
};
