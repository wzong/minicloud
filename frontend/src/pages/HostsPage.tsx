import React, { useState } from 'react';
import { Typography, Table, Button, Space, Tag, Modal, message, Popconfirm, Tooltip } from 'antd';
import { PlusOutlined, ReloadOutlined, DeleteOutlined, ToolOutlined, SearchOutlined } from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { hostsApi } from '../api/hosts';
import type { Host } from '../types';
import AddHostModal from '../components/hosts/AddHostModal';
import HostDetailDrawer from '../components/hosts/HostDetailDrawer';

const HostsPage: React.FC = () => {
  const [addModalOpen, setAddModalOpen] = useState(false);
  const [detailHost, setDetailHost] = useState<Host | null>(null);
  const queryClient = useQueryClient();

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

  const statusColor: Record<string, string> = {
    online: 'green',
    pending: 'orange',
    offline: 'red',
    error: 'red',
  };

  const columns = [
    {
      title: 'Rack',
      dataIndex: 'rack_name',
      key: 'rack_name',
      width: 80,
      render: (name: string) => <Tag>{name.toUpperCase()}</Tag>,
    },
    {
      title: 'IP Address',
      dataIndex: 'ip_address',
      key: 'ip_address',
    },
    {
      title: 'OS',
      dataIndex: 'os_type',
      key: 'os_type',
      render: (os: string | null) => os ? <Tag>{os}</Tag> : <Tag color="default">unknown</Tag>,
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => <Tag color={statusColor[status] || 'default'}>{status}</Tag>,
    },
    {
      title: 'CPU',
      dataIndex: 'cpu_cores',
      key: 'cpu_cores',
      render: (v: number | null) => v ? `${v} cores` : '-',
    },
    {
      title: 'RAM',
      dataIndex: 'ram_mb',
      key: 'ram_mb',
      render: (v: number | null) => v ? `${(v / 1024).toFixed(1)} GB` : '-',
    },
    {
      title: 'Disk',
      dataIndex: 'disk_gb',
      key: 'disk_gb',
      render: (v: number | null) => v ? `${v} GB` : '-',
    },
    {
      title: 'Hypervisor',
      dataIndex: 'hypervisor_installed',
      key: 'hypervisor',
      render: (installed: boolean, record: Host) =>
        installed ? (
          <Tag color="green">{record.hypervisor_type}</Tag>
        ) : (
          <Tag color="orange">Not installed</Tag>
        ),
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_: any, record: Host) => (
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
          <Popconfirm title="Delete this host?" onConfirm={() => deleteMutation.mutate(record.id)}>
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Typography.Title level={2} style={{ margin: 0 }}>Hosts</Typography.Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setAddModalOpen(true)}>
          Add Host
        </Button>
      </div>
      <Table
        columns={columns}
        dataSource={hosts}
        rowKey="id"
        loading={isLoading}
        pagination={false}
      />
      <AddHostModal
        open={addModalOpen}
        onClose={() => setAddModalOpen(false)}
      />
      <HostDetailDrawer
        host={detailHost}
        onClose={() => setDetailHost(null)}
      />
    </div>
  );
};

export default HostsPage;
