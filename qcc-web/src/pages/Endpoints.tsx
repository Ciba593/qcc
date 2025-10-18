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
  Badge,
  Select,
  Statistic,
  Row,
  Col,
  Divider,
  List
} from 'antd';
import {
  PlusOutlined,
  DeleteOutlined,
  EyeOutlined,
  EditOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  QuestionCircleOutlined,
  WarningOutlined,
  ThunderboltOutlined,
  ApiOutlined,
  MinusCircleOutlined
} from '@ant-design/icons';
import { api } from '../api/client';

const { Title, Text } = Typography;
const { TextArea } = Input;

// ========== 类型定义 ==========

interface EndpointGroup {
  id: string;
  name: string;
  description: string;
  primary_configs: string[];
  secondary_configs: string[];
  enabled: boolean;
  created_at: string;
  updated_at: string;
  metadata?: Record<string, any>;
}

export default function Endpoints() {
  const queryClient = useQueryClient();
  const [form] = Form.useForm();
  const [editForm] = Form.useForm();
  const [messageApi, contextHolder] = message.useMessage();

  // 状态管理
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [selectedGroup, setSelectedGroup] = useState<EndpointGroup | null>(null);

  // 查询所有配置（用于选择主副节点）
  const { data: configsResponse } = useQuery({
    queryKey: ['configs'],
    queryFn: api.configs.list,
  });

  // 查询所有 EndpointGroup
  const { data: groupsResponse, isLoading } = useQuery({
    queryKey: ['endpoints'],
    queryFn: api.endpoints.list,
    refetchInterval: 10000, // 10秒自动刷新
  });

  // 查询代理状态
  const { data: proxyStatusResponse } = useQuery({
    queryKey: ['proxy-status'],
    queryFn: api.proxy.status,
    refetchInterval: 5000,
  });

  const configs = (configsResponse as any)?.data || [];
  const groups = (groupsResponse as any)?.data || [];
  const proxyStatus = (proxyStatusResponse as any)?.data || {};
  const isProxyRunning = proxyStatus.running || false;
  const currentClusterName = proxyStatus.config;

  // 创建 EndpointGroup
  const createMutation = useMutation({
    mutationFn: (values: any) => api.endpoints.create(values),
    onSuccess: (response: any) => {
      messageApi.success(response?.message || 'EndpointGroup 创建成功');
      setIsCreateModalOpen(false);
      form.resetFields();
      queryClient.invalidateQueries({ queryKey: ['endpoints'] });
    },
    onError: (error: any) => {
      const errorMsg = error?.response?.data?.detail || error.message || '创建失败';
      messageApi.error(errorMsg);
      console.error('创建 EndpointGroup 错误:', error);
    },
  });

  // 重启代理
  const restartProxyMutation = useMutation({
    mutationFn: async () => {
      await api.proxy.stop();
      await new Promise(resolve => setTimeout(resolve, 1000)); // 等待1秒
      return api.proxy.start({
        host: proxyStatus.host || '127.0.0.1',
        port: proxyStatus.port || 7860,
        cluster: currentClusterName
      });
    },
    onSuccess: () => {
      messageApi.success('代理服务已重启，新配置已生效');
      queryClient.invalidateQueries({ queryKey: ['proxy-status'] });
    },
    onError: (error: any) => {
      messageApi.error(`重启失败: ${error.message}`);
    },
  });

  // 更新 EndpointGroup
  const updateMutation = useMutation({
    mutationFn: ({ name, data }: { name: string; data: any }) =>
      api.endpoints.update(name, data),
    onSuccess: (response: any, variables: any) => {
      messageApi.success(response?.message || 'EndpointGroup 更新成功');

      // 检查是否需要重启代理
      if (isProxyRunning && currentClusterName === variables.name) {
        Modal.confirm({
          title: '需要重启代理服务',
          content: '您修改了当前正在使用的 EndpointGroup 配置。需要重启代理服务以应用新配置。',
          okText: '立即重启',
          cancelText: '稍后手动重启',
          onOk: () => {
            restartProxyMutation.mutate();
          },
        });
      }

      setIsEditModalOpen(false);
      editForm.resetFields();
      queryClient.invalidateQueries({ queryKey: ['endpoints'] });
    },
    onError: (error: any) => {
      const errorMsg = error?.response?.data?.detail || error.message || '更新失败';
      messageApi.error(errorMsg);
      console.error('更新 EndpointGroup 错误:', error);
    },
  });

  // 删除 EndpointGroup
  const deleteMutation = useMutation({
    mutationFn: (name: string) => api.endpoints.delete(name),
    onSuccess: (response: any) => {
      messageApi.success(response?.message || 'EndpointGroup 删除成功');
      queryClient.invalidateQueries({ queryKey: ['endpoints'] });
    },
    onError: (error: any) => {
      const errorMsg = error?.response?.data?.detail || error.message || '删除失败';
      messageApi.error(errorMsg);
      console.error('删除 EndpointGroup 错误:', error);
    },
  });

  // 添加主节点
  const addPrimaryMutation = useMutation({
    mutationFn: ({ name, config_name }: { name: string; config_name: string }) =>
      api.endpoints.addPrimary(name, config_name),
    onSuccess: () => {
      messageApi.success('主节点添加成功');
      queryClient.invalidateQueries({ queryKey: ['endpoints'] });
    },
    onError: (error: any) => {
      messageApi.error(error.message || '添加主节点失败');
    },
  });

  // 移除主节点
  const removePrimaryMutation = useMutation({
    mutationFn: ({ name, config_name }: { name: string; config_name: string }) =>
      api.endpoints.removePrimary(name, config_name),
    onSuccess: () => {
      messageApi.success('主节点移除成功');
      queryClient.invalidateQueries({ queryKey: ['endpoints'] });
    },
    onError: (error: any) => {
      messageApi.error(error.message || '移除主节点失败');
    },
  });

  // 添加副节点
  const addSecondaryMutation = useMutation({
    mutationFn: ({ name, config_name }: { name: string; config_name: string }) =>
      api.endpoints.addSecondary(name, config_name),
    onSuccess: () => {
      messageApi.success('副节点添加成功');
      queryClient.invalidateQueries({ queryKey: ['endpoints'] });
    },
    onError: (error: any) => {
      messageApi.error(error.message || '添加副节点失败');
    },
  });

  // 移除副节点
  const removeSecondaryMutation = useMutation({
    mutationFn: ({ name, config_name }: { name: string; config_name: string }) =>
      api.endpoints.removeSecondary(name, config_name),
    onSuccess: () => {
      messageApi.success('副节点移除成功');
      queryClient.invalidateQueries({ queryKey: ['endpoints'] });
    },
    onError: (error: any) => {
      messageApi.error(error.message || '移除副节点失败');
    },
  });

  // 打开创建对话框
  const handleCreate = () => {
    form.resetFields();
    setIsCreateModalOpen(true);
  };

  // 查看详情
  const handleViewDetail = (group: EndpointGroup) => {
    setSelectedGroup(group);
    setIsDetailModalOpen(true);
  };

  // 编辑
  const handleEdit = (group: EndpointGroup) => {
    setSelectedGroup(group);
    editForm.setFieldsValue({
      description: group.description,
      primary_configs: group.primary_configs || [],
      secondary_configs: group.secondary_configs || [],
      enabled: group.enabled,
    });
    setIsEditModalOpen(true);
  };

  // 提交创建
  const handleCreateSubmit = () => {
    form.validateFields().then((values) => {
      createMutation.mutate(values);
    });
  };

  // 提交编辑
  const handleEditSubmit = () => {
    if (!selectedGroup) return;
    editForm.validateFields().then((values) => {
      updateMutation.mutate({
        name: selectedGroup.name,
        data: values,
      });
    });
  };

  // 统计信息
  const stats = {
    total: groups.length,
    enabled: groups.filter((g: EndpointGroup) => g.enabled).length,
    disabled: groups.filter((g: EndpointGroup) => !g.enabled).length,
    totalPrimaryNodes: groups.reduce((sum: number, g: EndpointGroup) => sum + (g.primary_configs?.length || 0), 0),
    totalSecondaryNodes: groups.reduce((sum: number, g: EndpointGroup) => sum + (g.secondary_configs?.length || 0), 0),
  };

  // 表格列定义
  const columns = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      width: 150,
      render: (name: string) => <Text strong>{name}</Text>,
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      width: 250,
      ellipsis: true,
      render: (desc: string) => <Text type="secondary">{desc || '-'}</Text>,
    },
    {
      title: '主节点',
      key: 'primary',
      width: 120,
      render: (_: any, record: EndpointGroup) => (
        <Tag color="blue">{record.primary_configs?.length || 0} 个</Tag>
      ),
    },
    {
      title: '副节点',
      key: 'secondary',
      width: 120,
      render: (_: any, record: EndpointGroup) => (
        <Tag color="orange">{record.secondary_configs?.length || 0} 个</Tag>
      ),
    },
    {
      title: '状态',
      key: 'enabled',
      width: 100,
      render: (_: any, record: EndpointGroup) => (
        record.enabled ? (
          <Badge status="success" text="启用" />
        ) : (
          <Badge status="default" text="禁用" />
        )
      ),
    },
    {
      title: '创建时间',
      key: 'created_at',
      width: 180,
      render: (_: any, record: EndpointGroup) => (
        <Text type="secondary">
          {new Date(record.created_at).toLocaleString('zh-CN')}
        </Text>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 180,
      fixed: 'right' as const,
      render: (_: any, record: EndpointGroup) => (
        <Space size="small">
          <Tooltip title="查看详情">
            <Button
              size="small"
              icon={<EyeOutlined />}
              onClick={() => handleViewDetail(record)}
            />
          </Tooltip>
          <Tooltip title="编辑">
            <Button
              size="small"
              icon={<EditOutlined />}
              onClick={() => handleEdit(record)}
            />
          </Tooltip>
          <Popconfirm
            title="确定删除此 EndpointGroup 吗?"
            description="删除后无法恢复，请谨慎操作。"
            onConfirm={() => deleteMutation.mutate(record.name)}
            okText="删除"
            cancelText="取消"
            okButtonProps={{ danger: true }}
          >
            <Tooltip title="删除">
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
            <Title level={2} style={{ margin: 0 }}>
              <ApiOutlined /> EndpointGroup 管理
            </Title>
            <Text type="secondary">
              管理高可用代理组，支持主副节点自动故障切换
            </Text>
          </div>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={handleCreate}
          >
            创建 EndpointGroup
          </Button>
        </div>

        {/* 统计信息 */}
        <Row gutter={16} style={{ marginTop: 16 }}>
          <Col span={6}>
            <Statistic
              title="总代理组数"
              value={stats.total}
              prefix={<ThunderboltOutlined />}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="启用"
              value={stats.enabled}
              valueStyle={{ color: '#3f8600' }}
              prefix={<CheckCircleOutlined />}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="主节点总数"
              value={stats.totalPrimaryNodes}
              valueStyle={{ color: '#1890ff' }}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="副节点总数"
              value={stats.totalSecondaryNodes}
              valueStyle={{ color: '#fa8c16' }}
            />
          </Col>
        </Row>
      </Card>

      {/* EndpointGroup 列表表格 */}
      <Card>
        <Table
          columns={columns}
          dataSource={groups}
          loading={isLoading}
          rowKey="id"
          scroll={{ x: 1300 }}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 个 EndpointGroup`,
            pageSizeOptions: ['5', '10', '20', '50'],
          }}
        />
      </Card>

      {/* 创建 EndpointGroup 对话框 */}
      <Modal
        title="创建 EndpointGroup"
        open={isCreateModalOpen}
        onOk={handleCreateSubmit}
        onCancel={() => {
          setIsCreateModalOpen(false);
          form.resetFields();
        }}
        confirmLoading={createMutation.isPending}
        width={700}
      >
        <Form form={form} layout="vertical" style={{ marginTop: 24 }}>
          <Form.Item
            label="名称"
            name="name"
            rules={[{ required: true, message: '请输入名称' }]}
          >
            <Input placeholder="例如: production-cluster" />
          </Form.Item>

          <Form.Item
            label="描述"
            name="description"
          >
            <TextArea rows={2} placeholder="描述此 EndpointGroup 的用途" />
          </Form.Item>

          <Form.Item
            label="主节点配置"
            name="primary_configs"
            rules={[{ required: true, message: '请选择至少一个主节点' }]}
          >
            <Select
              mode="multiple"
              placeholder="选择主节点配置"
              options={configs.map((config: any) => ({
                label: `${config.name} - ${config.description}`,
                value: config.name,
              }))}
            />
          </Form.Item>

          <Form.Item
            label="副节点配置"
            name="secondary_configs"
          >
            <Select
              mode="multiple"
              placeholder="选择副节点配置（可选）"
              options={configs.map((config: any) => ({
                label: `${config.name} - ${config.description}`,
                value: config.name,
              }))}
            />
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

      {/* 编辑 EndpointGroup 对话框 */}
      <Modal
        title={`编辑 EndpointGroup: ${selectedGroup?.name}`}
        open={isEditModalOpen}
        onOk={handleEditSubmit}
        onCancel={() => {
          setIsEditModalOpen(false);
          setSelectedGroup(null);
          editForm.resetFields();
        }}
        confirmLoading={updateMutation.isPending}
        width={700}
      >
        <Form form={editForm} layout="vertical" style={{ marginTop: 24 }}>
          <Form.Item
            label="描述"
            name="description"
          >
            <TextArea rows={2} placeholder="描述此 EndpointGroup 的用途" />
          </Form.Item>

          <Form.Item
            label="主节点配置"
            name="primary_configs"
          >
            <Select
              mode="multiple"
              placeholder="选择主节点配置"
              options={configs.map((config: any) => ({
                label: `${config.name} - ${config.description}`,
                value: config.name,
              }))}
            />
          </Form.Item>

          <Form.Item
            label="副节点配置"
            name="secondary_configs"
          >
            <Select
              mode="multiple"
              placeholder="选择副节点配置"
              options={configs.map((config: any) => ({
                label: `${config.name} - ${config.description}`,
                value: config.name,
              }))}
            />
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

      {/* EndpointGroup 详情对话框 */}
      <Modal
        title={`EndpointGroup 详情: ${selectedGroup?.name}`}
        open={isDetailModalOpen}
        onCancel={() => {
          setIsDetailModalOpen(false);
          setSelectedGroup(null);
        }}
        footer={[
          <Button key="close" onClick={() => setIsDetailModalOpen(false)}>
            关闭
          </Button>,
        ]}
        width={900}
      >
        {selectedGroup && (
          <>
            <Descriptions bordered column={2} style={{ marginTop: 24 }}>
              <Descriptions.Item label="ID" span={2}>
                <Text code copyable={{ text: selectedGroup.id }}>
                  {selectedGroup.id}
                </Text>
              </Descriptions.Item>
              <Descriptions.Item label="名称">
                <Text strong>{selectedGroup.name}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="状态">
                {selectedGroup.enabled ? (
                  <Badge status="success" text="启用" />
                ) : (
                  <Badge status="default" text="禁用" />
                )}
              </Descriptions.Item>
              <Descriptions.Item label="描述" span={2}>
                {selectedGroup.description || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="主节点数量">
                <Tag color="blue">{selectedGroup.primary_configs?.length || 0} 个</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="副节点数量">
                <Tag color="orange">{selectedGroup.secondary_configs?.length || 0} 个</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="创建时间">
                {new Date(selectedGroup.created_at).toLocaleString('zh-CN')}
              </Descriptions.Item>
              <Descriptions.Item label="更新时间">
                {new Date(selectedGroup.updated_at).toLocaleString('zh-CN')}
              </Descriptions.Item>
            </Descriptions>

            <Divider />

            <Row gutter={16}>
              <Col span={12}>
                <Title level={5}>主节点配置 ({selectedGroup.primary_configs?.length || 0})</Title>
                <List
                  size="small"
                  bordered
                  dataSource={selectedGroup.primary_configs || []}
                  renderItem={item => (
                    <List.Item>
                      <Tag color="blue">{item}</Tag>
                    </List.Item>
                  )}
                  locale={{ emptyText: '暂无主节点配置' }}
                />
              </Col>
              <Col span={12}>
                <Title level={5}>副节点配置 ({selectedGroup.secondary_configs?.length || 0})</Title>
                <List
                  size="small"
                  bordered
                  dataSource={selectedGroup.secondary_configs || []}
                  renderItem={item => (
                    <List.Item>
                      <Tag color="orange">{item}</Tag>
                    </List.Item>
                  )}
                  locale={{ emptyText: '暂无副节点配置' }}
                />
              </Col>
            </Row>
          </>
        )}
      </Modal>
    </div>
  );
}
