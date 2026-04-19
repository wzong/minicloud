import React from 'react';
import { Popover, Space, Tag, Button, Spin } from 'antd';
import {
  CheckCircleTwoTone,
  CloseCircleTwoTone,
  QuestionCircleOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { vmsApi } from '../../api/vms';
import type { VMReadiness } from '../../types';

const yes = <CheckCircleTwoTone twoToneColor="#52c41a" />;
const no = <CloseCircleTwoTone twoToneColor="#ff4d4f" />;

const row = (label: string, ok: boolean) => (
  <div style={{ display: 'flex', justifyContent: 'space-between', gap: 24 }}>
    <span>{label}</span>
    <span>{ok ? yes : no}</span>
  </div>
);

const cloudInitColor = (status: string | null): string => {
  if (status === 'done') return 'green';
  if (status === 'running') return 'blue';
  if (status === 'error') return 'red';
  return 'default';
};

interface Props {
  vmId: number;
  enabled: boolean;
}

const ReadinessPanel: React.FC<Props> = ({ vmId, enabled }) => {
  const { data, isFetching, refetch } = useQuery<VMReadiness>({
    queryKey: ['vm-readiness', vmId],
    queryFn: () => vmsApi.readiness(vmId),
    enabled,
    staleTime: 0,
    gcTime: 0,
    refetchOnWindowFocus: false,
  });

  if (isFetching && !data) {
    return (
      <div style={{ width: 220, textAlign: 'center', padding: 12 }}>
        <Spin size="small" />
      </div>
    );
  }

  if (!data) {
    return <div style={{ width: 220 }}>No data</div>;
  }

  return (
    <Space direction="vertical" size={6} style={{ width: 240 }}>
      {row('Hypervisor running', data.hypervisor_running)}
      {row('IP reachable (ping)', data.ip_reachable)}
      {row('SSH port 22 open', data.ssh_port_open)}
      {row('SSH auth OK', data.ssh_auth_ok)}
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 24 }}>
        <span>cloud-init</span>
        {data.cloud_init_status ? (
          <Tag color={cloudInitColor(data.cloud_init_status)} style={{ margin: 0 }}>
            {data.cloud_init_status}
          </Tag>
        ) : (
          <Tag style={{ margin: 0 }}>unknown</Tag>
        )}
      </div>
      <Button
        size="small"
        icon={<ReloadOutlined spin={isFetching} />}
        onClick={() => refetch()}
        loading={isFetching}
        block
      >
        Re-check
      </Button>
    </Space>
  );
};

interface WrapperProps {
  vmId: number;
  children: React.ReactNode;
}

const ReadinessPopover: React.FC<WrapperProps> = ({ vmId, children }) => {
  const [open, setOpen] = React.useState(false);

  return (
    <Popover
      title={
        <Space>
          <QuestionCircleOutlined />
          <span>VM Readiness</span>
        </Space>
      }
      content={<ReadinessPanel vmId={vmId} enabled={open} />}
      trigger="click"
      open={open}
      onOpenChange={setOpen}
      destroyTooltipOnHide
    >
      {children}
    </Popover>
  );
};

export default ReadinessPopover;
