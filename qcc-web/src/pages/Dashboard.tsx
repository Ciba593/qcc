import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, Row, Col, Statistic, Tag, Spin, Alert, Button, message, Table, Space, Progress } from 'antd';
import {
  DatabaseOutlined,
  CloudServerOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  CloseCircleOutlined,
  PlayCircleOutlined,
  StopOutlined,
  HeartOutlined,
} from '@ant-design/icons';
import { api } from '../api/client';
import { useNavigate } from 'react-router-dom';

export default function Dashboard() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const { data: summary, isLoading, error } = useQuery({
    queryKey: ['dashboard-summary'],
    queryFn: api.dashboard.getSummary,
    refetchInterval: 5000, // 每 5 秒刷新
  });

  // 获取健康状态
  const { data: healthData } = useQuery({
    queryKey: ['health-status'],
    queryFn: api.health.status,
    refetchInterval: 10000, // 每 10 秒刷新
  });

  // 启动代理
  const startProxyMutation = useMutation({
    mutationFn: ({ cluster }: { cluster: string }) =>
      api.proxy.start({ host: '127.0.0.1', port: 7860, cluster }),
    onSuccess: () => {
      message.success('代理服务启动成功');
      queryClient.invalidateQueries({ queryKey: ['dashboard-summary'] });
    },
    onError: (error: any) => {
      message.error(`启动失败: ${error.message}`);
    },
  });

  // 停止代理
  const stopProxyMutation = useMutation({
    mutationFn: api.proxy.stop,
    onSuccess: () => {
      message.success('代理服务已停止');
      queryClient.invalidateQueries({ queryKey: ['dashboard-summary'] });
    },
    onError: (error: any) => {
      message.error(`停止失败: ${error.message}`);
    },
  });

  if (isLoading) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Spin size="large" tip="加载中..." />
      </div>
    );
  }

  if (error) {
    return (
      <Alert
        message="加载失败"
        description={(error as Error).message}
        type="error"
        showIcon
      />
    );
  }

  const dashboardData: any = summary?.data || {};
  const proxyStatus: any = dashboardData.proxy_status || {};
  const endpointHealth: any = dashboardData.endpoint_health || {};
  const endpointGroups: any[] = dashboardData.endpoint_groups || [];

  // 健康状态数据
  const healthSummary = (healthData as any)?.data?.summary || {
    healthy: 0,
    degraded: 0,
    unhealthy: 0,
    unknown: 0,
    total: 0,
  };

  // 计算总体健康率
  const overallHealthRate =
    healthSummary.total > 0
      ? ((healthSummary.healthy / healthSummary.total) * 100).toFixed(1)
      : 0;

  // EndpointGroup 表格列定义
  const groupColumns = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
    },
    {
      title: '主节点',
      dataIndex: 'primary_configs',
      key: 'primary_configs',
      render: (configs: string[]) => (
        <Space>
          {configs.map((config) => (
            <Tag key={config} color="blue">
              {config}
            </Tag>
          ))}
        </Space>
      ),
    },
    {
      title: '副节点',
      dataIndex: 'secondary_configs',
      key: 'secondary_configs',
      render: (configs: string[]) => (
        <Space>
          {configs.map((config) => (
            <Tag key={config} color="green">
              {config}
            </Tag>
          ))}
        </Space>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: any, record: any) => (
        <Space>
          {proxyStatus.running ? (
            <Button
              type="primary"
              danger
              size="small"
              icon={<StopOutlined />}
              onClick={() => stopProxyMutation.mutate()}
              loading={stopProxyMutation.isPending}
            >
              停止代理
            </Button>
          ) : (
            <Button
              type="primary"
              size="small"
              icon={<PlayCircleOutlined />}
              onClick={() => startProxyMutation.mutate({ cluster: record.name })}
              loading={startProxyMutation.isPending}
            >
              启动代理
            </Button>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div>
      <h1>系统概览</h1>

      <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
        {/* 配置统计 */}
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="配置总数"
              value={dashboardData.total_configs || 0}
              prefix={<DatabaseOutlined />}
            />
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="活跃配置"
              value={dashboardData.active_config || '未设置'}
              valueStyle={{ fontSize: '20px' }}
            />
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="存储方式"
              value={dashboardData.storage_backend || '未知'}
              valueStyle={{ fontSize: '20px' }}
            />
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Card>
            <div style={{ marginBottom: 8, color: 'rgba(0, 0, 0, 0.45)' }}>
              代理服务
            </div>
            {proxyStatus.running ? (
              <Tag icon={<CheckCircleOutlined />} color="success">
                运行中 (PID: {proxyStatus.pid})
              </Tag>
            ) : (
              <Tag color="default">未运行</Tag>
            )}
          </Card>
        </Col>
      </Row>

      {/* Endpoint 健康状况 */}
      <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
        <Col xs={24}>
          <Card
            title="Endpoint 健康状况"
            extra={
              <Button
                type="link"
                icon={<HeartOutlined />}
                onClick={(e) => {
                  e.stopPropagation();
                  navigate('/health');
                }}
              >
                查看详情
              </Button>
            }
          >
            <Row gutter={16}>
              <Col xs={24} sm={12} md={6}>
                <Statistic
                  title="总体健康率"
                  value={overallHealthRate}
                  suffix="%"
                  valueStyle={{
                    color: Number(overallHealthRate) >= 80 ? '#52c41a' : '#faad14',
                  }}
                  prefix={<HeartOutlined />}
                />
                <Progress
                  percent={Number(overallHealthRate)}
                  status={Number(overallHealthRate) >= 80 ? 'success' : 'normal'}
                  style={{ marginTop: 8 }}
                />
              </Col>
              <Col xs={8} sm={6} md={4}>
                <Statistic
                  title="健康"
                  value={healthSummary.healthy}
                  valueStyle={{ color: '#52c41a' }}
                  prefix={<CheckCircleOutlined />}
                  suffix={`/ ${healthSummary.total}`}
                />
              </Col>
              <Col xs={8} sm={6} md={4}>
                <Statistic
                  title="降级"
                  value={healthSummary.degraded}
                  valueStyle={{ color: '#faad14' }}
                  prefix={<WarningOutlined />}
                  suffix={`/ ${healthSummary.total}`}
                />
              </Col>
              <Col xs={8} sm={6} md={5}>
                <Statistic
                  title="不健康"
                  value={healthSummary.unhealthy}
                  valueStyle={{ color: '#f5222d' }}
                  prefix={<CloseCircleOutlined />}
                  suffix={`/ ${healthSummary.total}`}
                />
              </Col>
              <Col xs={24} sm={6} md={5}>
                <Statistic
                  title="未知"
                  value={healthSummary.unknown}
                  valueStyle={{ color: '#d9d9d9' }}
                  suffix={`/ ${healthSummary.total}`}
                />
              </Col>
            </Row>
          </Card>
        </Col>
      </Row>

      {/* EndpointGroup 列表与代理控制 */}
      <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
        <Col xs={24}>
          <Card title="代理组管理">
            {endpointGroups.length > 0 ? (
              <Table
                dataSource={endpointGroups}
                columns={groupColumns}
                rowKey="name"
                pagination={false}
              />
            ) : (
              <div style={{ textAlign: 'center', padding: '20px', color: '#999' }}>
                暂无代理组，请先创建 EndpointGroup
              </div>
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
}
