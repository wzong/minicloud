import React, { useState } from 'react';
import { Typography, Card, Table, Button, Tag, Space, Descriptions, Modal, Form, Input, message, Popconfirm, Tooltip } from 'antd';
import { PlusOutlined, ReloadOutlined, CopyOutlined, DeleteOutlined } from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { wireguardApi } from '../api/wireguard';
import type { WGPeer } from '../types';

const WireGuardPage: React.FC = () => {
  const [addOpen, setAddOpen] = useState(false);
  const [form] = Form.useForm();
  const queryClient = useQueryClient();

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

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Typography.Title level={2} style={{ margin: 0 }}>WireGuard</Typography.Title>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={() => reloadMutation.mutate()} loading={reloadMutation.isPending}>
            Reload
          </Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setAddOpen(true)}>Add Peer</Button>
        </Space>
      </div>

      {status && (
        <Card style={{ marginBottom: 16 }}>
          <Descriptions bordered size="small" column={2}>
            <Descriptions.Item label="Interface">{status.interface}</Descriptions.Item>
            <Descriptions.Item label="Status">
              <Tag color={status.is_up ? 'green' : 'red'}>{status.is_up ? 'UP' : 'DOWN'}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="Listen Port">{status.listen_port}</Descriptions.Item>
            <Descriptions.Item label="Address">{status.address}</Descriptions.Item>
            <Descriptions.Item label="Public Key" span={2}>
              <Space>
                <Typography.Text code style={{ fontSize: 12 }}>{status.public_key}</Typography.Text>
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

      <Typography.Title level={4}>Peers</Typography.Title>
      <Table columns={peerColumns} dataSource={status?.peers || []} rowKey="datacenter_code" pagination={false} />

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
