import React, { useState } from 'react';
import { Typography, Card, Table, Button, Tag, Space, Descriptions, Modal, Form, Input, message, Popconfirm, Tooltip, Grid, Empty } from 'antd';
import { PlusOutlined, ReloadOutlined, CopyOutlined, DeleteOutlined } from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { wireguardApi } from '../api/wireguard';
import type { WGPeer } from '../types';

const { useBreakpoint } = Grid;

const WireGuardPage: React.FC = () => {
  const [addOpen, setAddOpen] = useState(false);
  const [form] = Form.useForm();
  const queryClient = useQueryClient();
  const screens = useBreakpoint();
  const isMobile = !screens.md;

  const { data: status } = useQuery({
    queryKey: ['wg-status'],
    queryFn: wireguardApi.status,
    refetchInterval: 10000,
  });

  const addPeerMutation = useMutation({
    mutationFn: wireguardApi.addPeer,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['wg-status'] });
      message.success('Peer added');
      form.resetFields();
      setAddOpen(false);
    },
    onError: (err: any) => message.error(err.response?.data?.detail || 'Failed'),
  });

  const removePeerMutation = useMutation({
    mutationFn: wireguardApi.removePeer,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['wg-status'] });
      message.success('Peer removed');
    },
  });

  const reloadMutation = useMutation({
    mutationFn: wireguardApi.reload,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['wg-status'] });
      message.success('WireGuard reloaded');
    },
  });

  const peerColumns = [
    { title: 'Datacenter', dataIndex: 'datacenter_code', key: 'dc', render: (dc: string) => <Tag>{dc.toUpperCase()}</Tag> },
    { title: 'Endpoint', dataIndex: 'endpoint', key: 'endpoint' },
    { title: 'Allowed IPs', dataIndex: 'allowed_ips', key: 'allowed_ips' },
    { title: 'Handshake', dataIndex: 'latest_handshake', key: 'handshake', render: (v: string | undefined) => v || 'Never' },
    { title: 'RX', dataIndex: 'transfer_rx', key: 'rx', render: (v: string | undefined) => v || '-' },
    { title: 'TX', dataIndex: 'transfer_tx', key: 'tx', render: (v: string | undefined) => v || '-' },
    {
      title: 'Actions',
      key: 'actions',
      render: (_: any, record: WGPeer) => (
        <Popconfirm title="Remove this peer?" onConfirm={() => removePeerMutation.mutate(record.datacenter_code)}>
          <Button size="small" danger icon={<DeleteOutlined />} />
        </Popconfirm>
      ),
    },
  ];

  const renderPeerCards = (peers: WGPeer[]) => {
    if (peers.length === 0) return <Empty description="No peers" />;
    return (
      <Space direction="vertical" size={12} style={{ width: '100%' }}>
        {peers.map((peer) => (
          <Card
            key={peer.datacenter_code}
            size="small"
            title={<Tag>{peer.datacenter_code.toUpperCase()}</Tag>}
            extra={
              <Popconfirm title="Remove this peer?" onConfirm={() => removePeerMutation.mutate(peer.datacenter_code)}>
                <Button size="small" danger icon={<DeleteOutlined />} />
              </Popconfirm>
            }
          >
            <Descriptions size="small" column={1} colon={false}>
              <Descriptions.Item label="Endpoint">{peer.endpoint}</Descriptions.Item>
              <Descriptions.Item label="Allowed IPs">{peer.allowed_ips}</Descriptions.Item>
              <Descriptions.Item label="Handshake">{peer.latest_handshake || 'Never'}</Descriptions.Item>
              <Descriptions.Item label="RX">{peer.transfer_rx || '-'}</Descriptions.Item>
              <Descriptions.Item label="TX">{peer.transfer_tx || '-'}</Descriptions.Item>
            </Descriptions>
          </Card>
        ))}
      </Space>
    );
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Typography.Title level={isMobile ? 3 : 2} style={{ margin: 0 }}>WireGuard</Typography.Title>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={() => reloadMutation.mutate()} loading={reloadMutation.isPending}>
            Reload
          </Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setAddOpen(true)}>Add Peer</Button>
        </Space>
      </div>

      {status && (
        <Card style={{ marginBottom: 16 }}>
          <Descriptions bordered size="small" column={isMobile ? 1 : 2}>
            <Descriptions.Item label="Interface">{status.interface}</Descriptions.Item>
            <Descriptions.Item label="Status">
              <Tag color={status.is_up ? 'green' : 'red'}>{status.is_up ? 'UP' : 'DOWN'}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="Listen Port">{status.listen_port}</Descriptions.Item>
            <Descriptions.Item label="Address">{status.address}</Descriptions.Item>
            <Descriptions.Item label="Public Key" span={isMobile ? 1 : 2}>
              <Space wrap>
                <Typography.Text code style={{ fontSize: 12, wordBreak: 'break-all' }}>{status.public_key}</Typography.Text>
                <Tooltip title="Copy">
                  <Button
                    size="small"
                    icon={<CopyOutlined />}
                    onClick={() => { navigator.clipboard.writeText(status.public_key); message.success('Copied'); }}
                  />
                </Tooltip>
              </Space>
            </Descriptions.Item>
          </Descriptions>
        </Card>
      )}

      <Typography.Title level={isMobile ? 5 : 4}>Peers</Typography.Title>
      {isMobile
        ? renderPeerCards(status?.peers || [])
        : <Table columns={peerColumns} dataSource={status?.peers || []} rowKey="datacenter_code" pagination={false} scroll={{ x: 'max-content' }} />
      }

      <Modal
        title="Add WireGuard Peer"
        open={addOpen}
        onCancel={() => setAddOpen(false)}
        onOk={() => form.submit()}
        confirmLoading={addPeerMutation.isPending}
      >
        <Form form={form} layout="vertical" onFinish={addPeerMutation.mutate}>
          <Form.Item name="datacenter_code" label="Datacenter Code" rules={[{ required: true }]}>
            <Input placeholder="ny" />
          </Form.Item>
          <Form.Item name="public_key" label="Public Key" rules={[{ required: true }]}>
            <Input placeholder="Peer's WireGuard public key" />
          </Form.Item>
          <Form.Item name="endpoint" label="Endpoint" rules={[{ required: true }]}>
            <Input placeholder="203.0.113.10:51820" />
          </Form.Item>
          <Form.Item name="allowed_ips" label="Allowed IPs" rules={[{ required: true }]}>
            <Input placeholder="10.101.0.0/24, 10.200.0.2/32" />
          </Form.Item>
          <Form.Item name="comment" label="Comment">
            <Input placeholder="New York DC" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default WireGuardPage;
