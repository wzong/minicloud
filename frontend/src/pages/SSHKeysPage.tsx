import React, { useState } from 'react';
import { Typography, Table, Button, Space, Modal, Form, Input, message, Popconfirm, Tag, Tooltip } from 'antd';
import { PlusOutlined, ImportOutlined, DeleteOutlined, CopyOutlined } from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { sshKeysApi } from '../api/sshKeys';
import type { SSHKey } from '../types';

const SSHKeysPage: React.FC = () => {
  const [generateOpen, setGenerateOpen] = useState(false);
  const [importOpen, setImportOpen] = useState(false);
  const [genForm] = Form.useForm();
  const [impForm] = Form.useForm();
  const queryClient = useQueryClient();

  const { data: keys = [], isLoading } = useQuery({
    queryKey: ['ssh-keys'],
    queryFn: sshKeysApi.list,
  });

  const generateMutation = useMutation({
    mutationFn: (name: string) => sshKeysApi.generate(name),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ssh-keys'] });
      message.success('SSH key generated');
      genForm.resetFields();
      setGenerateOpen(false);
    },
    onError: (err: any) => message.error(err.response?.data?.detail || 'Failed'),
  });

  const importMutation = useMutation({
    mutationFn: (values: { name: string; private_key: string }) =>
      sshKeysApi.import(values.name, values.private_key),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ssh-keys'] });
      message.success('SSH key imported');
      impForm.resetFields();
      setImportOpen(false);
    },
    onError: (err: any) => message.error(err.response?.data?.detail || 'Failed'),
  });

  const deleteMutation = useMutation({
    mutationFn: sshKeysApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ssh-keys'] });
      message.success('SSH key deleted');
    },
  });

  const columns = [
    { title: 'Name', dataIndex: 'name', key: 'name' },
    {
      title: 'Fingerprint',
      dataIndex: 'fingerprint',
      key: 'fingerprint',
      render: (fp: string) => <Typography.Text code style={{ fontSize: 12 }}>{fp}</Typography.Text>,
    },
    {
      title: 'Public Key',
      dataIndex: 'public_key',
      key: 'public_key',
      render: (key: string) => (
        <Space>
          <Typography.Text ellipsis style={{ maxWidth: 200 }}>{key}</Typography.Text>
          <Tooltip title="Copy public key">
            <Button
              size="small"
              icon={<CopyOutlined />}
              onClick={() => { navigator.clipboard.writeText(key); message.success('Copied'); }}
            />
          </Tooltip>
        </Space>
      ),
    },
    {
      title: 'Created',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (d: string) => new Date(d).toLocaleDateString(),
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_: any, record: SSHKey) => (
        <Popconfirm title="Delete this key?" onConfirm={() => deleteMutation.mutate(record.id)}>
          <Button size="small" danger icon={<DeleteOutlined />} />
        </Popconfirm>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Typography.Title level={2} style={{ margin: 0 }}>SSH Keys</Typography.Title>
        <Space>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setGenerateOpen(true)}>Generate</Button>
          <Button icon={<ImportOutlined />} onClick={() => setImportOpen(true)}>Import</Button>
        </Space>
      </div>
      <Table columns={columns} dataSource={keys} rowKey="id" loading={isLoading} pagination={false} />

      <Modal
        title="Generate SSH Key"
        open={generateOpen}
        onCancel={() => setGenerateOpen(false)}
        onOk={() => genForm.submit()}
        confirmLoading={generateMutation.isPending}
      >
        <Form form={genForm} layout="vertical" onFinish={(v) => generateMutation.mutate(v.name)}>
          <Form.Item name="name" label="Key Name" rules={[{ required: true }]}>
            <Input placeholder="my-key" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="Import SSH Key"
        open={importOpen}
        onCancel={() => setImportOpen(false)}
        onOk={() => impForm.submit()}
        confirmLoading={importMutation.isPending}
      >
        <Form form={impForm} layout="vertical" onFinish={(v) => importMutation.mutate(v)}>
          <Form.Item name="name" label="Key Name" rules={[{ required: true }]}>
            <Input placeholder="my-key" />
          </Form.Item>
          <Form.Item name="private_key" label="Private Key (PEM)" rules={[{ required: true }]}>
            <Input.TextArea rows={8} placeholder="-----BEGIN OPENSSH PRIVATE KEY-----" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default SSHKeysPage;
