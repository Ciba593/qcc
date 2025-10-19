import { useState, useEffect } from 'react';
import {
  Card,
  Form,
  Select,
  Radio,
  Button,
  Space,
  Divider,
  Alert,
  Spin,
  Tag,
  Typography,
  message,
  Row,
  Col,
  Descriptions,
} from 'antd';
import {
  SettingOutlined,
  SaveOutlined,
  ReloadOutlined,
  ThunderboltOutlined,
  DollarOutlined,
  RocketOutlined,
} from '@ant-design/icons';
import { apiClient } from '../api/client';

const { Title, Text, Paragraph } = Typography;
const { Option } = Select;

interface ModelInfo {
  id: string;
  name: string;
  description: string;
  context_window: number;
  max_output: number;
  supports_vision: boolean;
  price_input: number;
  price_output: number;
  recommended_for: string;
}

interface ModelConfig {
  test_model: string;
  proxy_model_mode: string;
  proxy_model_override: string;
}

const Settings = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [config, setConfig] = useState<ModelConfig | null>(null);
  const [selectedTestModel, setSelectedTestModel] = useState<ModelInfo | null>(null);
  const [selectedProxyModel, setSelectedProxyModel] = useState<ModelInfo | null>(null);

  // 加载模型列表
  const loadModels = async () => {
    try {
      const response: any = await apiClient.get('/api/system/models');
      if (response.success) {
        setModels(response.data.models);
      }
    } catch (error) {
      message.error('加载模型列表失败');
    }
  };

  // 加载当前配置
  const loadConfig = async () => {
    setLoading(true);
    try {
      const response: any = await apiClient.get('/api/system/model-config');
      if (response.success) {
        const cfg = response.data;
        setConfig(cfg);
        form.setFieldsValue(cfg);

        // 设置选中的模型信息
        const testModel = models.find(m => m.id === cfg.test_model);
        const proxyModel = models.find(m => m.id === cfg.proxy_model_override);
        setSelectedTestModel(testModel || null);
        setSelectedProxyModel(proxyModel || null);
      }
    } catch (error) {
      message.error('加载配置失败');
    } finally {
      setLoading(false);
    }
  };

  // 保存配置
  const handleSave = async (values: ModelConfig) => {
    setSaving(true);
    try {
      const response: any = await apiClient.post('/api/system/model-config', values);
      if (response.success) {
        message.success('配置已保存并立即生效！');
        setConfig(values);
      } else {
        message.error(response.message || '保存失败');
      }
    } catch (error) {
      message.error('保存配置失败');
    } finally {
      setSaving(false);
    }
  };

  // 初始化
  useEffect(() => {
    loadModels();
  }, []);

  useEffect(() => {
    if (models.length > 0) {
      loadConfig();
    }
  }, [models]);

  // 监听表单变化，更新选中的模型信息
  const handleTestModelChange = (value: string) => {
    const model = models.find(m => m.id === value);
    setSelectedTestModel(model || null);
  };

  const handleProxyModelChange = (value: string) => {
    const model = models.find(m => m.id === value);
    setSelectedProxyModel(model || null);
  };

  // 渲染模型选项
  const renderModelOption = (model: ModelInfo) => (
    <Option key={model.id} value={model.id}>
      <Space direction="vertical" size={0} style={{ width: '100%' }}>
        <Space>
          <Text strong>{model.name}</Text>
          <Tag color="blue">${model.price_input}/${model.price_output}</Tag>
        </Space>
        <Text type="secondary" style={{ fontSize: '12px' }}>
          {model.description}
        </Text>
      </Space>
    </Option>
  );

  // 渲染模型详情卡片
  const renderModelCard = (model: ModelInfo | null, title: string) => {
    if (!model) return null;

    return (
      <Card size="small" style={{ marginTop: 8 }}>
        <Descriptions column={2} size="small">
          <Descriptions.Item label="模型名称" span={2}>
            <Text strong>{model.name}</Text>
          </Descriptions.Item>
          <Descriptions.Item label="上下文窗口">
            {(model.context_window / 1000).toFixed(0)}K tokens
          </Descriptions.Item>
          <Descriptions.Item label="最大输出">
            {(model.max_output / 1000).toFixed(0)}K tokens
          </Descriptions.Item>
          <Descriptions.Item label="输入价格">
            ${model.price_input}/MTok
          </Descriptions.Item>
          <Descriptions.Item label="输出价格">
            ${model.price_output}/MTok
          </Descriptions.Item>
          <Descriptions.Item label="推荐用途" span={2}>
            {model.recommended_for}
          </Descriptions.Item>
        </Descriptions>
      </Card>
    );
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '100px 0' }}>
        <Spin size="large" tip="加载配置中..." />
      </div>
    );
  }

  return (
    <div style={{ padding: '24px' }}>
      <Title level={2}>
        <SettingOutlined /> 系统配置
      </Title>
      <Paragraph type="secondary">
        配置测试模型和代理模型，修改后立即生效，无需重启服务
      </Paragraph>

      <Alert
        message="配置说明"
        description={
          <div>
            <p><strong>测试模型</strong>: 用于健康检查和 endpoint 验证，推荐使用 Haiku 3.5（最快最便宜）</p>
            <p><strong>代理模型模式</strong>:</p>
            <ul>
              <li><strong>按实际请求</strong>: 使用客户端指定的模型（透明代理）</li>
              <li><strong>强制替换</strong>: 将所有请求统一替换为指定模型（成本控制）</li>
            </ul>
          </div>
        }
        type="info"
        showIcon
        style={{ marginBottom: 24 }}
      />

      <Form
        form={form}
        layout="vertical"
        onFinish={handleSave}
        initialValues={config || undefined}
      >
        <Row gutter={24}>
          {/* 左侧：测试模型配置 */}
          <Col xs={24} lg={12}>
            <Card
              title={
                <Space>
                  <ThunderboltOutlined />
                  测试模型配置
                </Space>
              }
              bordered={false}
            >
              <Form.Item
                label="健康检查使用的模型"
                name="test_model"
                rules={[{ required: true, message: '请选择测试模型' }]}
              >
                <Select
                  placeholder="选择模型"
                  onChange={handleTestModelChange}
                  showSearch
                  optionFilterProp="children"
                  size="large"
                >
                  {models.map(renderModelOption)}
                </Select>
              </Form.Item>

              {renderModelCard(selectedTestModel, '测试模型详情')}

              <Alert
                message="推荐使用 Haiku 3.5"
                description="健康检查每 60 秒执行一次，使用 Haiku 可显著降低成本"
                type="success"
                showIcon
                style={{ marginTop: 16 }}
              />
            </Card>
          </Col>

          {/* 右侧：代理模型配置 */}
          <Col xs={24} lg={12}>
            <Card
              title={
                <Space>
                  <RocketOutlined />
                  代理模型配置
                </Space>
              }
              bordered={false}
            >
              <Form.Item
                label="代理模型模式"
                name="proxy_model_mode"
                rules={[{ required: true, message: '请选择代理模式' }]}
              >
                <Radio.Group size="large">
                  <Space direction="vertical">
                    <Radio value="passthrough">
                      <Space>
                        <Text strong>按实际请求</Text>
                        <Tag color="default">透明代理</Tag>
                      </Space>
                      <br />
                      <Text type="secondary" style={{ fontSize: '12px' }}>
                        使用客户端指定的模型，不做任何修改
                      </Text>
                    </Radio>
                    <Radio value="override">
                      <Space>
                        <Text strong>强制替换</Text>
                        <Tag color="orange">成本控制</Tag>
                      </Space>
                      <br />
                      <Text type="secondary" style={{ fontSize: '12px' }}>
                        将所有请求统一替换为指定模型
                      </Text>
                    </Radio>
                  </Space>
                </Radio.Group>
              </Form.Item>

              <Form.Item
                noStyle
                shouldUpdate={(prevValues, currentValues) =>
                  prevValues.proxy_model_mode !== currentValues.proxy_model_mode
                }
              >
                {({ getFieldValue }) =>
                  getFieldValue('proxy_model_mode') === 'override' ? (
                    <>
                      <Form.Item
                        label="强制使用的模型"
                        name="proxy_model_override"
                        rules={[{ required: true, message: '请选择强制替换的模型' }]}
                      >
                        <Select
                          placeholder="选择模型"
                          onChange={handleProxyModelChange}
                          showSearch
                          optionFilterProp="children"
                          size="large"
                        >
                          {models.map(renderModelOption)}
                        </Select>
                      </Form.Item>

                      {renderModelCard(selectedProxyModel, '代理模型详情')}

                      <Alert
                        message={
                          <Space>
                            <DollarOutlined />
                            成本优化提示
                          </Space>
                        }
                        description="使用 Haiku 系列可节省高达 93% 的成本（相比 Opus）"
                        type="warning"
                        showIcon
                        style={{ marginTop: 16 }}
                      />
                    </>
                  ) : (
                    <Alert
                      message="透明代理模式"
                      description="代理服务器将保持请求原样，不修改模型字段"
                      type="info"
                      showIcon
                    />
                  )
                }
              </Form.Item>
            </Card>
          </Col>
        </Row>

        <Divider />

        {/* 操作按钮 */}
        <Space size="large">
          <Button
            type="primary"
            size="large"
            icon={<SaveOutlined />}
            htmlType="submit"
            loading={saving}
          >
            保存配置
          </Button>
          <Button
            size="large"
            icon={<ReloadOutlined />}
            onClick={loadConfig}
            disabled={loading || saving}
          >
            重新加载
          </Button>
        </Space>
      </Form>

      <Divider />

      {/* 当前配置总结 */}
      {config && (
        <Card title="当前配置" size="small">
          <Descriptions column={1} bordered size="small">
            <Descriptions.Item label="测试模型">
              <Tag color="blue">{config.test_model}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="代理模式">
              {config.proxy_model_mode === 'passthrough' ? (
                <Tag color="default">按实际请求（透明代理）</Tag>
              ) : (
                <Tag color="orange">强制替换</Tag>
              )}
            </Descriptions.Item>
            {config.proxy_model_mode === 'override' && (
              <Descriptions.Item label="强制使用模型">
                <Tag color="green">{config.proxy_model_override}</Tag>
              </Descriptions.Item>
            )}
          </Descriptions>
        </Card>
      )}
    </div>
  );
};

export default Settings;
