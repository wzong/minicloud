import React, { useState } from 'react';
import { Typography, Table, Button, Tag, Space, Modal, Form, Input, message, Popconfirm, Card, Row, Col, Statistic, Descriptions, Empty, Grid, theme } from 'antd';
import { LockOutlined, UnlockOutlined } from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ipApi } from '../api/ip';
import type { IPAllocation } from '../types';

const { useBreakpoint } = Grid;

const IPManagementPage: React.FC = () => {
  const [reserveOpen, setReserveOpen] = useState(false);
  const [form] = Form.useForm();
  const queryClient = useQueryClient();
  const { token } = theme.useToken();
  const screens = useBreakpoint();
  const isMobile = !screens.md;

  const { data: config } = useQuery({
    queryKey: ['ip-config'],
    queryFn: ipApi.config,
  });

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

  const ipStatus = (record: IPAllocation) => {
    if (record.vm_id) return <Tag color="blue">Allocated</Tag>;
    if (record.is_reserved) return <Tag color="orange">Reserved</Tag>;
    return <Tag color="green">Available</Tag>;
  };

  const releaseAction = (record: IPAllocation) =>
    record.is_reserved && !record.vm_id ? (
      <Popconfirm title="Release this reservation?" onConfirm={() => unreserveMutation.mutate(record.ip_address)}>
        <Button size="small" icon={<UnlockOutlined />}>Release</Button>
      </Popconfirm>
    ) : null;

  const columns = [
    { title: 'IP Address', dataIndex: 'ip_address', key: 'ip_address' },
    { title: 'Status', key: 'status', render: (_: any, record: IPAllocation) => ipStatus(record) },
    { title: 'VM', dataIndex: 'vm_name', key: 'vm_name', render: (v: string | null) => v || '-' },
    { title: 'Notes', dataIndex: 'notes', key: 'notes', render: (v: string | null) => v || '-' },
    { title: 'Actions', key: 'actions', render: (_: any, record: IPAllocation) => releaseAction(record) },
  ];

  const renderCards = () => {
    if (allocations.length === 0 && !isLoading) return <Empty description="No IP allocations" />;
    return (
      <Space direction="vertical" size={12} style={{ width: '100%' }}>
        {allocations.map((record) => (
          <Card
            key={record.id}
            size="small"
            title={<Typography.Text strong>{record.ip_address}</Typography.Text>}
            extra={ipStatus(record)}
            actions={releaseAction(record) ? [releaseAction(record)] : undefined}
          >
            <Descriptions size="small" column={1} colon={false}>
              {record.vm_name && <Descriptions.Item label="VM">{record.vm_name}</Descriptions.Item>}
              {record.notes && <Descriptions.Item label="Notes">{record.notes}</Descriptions.Item>}
            </Descriptions>
          </Card>
        ))}
      </Space>
    );
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Typography.Title level={isMobile ? 3 : 2} style={{ margin: 0 }}>IP Management</Typography.Title>
        <Button icon={<LockOutlined />} onClick={() => setReserveOpen(true)}>Reserve IP</Button>
      </div>

      {config && (
        <Card size="small" style={{ marginBottom: 16 }}>
          <Descriptions size="small" column={isMobile ? 1 : 4} colon>
            <Descriptions.Item label="Range">{config.range_start} – {config.range_end}</Descriptions.Item>
            <Descriptions.Item label="Subnet">{config.subnet_mask}</Descriptions.Item>
            <Descriptions.Item label="Gateway">{config.gateway}</Descriptions.Item>
            <Descriptions.Item label="DNS">{config.dns.join(', ')}</Descriptions.Item>
          </Descriptions>
        </Card>
      )}

      {available && (
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={8}>
            <Card><Statistic title="Available" value={available.total_available} valueStyle={{ color: token.colorSuccess }} /></Card>
          </Col>
          <Col span={8}>
            <Card><Statistic title="Used" value={available.total_range - available.total_available} valueStyle={{ color: token.colorPrimary }} /></Card>
          </Col>
          <Col span={8}>
            <Card><Statistic title="Total Range" value={available.total_range} /></Card>
          </Col>
        </Row>
      )}

      {isMobile ? renderCards() : (
        <Table columns={columns} dataSource={allocations} rowKey="id" loading={isLoading} pagination={false} scroll={{ x: 'max-content' }} />
      )}

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
