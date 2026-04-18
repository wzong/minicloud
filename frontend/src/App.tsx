import React, { useEffect, useState } from 'react';
import { Routes, Route, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu, Typography, theme, Button, Drawer, Grid, ConfigProvider, Tooltip } from 'antd';
import {
  DashboardOutlined,
  CloudServerOutlined,
  DesktopOutlined,
  ClusterOutlined,
  KeyOutlined,
  GlobalOutlined,
  ApiOutlined,
  MenuOutlined,
  BulbOutlined,
  BulbFilled,
} from '@ant-design/icons';
import Dashboard from './pages/Dashboard';
import HostsPage from './pages/HostsPage';
import VMsPage from './pages/VMsPage';
import ClustersPage from './pages/ClustersPage';
import SSHKeysPage from './pages/SSHKeysPage';
import IPManagementPage from './pages/IPManagementPage';
import WireGuardPage from './pages/WireGuardPage';

const { Sider, Content, Header } = Layout;
const { useBreakpoint } = Grid;

const THEME_KEY = 'mc.theme';

const menuItems = [
  { key: '/', icon: <DashboardOutlined />, label: 'Dashboard' },
  { key: '/hosts', icon: <CloudServerOutlined />, label: 'Hosts' },
  { key: '/vms', icon: <DesktopOutlined />, label: 'Virtual Machines' },
  { key: '/clusters', icon: <ClusterOutlined />, label: 'Clusters' },
  { key: '/ssh-keys', icon: <KeyOutlined />, label: 'SSH Keys' },
  { key: '/ip-management', icon: <GlobalOutlined />, label: 'IP Management' },
  { key: '/wireguard', icon: <ApiOutlined />, label: 'WireGuard' },
];

const getInitialDark = (): boolean => {
  const stored = localStorage.getItem(THEME_KEY);
  if (stored === 'dark') return true;
  if (stored === 'light') return false;
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ?? false;
};

interface AppLayoutProps {
  isDark: boolean;
  onToggleTheme: () => void;
}

const AppLayout: React.FC<AppLayoutProps> = ({ isDark, onToggleTheme }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const { token } = theme.useToken();
  const screens = useBreakpoint();
  const isMobile = !screens.md;

  const [desktopCollapsed, setDesktopCollapsed] = useState(false);
  const [mobileDrawerOpen, setMobileDrawerOpen] = useState(false);

  useEffect(() => {
    if (isMobile) setMobileDrawerOpen(false);
  }, [location.pathname, isMobile]);

  useEffect(() => {
    document.body.style.background = token.colorBgLayout;
  }, [token.colorBgLayout]);

  const brand = (
    <div
      style={{
        padding: '16px 24px',
        borderBottom: `1px solid ${token.colorBorderSecondary}`,
      }}
    >
      <Typography.Title level={4} style={{ margin: 0 }}>
        Minicloud
      </Typography.Title>
    </div>
  );

  const navMenu = (
    <Menu
      mode="inline"
      selectedKeys={[location.pathname]}
      items={menuItems}
      onClick={({ key }) => navigate(key)}
      style={{ borderRight: 0 }}
    />
  );

  return (
    <Layout style={{ minHeight: '100vh' }}>
      {!isMobile && (
        <Sider
          width={220}
          collapsedWidth={64}
          collapsed={desktopCollapsed}
          trigger={null}
          style={{ background: token.colorBgContainer }}
        >
          {!desktopCollapsed && brand}
          {navMenu}
        </Sider>
      )}
      <Layout>
        <Header
          style={{
            padding: '0 16px',
            background: token.colorBgContainer,
            borderBottom: `1px solid ${token.colorBorderSecondary}`,
            display: 'flex',
            alignItems: 'center',
            gap: 12,
            height: 56,
            lineHeight: '56px',
          }}
        >
          <Button
            type="text"
            icon={<MenuOutlined />}
            aria-label="Toggle sidebar"
            onClick={() =>
              isMobile ? setMobileDrawerOpen(true) : setDesktopCollapsed((v) => !v)
            }
          />
          {isMobile && (
            <Typography.Title level={4} style={{ margin: 0 }}>
              Minicloud
            </Typography.Title>
          )}
          <Tooltip title={isDark ? 'Switch to light theme' : 'Switch to dark theme'}>
            <Button
              type="text"
              style={{ marginLeft: 'auto' }}
              icon={isDark ? <BulbFilled /> : <BulbOutlined />}
              aria-label="Toggle dark theme"
              onClick={onToggleTheme}
            />
          </Tooltip>
        </Header>
        <Drawer
          placement="left"
          open={isMobile && mobileDrawerOpen}
          onClose={() => setMobileDrawerOpen(false)}
          width={240}
          styles={{ body: { padding: 0 } }}
          title={null}
          closable={false}
        >
          {brand}
          {navMenu}
        </Drawer>
        <Content
          style={{
            padding: isMobile ? 12 : 24,
            background: token.colorBgLayout,
          }}
        >
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

const App: React.FC = () => {
  const [isDark, setIsDark] = useState<boolean>(getInitialDark);

  const toggleTheme = () => {
    setIsDark((prev) => {
      const next = !prev;
      localStorage.setItem(THEME_KEY, next ? 'dark' : 'light');
      return next;
    });
  };

  return (
    <ConfigProvider
      theme={{
        algorithm: isDark ? theme.darkAlgorithm : theme.defaultAlgorithm,
      }}
    >
      <AppLayout isDark={isDark} onToggleTheme={toggleTheme} />
    </ConfigProvider>
  );
};

export default App;
