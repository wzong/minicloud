import { api } from './client';
import type {
  GcodePreview, Job, Preset, PresetValues, SettingsCatalog, SliceRequest, Upload,
} from '../types';

export const slicerApi = {
  health: () => api.get<{
    ok: boolean; slicer_present: boolean; slicer_version: string | null; slicer_bin: string;
  }>('/health').then(r => r.data),

  catalog: () => api.get<SettingsCatalog>('/settings/catalog').then(r => r.data),

  listPresets: (kind?: 'printer' | 'filament' | 'process') =>
    api.get<Preset[]>('/presets', { params: { kind } }).then(r => r.data),

  presetValues: (kind: 'printer' | 'filament' | 'process', name: string) =>
    api.get<PresetValues>(`/presets/${kind}/${encodeURIComponent(name)}`).then(r => r.data),

  uploadModel: async (file: File): Promise<Upload> => {
    const fd = new FormData();
    fd.append('file', file);
    const r = await api.post<Upload>('/uploads', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return r.data;
  },

  startSlice: (req: SliceRequest) => api.post<Job>('/slice', req).then(r => r.data),

  getJob: (id: string) => api.get<Job>(`/jobs/${id}`).then(r => r.data),

  getPreview: (id: string, skipTravel = false) =>
    api.get<GcodePreview>(`/jobs/${id}/preview`, { params: { skip_travel: skipTravel } })
      .then(r => r.data),

  getLogs: (id: string) => api.get<string>(`/jobs/${id}/logs`).then(r => r.data),

  gcodeUrl: (id: string) => `/api/jobs/${id}/gcode`,
};
