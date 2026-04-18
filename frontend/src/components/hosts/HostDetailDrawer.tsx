import React from 'react';
import { Drawer, Descriptions, Tag, Button, Space, Typography, Alert, message } from 'antd';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { hostsApi } from '../../api/hosts';
import type { Host, HypervisorCheck, BridgeCheck } from '../../types';

interface Props {
  host: Host | null;
  onClose: () => void;
}

const HostDetailDrawer: React.FC<Props> = ({ host, onClose }) => {
  const queryClient = useQueryClient();
  const [hypervisorInfo, setHypervisorInfo] = React.useState<HypervisorCheck | null>(null);
  const [bridgeInfo, setBridgeInfo] = React.useState<BridgeCheck | null>(null);

  const checkHypervisor = useMutation({
    mutationFn: (id: number) => hostsApi.checkHypervisor(id),
    onSuccess: (data) => {
      setHypervisorInfo(data);
      queryClient.invalidateQueries({ queryKey: ['hosts'] });
    },
    onError: (err: any) => message.error(err.response?.data?.detail || 'Check failed'),
  });

  const checkBridge = useMutation({
    mutationFn: (id: number) => hostsApi.checkBridge(id),
    onSuccess: (data) => {
      setBridgeInfo(data);
      queryClient.invalidateQueries({ queryKey: ['hosts'] });
    },
    onError: (err: any) => message.error(err.response?.data?.detail || 'Check failed'),
  });

  React.useEffect(() => {
    setHypervisorInfo(null);
    setBridgeInfo(null);
    if (host && !host.hypervisor_installed) {
      checkHypervisor.mutate(host.id);
    }
    if (host && !host.bridge_configured) {
      checkBridge.mutate(host.id);
    }
  }, [host?.id]);

  if (!host) return null;

  return (
    <Drawer
      title={`Host ${host.rack_name.toUpperCase()} - ${host.ip_address}`}
      open={!!host}
      onClose={onClose}
      width={500}
    >
      <Descriptions column={1} bordered size="small">
        <Descriptions.Item label="Rack Name">
          <Tag>{host.rack_name.toUpperCase()}</Tag>
        </Descriptions.Item>
        <Descriptions.Item label="IP Address">{host.ip_address}</Descriptions.Item>
        <Descriptions.Item label="SSH">{host.ssh_user}@{host.ip_address}:{host.ssh_port}</Descriptions.Item>
        <Descriptions.Item label="OS">
          {host.os_type ? <Tag>{host.os_type}</Tag> : 'Not detected'}
        </Descriptions.Item>
        <Descriptions.Item label="Status">
          <Tag color={host.status === 'online' ? 'green' : 'orange'}>{host.status}</Tag>
        </Descriptions.Item>
        <Descriptions.Item label="CPU">{host.cpu_cores ? `${host.cpu_cores} cores` : '-'}</Descriptions.Item>
        <Descriptions.Item label="RAM">{host.ram_mb ? `${(host.ram_mb / 1024).toFixed(1)} GB` : '-'}</Descriptions.Item>
        <Descriptions.Item label="Disk">{host.disk_gb ? `${host.disk_gb} GB` : '-'}</Descriptions.Item>
        <Descriptions.Item label="Gateway">{host.gateway || '-'}</Descriptions.Item>
        <Descriptions.Item label="Subnet">{host.subnet_mask || '-'}</Descriptions.Item>
        <Descriptions.Item label="DNS">{host.dns_servers || '-'}</Descriptions.Item>
        <Descriptions.Item label="Bridge">{host.bridge_interface || '-'}</Descriptions.Item>
        <Descriptions.Item label="Bridge Status">
          {host.bridge_configured === null ? (
            <Tag>unknown</Tag>
          ) : host.bridge_configured ? (
            <Tag color="green">Configured</Tag>
          ) : (
            <Tag color="orange">Not configured</Tag>
          )}
        </Descriptions.Item>
        <Descriptions.Item label="Hypervisor">
          {host.hypervisor_installed === null ? (
            <Tag>unknown</Tag>
          ) : host.hypervisor_installed ? (
            <Tag color="green">{host.hypervisor_type}</Tag>
          ) : (
            <Tag color="orange">Not installed</Tag>
          )}
        </Descriptions.Item>
      </Descriptions>

      <div style={{ marginTop: 16 }}>
        <Space>
          <Button
            onClick={() => checkHypervisor.mutate(host.id)}
            loading={checkHypervisor.isPending}
          >
            Check Hypervisor
          </Button>
          <Button
            onClick={() => checkBridge.mutate(host.id)}
            loading={checkBridge.isPending}
          >
            Check Bridge
          </Button>
        </Space>
      </div>

      {hypervisorInfo && !hypervisorInfo.installed && hypervisorInfo.install_commands && (
        <Alert
          style={{ marginTop: 16 }}
          type="warning"
          message="Hypervisor Not Installed"
          description={
            <div>
              <Typography.Text>Run these commands to install:</Typography.Text>
              <Typography.Paragraph
                copyable={{ text: hypervisorInfo.install_commands.join('\n') }}
                style={{ marginTop: 8 }}
              >
                <pre style={{ fontSize: 12, overflowX: 'auto', whiteSpace: 'pre-wrap', wordBreak: 'break-all', margin: 0 }}>
                  {hypervisorInfo.install_commands.join('\n')}
                </pre>
              </Typography.Paragraph>
            </div>
          }
        />
      )}

      {bridgeInfo && !bridgeInfo.configured && bridgeInfo.setup_commands && (
        <Alert
          style={{ marginTop: 16 }}
          type="warning"
          message="Bridge Network Not Configured"
          description={
            <div>
              <Typography.Text>
                {bridgeInfo.bridge_name
                  ? `Bridge "${bridgeInfo.bridge_name}" not found. Run these commands to set it up:`
                  : 'No bridge network detected. Run these commands to set it up:'}
              </Typography.Text>
              <Typography.Paragraph
                copyable={{ text: bridgeInfo.setup_commands.join('\n') }}
                style={{ marginTop: 8 }}
              >
                <pre style={{ fontSize: 12, overflowX: 'auto', whiteSpace: 'pre-wrap', wordBreak: 'break-all', margin: 0 }}>
                  {bridgeInfo.setup_commands.join('\n')}
                </pre>
              </Typography.Paragraph>
            </div>
          }
        />
      )}
    </Drawer>
  );
};

export default HostDetailDrawer;
