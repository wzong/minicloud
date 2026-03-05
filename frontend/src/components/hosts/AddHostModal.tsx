import React from 'react';
import { Modal, Form, Input, InputNumber, Select, message } from 'antd';
import { useMutation, useQueryClient, useQuery } from '@tanstack/react-query';
import { hostsApi } from '../../api/hosts';
import { sshKeysApi } from '../../api/sshKeys';

interface Props {
  open: boolean;
  onClose: () => void;
}

const AddHostModal: React.FC<Props> = ({ open, onClose }) => {
  const [form] = Form.useForm();
  const queryClient = useQueryClient();

  const { data: sshKeys = [] } = useQuery({
    queryKey: ['ssh-keys'],
    queryFn: sshKeysApi.list,
    enabled: open,
  });

  const createMutation = useMutation({
    mutationFn: async (values: any) => {
      const host = await hostsApi.create(values);
      // Auto-trigger detection
      try {
        await hostsApi.detect(host.id);
      } catch (e) {
        // Detection failure is non-fatal
      }
      return host;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['hosts'] });
      message.success('Host added successfully');
      form.resetFields();
      onClose();
    },
    onError: (err: any) => message.error(err.response?.data?.detail || 'Failed to add host'),
  });

  return (
    <Modal
      title="Add Host"
      open={open}
      onCancel={onClose}
      onOk={() => form.submit()}
      confirmLoading={createMutation.isPending}
    >
      <Form form={form} layout="vertical" onFinish={createMutation.mutate}>
        <Form.Item name="ip_address" label="IP Address" rules={[{ required: true }]}>
          <Input placeholder="192.168.1.100" />
        </Form.Item>
        <Form.Item name="ssh_port" label="SSH Port" initialValue={22}>
          <InputNumber min={1} max={65535} style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item name="ssh_user" label="SSH User" initialValue="root">
          <Input />
        </Form.Item>
        <Form.Item name="ssh_key_path" label="SSH Key">
          <Select allowClear placeholder="Select an SSH key">
            {sshKeys.map((k) => (
              <Select.Option key={k.id} value={`/app/data/ssh_keys/${k.name}`}>
                {k.name} ({k.fingerprint.substring(0, 20)}...)
              </Select.Option>
            ))}
          </Select>
        </Form.Item>
        <Form.Item name="ssh_password" label="Password (if no key)">
          <Input.Password placeholder="Leave empty if using SSH key" />
        </Form.Item>
      </Form>
    </Modal>
  );
};

export default AddHostModal;
