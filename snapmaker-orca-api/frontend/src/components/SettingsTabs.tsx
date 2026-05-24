import { Tabs, Collapse, Empty } from 'antd';
import type { SettingsCatalog } from '../types';
import { SettingField } from './SettingField';

interface Props {
  catalog: SettingsCatalog;
  overrides: Record<string, unknown>;
  presetValues: Record<string, unknown>;
  onOverrideChange: (key: string, value: unknown) => void;
  onOverrideClear: (key: string) => void;
}

export function SettingsTabs({
  catalog, overrides, presetValues, onOverrideChange, onOverrideClear,
}: Props) {
  if (!catalog.tabs.length) {
    return <Empty description="Settings catalog is empty" />;
  }
  return (
    <Tabs
      size="small"
      tabPosition="top"
      defaultActiveKey={catalog.tabs[0].key}
      items={catalog.tabs.map((tab) => ({
        key: tab.key,
        label: tab.title,
        children: (
          <Collapse
            size="small"
            defaultActiveKey={tab.groups.slice(0, 1).map((g) => g.title)}
            ghost
            items={tab.groups.map((group) => ({
              key: group.title,
              label: group.title,
              children: (
                <div>
                  {group.settings.map((def) => (
                    <SettingField
                      key={def.key}
                      def={def}
                      value={overrides[def.key]}
                      resolvedDefault={presetValues[def.key]}
                      onChange={(v) => onOverrideChange(def.key, v)}
                      onClear={() => onOverrideClear(def.key)}
                      isOverridden={def.key in overrides}
                    />
                  ))}
                </div>
              ),
            }))}
          />
        ),
      }))}
    />
  );
}
