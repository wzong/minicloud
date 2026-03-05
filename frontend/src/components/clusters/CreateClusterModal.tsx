import React, { useState } from 'react';
import { Modal, Form, Input, InputNumber, Select, Steps, Button, Space, Slider, Table, Tag, message } from 'antd';
import { useMutation, useQueryClient, useQuery } from '@tanstack/react-query';
import { clustersApi } from '../../api/clusters';
import { hostsApi } from '../../api/hosts';
import { sshKeysApi } from '../../api/sshKeys';
import type { ClusterPreview } from '../../types';

interface Props {
  open: boolean;
  onClose: () => void;
}

const CreateClusterModal: React.FC<Props> = ({ open, onClose }) => {
  const [form] = Form.useForm();
  const [step, setStep] = useState(0);
  const [preview, setPreview] = useState<ClusterPreview | null>(null);
  const queryClient = useQueryClient();

  const { data: hosts = [] } = useQuery({ queryKey: ['hosts'], queryFn: hostsApi.list, enabled: open });
  const { data: sshKeys = [] } = useQuery({ queryKey: ['ssh-keys'], queryFn: sshKeysApi.list, enabled: open });

  const previewMutation = useMutation({
    mutationFn: clustersApi.preview,
    onSuccess: (data) => { setPreview(data); setStep(2); },
    onError: (err: any) => message.error(err.response?.data?.detail || 'Preview failed'),
  });

  const createMutation = useMutation({
    mutationFn: clustersApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['clusters'] });
      message.success('Cluster creation started');
      form.resetFields();
      setStep(0);
      setPreview(null);
      onClose();
    },
    onError: (err: any) => message.error(err.response?.data?.detail || 'Failed'),
  });

  const handleNext = async () => {
    if (step === 0) {
      await form.validateFields(['name', 'k3s_version', 'ssh_key_id', 'os_image']);
      setStep(1);
    } else if (step === 1) {
      await form.validateFields();
      const values = form.getFieldsValue();
      previewMutation.mutate(values);
    }
  };

  const handleCreate = () => {
    createMutation.mutate(form.getFieldsValue());
  };

  return (
    <Modal
      title="Create Kubernetes Cluster"
      open={open}
      onCancel={() => { onClose(); setStep(0); setPreview(null); }}
      width={600}
      footer={
        <Space>
          {step > 0 && <Button onClick={() => setStep(step - 1)}>Back</Button>}
          {step < 2 && <Button type="primary" onClick={handleNext}>Next</Button>}
          {step === 2 && <Button type="primary" onClick={handleCreate} loading={createMutation.isPending}>Create Cluster</Button>}
        </Space>
      }
    >
      <Steps current={step} size="small" style={{ marginBottom: 24 }} items={[
        { title: 'Basics' },
        { title: 'Size' },
        { title: 'Confirm' },
      ]} />

      <Form form={form} layout="vertical" initialValues={{
        k3s_version: 'stable', os_image: 'ubuntu-22.04',
        control_plane_count: 1, worker_count: 2,
        cpu_cores: 2, ram_mb: 2048, disk_gb: 20,
      }}>
        <div style={{ display: step === 0 ? 'block' : 'none' }}>
          <Form.Item name="name" label="Cluster Name" rules={[{ required: true }]}>
            <Input placeholder="my-cluster" />
          </Form.Item>
          <Form.Item name="k3s_version" label="K3s Version">
            <Select>
              <Select.Option value="stable">Stable</Select.Option>
              <Select.Option value="latest">Latest</Select.Option>
              <Select.Option value="v1.28">v1.28</Select.Option>
              <Select.Option value="v1.29">v1.29</Select.Option>
              <Select.Option value="v1.30">v1.30</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="ssh_key_id" label="SSH Key" rules={[{ required: true }]}>
            <Select placeholder="Select SSH key">
              {sshKeys.map(k => (
                <Select.Option key={k.id} value={k.id}>{k.name}</Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item name="os_image" label="OS Image">
            <Select>
              <Select.Option value="ubuntu-22.04">Ubuntu 22.04</Select.Option>
              <Select.Option value="ubuntu-24.04">Ubuntu 24.04</Select.Option>
              <Select.Option value="debian-12">Debian 12</Select.Option>
            </Select>
          </Form.Item>
        </div>

        <div style={{ display: step === 1 ? 'block' : 'none' }}>
          <Form.Item name="control_plane_count" label="Control Plane Nodes">
            <InputNumber min={1} max={5} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="worker_count" label="Worker Nodes">
            <InputNumber min={0} max={50} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="cpu_cores" label="CPU per VM">
            <Slider min={1} max={16} marks={{ 1: '1', 2: '2', 4: '4', 8: '8' }} />
          </Form.Item>
          <Form.Item name="ram_mb" label="RAM per VM (MB)">
            <InputNumber min={512} max={32768} step={512} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="disk_gb" label="Disk per VM (GB)">
            <InputNumber min={10} max={500} step={10} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="host_ids" label="Hosts (leave empty for auto)">
            <Select mode="multiple" allowClear placeholder="Auto-distribute">
              {hosts.filter(h => h.status === 'online').map(h => (
                <Select.Option key={h.id} value={h.id}>{h.rack_name.toUpperCase()} - {h.ip_address}</Select.Option>
              ))}
            </Select>
          </Form.Item>
        </div>

        {step === 2 && preview && (
          <div>
            <p><strong>Total VMs:</strong> {preview.total_vms}</p>
            <p><strong>Total CPU:</strong> {preview.total_cpu} cores</p>
            <p><strong>Total RAM:</strong> {(preview.total_ram_mb / 1024).toFixed(1)} GB</p>
            <p><strong>Total Disk:</strong> {preview.total_disk_gb} GB</p>
            <Table
              size="small"
              pagination={false}
              dataSource={Object.entries(preview.distribution).map(([hostId, counts]) => ({
                key: hostId,
                host_id: hostId,
                control_plane: (counts as any).control_plane,
                worker: (counts as any).worker,
              }))}
              columns={[
                { title: 'Host ID', dataIndex: 'host_id' },
                { title: 'Control Plane', dataIndex: 'control_plane', render: (n: number) => <Tag color="blue">{n}</Tag> },
                { title: 'Workers', dataIndex: 'worker', render: (n: number) => <Tag color="green">{n}</Tag> },
              ]}
            />
          </div>
        )}
      </Form>
    </Modal>
  );
};

export default CreateClusterModal;
