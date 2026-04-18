import React from 'react';
import { Modal, Form, Select, InputNumber, Radio, Typography, Space, message } from 'antd';
import { useMutation, useQueryClient, useQuery } from '@tanstack/react-query';
import { vmsApi } from '../../api/vms';
import { hostsApi } from '../../api/hosts';
import { sshKeysApi } from '../../api/sshKeys';

interface Props {
  open: boolean;
  onClose: () => void;
}

const M3_TYPES = [
  { name: 'm3.medium',  cpu: 1, ram: 3840,  ramDisplay: '3.75 GB' },
  { name: 'm3.large',   cpu: 2, ram: 7680,  ramDisplay: '7.5 GB' },
  { name: 'm3.xlarge',  cpu: 4, ram: 15360, ramDisplay: '15 GB' },
  { name: 'm3.2xlarge', cpu: 8, ram: 30720, ramDisplay: '30 GB' },
];

const CreateVMModal: React.FC<Props> = ({ open, onClose }) => {
  const [form] = Form.useForm();
  const queryClient = useQueryClient();

  const { data: hosts = [] } = useQuery({ queryKey: ['hosts'], queryFn: hostsApi.list, enabled: open });
  const { data: sshKeys = [] } = useQuery({ queryKey: ['ssh-keys'], queryFn: sshKeysApi.list, enabled: open });

  const createMutation = useMutation({
    mutationFn: vmsApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['vms'] });
      message.success('VM created');
      form.resetFields();
      onClose();
    },
    onError: (err: any) => message.error(err.response?.data?.detail || 'Failed to create VM'),
  });

  const handleFinish = (values: any) => {
    const { instance_type, ...rest } = values;
    const type = M3_TYPES.find(t => t.name === instance_type)!;
    createMutation.mutate({ ...rest, cpu_cores: type.cpu, ram_mb: type.ram });
  };

  return (
    <Modal
      title="Create Virtual Machine"
      open={open}
      onCancel={onClose}
      onOk={() => form.submit()}
      confirmLoading={createMutation.isPending}
      width={500}
    >
      <Form
        form={form}
        layout="vertical"
        onFinish={handleFinish}
        initialValues={{ instance_type: 'm3.medium', disk_gb: 40, os_image: 'ubuntu-22.04' }}
      >
        <Form.Item name="host_id" label="Host (leave empty for auto-select)">
          <Select allowClear placeholder="Auto-select">
            {hosts.filter(h => h.status === 'online').map(h => (
              <Select.Option key={h.id} value={h.id}>
                {h.rack_name.toUpperCase()} - {h.ip_address} ({h.cpu_cores} CPU, {((h.ram_mb || 0) / 1024).toFixed(0)} GB)
              </Select.Option>
            ))}
          </Select>
        </Form.Item>
        <Form.Item name="instance_type" label="Instance Type" rules={[{ required: true }]}>
          <Radio.Group style={{ width: '100%' }}>
            <Space direction="vertical" style={{ width: '100%' }}>
              {M3_TYPES.map(t => (
                <Radio key={t.name} value={t.name} style={{ width: '100%' }}>
                  <Space>
                    <Typography.Text strong>{t.name}</Typography.Text>
                    <Typography.Text type="secondary">{t.cpu} vCPU / {t.ramDisplay}</Typography.Text>
                  </Space>
                </Radio>
              ))}
            </Space>
          </Radio.Group>
        </Form.Item>
        <Form.Item name="disk_gb" label="Disk (GB)">
          <InputNumber min={10} max={1000} step={10} style={{ width: '100%' }} addonAfter="GB" />
        </Form.Item>
        <Form.Item name="os_image" label="OS Image">
          <Select>
            <Select.Option value="ubuntu-22.04">Ubuntu 22.04</Select.Option>
            <Select.Option value="ubuntu-24.04">Ubuntu 24.04</Select.Option>
            <Select.Option value="debian-12">Debian 12</Select.Option>
          </Select>
        </Form.Item>
        <Form.Item name="ssh_key_id" label="SSH Key">
          <Select allowClear placeholder="Select SSH key">
            {sshKeys.map(k => (
              <Select.Option key={k.id} value={k.id}>{k.name}</Select.Option>
            ))}
          </Select>
        </Form.Item>
      </Form>
    </Modal>
  );
};

export default CreateVMModal;
