import React from 'react';
import { Routes, Route, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu, Typography, theme } from 'antd';
import {
  DashboardOutlined,
  CloudServerOutlined,
  DesktopOutlined,
  ClusterOutlined,
  KeyOutlined,
  GlobalOutlined,
  ApiOutlined,
} from '@ant-design/icons';
import Dashboard from './pages/Dashboard';
import HostsPage from './pages/HostsPage';
import VMsPage from './pages/VMsPage';
import ClustersPage from './pages/ClustersPage';
import SSHKeysPage from './pages/SSHKeysPage';
import IPManagementPage from './pages/IPManagementPage';
import WireGuardPage from './pages/WireGuardPage';

const { Sider, Content, Header } = Layout;

const menuItems = [
  { key: '/', icon: <DashboardOutlined />, label: 'Dashboard' },
  { key: '/hosts', icon: <CloudServerOutlined />, label: 'Hosts' },
  { key: '/vms', icon: <DesktopOutlined />, label: 'Virtual Machines' },
  { key: '/clusters', icon: <ClusterOutlined />, label: 'Clusters' },
  { key: '/ssh-keys', icon: <KeyOutlined />, label: 'SSH Keys' },
  { key: '/ip-management', icon: <GlobalOutlined />, label: 'IP Management' },
  { key: '/wireguard', icon: <ApiOutlined />, label: 'WireGuard' },
];

const App: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { token } = theme.useToken();

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider width={220} style={{ background: token.colorBgContainer }}>
        <div style={{ padding: '16px 24px', borderBottom: `1px solid ${token.colorBorderSecondary}` }}>
          <Typography.Title level={4} style={{ margin: 0 }}>Minicloud</Typography.Title>
        </div>
        <Menu
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
          style={{ borderRight: 0 }}
        />
      </Sider>
      <Layout>
        <Content style={{ padding: 24, background: token.colorBgLayout }}>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/hosts" element={<HostsPage />} />
            <Route path="/vms" element={<VMsPage />} />
            <Route path="/clusters" element={<ClustersPage />} />
            <Route path="/ssh-keys" element={<SSHKeysPage />} />
            <Route path="/ip-management" element={<IPManagementPage />} />
            <Route path="/wireguard" element={<WireGuardPage />} />
          </Routes>
        </Content>
      </Layout>
    </Layout>
  );
};

export default App;
