import React, { useState } from 'react';
import { Typography, Table, Button, Tag, Space, Modal, Form, Input, message, Popconfirm, Card, Row, Col, Statistic } from 'antd';
import { LockOutlined, UnlockOutlined } from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ipApi } from '../api/ip';

const IPManagementPage: React.FC = () => {
  const [reserveOpen, setReserveOpen] = useState(false);
  const [form] = Form.useForm();
  const queryClient = useQueryClient();

  const { data: allocations = [], isLoading } = useQuery({
    queryKey: ['ip-allocations'],
    queryFn: ipApi.allocations,
  });

  const { data: available } = useQuery({
    queryKey: ['ip-available'],
    queryFn: ipApi.available,
  });

  const reserveMutation = useMutation({
    mutationFn: (values: { ip_address: string; notes?: string }) =>
      ipApi.reserve(values.ip_address, values.notes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ip-allocations'] });
      queryClient.invalidateQueries({ queryKey: ['ip-available'] });
      message.success('IP reserved');
      form.resetFields();
      setReserveOpen(false);
    },
    onError: (err: any) => message.error(err.response?.data?.detail || 'Failed'),
  });

  const unreserveMutation = useMutation({
    mutationFn: ipApi.unreserve,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ip-allocations'] });
      queryClient.invalidateQueries({ queryKey: ['ip-available'] });
      message.success('IP released');
    },
  });

  const columns = [
    { title: 'IP Address', dataIndex: 'ip_address', key: 'ip_address' },
    {
      title: 'Status',
      key: 'status',
      render: (_: any, record: any) => {
        if (record.vm_id) return <Tag color="blue">Allocated</Tag>;
        if (record.is_reserved) return <Tag color="orange">Reserved</Tag>;
        return <Tag color="green">Available</Tag>;
      },
    },
    { title: 'VM', dataIndex: 'vm_name', key: 'vm_name', render: (v: string | null) => v || '-' },
    { title: 'Notes', dataIndex: 'notes', key: 'notes', render: (v: string | null) => v || '-' },
    {
      title: 'Actions',
      key: 'actions',
      render: (_: any, record: any) =>
        record.is_reserved && !record.vm_id ? (
          <Popconfirm title="Release this reservation?" onConfirm={() => unreserveMutation.mutate(record.ip_address)}>
            <Button size="small" icon={<UnlockOutlined />}>Release</Button>
          </Popconfirm>
        ) : null,
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Typography.Title level={2} style={{ margin: 0 }}>IP Management</Typography.Title>
        <Button icon={<LockOutlined />} onClick={() => setReserveOpen(true)}>Reserve IP</Button>
      </div>

      {available && (
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={8}>
            <Card><Statistic title="Available" value={available.total_available} valueStyle={{ color: '#3f8600' }} /></Card>
          </Col>
          <Col span={8}>
            <Card><Statistic title="Used" value={available.total_range - available.total_available} valueStyle={{ color: '#1677ff' }} /></Card>
          </Col>
          <Col span={8}>
            <Card><Statistic title="Total Range" value={available.total_range} /></Card>
          </Col>
        </Row>
      )}

      <Table columns={columns} dataSource={allocations} rowKey="id" loading={isLoading} pagination={false} />

      <Modal
        title="Reserve IP Address"
        open={reserveOpen}
        onCancel={() => setReserveOpen(false)}
        onOk={() => form.submit()}
        confirmLoading={reserveMutation.isPending}
      >
        <Form form={form} layout="vertical" onFinish={reserveMutation.mutate}>
          <Form.Item name="ip_address" label="IP Address" rules={[{ required: true }]}>
            <Input placeholder="10.100.0.50" />
          </Form.Item>
          <Form.Item name="notes" label="Notes">
            <Input placeholder="Reserved for..." />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default IPManagementPage;
