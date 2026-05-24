import { Select } from 'antd';
import { useQuery } from '@tanstack/react-query';
import { slicerApi } from '../api/slicer';

interface Props {
  kind: 'printer' | 'filament' | 'process';
  value: string | undefined;
  onChange: (name: string | undefined) => void;
}

export function PresetPicker({ kind, value, onChange }: Props) {
  const { data, isLoading } = useQuery({
    queryKey: ['presets', kind],
    queryFn: () => slicerApi.listPresets(kind),
  });
  return (
    <Select
      size="small"
      allowClear
      showSearch
      placeholder={`Select ${kind} preset…`}
      style={{ width: '100%' }}
      loading={isLoading}
      value={value}
      onChange={(v) => onChange(v || undefined)}
      filterOption={(input, opt) =>
        (opt?.label as string).toLowerCase().includes(input.toLowerCase())
      }
      options={(data ?? []).map((p) => ({ value: p.name, label: p.name }))}
    />
  );
}
