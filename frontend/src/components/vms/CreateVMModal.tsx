import React from 'react';
import { Modal, Form, Select, Slider, InputNumber, Typography, message } from 'antd';
import { useMutation, useQueryClient, useQuery } from '@tanstack/react-query';
import { vmsApi } from '../../api/vms';
import { hostsApi } from '../../api/hosts';
import { sshKeysApi } from '../../api/sshKeys';

interface Props {
  open: boolean;
  onClose: () => void;
}

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

  return (
    <Modal
      title="Create Virtual Machine"
      open={open}
      onCancel={onClose}
      onOk={() => form.submit()}
      confirmLoading={createMutation.isPending}
      width={500}
    >
      <Form form={form} layout="vertical" onFinish={createMutation.mutate} initialValues={{ cpu_cores: 2, ram_mb: 2048, disk_gb: 20, os_image: 'ubuntu-22.04' }}>
        <Form.Item name="host_id" label="Host (leave empty for auto-select)">
          <Select allowClear placeholder="Auto-select">
            {hosts.filter(h => h.status === 'online').map(h => (
              <Select.Option key={h.id} value={h.id}>
                {h.rack_name.toUpperCase()} - {h.ip_address} ({h.cpu_cores} CPU, {((h.ram_mb || 0) / 1024).toFixed(0)} GB)
              </Select.Option>
            ))}
          </Select>
        </Form.Item>
        <Form.Item name="cpu_cores" label="CPU Cores">
          <Slider min={1} max={16} marks={{ 1: '1', 2: '2', 4: '4', 8: '8', 16: '16' }} />
        </Form.Item>
        <Form.Item name="ram_mb" label="RAM (MB)">
          <InputNumber min={512} max={65536} step={512} style={{ width: '100%' }} addonAfter="MB" />
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
