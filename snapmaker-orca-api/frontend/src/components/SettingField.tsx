import { InputNumber, Switch, Select, Input, Tooltip, Tag } from 'antd';
import type { SettingDef } from '../types';

interface Props {
  def: SettingDef;
  value: unknown;
  resolvedDefault: unknown;     // value from preset (before overrides)
  onChange: (v: unknown) => void;
  onClear: () => void;          // remove override → fall back to preset
  isOverridden: boolean;
}

function parseNumber(v: unknown): number | undefined {
  if (typeof v === 'number') return v;
  if (typeof v === 'string' && v !== '') {
    const n = Number(v);
    return Number.isFinite(n) ? n : undefined;
  }
  if (Array.isArray(v) && v.length > 0) return parseNumber(v[0]);
  return undefined;
}

function parseBool(v: unknown): boolean {
  if (typeof v === 'boolean') return v;
  if (typeof v === 'string') return v === '1' || v.toLowerCase() === 'true';
  if (typeof v === 'number') return v !== 0;
  return false;
}

function parseString(v: unknown): string {
  if (v == null) return '';
  if (typeof v === 'string') return v;
  if (Array.isArray(v)) return v.map(parseString).join(', ');
  return String(v);
}

export function SettingField({ def, value, resolvedDefault, onChange, onClear, isOverridden }: Props) {
  const effective = value ?? resolvedDefault ?? def.default;
  const placeholder = parseString(resolvedDefault ?? def.default);

  let control;
  switch (def.type) {
    case 'bool':
      control = (
        <Switch
          checked={parseBool(effective)}
          onChange={(v) => onChange(v)}
        />
      );
      break;
    case 'enum':
      control = (
        <Select
          value={parseString(effective)}
          onChange={(v) => onChange(v)}
          options={def.choices ?? []}
          style={{ width: '100%' }}
          size="small"
        />
      );
      break;
    case 'string':
      control = (
        <Input.TextArea
          value={parseString(value ?? '')}
          placeholder={placeholder}
          onChange={(e) => onChange(e.target.value)}
          size="small"
          autoSize={{ minRows: 1, maxRows: 6 }}
        />
      );
      break;
    case 'int':
    case 'float':
    case 'percent':
      control = (
        <InputNumber
          value={parseNumber(effective)}
          min={def.min}
          max={def.max}
          step={def.type === 'int' ? 1 : 0.01}
          addonAfter={def.unit}
          onChange={(v) => onChange(v)}
          placeholder={placeholder}
          size="small"
          style={{ width: '100%' }}
        />
      );
      break;
    case 'floats':
    case 'ints':
    case 'strings':
      control = (
        <Input
          value={parseString(value ?? effective)}
          placeholder={placeholder}
          onChange={(e) => {
            const parts = e.target.value.split(',').map((s) => s.trim()).filter(Boolean);
            onChange(parts);
          }}
          size="small"
        />
      );
      break;
    default:
      control = (
        <Input
          value={parseString(value ?? '')}
          placeholder={placeholder}
          onChange={(e) => onChange(e.target.value)}
          size="small"
        />
      );
  }

  return (
    <div className="setting-row">
      <Tooltip title={def.tooltip}>
        <label>
          {def.label}
          {isOverridden && (
            <Tag
              color="orange"
              style={{ marginLeft: 6, cursor: 'pointer', fontSize: 10 }}
              onClick={onClear}
            >
              override · reset
            </Tag>
          )}
        </label>
      </Tooltip>
      {control}
    </div>
  );
}
