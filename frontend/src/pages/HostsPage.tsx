import React, { useState } from 'react';
import {
  Typography,
  Table,
  Button,
  Space,
  Tag,
  message,
  Popconfirm,
  Tooltip,
  Card,
  Descriptions,
  Empty,
  Spin,
  Grid,
} from 'antd';
import { PlusOutlined, ReloadOutlined, DeleteOutlined, SearchOutlined, CodeOutlined } from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { hostsApi } from '../api/hosts';
import type { Host } from '../types';
import AddHostModal from '../components/hosts/AddHostModal';
import HostDetailDrawer from '../components/hosts/HostDetailDrawer';
import TerminalDrawer from '../components/terminal/TerminalDrawer';

const { useBreakpoint } = Grid;

const statusColor: Record<string, string> = {
  online: 'green',
  pending: 'orange',
  offline: 'red',
  error: 'red',
};

const formatRam = (v: number | null) => (v ? `${(v / 1024).toFixed(1)} GB` : '-');
const formatDisk = (v: number | null) => (v ? `${v} GB` : '-');
const formatCpu = (v: number | null) => (v ? `${v} cores` : '-');

const HostsPage: React.FC = () => {
  const [addModalOpen, setAddModalOpen] = useState(false);
  const [detailHost, setDetailHost] = useState<Host | null>(null);
  const [terminalHost, setTerminalHost] = useState<Host | null>(null);
  const queryClient = useQueryClient();
  const screens = useBreakpoint();
  const isMobile = !screens.md;

  const { data: hosts = [], isLoading } = useQuery({
    queryKey: ['hosts'],
    queryFn: hostsApi.list,
  });

  const deleteMutation = useMutation({
    mutationFn: hostsApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['hosts'] });
      message.success('Host deleted');
    },
    onError: (err: any) => message.error(err.response?.data?.detail || 'Failed to delete host'),
  });

  const detectMutation = useMutation({
    mutationFn: hostsApi.detect,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['hosts'] });
      message.success('Hardware detection complete');
    },
    onError: (err: any) => message.error(err.response?.data?.detail || 'Detection failed'),
  });

  const actionButtons = (record: Host) => (
    <Space>
      <Tooltip title="View Details">
        <Button size="small" icon={<SearchOutlined />} onClick={() => setDetailHost(record)} />
      </Tooltip>
      <Tooltip title="Detect Hardware">
        <Button
          size="small"
          icon={<ReloadOutlined />}
          loading={detectMutation.isPending}
          onClick={() => detectMutation.mutate(record.id)}
        />
      </Tooltip>
      <Tooltip title={record.status === 'online' ? 'Open terminal' : 'Host must be online'}>
        <Button
          size="small"
          icon={<CodeOutlined />}
          disabled={record.status !== 'online'}
          onClick={() => setTerminalHost(record)}
        />
      </Tooltip>
      <Popconfirm title="Delete this host?" onConfirm={() => deleteMutation.mutate(record.id)}>
        <Button size="small" danger icon={<DeleteOutlined />} />
      </Popconfirm>
    </Space>
  );

  const columns = [
    {
      title: 'Rack',
      dataIndex: 'rack_name',
      key: 'rack_name',
      width: 80,
      render: (name: string) => <Tag>{name.toUpperCase()}</Tag>,
    },
    { title: 'IP Address', dataIndex: 'ip_address', key: 'ip_address' },
    {
      title: 'OS',
      dataIndex: 'os_type',
      key: 'os_type',
      render: (os: string | null) =>
        os ? <Tag>{os}</Tag> : <Tag color="default">unknown</Tag>,
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => <Tag color={statusColor[status] || 'default'}>{status}</Tag>,
    },
    { title: 'CPU', dataIndex: 'cpu_cores', key: 'cpu_cores', render: formatCpu },
    { title: 'RAM', dataIndex: 'ram_mb', key: 'ram_mb', render: formatRam },
    { title: 'Disk', dataIndex: 'disk_gb', key: 'disk_gb', render: formatDisk },
    {
      title: 'Hypervisor',
      dataIndex: 'hypervisor_installed',
      key: 'hypervisor',
      render: (installed: boolean | null, record: Host) =>
        installed === null ? (
          <Tag>unknown</Tag>
        ) : installed ? (
          <Tag color="green">{record.hypervisor_type}</Tag>
        ) : (
          <Tag color="orange">Not installed</Tag>
        ),
    },
    {
      title: 'Bridge',
      dataIndex: 'bridge_configured',
      key: 'bridge',
      render: (configured: boolean | null) =>
        configured === null ? (
          <Tag>unknown</Tag>
        ) : configured ? (
          <Tag color="green">Configured</Tag>
        ) : (
          <Tag color="orange">Not configured</Tag>
        ),
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_: any, record: Host) => actionButtons(record),
    },
  ];

  const renderCards = () => {
    if (isLoading) {
      return (
        <div style={{ textAlign: 'center', padding: 40 }}>
          <Spin />
        </div>
      );
    }
    if (hosts.length === 0) {
      return <Empty description="No hosts" />;
    }
    return (
      <Space direction="vertical" size={12} style={{ width: '100%' }}>
        {hosts.map((host) => (
          <Card
            key={host.id}
            size="small"
            title={
              <Space>
                <Tag>{host.rack_name.toUpperCase()}</Tag>
                <span>{host.ip_address}</span>
              </Space>
            }
            extra={<Tag color={statusColor[host.status] || 'default'}>{host.status}</Tag>}
            actions={[actionButtons(host)]}
          >
            <Descriptions size="small" column={1} colon={false}>
              <Descriptions.Item label="OS">
                {host.os_type ? <Tag>{host.os_type}</Tag> : <Tag>unknown</Tag>}
              </Descriptions.Item>
              <Descriptions.Item label="CPU">{formatCpu(host.cpu_cores)}</Descriptions.Item>
              <Descriptions.Item label="RAM">{formatRam(host.ram_mb)}</Descriptions.Item>
              <Descriptions.Item label="Disk">{formatDisk(host.disk_gb)}</Descriptions.Item>
              <Descriptions.Item label="Hypervisor">
                {host.hypervisor_installed === null ? (
                  <Tag>unknown</Tag>
                ) : host.hypervisor_installed ? (
                  <Tag color="green">{host.hypervisor_type}</Tag>
                ) : (
                  <Tag color="orange">Not installed</Tag>
                )}
              </Descriptions.Item>
              <Descriptions.Item label="Bridge">
                {host.bridge_configured === null ? (
                  <Tag>unknown</Tag>
                ) : host.bridge_configured ? (
                  <Tag color="green">Configured</Tag>
                ) : (
                  <Tag color="orange">Not configured</Tag>
                )}
              </Descriptions.Item>
            </Descriptions>
          </Card>
        ))}
      </Space>
    );
  };

  return (
    <div>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 16,
          gap: 8,
          flexWrap: 'wrap',
        }}
      >
        <Typography.Title level={isMobile ? 3 : 2} style={{ margin: 0 }}>
          Hosts
        </Typography.Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setAddModalOpen(true)}>
          Add Host
        </Button>
      </div>
      {isMobile ? (
        renderCards()
      ) : (
        <Table
          columns={columns}
          dataSource={hosts}
          rowKey="id"
          loading={isLoading}
          pagination={false}
          scroll={{ x: 'max-content' }}
        />
      )}
      <AddHostModal open={addModalOpen} onClose={() => setAddModalOpen(false)} />
      <HostDetailDrawer host={detailHost} onClose={() => setDetailHost(null)} />
      <TerminalDrawer
        open={!!terminalHost}
        onClose={() => setTerminalHost(null)}
        wsPath={terminalHost ? `/api/hosts/${terminalHost.id}/terminal` : null}
        title={terminalHost ? `Terminal — ${terminalHost.ssh_user}@${terminalHost.ip_address}` : 'Terminal'}
      />
    </div>
  );
};

export default HostsPage;
