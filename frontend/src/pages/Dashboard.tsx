import React from 'react';
import { Typography, Card, Row, Col, Statistic, Table, Tag } from 'antd';
import { CloudServerOutlined, DesktopOutlined, ClusterOutlined, KeyOutlined } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { hostsApi } from '../api/hosts';
import { vmsApi } from '../api/vms';
import { clustersApi } from '../api/clusters';
import { sshKeysApi } from '../api/sshKeys';

const Dashboard: React.FC = () => {
  const { data: hosts = [] } = useQuery({ queryKey: ['hosts'], queryFn: hostsApi.list });
  const { data: vms = [] } = useQuery({ queryKey: ['vms'], queryFn: () => vmsApi.list() });
  const { data: clusters = [] } = useQuery({ queryKey: ['clusters'], queryFn: clustersApi.list });
  const { data: sshKeys = [] } = useQuery({ queryKey: ['ssh-keys'], queryFn: sshKeysApi.list });

  const onlineHosts = hosts.filter((h) => h.status === 'online').length;
  const runningVMs = vms.filter((v) => v.status === 'running').length;
  const runningClusters = clusters.filter((c) => c.status === 'running').length;

  return (
    <div>
      <Typography.Title level={2}>Dashboard</Typography.Title>
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic title="Hosts" value={hosts.length} prefix={<CloudServerOutlined />}
              suffix={<Typography.Text type="secondary" style={{ fontSize: 14 }}>({onlineHosts} online)</Typography.Text>} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="Virtual Machines" value={vms.length} prefix={<DesktopOutlined />}
              suffix={<Typography.Text type="secondary" style={{ fontSize: 14 }}>({runningVMs} running)</Typography.Text>} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="Clusters" value={clusters.length} prefix={<ClusterOutlined />}
              suffix={<Typography.Text type="secondary" style={{ fontSize: 14 }}>({runningClusters} running)</Typography.Text>} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="SSH Keys" value={sshKeys.length} prefix={<KeyOutlined />} />
          </Card>
        </Col>
      </Row>

      <Row gutter={16}>
        <Col span={12}>
          <Card title="Recent Hosts" size="small">
            <Table
              size="small"
              pagination={false}
              dataSource={hosts.slice(0, 5)}
              rowKey="id"
              columns={[
                { title: 'Rack', dataIndex: 'rack_name', render: (n: string) => <Tag>{n.toUpperCase()}</Tag> },
                { title: 'IP', dataIndex: 'ip_address' },
                { title: 'Status', dataIndex: 'status', render: (s: string) => <Tag color={s === 'online' ? 'green' : 'orange'}>{s}</Tag> },
              ]}
            />
          </Card>
        </Col>
        <Col span={12}>
          <Card title="Recent VMs" size="small">
            <Table
              size="small"
              pagination={false}
              dataSource={vms.slice(0, 5)}
              rowKey="id"
              columns={[
                { title: 'Name', dataIndex: 'name', render: (n: string) => <Typography.Text code>{n}</Typography.Text> },
                { title: 'IP', dataIndex: 'ip_address' },
                { title: 'Status', dataIndex: 'status', render: (s: string) => <Tag color={s === 'running' ? 'green' : 'default'}>{s}</Tag> },
              ]}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Dashboard;
