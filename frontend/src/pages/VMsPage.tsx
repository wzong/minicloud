import React, { useState } from 'react';
import { Typography, Table, Button, Space, Tag, message, Popconfirm, Tooltip, Switch } from 'antd';
import { PlusOutlined, CaretRightOutlined, PoweroffOutlined, DeleteOutlined, ReloadOutlined } from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { vmsApi } from '../api/vms';
import type { VM } from '../types';
import CreateVMModal from '../components/vms/CreateVMModal';

const VMsPage: React.FC = () => {
  const [createOpen, setCreateOpen] = useState(false);
  const [groupByRack, setGroupByRack] = useState(false);
  const queryClient = useQueryClient();

  const { data: vms = [], isLoading } = useQuery({
    queryKey: ['vms'],
    queryFn: () => vmsApi.list(),
  });

  const { data: vmsByRack = [] } = useQuery({
    queryKey: ['vms-by-rack'],
    queryFn: vmsApi.byRack,
    enabled: groupByRack,
  });

  const startMutation = useMutation({
    mutationFn: vmsApi.start,
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['vms'] }); message.success('VM started'); },
    onError: (err: any) => message.error(err.response?.data?.detail || 'Failed'),
  });

  const stopMutation = useMutation({
    mutationFn: vmsApi.stop,
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['vms'] }); message.success('VM stopped'); },
    onError: (err: any) => message.error(err.response?.data?.detail || 'Failed'),
  });

  const deleteMutation = useMutation({
    mutationFn: vmsApi.delete,
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['vms'] }); message.success('VM deleted'); },
    onError: (err: any) => message.error(err.response?.data?.detail || 'Failed'),
  });

  const statusColor: Record<string, string> = {
    running: 'green', stopped: 'default', creating: 'blue', error: 'red', deleting: 'orange',
  };

  const columns = [
    { title: 'Name', dataIndex: 'name', key: 'name', render: (n: string) => <Typography.Text code>{n}</Typography.Text> },
    { title: 'Rack', dataIndex: 'rack_name', key: 'rack_name', render: (n: string) => n ? <Tag>{n.toUpperCase()}</Tag> : '-' },
    { title: 'Host IP', dataIndex: 'host_ip', key: 'host_ip' },
    { title: 'VM IP', dataIndex: 'ip_address', key: 'ip_address' },
    { title: 'Status', dataIndex: 'status', key: 'status', render: (s: string) => <Tag color={statusColor[s] || 'default'}>{s}</Tag> },
    { title: 'CPU', dataIndex: 'cpu_cores', key: 'cpu_cores', render: (v: number) => `${v} cores` },
    { title: 'RAM', dataIndex: 'ram_mb', key: 'ram_mb', render: (v: number) => `${(v / 1024).toFixed(1)} GB` },
    { title: 'Disk', dataIndex: 'disk_gb', key: 'disk_gb', render: (v: number) => `${v} GB` },
    {
      title: 'Actions',
      key: 'actions',
      render: (_: any, record: VM) => (
        <Space>
          {record.status === 'stopped' && (
            <Tooltip title="Start"><Button size="small" icon={<CaretRightOutlined />} onClick={() => startMutation.mutate(record.id)} /></Tooltip>
          )}
          {record.status === 'running' && (
            <Tooltip title="Stop"><Button size="small" icon={<PoweroffOutlined />} onClick={() => stopMutation.mutate(record.id)} /></Tooltip>
          )}
          <Popconfirm title="Delete this VM?" onConfirm={() => deleteMutation.mutate(record.id)}>
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Typography.Title level={2} style={{ margin: 0 }}>Virtual Machines</Typography.Title>
        <Space>
          <span>Group by Rack</span>
          <Switch checked={groupByRack} onChange={setGroupByRack} />
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>Create VM</Button>
        </Space>
      </div>

      {groupByRack ? (
        vmsByRack.map((rack) => (
          <div key={rack.rack_name} style={{ marginBottom: 24 }}>
            <Typography.Title level={4}>Rack {rack.rack_name.toUpperCase()} ({rack.host_ip})</Typography.Title>
            <Table columns={columns} dataSource={rack.vms} rowKey="id" pagination={false} size="small" />
          </div>
        ))
      ) : (
        <Table columns={columns} dataSource={vms} rowKey="id" loading={isLoading} pagination={false} />
      )}

      <CreateVMModal open={createOpen} onClose={() => setCreateOpen(false)} />
    </div>
  );
};

export default VMsPage;
