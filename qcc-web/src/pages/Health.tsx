import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Card,
  Row,
  Col,
  Statistic,
  Table,
  Tag,
  Button,
  Space,
  Alert,
  Spin,
  message,
  Divider,
  Progress,
  Tooltip,
  Badge,
  Dropdown,
  Modal,
  Select,
  Typography,
} from 'antd';
import type { MenuProps } from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  WarningOutlined,
  QuestionCircleOutlined,
  SyncOutlined,
  MoreOutlined,
  PlusOutlined,
  SwapOutlined,
  StopOutlined,
  ReloadOutlined,
  InfoCircleOutlined,
  DeleteOutlined,
} from '@ant-design/icons';
import { api } from '../api/client';

const { Title, Text, Paragraph } = Typography;

interface NodeInfo {
  config_name: string;
  endpoint_id: string;
  base_url: string;
  enabled: boolean;
  status: string;
  success_rate: number;
  avg_response_time: number;
  total_requests: number;
  failed_requests: number;
  consecutive_failures: number;
  last_check?: string;
  priority: number;
  retry_count?: number;
  next_retry?: string | null;
  is_active?: boolean;  // 是否为当前正在使用的节点
  last_error?: string;  // 最后一次错误信息
}

interface RuntimeData {
  proxy_running: boolean;
  cluster_name?: string;
  endpoint_group?: {
    name: string;
    description: string;
    enabled: boolean;
  };
  primary_nodes: NodeInfo[];
  secondary_nodes: NodeInfo[];
  retry_queue: NodeInfo[];
  summary: {
    primary_count: number;
    secondary_count: number;
    retry_count: number;
    primary_healthy: number;
    secondary_healthy: number;
  };
  message?: string;
}

