export type JobStatus = 'pending' | 'running' | 'succeeded' | 'failed' | 'cancelled';

export interface Upload {
  id: string;
  filename: string;
  size_bytes: number;
  created_at: string;
}

export interface SliceStats {
  estimated_print_time_sec?: number | null;
  estimated_print_time_str?: string | null;
  filament_used_mm?: number | null;
  filament_used_g?: number | null;
  filament_cost?: number | null;
  layer_count?: number | null;
}

export interface Job {
  id: string;
  upload_id: string;
  status: JobStatus;
  progress: number;
  stage?: string | null;
  error?: string | null;
  stats?: SliceStats | null;
  created_at: string;
  started_at?: string | null;
  finished_at?: string | null;
}

export type SettingType =
  | 'float' | 'int' | 'bool' | 'enum' | 'percent' | 'string'
  | 'floats' | 'ints' | 'strings' | 'color';

export interface EnumChoice { value: string; label: string }

export interface SettingDef {
  key: string;
  label: string;
  type: SettingType;
  default?: unknown;
  min?: number;
  max?: number;
  unit?: string;
  tooltip?: string;
  choices?: EnumChoice[];
}

export interface SettingGroup { title: string; settings: SettingDef[] }
export interface SettingTab { key: string; title: string; groups: SettingGroup[] }
export interface SettingsCatalog { version: string; tabs: SettingTab[] }

export interface Preset {
  name: string;
  kind: 'printer' | 'filament' | 'process';
  inherits: string | null;
  source: string;
}

export interface PresetValues {
  name: string;
  kind: 'printer' | 'filament' | 'process';
  inherits_chain: string[];
  values: Record<string, unknown>;
}

export interface GcodeLayer {
  index: number;
  z: number;
  extrude_segments: number[];
  travel_segments: number[];
  feature_ids: number[];
}

export interface GcodePreview {
  layer_count: number;
  bbox: [number, number, number, number, number, number];
  feature_legend: Record<string, number>;
  layers: GcodeLayer[];
  total_extruded_mm: number;
  total_travel_mm: number;
}

export interface SliceRequest {
  upload_id: string;
  printer_preset?: string | null;
  filament_preset?: string | null;
  process_preset?: string | null;
  overrides: Record<string, unknown>;
  plate?: number;
  arrange?: boolean;
  orient?: boolean;
  bed_type?: string | null;
}
