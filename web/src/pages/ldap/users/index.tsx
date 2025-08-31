import React, { useState, useEffect } from 'react';
import {
  Table,
  Card,
  Tag,
  Button,
  Space,
  Switch,
  Modal,
  Tooltip,
  message,
  Input,
  Row,
  Col,
  Descriptions,
  Typography
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
  UserOutlined,
  SyncOutlined,
  SearchOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  InfoCircleOutlined
} from '@ant-design/icons';
import ldapService, { type LDAPUser } from '@/services/ldap-service';

const { Title } = Typography;
const { Search } = Input;

const LDAPUsersPage: React.FC = () => {
  const [users, setUsers] = useState<LDAPUser[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [showInactive, setShowInactive] = useState(false);
  const [selectedUser, setSelectedUser] = useState<LDAPUser | null>(null);
  const [detailVisible, setDetailVisible] = useState(false);

  useEffect(() => {
    loadUsers();
  }, [showInactive]);

  const loadUsers = async () => {
    try {
      setLoading(true);
      const response = await ldapService.getUsers(!showInactive);
      if (response.code === 0) {
        setUsers(response.data || []);
      } else {
        message.error(response.message || '获取用户列表失败');
      }
    } catch (error) {
      message.error('加载用户列表时发生错误');
    } finally {
      setLoading(false);
    }
  };

  const handleStatusChange = async (userId: string, isActive: boolean) => {
    try {
      const response = await ldapService.updateUserStatus(userId, isActive);
      if (response.code === 0) {
        message.success(`用户状态${isActive ? '激活' : '禁用'}成功`);
        loadUsers();
      } else {
        message.error(response.message || '更新用户状态失败');
      }
    } catch (error) {
      message.error('更新用户状态时发生错误');
    }
  };

  const showUserDetail = (user: LDAPUser) => {
    setSelectedUser(user);
    setDetailVisible(true);
  };

  const filteredUsers = users.filter(user => {
    if (!searchText) return true;
    const searchLower = searchText.toLowerCase();
    return (
      user.ldap_username?.toLowerCase().includes(searchLower) ||
      user.email?.toLowerCase().includes(searchLower) ||
      user.nickname?.toLowerCase().includes(searchLower) ||
      user.ldap_dn?.toLowerCase().includes(searchLower)
    );
  });

  const columns: ColumnsType<LDAPUser> = [
    {
      title: '用户名',
      dataIndex: 'ldap_username',
      key: 'ldap_username',
      render: (text: string, record: LDAPUser) => (
        <Space>
          <UserOutlined />
          <Button type="link" onClick={() => showUserDetail(record)}>
            {text}
          </Button>
        </Space>
      ),
    },
    {
      title: '邮箱',
      dataIndex: 'email',
      key: 'email',
      render: (email: string) => email || '-',
    },
    {
      title: '显示名',
      dataIndex: 'nickname',
      key: 'nickname',
      render: (nickname: string, record: LDAPUser) => 
        nickname || `${record.first_name || ''} ${record.last_name || ''}`.trim() || '-',
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      render: (isActive: boolean, record: LDAPUser) => (
        <Space>
          <Tag color={isActive ? 'success' : 'default'} icon={isActive ? <CheckCircleOutlined /> : <CloseCircleOutlined />}>
            {isActive ? '活跃' : '禁用'}
          </Tag>
          <Switch
            checked={isActive}
            size="small"
            onChange={(checked) => handleStatusChange(record.id, checked)}
          />
        </Space>
      ),
    },
    {
      title: '系统用户',
      dataIndex: 'system_user',
      key: 'system_user',
      render: (systemUser: any) => (
        systemUser ? (
          <Tag color="blue">
            {systemUser.nickname || systemUser.email}
          </Tag>
        ) : (
          <Tag color="default">未关联</Tag>
        )
      ),
    },
    {
      title: '同步状态',
      dataIndex: 'sync_status',
      key: 'sync_status',
      render: (status: string) => {
        const color = status === 'synced' ? 'success' : 
                     status === 'stale' ? 'warning' : 'default';
        return <Tag color={color}>{status}</Tag>;
      },
    },
    {
      title: '最后登录',
      dataIndex: 'last_login_time',
      key: 'last_login_time',
      render: (time: string) => 
        time ? new Date(time).toLocaleString() : '-',
    },
    {
      title: '最后同步',
      dataIndex: 'last_sync_time',
      key: 'last_sync_time',
      render: (time: string) => 
        time ? new Date(time).toLocaleString() : '-',
    },
    {
      title: '操作',
      key: 'actions',
      render: (_, record: LDAPUser) => (
        <Space>
          <Tooltip title="查看详情">
            <Button 
              type="text" 
              icon={<InfoCircleOutlined />} 
              onClick={() => showUserDetail(record)}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Title level={2}>
        <UserOutlined /> LDAP 用户管理
      </Title>

      <Card>
        <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
          <Col flex={1}>
            <Search
              placeholder="搜索用户名、邮箱、显示名或DN"
              allowClear
              enterButton={<SearchOutlined />}
              size="large"
              onSearch={setSearchText}
              onChange={(e) => !e.target.value && setSearchText('')}
            />
          </Col>
          <Col>
            <Space>
              <span>显示禁用用户:</span>
              <Switch
                checked={showInactive}
                onChange={setShowInactive}
              />
              <Button
                icon={<SyncOutlined />}
                onClick={loadUsers}
                loading={loading}
              >
                刷新
              </Button>
            </Space>
          </Col>
        </Row>

        <Table
          columns={columns}
          dataSource={filteredUsers}
          rowKey="id"
          loading={loading}
          pagination={{
            total: filteredUsers.length,
            pageSize: 20,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) =>
              `第 ${range[0]}-${range[1]} 条，共 ${total} 条`,
          }}
        />
      </Card>

      {/* 用户详情模态框 */}
      <Modal
        title="LDAP 用户详情"
        visible={detailVisible}
        onCancel={() => setDetailVisible(false)}
        footer={null}
        width={800}
      >
        {selectedUser && (
          <Descriptions column={2} bordered>
            <Descriptions.Item label="用户名" span={2}>
              {selectedUser.ldap_username}
            </Descriptions.Item>
            <Descriptions.Item label="DN" span={2}>
              <code>{selectedUser.ldap_dn}</code>
            </Descriptions.Item>
            <Descriptions.Item label="邮箱">
              {selectedUser.email || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="显示名">
              {selectedUser.nickname || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="名字">
              {selectedUser.first_name || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="姓氏">
              {selectedUser.last_name || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="状态">
              <Tag color={selectedUser.is_active ? 'success' : 'default'}>
                {selectedUser.is_active ? '活跃' : '禁用'}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="同步状态">
              <Tag color={selectedUser.sync_status === 'synced' ? 'success' : 'warning'}>
                {selectedUser.sync_status}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="最后登录时间">
              {selectedUser.last_login_time 
                ? new Date(selectedUser.last_login_time).toLocaleString() 
                : '-'
              }
            </Descriptions.Item>
            <Descriptions.Item label="最后同步时间">
              {selectedUser.last_sync_time 
                ? new Date(selectedUser.last_sync_time).toLocaleString() 
                : '-'
              }
            </Descriptions.Item>
            {selectedUser.system_user && (
              <>
                <Descriptions.Item label="关联系统用户" span={2}>
                  <Space>
                    <Tag color="blue">ID: {selectedUser.system_user.id}</Tag>
                    <Tag color="green">{selectedUser.system_user.nickname}</Tag>
                    <Tag>{selectedUser.system_user.email}</Tag>
                  </Space>
                </Descriptions.Item>
              </>
            )}
            {Object.keys(selectedUser.ldap_attributes || {}).length > 0 && (
              <Descriptions.Item label="LDAP 属性" span={2}>
                <div style={{ maxHeight: 200, overflow: 'auto' }}>
                  <pre style={{ fontSize: '12px' }}>
                    {JSON.stringify(selectedUser.ldap_attributes, null, 2)}
                  </pre>
                </div>
              </Descriptions.Item>
            )}
          </Descriptions>
        )}
      </Modal>
    </div>
  );
};

export default LDAPUsersPage;