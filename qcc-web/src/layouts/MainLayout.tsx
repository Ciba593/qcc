import { useState } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  DashboardOutlined,
  SettingOutlined,
  ApiOutlined,
  CloudServerOutlined,
  HeartOutlined,
  CheckCircleOutlined,
  CloudOutlined,
} from '@ant-design/icons';
import { Layout, Menu, Typography, theme, Tag, Space, Tooltip } from 'antd';
import type { MenuProps } from 'antd';
import { api } from '../api/client';

const { Header, Sider, Content } = Layout;
const { Title, Text } = Typography;

type MenuItem = Required<MenuProps>['items'][number];

const menuItems: MenuItem[] = [
  {
    key: '/dashboard',
    icon: <DashboardOutlined />,
    label: '仪表盘',
  },
  {
    key: '/configs',
    icon: <SettingOutlined />,
    label: '配置管理',
  },
  {
    key: '/endpoints',
    icon: <ApiOutlined />,
    label: 'Endpoint 管理',
  },
  {
    key: '/proxy',
    icon: <CloudServerOutlined />,
    label: '代理服务',
  },
  {
    key: '/health',
    icon: <HeartOutlined />,
    label: '健康监控',
  },
];

export default function MainLayout() {
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const {
    token: { colorBgContainer, borderRadiusLG },
  } = theme.useToken();

  // 查询 Claude Code 配置状态
  const { data: claudeConfigStatus } = useQuery({
    queryKey: ['claude-config-status'],
    queryFn: api.claudeConfig.status,
    refetchInterval: 5000, // 5秒刷新
  });

  // 查询运行时节点状态
  const { data: runtimeStatus } = useQuery({
    queryKey: ['health-runtime'],
    queryFn: api.health.runtime,
    refetchInterval: 5000, // 5秒刷新
  });

  const handleMenuClick: MenuProps['onClick'] = ({ key }) => {
    navigate(key);
  };

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        style={{
          overflow: 'auto',
          height: '100vh',
          position: 'fixed',
          left: 0,
          top: 0,
          bottom: 0,
        }}
      >
        <div style={{
          height: 64,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'white',
          fontSize: collapsed ? '16px' : '20px',
          fontWeight: 'bold'
        }}>
          {collapsed ? 'QCC' : 'QCC Dashboard'}
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={handleMenuClick}
        />
      </Sider>
      <Layout style={{ marginLeft: collapsed ? 80 : 200, transition: 'margin-left 0.2s', height: '100vh', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        <Header
          style={{
            padding: '0 24px',
            background: colorBgContainer,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderBottom: '1px solid #f0f0f0',
            flexShrink: 0,
          }}
        >
          <Title level={4} style={{ margin: 0 }}>
            QCC - Quick Claude Config
          </Title>

          <Space size="large">
            {/* Claude Code 系统配置状态 */}
            {(claudeConfigStatus as any)?.data?.current_base_url && (
              <Tooltip title={`Claude Code 当前配置: ${(claudeConfigStatus as any).data.current_base_url}`}>
                <Space size="small">
                  <CheckCircleOutlined style={{ color: '#52c41a' }} />
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    系统:
                  </Text>
                  <Tag color="green" style={{ margin: 0 }}>
                    {new URL((claudeConfigStatus as any).data.current_base_url).hostname.split('.')[0]}
                  </Tag>
                </Space>
              </Tooltip>
            )}

            {/* 运行时节点状态 */}
            {(runtimeStatus as any)?.data?.proxy_running && (() => {
              const data = (runtimeStatus as any).data;
              const activeNode = [...(data.primary_nodes || []), ...(data.secondary_nodes || [])]
                .find((n: any) => n.is_active);
              const activeNodeName = activeNode?.config_name || '未知';
              const primaryCount = data.primary_nodes?.length || 0;
              const secondaryCount = data.secondary_nodes?.length || 0;

              return (
                <Tooltip
                  title={
                    <div>
                      <div style={{ marginBottom: 4, fontWeight: 'bold' }}>
                        当前激活: {activeNodeName}
                      </div>
                      <div>主节点: {data.primary_nodes?.map((n: any) => n.config_name).join(', ') || '无'}</div>
                      <div>副节点: {data.secondary_nodes?.map((n: any) => n.config_name).join(', ') || '无'}</div>
                    </div>
                  }
                >
                  <Space size="small">
                    <CloudOutlined style={{ color: '#1890ff' }} />
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      节点:
                    </Text>
                    <Tag color="blue" style={{ margin: 0 }}>
                      {activeNodeName}
                    </Tag>
                    <Text type="secondary" style={{ fontSize: 11 }}>
                      ({primaryCount}主/{secondaryCount}副)
                    </Text>
                  </Space>
                </Tooltip>
              );
            })()}
          </Space>
        </Header>
        <Content
          style={{
            margin: '24px 16px',
            padding: 24,
            background: colorBgContainer,
            borderRadius: borderRadiusLG,
            overflow: 'auto',
            flex: 1,
          }}
        >
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
