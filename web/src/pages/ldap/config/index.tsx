import React, { useState, useEffect } from 'react';
import {
  Form,
  Input,
  InputNumber,
  Switch,
  Button,
  Card,
  Space,
  Divider,
  Row,
  Col,
  Spin,
  message,
  Tag,
  Descriptions,
  Modal,
  Typography
} from 'antd';
import { 
  SettingOutlined, 
  SyncOutlined, 
  TestOutlined,
  UserOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  CloseCircleOutlined
} from '@ant-design/icons';
import ldapService, { type LDAPConfig, type LDAPStatus } from '@/services/ldap-service';

const { Title, Paragraph } = Typography;

const LDAPConfigPage: React.FC = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [testing, setTesting] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [status, setStatus] = useState<LDAPStatus | null>(null);
  const [config, setConfig] = useState<LDAPConfig | null>(null);
  const [statusLoading, setStatusLoading] = useState(true);

  useEffect(() => {
    loadConfig();
    loadStatus();
  }, []);

  const loadConfig = async () => {
    try {
      const response = await ldapService.getConfig();
      if (response.code === 0 && response.data) {
        setConfig(response.data);
        form.setFieldsValue(response.data);
      }
    } catch (error) {
      console.error('Failed to load LDAP config:', error);
    }
  };

  const loadStatus = async () => {
    try {
      setStatusLoading(true);
      const response = await ldapService.getStatus();
      if (response.code === 0) {
        setStatus(response.data);
      }
    } catch (error) {
      console.error('Failed to load LDAP status:', error);
    } finally {
      setStatusLoading(false);
    }
  };

  const handleSave = async (values: any) => {
    try {
      setLoading(true);
      const response = await ldapService.saveConfig(values);
      if (response.code === 0) {
        message.success('LDAP配置保存成功');
        loadConfig();
        loadStatus();
      } else {
        message.error(response.message || '保存失败');
      }
    } catch (error) {
      message.error('保存配置时发生错误');
    } finally {
      setLoading(false);
    }
  };

  const handleTest = async () => {
    try {
      setTesting(true);
      const response = await ldapService.testConnection();
      if (response.code === 0 && response.data) {
        message.success('LDAP连接测试成功');
      } else {
        message.error(response.message || 'LDAP连接测试失败');
      }
    } catch (error) {
      message.error('连接测试时发生错误');
    } finally {
      setTesting(false);
    }
  };

  const handleSync = async () => {
    Modal.confirm({
      title: '确认同步',
      content: '确定要立即同步LDAP用户吗？这可能需要一些时间。',
      onOk: async () => {
        try {
          setSyncing(true);
          const response = await ldapService.forceSync();
          if (response.code === 0 && response.data) {
            message.success('LDAP用户同步已开始');
            // 延迟刷新状态
            setTimeout(() => {
              loadStatus();
            }, 2000);
          } else {
            message.error(response.message || '同步失败');
          }
        } catch (error) {
          message.error('同步时发生错误');
        } finally {
          setSyncing(false);
        }
      }
    });
  };

  const getStatusIcon = (status?: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
      case 'running':
        return <SyncOutlined spin style={{ color: '#1890ff' }} />;
      case 'error':
        return <ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />;
      default:
        return <CloseCircleOutlined style={{ color: '#d9d9d9' }} />;
    }
  };

  const getStatusColor = (status?: string) => {
    switch (status) {
      case 'completed': return 'success';
      case 'running': return 'processing';
      case 'error': return 'error';
      default: return 'default';
    }
  };

  return (
    <div style={{ padding: 24 }}>
      <Title level={2}>
        <SettingOutlined /> LDAP 配置管理
      </Title>
      
      <Row gutter={[24, 24]}>
        {/* 状态卡片 */}
        <Col span={24}>
          <Card 
            title={<><SyncOutlined /> LDAP 服务状态</>}
            extra={
              <Button 
                icon={<SyncOutlined />} 
                onClick={loadStatus} 
                loading={statusLoading}
              >
                刷新状态
              </Button>
            }
          >
            <Spin spinning={statusLoading}>
              {status && (
                <>
                  <Descriptions column={2} size=\"small\">
                    <Descriptions.Item label=\"配置状态\">
                      <Tag color={status.configured ? 'success' : 'error'}>
                        {status.configured ? '已配置' : '未配置'}
                      </Tag>
                    </Descriptions.Item>
                    <Descriptions.Item label=\"认证服务\">
                      <Tag color={status.enabled ? 'success' : 'default'}>
                        {status.enabled ? '已启用' : '已禁用'}
                      </Tag>
                    </Descriptions.Item>
                    <Descriptions.Item label=\"用户同步\">
                      <Tag color={status.sync_enabled ? 'success' : 'default'}>
                        {status.sync_enabled ? '已启用' : '已禁用'}
                      </Tag>
                    </Descriptions.Item>
                    <Descriptions.Item label=\"同步间隔\">
                      {status.sync_interval} 秒
                    </Descriptions.Item>
                    <Descriptions.Item label=\"同步状态\">
                      {getStatusIcon(status.sync_status)}
                      <Tag color={getStatusColor(status.sync_status)} style={{ marginLeft: 8 }}>
                        {status.sync_status}
                      </Tag>
                    </Descriptions.Item>
                    <Descriptions.Item label=\"最后同步\">
                      {status.last_sync_time 
                        ? new Date(status.last_sync_time).toLocaleString()
                        : '从未同步'
                      }
                    </Descriptions.Item>
                    <Descriptions.Item label=\"LDAP3库\">
                      <Tag color={status.ldap3_available ? 'success' : 'error'}>
                        {status.ldap3_available ? '可用' : '不可用'}
                      </Tag>
                    </Descriptions.Item>
                  </Descriptions>
                  
                  {status.user_stats && (
                    <>
                      <Divider orientation=\"left\">用户统计</Divider>
                      <Row gutter={16}>
                        <Col span={8}>
                          <Card size=\"small\" className=\"text-center\">
                            <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#1890ff' }}>
                              {status.user_stats.total_users}
                            </div>
                            <div>总用户数</div>
                          </Card>
                        </Col>
                        <Col span={8}>
                          <Card size=\"small\" className=\"text-center\">
                            <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#52c41a' }}>
                              {status.user_stats.active_users}
                            </div>
                            <div>活跃用户</div>
                          </Card>
                        </Col>
                        <Col span={8}>
                          <Card size=\"small\" className=\"text-center\">
                            <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#faad14' }}>
                              {status.user_stats.inactive_users}
                            </div>
                            <div>非活跃用户</div>
                          </Card>
                        </Col>
                      </Row>
                    </>
                  )}
                </>
              )}
            </Spin>
          </Card>
        </Col>
        
        {/* 配置表单 */}
        <Col span={24}>
          <Card 
            title=\"LDAP 服务器配置\"
            extra={
              <Space>
                <Button 
                  icon={<TestOutlined />} 
                  onClick={handleTest}
                  loading={testing}
                  disabled={!config?.server_host}
                >
                  测试连接
                </Button>
                <Button 
                  icon={<SyncOutlined />} 
                  onClick={handleSync}
                  loading={syncing}
                  disabled={!status?.configured || !status?.sync_enabled}
                >
                  立即同步
                </Button>
              </Space>
            }
          >
            <Form
              form={form}
              layout=\"vertical\"
              onFinish={handleSave}
              initialValues={{
                server_port: 389,
                use_ssl: false,
                search_filter: '(objectClass=person)',
                attr_mapping: {
                  username: 'uid',
                  email: 'mail',
                  nickname: 'displayName',
                  first_name: 'givenName',
                  last_name: 'sn'
                },
                enabled: true,
                auto_create_user: true,
                sync_enabled: true,
                sync_interval: 30
              }}
            >
              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item
                    name=\"name\"
                    label=\"配置名称\"
                    rules={[{ required: true, message: '请输入配置名称' }]}
                  >
                    <Input placeholder=\"LDAP配置名称\" />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item
                    name=\"enabled\"
                    label=\"启用LDAP认证\"
                    valuePropName=\"checked\"
                  >
                    <Switch />
                  </Form.Item>
                </Col>
              </Row>
              
              <Divider orientation=\"left\">服务器设置</Divider>
              
              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item
                    name=\"server_host\"
                    label=\"LDAP服务器地址\"
                    rules={[{ required: true, message: '请输入LDAP服务器地址' }]}
                  >
                    <Input placeholder=\"ldap.example.com\" />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    name=\"server_port\"
                    label=\"端口\"
                    rules={[{ required: true, message: '请输入端口' }]}
                  >
                    <InputNumber min={1} max={65535} style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
                <Col span={4}>
                  <Form.Item
                    name=\"use_ssl\"
                    label=\"使用SSL\"
                    valuePropName=\"checked\"
                  >
                    <Switch />
                  </Form.Item>
                </Col>
              </Row>
              
              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item
                    name=\"bind_dn\"
                    label=\"绑定DN（可选）\"
                  >
                    <Input placeholder=\"cn=admin,dc=example,dc=com\" />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item
                    name=\"bind_password\"
                    label=\"绑定密码（可选）\"
                  >
                    <Input.Password placeholder=\"管理员密码\" />
                  </Form.Item>
                </Col>
              </Row>
              
              <Divider orientation=\"left\">用户搜索设置</Divider>
              
              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item
                    name=\"search_base\"
                    label=\"搜索基础DN\"
                    rules={[{ required: true, message: '请输入搜索基础DN' }]}
                  >
                    <Input placeholder=\"ou=users,dc=example,dc=com\" />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item
                    name=\"search_filter\"
                    label=\"搜索过滤器\"
                  >
                    <Input placeholder=\"(objectClass=person)\" />
                  </Form.Item>
                </Col>
              </Row>
              
              <Form.Item
                name=\"user_dn_template\"
                label=\"用户DN模板（可选）\"
                extra=\"用于直接认证，格式如：uid={username},ou=users,dc=example,dc=com\"
              >
                <Input placeholder=\"uid={username},ou=users,dc=example,dc=com\" />
              </Form.Item>
              
              <Divider orientation=\"left\">属性映射</Divider>
              
              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item name={['attr_mapping', 'username']} label=\"用户名属性\">
                    <Input placeholder=\"uid\" />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item name={['attr_mapping', 'email']} label=\"邮箱属性\">
                    <Input placeholder=\"mail\" />
                  </Form.Item>
                </Col>
              </Row>
              
              <Row gutter={16}>
                <Col span={8}>
                  <Form.Item name={['attr_mapping', 'nickname']} label=\"显示名属性\">
                    <Input placeholder=\"displayName\" />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item name={['attr_mapping', 'first_name']} label=\"名字属性\">
                    <Input placeholder=\"givenName\" />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item name={['attr_mapping', 'last_name']} label=\"姓氏属性\">
                    <Input placeholder=\"sn\" />
                  </Form.Item>
                </Col>
              </Row>
              
              <Divider orientation=\"left\">同步设置</Divider>
              
              <Row gutter={16}>
                <Col span={8}>
                  <Form.Item
                    name=\"auto_create_user\"
                    label=\"自动创建用户\"
                    valuePropName=\"checked\"
                  >
                    <Switch />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    name=\"sync_enabled\"
                    label=\"启用用户同步\"
                    valuePropName=\"checked\"
                  >
                    <Switch />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    name=\"sync_interval\"
                    label=\"同步间隔（秒）\"
                    rules={[{ 
                      type: 'number', 
                      min: 30, 
                      message: '同步间隔不能少于30秒' 
                    }]}
                  >
                    <InputNumber min={30} style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
              </Row>
              
              <Form.Item>
                <Button type=\"primary\" htmlType=\"submit\" loading={loading} size=\"large\">
                  保存配置
                </Button>
              </Form.Item>
            </Form>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default LDAPConfigPage;