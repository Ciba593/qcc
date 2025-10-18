import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, Button, Tag, message, Descriptions, Space, Select, Form, Modal, Alert, Input, Spin, Typography, Divider } from 'antd';
import { PlayCircleOutlined, StopOutlined, SettingOutlined, ThunderboltOutlined, RollbackOutlined, FileTextOutlined, ReloadOutlined, SearchOutlined } from '@ant-design/icons';
import { api } from '../api/client';

const { TextArea } = Input;
const { Text } = Typography;

export default function Proxy() {
  const queryClient = useQueryClient();
  const [isStartModalOpen, setIsStartModalOpen] = useState(false);
  const [isLogsModalOpen, setIsLogsModalOpen] = useState(false);
  const [logLines, setLogLines] = useState(100);
  const [logLevel, setLogLevel] = useState('ALL');
  const [logGrep, setLogGrep] = useState('');
  const [form] = Form.useForm();

  const { data: status } = useQuery({
    queryKey: ['proxy-status'],
    queryFn: api.proxy.status,
    refetchInterval: 3000,
  });

  // 查询所有 EndpointGroup
  const { data: groupsResponse } = useQuery({
    queryKey: ['endpoints'],
    queryFn: api.endpoints.list,
  });

  // 查询 Claude Code 配置状态
  const { data: claudeConfigStatus, refetch: refetchClaudeConfig } = useQuery({
    queryKey: ['claude-config-status'],
    queryFn: api.claudeConfig.status,
    refetchInterval: 3000,
  });

  // 查询日志
  const { data: logsData, isLoading: logsLoading, refetch: refetchLogs } = useQuery({
    queryKey: ['proxy-logs', logLines, logLevel, logGrep],
    queryFn: () => api.proxy.logs({ lines: logLines, level: logLevel, grep: logGrep }),
    enabled: isLogsModalOpen, // 只在弹窗打开时查询
    refetchInterval: isLogsModalOpen ? 3000 : false, // 弹窗打开时每3秒刷新
  });

  const groups = (groupsResponse as any)?.data || [];
  const enabledGroups = groups.filter((g: any) => g.enabled);
  const claudeStatus: any = claudeConfigStatus?.data || {};
  const logsInfo: any = logsData?.data || { logs: [], total_lines: 0, displayed_lines: 0 };

  const startMutation = useMutation({
    mutationFn: (params: { host: string; port: number; cluster?: string }) =>
      api.proxy.start(params),
    onSuccess: () => {
      message.success('代理服务已启动');
      queryClient.invalidateQueries({ queryKey: ['proxy-status'] });
      setIsStartModalOpen(false);
      form.resetFields();
    },
    onError: (error: Error) => {
      message.error(`启动失败: ${error.message}`);
    },
  });

  const stopMutation = useMutation({
    mutationFn: api.proxy.stop,
    onSuccess: () => {
      message.success('代理服务已停止');
      queryClient.invalidateQueries({ queryKey: ['proxy-status'] });
      queryClient.invalidateQueries({ queryKey: ['claude-config-status'] });
    },
    onError: (error: Error) => {
      message.error(`停止失败: ${error.message}`);
    },
  });

  // 应用代理到 Claude Code
  const applyClaudeMutation = useMutation({
    mutationFn: api.claudeConfig.apply,
    onSuccess: (response: any) => {
      message.success(response?.message || '成功应用代理到 Claude Code');
      refetchClaudeConfig();
    },
    onError: (error: any) => {
      message.error(`应用失败: ${error.message}`);
    },
  });

  // 还原 Claude Code 配置
  const restoreClaudeMutation = useMutation({
    mutationFn: api.claudeConfig.restore,
    onSuccess: (response: any) => {
      message.success(response?.message || '成功还原 Claude Code 配置');
      refetchClaudeConfig();
    },
    onError: (error: any) => {
      message.error(`还原失败: ${error.message}`);
    },
  });

  const proxyData: any = status?.data || {};
  const isRunning = proxyData.running || false;
  const uptime = proxyData.uptime ? (proxyData.uptime / 60).toFixed(0) : '-';

  // 处理启动按钮点击
  const handleStartClick = () => {
    if (enabledGroups.length === 0) {
      message.warning('暂无可用的 EndpointGroup，请先创建');
      return;
    }
    setIsStartModalOpen(true);
  };

  // 提交启动表单
  const handleStartSubmit = () => {
    form.validateFields().then((values) => {
      startMutation.mutate({
        host: values.host || '127.0.0.1',
        port: values.port || 7860,
        cluster: values.cluster,
      });
    });
  };

  return (
    <div>
      <h1>代理服务</h1>

      <Card title="代理服务状态" style={{ marginTop: 16 }}>
        <Descriptions bordered column={2}>
          <Descriptions.Item label="状态">
            {isRunning ? (
              <Tag color="success">运行中</Tag>
            ) : (
              <Tag>未运行</Tag>
            )}
          </Descriptions.Item>
          <Descriptions.Item label="PID">
            {proxyData.pid || '-'}
          </Descriptions.Item>
          <Descriptions.Item label="监听地址">
            {proxyData.host || '-'}
          </Descriptions.Item>
          <Descriptions.Item label="监听端口">
            {proxyData.port || '-'}
          </Descriptions.Item>
          <Descriptions.Item label="运行时长">
            {uptime !== '-' ? uptime + ' 分钟' : '-'}
          </Descriptions.Item>
          <Descriptions.Item label="集群配置">
            {proxyData.config || '-'}
          </Descriptions.Item>
        </Descriptions>

        <Space style={{ marginTop: 16 }}>
          {isRunning ? (
            <>
              <Button
                danger
                icon={<StopOutlined />}
                onClick={() => stopMutation.mutate()}
                loading={stopMutation.isPending}
              >
                停止服务
              </Button>
              <Button
                icon={<FileTextOutlined />}
                onClick={() => setIsLogsModalOpen(true)}
              >
                查看日志
              </Button>
            </>
          ) : (
            <Button
              type="primary"
              icon={<PlayCircleOutlined />}
              onClick={handleStartClick}
              loading={startMutation.isPending}
            >
              启动服务
            </Button>
          )}
        </Space>
      </Card>

      {/* Claude Code 配置管理 */}
      <Card title="Claude Code 配置管理" style={{ marginTop: 16 }}>
        <Alert
          message="一键应用代理到 Claude Code"
          description="点击「应用代理」按钮后，QCC 会自动备份当前 Claude Code 配置并应用代理地址。停止代理服务时会自动还原配置。"
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />

        <Descriptions bordered column={2}>
          <Descriptions.Item label="配置状态">
            {claudeStatus.is_proxy_applied ? (
              <Tag color="success">已应用代理</Tag>
            ) : (
              <Tag>未应用</Tag>
            )}
          </Descriptions.Item>
          <Descriptions.Item label="当前地址">
            {claudeStatus.current_base_url || '-'}
          </Descriptions.Item>
          <Descriptions.Item label="配置文件" span={2}>
            <code style={{ fontSize: '12px' }}>{claudeStatus.config_file || '-'}</code>
          </Descriptions.Item>
        </Descriptions>

        <Space style={{ marginTop: 16 }}>
          {!claudeStatus.is_proxy_applied ? (
            <Button
              type="primary"
              icon={<ThunderboltOutlined />}
              onClick={() => applyClaudeMutation.mutate(undefined)}
              loading={applyClaudeMutation.isPending}
              disabled={!isRunning}
            >
              应用代理到 Claude Code
            </Button>
          ) : (
            <Button
              icon={<RollbackOutlined />}
              onClick={() => restoreClaudeMutation.mutate(undefined)}
              loading={restoreClaudeMutation.isPending}
            >
              还原 Claude Code 配置
            </Button>
          )}
          {!isRunning && (
            <span style={{ marginLeft: 8, color: '#999', fontSize: '12px' }}>
              请先启动代理服务
            </span>
          )}
        </Space>
      </Card>

      {/* 启动配置弹窗 */}
      <Modal
        title="启动代理服务"
        open={isStartModalOpen}
        onOk={handleStartSubmit}
        onCancel={() => {
          setIsStartModalOpen(false);
          form.resetFields();
        }}
        confirmLoading={startMutation.isPending}
        okText="启动"
        cancelText="取消"
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={{
            host: '127.0.0.1',
            port: 7860,
          }}
        >
          <Form.Item
            label="选择 EndpointGroup"
            name="cluster"
            rules={[{ required: true, message: '请选择 EndpointGroup' }]}
          >
            <Select
              placeholder="选择要使用的 EndpointGroup"
              options={enabledGroups.map((group: any) => ({
                label: `${group.name}${group.description ? ` - ${group.description}` : ''}`,
                value: group.name,
              }))}
            />
          </Form.Item>

          <Form.Item
            label="监听地址"
            name="host"
            rules={[{ required: true, message: '请输入监听地址' }]}
          >
            <Select
              options={[
                { label: '127.0.0.1 (仅本机)', value: '127.0.0.1' },
                { label: '0.0.0.0 (允许外部访问)', value: '0.0.0.0' },
              ]}
            />
          </Form.Item>

          <Form.Item
            label="监听端口"
            name="port"
            rules={[
              { required: true, message: '请输入监听端口' },
              { type: 'number', min: 1024, max: 65535, message: '端口范围: 1024-65535' },
            ]}
          >
            <Select
              options={[
                { label: '7860 (推荐)', value: 7860 },
                { label: '8080', value: 8080 },
                { label: '9000', value: 9000 },
              ]}
              showSearch
            />
          </Form.Item>
        </Form>
      </Modal>

      {/* 日志查看弹窗 */}
      <Modal
        title="代理服务日志"
        open={isLogsModalOpen}
        onCancel={() => setIsLogsModalOpen(false)}
        width={1000}
        footer={[
          <Button key="close" onClick={() => setIsLogsModalOpen(false)}>
            关闭
          </Button>,
          <Button
            key="refresh"
            type="primary"
            icon={<ReloadOutlined />}
            onClick={() => refetchLogs()}
            loading={logsLoading}
          >
            刷新
          </Button>,
        ]}
      >
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          {/* 日志过滤器 */}
          <Card size="small">
            <Space wrap>
              <Space>
                <Text>显示行数:</Text>
                <Select
                  style={{ width: 120 }}
                  value={logLines}
                  onChange={setLogLines}
                  options={[
                    { label: '50 行', value: 50 },
                    { label: '100 行', value: 100 },
                    { label: '200 行', value: 200 },
                    { label: '500 行', value: 500 },
                  ]}
                />
              </Space>
              <Space>
                <Text>日志级别:</Text>
                <Select
                  style={{ width: 120 }}
                  value={logLevel}
                  onChange={setLogLevel}
                  options={[
                    { label: '全部', value: 'ALL' },
                    { label: 'DEBUG', value: 'DEBUG' },
                    { label: 'INFO', value: 'INFO' },
                    { label: 'WARNING', value: 'WARNING' },
                    { label: 'ERROR', value: 'ERROR' },
                  ]}
                />
              </Space>
              <Space>
                <Text>搜索:</Text>
                <Input
                  style={{ width: 200 }}
                  placeholder="输入关键词过滤"
                  value={logGrep}
                  onChange={(e) => setLogGrep(e.target.value)}
                  prefix={<SearchOutlined />}
                  allowClear
                />
              </Space>
            </Space>
          </Card>

          {/* 日志信息 */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Space>
              <Text type="secondary">
                显示 {logsInfo.displayed_lines} / {logsInfo.total_lines} 行
              </Text>
              {logsInfo.log_file && (
                <Text type="secondary" style={{ fontSize: '12px' }}>
                  ({logsInfo.log_file})
                </Text>
              )}
            </Space>
            <Tag color="processing">自动刷新（3秒）</Tag>
          </div>

          {/* 日志内容 */}
          {logsLoading && !logsInfo.logs?.length ? (
            <div style={{ textAlign: 'center', padding: '40px' }}>
              <Spin tip="加载日志..." />
            </div>
          ) : logsInfo.logs?.length > 0 ? (
            <TextArea
              value={logsInfo.logs.join('\n')}
              readOnly
              style={{
                fontFamily: 'Monaco, Consolas, "Courier New", monospace',
                fontSize: '12px',
                lineHeight: '1.5',
                backgroundColor: '#1e1e1e',
                color: '#d4d4d4',
                padding: '12px',
              }}
              rows={20}
            />
          ) : (
            <Alert
              message={logsInfo.message || '暂无日志'}
              type="info"
              showIcon
            />
          )}
        </Space>
      </Modal>
    </div>
  );
}