export default function Health() {
  const queryClient = useQueryClient();
  const [addNodeModalVisible, setAddNodeModalVisible] = useState(false);
  const [selectedNodeType, setSelectedNodeType] = useState<'primary' | 'secondary'>('primary');
  const [selectedConfig, setSelectedConfig] = useState<string>('');

  // 获取运行时状态
  const { data: runtimeData, isLoading, error, refetch } = useQuery({
    queryKey: ['health-runtime'],
    queryFn: api.health.runtime,
    refetchInterval: 5000, // 每 5 秒刷新
  });

  // 获取所有配置（用于添加节点）
  const { data: configsData } = useQuery({
    queryKey: ['configs-list'],
    queryFn: api.configs.list,
  });

  // 移动节点
  const moveNodeMutation = useMutation({
    mutationFn: (params: { config_name: string; to_type: string }) =>
      api.health.moveNode(params),
    onSuccess: (response: any) => {
      message.success(response?.message || '节点移动成功');
      queryClient.invalidateQueries({ queryKey: ['health-runtime'] });
    },
    onError: (error: any) => {
      message.error(`移动失败: ${error.message}`);
    },
  });

  // 添加节点
  const addNodeMutation = useMutation({
    mutationFn: (params: { config_name: string; node_type: string }) =>
      api.health.addNode(params),
    onSuccess: (response: any) => {
      message.success(response?.message || '节点添加成功');
      setAddNodeModalVisible(false);
      setSelectedConfig('');
      queryClient.invalidateQueries({ queryKey: ['health-runtime'] });
    },
    onError: (error: any) => {
      message.error(`添加失败: ${error.message}`);
    },
  });

  // 删除节点
  const removeNodeMutation = useMutation({
    mutationFn: (params: { config_name: string }) =>
      api.health.removeNode(params),
    onSuccess: (response: any) => {
      message.success(response?.message || '节点删除成功');
      queryClient.invalidateQueries({ queryKey: ['health-runtime'] });
    },
    onError: (error: any) => {
      message.error(`删除失败: ${error.message}`);
    },
  });

  const runtime: RuntimeData = (runtimeData as any)?.data || {
    proxy_running: false,
    primary_nodes: [],
    secondary_nodes: [],
    retry_queue: [],
    summary: {
      primary_count: 0,
      secondary_count: 0,
      retry_count: 0,
      primary_healthy: 0,
      secondary_healthy: 0,
    },
  };

  const availableConfigs = ((configsData as any)?.data || [])
    .filter((config: any) => {
      // 过滤掉已经在主节点或副节点中的配置
      const inPrimary = runtime.primary_nodes?.some(n => n.config_name === config.name);
      const inSecondary = runtime.secondary_nodes?.some(n => n.config_name === config.name);
      return !inPrimary && !inSecondary;
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

  if (!runtime.proxy_running) {
    return (
      <div>
        <Title level={2}>健康监控</Title>
        <Alert
          message="代理服务未运行"
          description={runtime.message || "请先启动代理服务以查看健康监控信息"}
          type="info"
          showIcon
          icon={<InfoCircleOutlined />}
          style={{ marginTop: 24 }}
        />
      </div>
    );
  }

  // 状态图标映射
  const getStatusBadge = (status: string) => {
    const statusMap = {
      healthy: { status: 'success' as const, text: '健康', color: '#52c41a' },
      degraded: { status: 'warning' as const, text: '降级', color: '#faad14' },
      unhealthy: { status: 'error' as const, text: '不健康', color: '#f5222d' },
      unknown: { status: 'default' as const, text: '未知', color: '#d9d9d9' },
    };
    const config = statusMap[status as keyof typeof statusMap] || statusMap.unknown;
    return (
      <Space>
        <Badge status={config.status} />
        <Tag color={config.status === 'success' ? 'success' : config.status === 'warning' ? 'warning' : config.status === 'error' ? 'error' : 'default'}>
          {config.text}
        </Tag>
      </Space>
    );
  };

  // 格式化时间
  const formatTime = (isoString?: string) => {
    if (!isoString) return '从未检查';
    const date = new Date(isoString);
    return date.toLocaleString('zh-CN');
  };

  // 格式化响应时间
  const formatResponseTime = (ms: number) => {
    if (ms < 1000) return `${ms.toFixed(0)}ms`;
    return `${(ms / 1000).toFixed(2)}s`;
  };

  // 节点操作菜单
  const getNodeActions = (node: NodeInfo, currentType: 'primary' | 'secondary' | 'retry'): MenuProps['items'] => {
    const items: MenuProps['items'] = [];

    if (currentType !== 'primary') {
      items.push({
        key: 'to-primary',
        label: '移到主节点',
        icon: <SwapOutlined />,
        onClick: () => moveNodeMutation.mutate({
          config_name: node.config_name,
          to_type: 'primary'
        }),
      });
    }

    if (currentType !== 'secondary') {
      items.push({
        key: 'to-secondary',
        label: '移到副节点',
        icon: <SwapOutlined />,
        onClick: () => moveNodeMutation.mutate({
          config_name: node.config_name,
          to_type: 'secondary'
        }),
      });
    }

    if (currentType !== 'retry') {
      items.push({
        key: 'to-retry',
        label: '移到重试队列',
        icon: <ReloadOutlined />,
        onClick: () => moveNodeMutation.mutate({
          config_name: node.config_name,
          to_type: 'retry_queue'
        }),
      });
    }

    items.push({
      type: 'divider',
    });

    items.push({
      key: 'remove',
      label: '删除节点',
      icon: <DeleteOutlined />,
      danger: true,
      onClick: () => {
        Modal.confirm({
          title: '确认删除节点',
          content: `确定要从当前 EndpointGroup 中删除节点 ${node.config_name} 吗？`,
          okText: '删除',
          cancelText: '取消',
          okButtonProps: { danger: true },
          onOk: () => removeNodeMutation.mutate({
            config_name: node.config_name
          }),
        });
      },
    });

    return items;
  };

  // 表格列定义
  const columns = [
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 140,
      render: (status: string) => getStatusBadge(status),
    },
    {
      title: '配置名称',
      dataIndex: 'config_name',
      key: 'config_name',
      width: 200,
      render: (name: string, record: NodeInfo) => (
        <span style={{ whiteSpace: 'nowrap' }}>
          <Text strong>{name}</Text>
          {record.is_active && (
            <Badge status="processing" text="使用中" style={{ marginLeft: 8 }} />
          )}
        </span>
      ),
    },
    {
      title: 'Base URL',
      dataIndex: 'base_url',
      key: 'base_url',
      ellipsis: true,
      render: (url: string) => (
        <Tooltip title={url}>
          <a href={url} target="_blank" rel="noopener noreferrer">
            {url}
          </a>
        </Tooltip>
      ),
    },
    {
      title: '成功率',
      dataIndex: 'success_rate',
      key: 'success_rate',
      width: 100,
      render: (rate: number) => {
        const color = rate >= 90 ? '#52c41a' : rate >= 70 ? '#faad14' : '#f5222d';
        return <Text style={{ color, fontWeight: 500 }}>{rate.toFixed(1)}%</Text>;
      },
    },
    {
      title: '平均响应',
      dataIndex: 'avg_response_time',
      key: 'avg_response_time',
      width: 100,
      render: (time: number) => {
        const color = time < 200 ? '#52c41a' : time < 500 ? '#faad14' : '#f5222d';
        return <span style={{ color }}>{formatResponseTime(time)}</span>;
      },
    },
    {
      title: '请求统计',
      key: 'requests',
      width: 130,
      render: (_: any, record: NodeInfo) => (
        <Text>
          {record.total_requests}
          {record.failed_requests > 0 && (
            <Text type="danger"> / {record.failed_requests}</Text>
          )}
        </Text>
      ),
    },
    {
      title: '错误信息',
      key: 'last_error',
      width: 250,
      ellipsis: true,
      render: (_: any, record: NodeInfo) => {
        // 只在不健康状态时显示错误信息
        if (record.status !== 'unhealthy' && record.status !== 'degraded') {
          return <Text type="secondary">-</Text>;
        }
        if (!record.last_error) {
          return <Text type="secondary">无错误详情</Text>;
        }
        return (
          <Tooltip title={record.last_error}>
            <Text type="danger" ellipsis style={{ maxWidth: '250px' }}>
              {record.last_error}
            </Text>
          </Tooltip>
        );
      },
    },
    {
      title: '操作',
      key: 'actions',
      width: 80,
      fixed: 'right' as const,
      render: (_: any, record: NodeInfo) => (
        <Dropdown
          menu={{ items: getNodeActions(record, 'primary') }}
          trigger={['click']}
        >
          <Button
            type="text"
            icon={<MoreOutlined />}
            loading={moveNodeMutation.isPending}
          />
        </Dropdown>
      ),
    },
  ];

  // 为主节点、副节点和重试队列创建专门的列
  const primaryColumns = columns.map(col =>
    col.key === 'actions' ? {
      ...col,
      render: (_: any, record: NodeInfo) => (
        <Dropdown
          menu={{ items: getNodeActions(record, 'primary') }}
          trigger={['click']}
        >
          <Button
            type="text"
            icon={<MoreOutlined />}
            loading={moveNodeMutation.isPending}
          />
        </Dropdown>
      )
    } : col
  );

  const secondaryColumns = columns.map(col =>
    col.key === 'actions' ? {
      ...col,
      render: (_: any, record: NodeInfo) => (
        <Dropdown
          menu={{ items: getNodeActions(record, 'secondary') }}
          trigger={['click']}
        >
          <Button
            type="text"
            icon={<MoreOutlined />}
            loading={moveNodeMutation.isPending}
          />
        </Dropdown>
      )
    } : col
  );

  const retryColumns = [
    ...columns.filter(col => col.key !== 'success_rate'),
    {
      title: '重试次数',
      dataIndex: 'retry_count',
      key: 'retry_count',
      width: 100,
      render: (count: number) => (
        <Tag color="error">{count} 次</Tag>
      ),
    },
  ].map(col =>
    col.key === 'actions' ? {
      ...col,
      render: (_: any, record: NodeInfo) => (
        <Dropdown
          menu={{ items: getNodeActions(record, 'retry') }}
          trigger={['click']}
        >
          <Button
            type="text"
            icon={<MoreOutlined />}
            loading={moveNodeMutation.isPending}
          />
        </Dropdown>
      )
    } : col
  );

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Title level={2}>健康监控</Title>
        <Space>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setAddNodeModalVisible(true)}
          >
            添加节点
          </Button>
          <Button
            icon={<SyncOutlined />}
            onClick={() => refetch()}
          >
            刷新
          </Button>
        </Space>
      </div>

      {/* EndpointGroup 信息 */}
      {runtime.endpoint_group && (
        <Card style={{ marginTop: 24 }}>
          <Space direction="vertical" size="small" style={{ width: '100%' }}>
            <div>
              <Text type="secondary">当前代理组: </Text>
              <Text strong style={{ fontSize: '16px' }}>{runtime.endpoint_group.name}</Text>
              {runtime.endpoint_group.description && (
                <>
                  {' - '}
                  <Text type="secondary">{runtime.endpoint_group.description}</Text>
                </>
              )}
            </div>
          </Space>
        </Card>
      )}

      {/* 健康状态统计 */}
      <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
        <Col xs={12} sm={8}>
          <Card>
            <Statistic
              title="主节点总数"
              value={runtime.summary.primary_count}
              suffix={`/ ${runtime.summary.primary_healthy} 健康`}
              valueStyle={{ color: runtime.summary.primary_healthy === runtime.summary.primary_count ? '#52c41a' : '#faad14' }}
              prefix={<CheckCircleOutlined />}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8}>
          <Card>
            <Statistic
              title="副节点总数"
              value={runtime.summary.secondary_count}
              suffix={`/ ${runtime.summary.secondary_healthy} 健康`}
              valueStyle={{ color: runtime.summary.secondary_healthy === runtime.summary.secondary_count ? '#52c41a' : '#faad14' }}
              prefix={<WarningOutlined />}
            />
          </Card>
        </Col>
        <Col xs={12} sm={8}>
          <Card>
            <Statistic
              title="重试队列"
              value={runtime.summary.retry_count}
              valueStyle={{ color: runtime.summary.retry_count > 0 ? '#f5222d' : '#52c41a' }}
              prefix={<ReloadOutlined />}
            />
          </Card>
        </Col>
      </Row>

      <Divider />

      {/* 主节点列表 */}
      <Card
        title={
          <Space>
            <Badge status="processing" />
            <span>主节点 ({runtime.primary_nodes?.length || 0})</span>
          </Space>
        }
        style={{ marginTop: 24 }}
      >
        {runtime.primary_nodes && runtime.primary_nodes.length > 0 ? (
          <Table
            dataSource={runtime.primary_nodes}
            columns={primaryColumns}
            rowKey="endpoint_id"
            pagination={false}
            scroll={{ x: 1000 }}
            size="middle"
          />
        ) : (
          <div style={{ textAlign: 'center', padding: '20px', color: '#999' }}>
            暂无主节点
          </div>
        )}
      </Card>

      {/* 副节点列表 */}
      <Card
        title={
          <Space>
            <Badge status="default" />
            <span>副节点 ({runtime.secondary_nodes?.length || 0})</span>
          </Space>
        }
        style={{ marginTop: 24 }}
      >
        {runtime.secondary_nodes && runtime.secondary_nodes.length > 0 ? (
          <Table
            dataSource={runtime.secondary_nodes}
            columns={secondaryColumns}
            rowKey="endpoint_id"
            pagination={false}
            scroll={{ x: 1000 }}
            size="middle"
          />
        ) : (
          <div style={{ textAlign: 'center', padding: '20px', color: '#999' }}>
            暂无副节点
          </div>
        )}
      </Card>

      {/* 重试队列 */}
      <Card
        title={
          <Space>
            <Badge status="error" />
            <span>重试队列 ({runtime.retry_queue?.length || 0})</span>
          </Space>
        }
        style={{ marginTop: 24 }}
      >
        {runtime.retry_queue && runtime.retry_queue.length > 0 ? (
          <>
            <Alert
              message="这些节点已被标记为失败，系统会每 60 秒自动重试验证"
              type="warning"
              showIcon
              style={{ marginBottom: 16 }}
            />
            <Table
              dataSource={runtime.retry_queue}
              columns={retryColumns}
              rowKey="endpoint_id"
              pagination={false}
              scroll={{ x: 1000 }}
              size="middle"
            />
          </>
        ) : (
          <div style={{ textAlign: 'center', padding: '20px', color: '#999' }}>
            <CheckCircleOutlined style={{ fontSize: '48px', color: '#52c41a', marginBottom: '16px' }} />
            <div>重试队列为空，所有节点运行正常</div>
          </div>
        )}
      </Card>

      {/* 添加节点 Modal */}
      <Modal
        title="添加节点"
        open={addNodeModalVisible}
        onOk={() => {
          if (!selectedConfig) {
            message.warning('请选择配置');
            return;
          }
          addNodeMutation.mutate({
            config_name: selectedConfig,
            node_type: selectedNodeType,
          });
        }}
        onCancel={() => {
          setAddNodeModalVisible(false);
          setSelectedConfig('');
        }}
        confirmLoading={addNodeMutation.isPending}
      >
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <div>
            <Text>节点类型:</Text>
            <Select
              style={{ width: '100%', marginTop: 8 }}
              value={selectedNodeType}
              onChange={setSelectedNodeType}
              options={[
                { label: '主节点', value: 'primary' },
                { label: '副节点', value: 'secondary' },
              ]}
            />
          </div>
          <div>
            <Text>选择配置:</Text>
            <Select
              style={{ width: '100%', marginTop: 8 }}
              value={selectedConfig}
              onChange={setSelectedConfig}
              placeholder="请选择配置"
              showSearch
              filterOption={(input, option) =>
                String(option?.label ?? '').toLowerCase().includes(input.toLowerCase())
              }
              options={availableConfigs.map((config: any) => ({
                label: `${config.name} - ${config.base_url || '无URL'}`,
                value: config.name,
              }))}
            />
          </div>
        </Space>
      </Modal>
    </div>
  );
}
