import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Table,
  Button,
  Space,
  Tag,
  message,
  Popconfirm,
  Modal,
  Form,
  Input,
  Switch,
  Card,
  Tooltip,
  Typography,
  Descriptions,
  Badge
} from 'antd';
import {
  PlusOutlined,
  StarOutlined,
  DeleteOutlined,
  EditOutlined,
  PlayCircleOutlined,
  SyncOutlined,
  EyeOutlined,
  EyeInvisibleOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined
} from '@ant-design/icons';
import { api } from '../api/client';

const { Title, Text } = Typography;

interface ConfigProfile {
  name: string;
  description: string;
  base_url: string;
  api_key: string;
  enabled: boolean;
  priority: string;
  created_at: string;
  last_used?: string;
}

export default function Configs() {
  const queryClient = useQueryClient();
  const [form] = Form.useForm();
  const [messageApi, contextHolder] = message.useMessage();

  // 状态管理
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);
  const [selectedConfig, setSelectedConfig] = useState<ConfigProfile | null>(null);
  const [showApiKey, setShowApiKey] = useState<Record<string, boolean>>({});

  // 查询配置列表
  const { data: configsResponse, isLoading, refetch } = useQuery({
    queryKey: ['configs'],
    queryFn: api.configs.list,
    refetchInterval: 10000, // 10秒自动刷新
  });

  // 查询默认配置
  const { data: defaultConfigResponse } = useQuery({
    queryKey: ['configs', 'default'],
    queryFn: api.configs.getDefault,
  });

  // 查询当前使用的配置
  const { data: currentConfigResponse } = useQuery({
    queryKey: ['configs', 'current'],
    queryFn: api.configs.getCurrent,
  });

  const configs = (configsResponse as any)?.data || [];
  const defaultConfigName = (defaultConfigResponse as any)?.data?.name;
  const currentConfigName = (currentConfigResponse as any)?.data?.name;

  // 创建配置
  const createMutation = useMutation({
    mutationFn: (values: any) => api.configs.create(values),
    onSuccess: (response: any) => {
      messageApi.success(response?.message || '配置创建成功');
      setIsCreateModalOpen(false);
      form.resetFields();
      queryClient.invalidateQueries({ queryKey: ['configs'] });
    },
    onError: (error: any) => {
      const errorMsg = error?.response?.data?.detail || error.message || '创建失败';
      messageApi.error(errorMsg); // 显示 5 秒
      console.error('创建配置错误:', error);
    },
  });

  // 更新配置
  const updateMutation = useMutation({
    mutationFn: ({ name, data }: { name: string; data: any }) =>
      api.configs.update(name, data),
    onSuccess: (response: any) => {
      messageApi.success(response?.message || '配置更新成功');
      setIsEditModalOpen(false);
      form.resetFields();
      queryClient.invalidateQueries({ queryKey: ['configs'] });
    },
    onError: (error: any) => {
      const errorMsg = error?.response?.data?.detail || error.message || '更新失败';
      messageApi.error(errorMsg);
      console.error('更新配置错误:', error);
    },
  });

  // 删除配置
  const deleteMutation = useMutation({
    mutationFn: (name: string) => api.configs.delete(name),
    onSuccess: (response: any) => {
      messageApi.success(response?.message || '配置删除成功');
      queryClient.invalidateQueries({ queryKey: ['configs'] });
      queryClient.invalidateQueries({ queryKey: ['configs', 'default'] });
    },
    onError: (error: any) => {
      const errorMsg = error?.response?.data?.detail || error.message || '删除失败';
      messageApi.error(errorMsg);
      console.error('删除配置错误:', error);
    },
  });

  // 使用配置
  const useMutation_use = useMutation({
    mutationFn: (name: string) => api.configs.use(name),
    onSuccess: (response: any) => {
      messageApi.success(response?.message || '配置已应用到 Claude Code');
      queryClient.invalidateQueries({ queryKey: ['configs'] });
      queryClient.invalidateQueries({ queryKey: ['configs', 'current'] });
    },
    onError: (error: any) => {
      const errorMsg = error?.response?.data?.detail || error.message || '应用失败';
      messageApi.error(errorMsg);
      console.error('应用配置错误:', error);
    },
  });

  // 设置为默认配置
  const setDefaultMutation = useMutation({
    mutationFn: (name: string) => api.configs.setDefault(name),
    onSuccess: (response: any) => {
      messageApi.success(response?.message || '默认配置已设置');
      queryClient.invalidateQueries({ queryKey: ['configs'] });
      queryClient.invalidateQueries({ queryKey: ['configs', 'default'] });
    },
    onError: (error: any) => {
      const errorMsg = error?.response?.data?.detail || error.message || '设置失败';
      messageApi.error(errorMsg);
      console.error('设置默认配置错误:', error);
    },
  });

  // 同步配置
  const syncMutation = useMutation({
    mutationFn: () => api.configs.sync(),
    onSuccess: (response: any) => {
      messageApi.success(response?.message || '配置同步成功');
      queryClient.invalidateQueries({ queryKey: ['configs'] });
    },
    onError: (error: any) => {
      const errorMsg = error?.response?.data?.detail || error.message || '同步失败';
      messageApi.error(errorMsg);
      console.error('同步配置错误:', error);
    },
  });

  // 打开创建对话框
  const handleCreate = () => {
    form.resetFields();
    setIsCreateModalOpen(true);
  };

  // 打开编辑对话框
  const handleEdit = (config: ConfigProfile) => {
    setSelectedConfig(config);
    form.setFieldsValue(config);
    setIsEditModalOpen(true);
  };

  // 查看详情
  const handleViewDetail = (config: ConfigProfile) => {
    setSelectedConfig(config);
    setIsDetailModalOpen(true);
  };

  // 提交创建
  const handleCreateSubmit = () => {
    form.validateFields().then((values) => {
      createMutation.mutate(values);
    });
  };

  // 提交更新
  const handleUpdateSubmit = () => {
    form.validateFields().then((values) => {
      if (selectedConfig) {
        updateMutation.mutate({ name: selectedConfig.name, data: values });
      }
    });
  };

  // 切换 API Key 显示
  const toggleApiKeyVisibility = (configName: string) => {
    setShowApiKey(prev => ({
      ...prev,
      [configName]: !prev[configName]
    }));
  };

  // 表格列定义
  const columns = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      width: 150,
      render: (name: string, record: ConfigProfile) => (
        <Space>
          <Text strong>{name}</Text>
          {defaultConfigName === name && (
            <Tag icon={<StarOutlined />} color="gold">默认</Tag>
          )}
        </Space>
      ),
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      width: 200,
      ellipsis: true,
    },
    {
      title: 'Base URL',
      dataIndex: 'base_url',
      key: 'base_url',
      width: 250,
      ellipsis: true,
      render: (url: string) => (
        <Tooltip title={url}>
          <Text code copyable={{ text: url }}>{url}</Text>
        </Tooltip>
      ),
    },
    {
      title: 'API Key',
      dataIndex: 'api_key',
      key: 'api_key',
      width: 180,
      render: (apiKey: string, record: ConfigProfile) => {
        const isVisible = showApiKey[record.name];
        const displayKey = apiKey
          ? isVisible
            ? apiKey
            : `${apiKey.slice(0, 8)}...${apiKey.slice(-4)}`
          : '未设置';

        return (
          <Space>
            <Text code>{displayKey}</Text>
            {apiKey && (
              <Button
                size="small"
                type="text"
                icon={isVisible ? <EyeInvisibleOutlined /> : <EyeOutlined />}
                onClick={() => toggleApiKeyVisibility(record.name)}
              />
            )}
          </Space>
        );
      },
    },
    {
      title: '状态',
      key: 'status',
      width: 120,
      render: (_: any, record: ConfigProfile) => (
        <Space direction="vertical" size="small">
          {record.enabled ? (
            <Badge status="success" text="启用" />
          ) : (
            <Badge status="default" text="禁用" />
          )}
          {record.last_used && (
            <Tooltip title={`上次使用: ${new Date(record.last_used).toLocaleString()}`}>
              <Tag icon={<ClockCircleOutlined />} color="blue" style={{ margin: 0 }}>
                已使用
              </Tag>
            </Tooltip>
          )}
        </Space>
      ),
    },
    {
      title: '优先级',
      dataIndex: 'priority',
      key: 'priority',
      width: 100,
      render: (priority: string) => {
        const colorMap: Record<string, string> = {
          primary: 'red',
          secondary: 'orange',
          fallback: 'default'
        };
        return <Tag color={colorMap[priority] || 'default'}>{priority}</Tag>;
      },
    },
    {
      title: '操作',
      key: 'actions',
      width: 280,
      fixed: 'right' as const,
      render: (_: any, record: ConfigProfile) => (
        <Space size="small">
          <Tooltip title="查看详情">
            <Button
              size="small"
              icon={<EyeOutlined />}
              onClick={() => handleViewDetail(record)}
            />
          </Tooltip>
          <Tooltip title="编辑配置">
            <Button
              size="small"
              icon={<EditOutlined />}
              onClick={() => handleEdit(record)}
            />
          </Tooltip>
          <Tooltip title="使用此配置">
            <Button
              size="small"
              type="primary"
              icon={<PlayCircleOutlined />}
              onClick={() => useMutation_use.mutate(record.name)}
              loading={useMutation_use.isPending}
            >
              使用
            </Button>
          </Tooltip>
          {defaultConfigName !== record.name && (
            <Tooltip title="设为默认">
              <Button
                size="small"
                icon={<StarOutlined />}
                onClick={() => setDefaultMutation.mutate(record.name)}
                loading={setDefaultMutation.isPending}
              />
            </Tooltip>
          )}
          <Popconfirm
            title="确定删除此配置吗?"
            description="删除后无法恢复，请谨慎操作。"
            onConfirm={() => deleteMutation.mutate(record.name)}
            okText="删除"
            cancelText="取消"
            okButtonProps={{ danger: true }}
          >
            <Tooltip title="删除配置">
              <Button
                size="small"
                danger
                icon={<DeleteOutlined />}
                loading={deleteMutation.isPending}
              />
            </Tooltip>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ paddingBottom: 24 }}>
      {contextHolder}
      {/* 页面标题和操作栏 */}
      <Card style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <Title level={2} style={{ margin: 0 }}>配置管理</Title>
            <Text type="secondary">
              管理 Claude Code 的 API 配置档案，支持多配置切换
            </Text>
          </div>
          <Space>
            <Button
              icon={<SyncOutlined />}
              onClick={() => syncMutation.mutate()}
              loading={syncMutation.isPending}
            >
              同步配置
            </Button>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={handleCreate}
            >
              添加配置
            </Button>
          </Space>
        </div>

        {/* 统计信息 */}
        <div style={{ marginTop: 16, display: 'flex', gap: 24, flexWrap: 'wrap' }}>
          <div>
            <Text type="secondary">总配置数: </Text>
            <Text strong style={{ fontSize: 18 }}>{configs.length}</Text>
          </div>
          <div>
            <Text type="secondary">启用: </Text>
            <Text strong style={{ fontSize: 18, color: '#52c41a' }}>
              {configs.filter((c: ConfigProfile) => c.enabled).length}
            </Text>
          </div>
          <div>
            <Text type="secondary">禁用: </Text>
            <Text strong style={{ fontSize: 18, color: '#8c8c8c' }}>
              {configs.filter((c: ConfigProfile) => !c.enabled).length}
            </Text>
          </div>
          {defaultConfigName && (
            <div>
              <Text type="secondary">默认配置: </Text>
              <Tag icon={<StarOutlined />} color="gold">{defaultConfigName}</Tag>
            </div>
          )}
          {currentConfigName && (
            <div>
              <Text type="secondary">当前使用: </Text>
              <Tag icon={<CheckCircleOutlined />} color="green">{currentConfigName}</Tag>
            </div>
          )}
        </div>
      </Card>

      {/* 配置列表表格 */}
      <Card>
        <Table
          columns={columns}
          dataSource={configs}
          loading={isLoading}
          rowKey="name"
          scroll={{ x: 1400 }}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 个配置`,
            pageSizeOptions: ['5', '10', '20', '50'],
          }}
        />
      </Card>

      {/* 创建配置对话框 */}
      <Modal
        title="添加配置"
        open={isCreateModalOpen}
        onOk={handleCreateSubmit}
        onCancel={() => {
          setIsCreateModalOpen(false);
          form.resetFields();
        }}
        confirmLoading={createMutation.isPending}
        width={600}
      >
        <Form form={form} layout="vertical" style={{ marginTop: 24 }}>
          <Form.Item
            label="配置名称"
            name="name"
            rules={[
              { required: true, message: '请输入配置名称' },
              { pattern: /^[a-zA-Z0-9_-]+$/, message: '只能包含字母、数字、下划线和连字符' }
            ]}
          >
            <Input placeholder="例如: openai-prod" />
          </Form.Item>

          <Form.Item
            label="配置描述"
            name="description"
          >
            <Input.TextArea
              placeholder="简要描述此配置的用途"
              rows={3}
            />
          </Form.Item>

          <Form.Item
            label="Base URL"
            name="base_url"
            rules={[
              { required: true, message: '请输入 Base URL' },
              { type: 'url', message: '请输入有效的 URL' }
            ]}
          >
            <Input placeholder="https://api.openai.com/v1" />
          </Form.Item>

          <Form.Item
            label="API Key"
            name="api_key"
            rules={[{ required: true, message: '请输入 API Key' }]}
          >
            <Input.Password placeholder="sk-..." />
          </Form.Item>

          <Form.Item
            label="启用状态"
            name="enabled"
            valuePropName="checked"
            initialValue={true}
          >
            <Switch checkedChildren="启用" unCheckedChildren="禁用" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 编辑配置对话框 */}
      <Modal
        title={`编辑配置: ${selectedConfig?.name}`}
        open={isEditModalOpen}
        onOk={handleUpdateSubmit}
        onCancel={() => {
          setIsEditModalOpen(false);
          form.resetFields();
          setSelectedConfig(null);
        }}
        confirmLoading={updateMutation.isPending}
        width={600}
      >
        <Form form={form} layout="vertical" style={{ marginTop: 24 }}>
          <Form.Item
            label="配置描述"
            name="description"
          >
            <Input.TextArea
              placeholder="简要描述此配置的用途"
              rows={3}
            />
          </Form.Item>

          <Form.Item
            label="Base URL"
            name="base_url"
            rules={[
              { required: true, message: '请输入 Base URL' },
              { type: 'url', message: '请输入有效的 URL' }
            ]}
          >
            <Input placeholder="https://api.openai.com/v1" />
          </Form.Item>

          <Form.Item
            label="API Key"
            name="api_key"
            rules={[{ required: true, message: '请输入 API Key' }]}
            extra="留空则不修改现有 API Key"
          >
            <Input.Password placeholder="留空则不修改" />
          </Form.Item>

          <Form.Item
            label="启用状态"
            name="enabled"
            valuePropName="checked"
          >
            <Switch checkedChildren="启用" unCheckedChildren="禁用" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 配置详情对话框 */}
      <Modal
        title="配置详情"
        open={isDetailModalOpen}
        onCancel={() => {
          setIsDetailModalOpen(false);
          setSelectedConfig(null);
        }}
        footer={[
          <Button key="close" onClick={() => setIsDetailModalOpen(false)}>
            关闭
          </Button>,
          <Button
            key="edit"
            type="primary"
            icon={<EditOutlined />}
            onClick={() => {
              setIsDetailModalOpen(false);
              if (selectedConfig) {
                handleEdit(selectedConfig);
              }
            }}
          >
            编辑
          </Button>,
        ]}
        width={700}
      >
        {selectedConfig && (
          <Descriptions bordered column={1} style={{ marginTop: 24 }}>
            <Descriptions.Item label="配置名称">
              <Text strong>{selectedConfig.name}</Text>
              {defaultConfigName === selectedConfig.name && (
                <Tag icon={<StarOutlined />} color="gold" style={{ marginLeft: 8 }}>
                  默认配置
                </Tag>
              )}
            </Descriptions.Item>
            <Descriptions.Item label="描述">
              {selectedConfig.description || '无'}
            </Descriptions.Item>
            <Descriptions.Item label="Base URL">
              <Text code copyable={{ text: selectedConfig.base_url }}>
                {selectedConfig.base_url}
              </Text>
            </Descriptions.Item>
            <Descriptions.Item label="API Key">
              <Space>
                <Text code>
                  {showApiKey[selectedConfig.name]
                    ? selectedConfig.api_key
                    : `${selectedConfig.api_key?.slice(0, 8)}...${selectedConfig.api_key?.slice(-4)}`}
                </Text>
                <Button
                  size="small"
                  type="text"
                  icon={showApiKey[selectedConfig.name] ? <EyeInvisibleOutlined /> : <EyeOutlined />}
                  onClick={() => toggleApiKeyVisibility(selectedConfig.name)}
                />
              </Space>
            </Descriptions.Item>
            <Descriptions.Item label="状态">
              {selectedConfig.enabled ? (
                <Badge status="success" text="启用" />
              ) : (
                <Badge status="default" text="禁用" />
              )}
            </Descriptions.Item>
            <Descriptions.Item label="优先级">
              <Tag color={
                selectedConfig.priority === 'primary' ? 'red' :
                selectedConfig.priority === 'secondary' ? 'orange' : 'default'
              }>
                {selectedConfig.priority}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="创建时间">
              {new Date(selectedConfig.created_at).toLocaleString('zh-CN')}
            </Descriptions.Item>
            <Descriptions.Item label="上次使用">
              {selectedConfig.last_used
                ? new Date(selectedConfig.last_used).toLocaleString('zh-CN')
                : '从未使用'}
            </Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
    </div>
  );
}
