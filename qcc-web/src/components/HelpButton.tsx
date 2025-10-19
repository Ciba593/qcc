import { useState } from 'react';
import { QuestionCircleOutlined, QqOutlined, MailOutlined, TeamOutlined } from '@ant-design/icons';
import { FloatButton, Modal, Space, Typography, Divider } from 'antd';

const { Title, Text, Link } = Typography;

export default function HelpButton() {
  const [open, setOpen] = useState(false);

  const handleClick = () => {
    setOpen(true);
  };

  const handleClose = () => {
    setOpen(false);
  };

  return (
    <>
      <FloatButton
        icon={<QuestionCircleOutlined />}
        type="primary"
        style={{ right: 24, bottom: 24 }}
        onClick={handleClick}
        tooltip="帮助与反馈"
      />

      <Modal
        title={
          <Space>
            <QuestionCircleOutlined />
            <span>帮助与反馈</span>
          </Space>
        }
        open={open}
        onCancel={handleClose}
        footer={null}
        width={480}
      >
        <div style={{ padding: '16px 0' }}>
          <Title level={5}>联系方式</Title>

          <Space direction="vertical" size="middle" style={{ width: '100%' }}>
            <div>
              <Space>
                <QqOutlined style={{ fontSize: 18, color: '#1890ff' }} />
                <Text strong>QQ：</Text>
                <Text copyable>1764807112</Text>
              </Space>
            </div>

            <div>
              <Space>
                <MailOutlined style={{ fontSize: 18, color: '#1890ff' }} />
                <Text strong>邮箱：</Text>
                <Text copyable>1764807112@qq.com</Text>
              </Space>
            </div>

            <Divider style={{ margin: '12px 0' }} />

            <div>
              <Space direction="vertical" size="small" style={{ width: '100%' }}>
                <Space>
                  <TeamOutlined style={{ fontSize: 18, color: '#52c41a' }} />
                  <Text strong>交流群：ChatGPT4</Text>
                </Space>
                <Link
                  href="https://qm.qq.com/q/NWhX5PTPS8"
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{ paddingLeft: 26 }}
                >
                  点击加入群聊
                </Link>
              </Space>
            </div>
          </Space>

          <Divider style={{ margin: '16px 0' }} />

          <div style={{ textAlign: 'center' }}>
            <Text type="secondary" style={{ fontSize: 12 }}>
              欢迎交流与反馈，我们将持续改进 QCC
            </Text>
          </div>
        </div>
      </Modal>
    </>
  );
}
