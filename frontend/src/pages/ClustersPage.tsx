import React, { useState } from 'react';
import { Typography, Table, Button, Space, Tag, message, Popconfirm, Tooltip, Drawer, Descriptions } from 'antd';
import { PlusOutlined, DeleteOutlined, DownloadOutlined, EyeOutlined } from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { clustersApi } from '../api/clusters';
import type { Cluster } from '../types';
import CreateClusterModal from '../components/clusters/CreateClusterModal';

const ClustersPage: React.FC = () => {
  const [createOpen, setCreateOpen] = useState(false);
  const [detailCluster, setDetailCluster] = useState<Cluster | null>(null);
  const queryClient = useQueryClient();

  const { data: clusters = [], isLoading } = useQuery({
    queryKey: ['clusters'],
    queryFn: clustersApi.list,
  });

  const deleteMutation = useMutation({
    mutationFn: clustersApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['clusters'] });
      message.success('Cluster deletion started');
    },
    onError: (err: any) => message.error(err.response?.data?.detail || 'Failed'),
  });

  const statusColor: Record<string, string> = {
    running: 'green', creating: 'blue', degraded: 'orange', error: 'red', deleting: 'orange',
  };

  const roleColor: Record<string, string> = {
    control_plane: 'blue',
    worker: 'green',
  };

  const columns = [
    { title: 'Name', dataIndex: 'name', key: 'name', render: (n: string) => <Typography.Text strong>{n}</Typography.Text> },
    { title: 'Status', dataIndex: 'status', key: 'status', render: (s: string) => <Tag color={statusColor[s] || 'default'}>{s}</Tag> },
    { title: 'Version', dataIndex: 'k3s_version', key: 'version' },
    { title: 'Control Plane', dataIndex: 'control_plane_count', key: 'cp', render: (n: number) => `${n} nodes` },
    { title: 'Workers', dataIndex: 'worker_count', key: 'workers', render: (n: number) => `${n} nodes` },
    { title: 'Created', dataIndex: 'created_at', key: 'created_at', render: (d: string) => new Date(d).toLocaleDateString() },
    {
      title: 'Actions',
      key: 'actions',
      render: (_: any, record: Cluster) => (
        <Space>
          <Tooltip title="View Details">
            <Button size="small" icon={<EyeOutlined />} onClick={() => setDetailCluster(record)} />
          </Tooltip>
          <Tooltip title="Download Kubeconfig">
            <Button
              size="small"
              icon={<DownloadOutlined />}
              disabled={record.status !== 'running'}
              onClick={async () => {
                try {
                  const kc = await clustersApi.getKubeconfig(record.id);
                  const blob = new Blob([kc], { type: 'text/yaml' });
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement('a');
                  a.href = url;
                  a.download = `${record.name}-kubeconfig.yaml`;
                  a.click();
                  URL.revokeObjectURL(url);
                } catch { message.error('Kubeconfig not available'); }
              }}
            />
          </Tooltip>
          <Popconfirm title="Delete this cluster and all its VMs?" onConfirm={() => deleteMutation.mutate(record.id)}>
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const nodeColumns = [
    { title: 'VM', dataIndex: 'vm_name', key: 'vm_name', render: (n: string) => <Typography.Text code>{n}</Typography.Text> },
    { title: 'Role', dataIndex: 'role', key: 'role', render: (r: string) => <Tag color={roleColor[r] || 'default'}>{r}</Tag> },
    { title: 'Status', dataIndex: 'status', key: 'status', render: (s: string) => <Tag color={s === 'ready' ? 'green' : 'orange'}>{s}</Tag> },
    { title: 'VM IP', dataIndex: 'vm_ip', key: 'vm_ip' },
    { title: 'Host', dataIndex: 'host_ip', key: 'host_ip' },
    { title: 'Rack', dataIndex: 'rack_name', key: 'rack_name', render: (n: string) => n ? <Tag>{n.toUpperCase()}</Tag> : '-' },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Typography.Title level={2} style={{ margin: 0 }}>Clusters</Typography.Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>Create Cluster</Button>
      </div>
      <Table columns={columns} dataSource={clusters} rowKey="id" loading={isLoading} pagination={false} />
      <CreateClusterModal open={createOpen} onClose={() => setCreateOpen(false)} />

      <Drawer
        title={detailCluster ? `Cluster: ${detailCluster.name}` : ''}
        open={!!detailCluster}
        onClose={() => setDetailCluster(null)}
        width={700}
      >
        {detailCluster && (
          <>
            <Descriptions bordered size="small" column={2}>
              <Descriptions.Item label="Status"><Tag color={statusColor[detailCluster.status]}>{detailCluster.status}</Tag></Descriptions.Item>
              <Descriptions.Item label="Version">{detailCluster.k3s_version}</Descriptions.Item>
              <Descriptions.Item label="Control Plane">{detailCluster.control_plane_count} nodes</Descriptions.Item>
              <Descriptions.Item label="Workers">{detailCluster.worker_count} nodes</Descriptions.Item>
            </Descriptions>
            <Typography.Title level={4} style={{ marginTop: 24 }}>Nodes</Typography.Title>
            <Table columns={nodeColumns} dataSource={detailCluster.nodes} rowKey="id" pagination={false} size="small" />
          </>
        )}
      </Drawer>
    </div>
  );
};

export default ClustersPage;
