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
  Switch,
  Card,
  Descriptions,
  Empty,
  Spin,
  Grid,
} from 'antd';
import {
  PlusOutlined,
  CaretRightOutlined,
  PoweroffOutlined,
  DeleteOutlined,
  CodeOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { vmsApi } from '../api/vms';
import type { VM } from '../types';
import CreateVMModal from '../components/vms/CreateVMModal';
import TerminalDrawer from '../components/terminal/TerminalDrawer';

const { useBreakpoint } = Grid;

const statusColor: Record<string, string> = {
  running: 'green',
  stopped: 'default',
  creating: 'blue',
  error: 'red',
  deleting: 'orange',
};

const VMsPage: React.FC = () => {
  const [createOpen, setCreateOpen] = useState(false);
  const [groupByRack, setGroupByRack] = useState(false);
  const [terminalVm, setTerminalVm] = useState<VM | null>(null);
  const queryClient = useQueryClient();
  const screens = useBreakpoint();
  const isMobile = !screens.md;

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
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['vms'] });
      message.success('VM started');
    },
    onError: (err: any) => message.error(err.response?.data?.detail || 'Failed'),
  });

  const stopMutation = useMutation({
    mutationFn: vmsApi.stop,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['vms'] });
      message.success('VM stopped');
    },
    onError: (err: any) => message.error(err.response?.data?.detail || 'Failed'),
  });

  const deleteMutation = useMutation({
    mutationFn: vmsApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['vms'] });
      message.success('VM deleted');
    },
    onError: (err: any) => message.error(err.response?.data?.detail || 'Failed'),
  });

  const vmActions = (record: VM) => (
    <Space>
      {record.status === 'stopped' && (
        <Tooltip title="Start">
          <Button
            size="small"
            icon={<CaretRightOutlined />}
            onClick={() => startMutation.mutate(record.id)}
          />
        </Tooltip>
      )}
      {record.status === 'running' && (
        <Tooltip title="Stop">
          <Button
            size="small"
            icon={<PoweroffOutlined />}
            onClick={() => stopMutation.mutate(record.id)}
          />
        </Tooltip>
      )}
      <Tooltip title={record.status === 'running' ? 'Open terminal' : 'VM must be running'}>
        <Button
          size="small"
          icon={<CodeOutlined />}
          disabled={record.status !== 'running'}
          onClick={() => setTerminalVm(record)}
        />
      </Tooltip>
      <Popconfirm title="Delete this VM?" onConfirm={() => deleteMutation.mutate(record.id)}>
        <Button size="small" danger icon={<DeleteOutlined />} />
      </Popconfirm>
    </Space>
  );

  const columns = [
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
      render: (n: string) => <Typography.Text code>{n}</Typography.Text>,
    },
    {
      title: 'Rack',
      dataIndex: 'rack_name',
      key: 'rack_name',
      render: (n: string) => (n ? <Tag>{n.toUpperCase()}</Tag> : '-'),
    },
    { title: 'Host IP', dataIndex: 'host_ip', key: 'host_ip' },
    { title: 'VM IP', dataIndex: 'ip_address', key: 'ip_address' },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (s: string) => <Tag color={statusColor[s] || 'default'}>{s}</Tag>,
    },
    { title: 'CPU', dataIndex: 'cpu_cores', key: 'cpu_cores', render: (v: number) => `${v} cores` },
    {
      title: 'RAM',
      dataIndex: 'ram_mb',
      key: 'ram_mb',
      render: (v: number) => `${(v / 1024).toFixed(1)} GB`,
    },
    { title: 'Disk', dataIndex: 'disk_gb', key: 'disk_gb', render: (v: number) => `${v} GB` },
    {
      title: 'Actions',
      key: 'actions',
      render: (_: any, record: VM) => vmActions(record),
    },
  ];

  const renderVMCard = (vm: VM) => (
    <Card
      key={vm.id}
      size="small"
      title={
        <Space wrap>
          <Typography.Text code>{vm.name}</Typography.Text>
          {vm.rack_name && <Tag>{vm.rack_name.toUpperCase()}</Tag>}
        </Space>
      }
      extra={<Tag color={statusColor[vm.status] || 'default'}>{vm.status}</Tag>}
      actions={[vmActions(vm)]}
    >
      <Descriptions size="small" column={1} colon={false}>
        <Descriptions.Item label="VM IP">{vm.ip_address}</Descriptions.Item>
        <Descriptions.Item label="Host IP">{vm.host_ip || '-'}</Descriptions.Item>
        <Descriptions.Item label="CPU">{vm.cpu_cores} cores</Descriptions.Item>
        <Descriptions.Item label="RAM">{(vm.ram_mb / 1024).toFixed(1)} GB</Descriptions.Item>
        <Descriptions.Item label="Disk">{vm.disk_gb} GB</Descriptions.Item>
      </Descriptions>
    </Card>
  );

  const renderCards = (list: VM[]) => {
    if (list.length === 0) return <Empty description="No VMs" />;
    return (
      <Space direction="vertical" size={12} style={{ width: '100%' }}>
        {list.map(renderVMCard)}
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
          Virtual Machines
        </Typography.Title>
        <Space wrap>
          <span>Group by Rack</span>
          <Switch checked={groupByRack} onChange={setGroupByRack} />
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>
            Create VM
          </Button>
        </Space>
      </div>

      {groupByRack ? (
        vmsByRack.map((rack) => (
          <div key={rack.rack_name} style={{ marginBottom: 24 }}>
            <Typography.Title level={isMobile ? 5 : 4}>
              Rack {rack.rack_name.toUpperCase()} ({rack.host_ip})
            </Typography.Title>
            {isMobile ? (
              renderCards(rack.vms)
            ) : (
              <Table
                columns={columns}
                dataSource={rack.vms}
                rowKey="id"
                pagination={false}
                size="small"
                scroll={{ x: 'max-content' }}
              />
            )}
          </div>
        ))
      ) : isMobile ? (
        isLoading ? (
          <div style={{ textAlign: 'center', padding: 40 }}>
            <Spin />
          </div>
        ) : (
          renderCards(vms)
        )
      ) : (
        <Table
          columns={columns}
          dataSource={vms}
          rowKey="id"
          loading={isLoading}
          pagination={false}
          scroll={{ x: 'max-content' }}
        />
      )}

      <CreateVMModal open={createOpen} onClose={() => setCreateOpen(false)} />
      <TerminalDrawer
        open={!!terminalVm}
        onClose={() => setTerminalVm(null)}
        wsPath={terminalVm ? `/api/vms/${terminalVm.id}/terminal` : null}
        title={terminalVm ? `Terminal — ubuntu@${terminalVm.ip_address} (${terminalVm.name})` : 'Terminal'}
      />
    </div>
  );
};

export default VMsPage;
