# RAGFlow LDAP模块

RAGFlow LDAP模块提供了与LDAP（Lightweight Directory Access Protocol）目录服务的集成，支持用户认证和自动同步功能。

## 功能特性

### 🔐 LDAP认证
- 支持标准LDAP和LDAPS（SSL/TLS）连接
- 灵活的用户DN模板或搜索配置
- 与现有用户系统无缝集成
- 支持自动用户创建

### 🔄 自动用户同步
- **30秒自动同步**：可配置的自动同步间隔（最小30秒）
- 实时用户状态管理（有效/无效）
- 增量同步，只更新变更的用户
- 自动清理过期用户

### 🎛️ 灵活配置
- 可自定义属性映射
- 支持多种LDAP服务器（AD、OpenLDAP等）
- 丰富的搜索过滤器选项
- 管理界面配置

## 快速开始

### 1. 安装依赖

LDAP模块需要 `ldap3` 库：

```bash
pip install ldap3>=2.9.0
```

或者使用uv安装：

```bash
uv add ldap3>=2.9.0
```

### 2. 配置LDAP服务器

在 `conf/service_conf.yaml` 中添加LDAP配置：

```yaml
ldap:
  enabled: true
  server_host: "ldap.example.com"
  server_port: 389
  use_ssl: false
  bind_dn: "cn=admin,dc=example,dc=com"
  bind_password: "admin_password"
  search_base: "ou=users,dc=example,dc=com"
  search_filter: "(objectClass=person)"
  user_dn_template: "uid={username},ou=users,dc=example,dc=com"
  attr_mapping:
    username: "uid"
    email: "mail"
    nickname: "displayName"
    first_name: "givenName"
    last_name: "sn"
  auto_create_user: true
  sync_enabled: true
  sync_interval: 30
```

### 3. 启动服务

启动RAGFlow服务器后，LDAP模块会自动初始化并开始同步调度器。

## API接口

### 认证接口

#### LDAP登录
```http
POST /api/v1/ldap/login
Content-Type: application/json

{
  "username": "user@example.com",
  "password": "encrypted_password"
}
```

### 配置管理

#### 获取LDAP配置
```http
GET /api/v1/ldap/config
Authorization: Bearer <admin_token>
```

#### 更新LDAP配置
```http
POST /api/v1/ldap/config
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "name": "Company LDAP",
  "server_host": "ldap.company.com",
  "server_port": 389,
  "search_base": "ou=employees,dc=company,dc=com",
  // ... 其他配置
}
```

#### 测试LDAP连接
```http
POST /api/v1/ldap/config/test
Authorization: Bearer <admin_token>
```

### 用户管理

#### 获取LDAP用户列表
```http
GET /api/v1/ldap/users?active_only=true
Authorization: Bearer <admin_token>
```

#### 强制同步用户
```http
POST /api/v1/ldap/sync
Authorization: Bearer <admin_token>
```

#### 更新用户状态
```http
PUT /api/v1/ldap/users/{user_id}/status
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "is_active": false
}
```

#### 获取服务状态
```http
GET /api/v1/ldap/status
Authorization: Bearer <admin_token>
```

## 前端管理界面

### LDAP配置页面
位置：`/ldap/config`
- 配置LDAP服务器连接参数
- 设置用户属性映射
- 配置同步选项
- 测试连接功能

### LDAP用户管理页面
位置：`/ldap/users`
- 查看所有LDAP用户
- 管理用户状态（启用/禁用）
- 查看用户详细信息
- 搜索和过滤用户

## 配置参数说明

### 基本连接设置
- `server_host`: LDAP服务器地址
- `server_port`: LDAP服务器端口（通常389或636）
- `use_ssl`: 是否使用SSL/TLS连接
- `bind_dn`: 用于连接的管理员DN（可选）
- `bind_password`: 管理员密码（可选）

### 用户搜索设置
- `search_base`: 搜索用户的基础DN
- `search_filter`: LDAP搜索过滤器
- `user_dn_template`: 用户DN模板，用于直接认证

### 属性映射
将LDAP属性映射到系统用户字段：
- `username`: 用户名属性（如uid、sAMAccountName）
- `email`: 邮箱属性（如mail、userPrincipalName）
- `nickname`: 显示名属性（如displayName、cn）
- `first_name`: 名字属性（如givenName）
- `last_name`: 姓氏属性（如sn）

### 同步设置
- `enabled`: 启用LDAP认证
- `auto_create_user`: 自动创建不存在的用户
- `sync_enabled`: 启用自动用户同步
- `sync_interval`: 同步间隔（秒，最小30秒）

## 支持的LDAP服务器

### Microsoft Active Directory
```yaml
ldap:
  server_host: "dc.company.com"
  server_port: 389
  search_base: "CN=Users,DC=company,DC=com"
  search_filter: "(&(objectCategory=person)(objectClass=user))"
  attr_mapping:
    username: "sAMAccountName"
    email: "userPrincipalName"
    nickname: "displayName"
    first_name: "givenName"
    last_name: "sn"
```

### OpenLDAP
```yaml
ldap:
  server_host: "openldap.company.com"
  server_port: 389
  search_base: "ou=people,dc=company,dc=com"
  search_filter: "(objectClass=inetOrgPerson)"
  attr_mapping:
    username: "uid"
    email: "mail"
    nickname: "displayName"
    first_name: "givenName"
    last_name: "sn"
```

### FreeIPA
```yaml
ldap:
  server_host: "ipa.company.com"
  server_port: 389
  search_base: "cn=users,cn=accounts,dc=company,dc=com"
  search_filter: "(objectClass=person)"
  attr_mapping:
    username: "uid"
    email: "mail"
    nickname: "displayName"
    first_name: "givenName"
    last_name: "sn"
```

## 安全考虑

### SSL/TLS连接
生产环境建议启用SSL连接：
```yaml
ldap:
  server_port: 636
  use_ssl: true
```

### 最小权限原则
- 使用专门的服务账户进行LDAP绑定
- 限制服务账户的权限，仅允许读取用户信息
- 定期轮换服务账户密码

### 访问控制
- 只有系统管理员可以访问LDAP配置接口
- 所有LDAP管理接口都需要身份验证
- 敏感信息（如密码）在API响应中被隐藏

## 故障排除

### 常见问题

#### 1. LDAP连接失败
```
错误: Failed to connect to LDAP server
```
解决方案：
- 检查服务器地址和端口
- 验证网络连接
- 确认SSL设置是否正确

#### 2. 认证失败
```
错误: Invalid LDAP credentials
```
解决方案：
- 检查用户DN模板或搜索配置
- 验证用户密码
- 确认用户在LDAP中存在且启用

#### 3. 同步失败
```
错误: LDAP sync failed
```
解决方案：
- 检查绑定DN和密码
- 验证搜索基础DN和过滤器
- 查看详细日志信息

#### 4. 属性映射问题
```
错误: User attribute not found
```
解决方案：
- 检查LDAP属性是否存在
- 验证属性映射配置
- 使用LDAP浏览器工具确认属性名

### 调试日志

启用详细日志记录：
```python
import logging
logging.getLogger('api.ldap').setLevel(logging.DEBUG)
```

## 性能优化

### 同步性能
- 适当设置同步间隔，避免过于频繁
- 使用有效的搜索过滤器减少查询结果
- 考虑在低峰时段进行大规模同步

### 连接池
LDAP模块使用连接池来提高性能：
- 连接会被自动管理和重用
- 支持并发用户认证
- 自动处理连接超时和重连

## 监控和维护

### 状态监控
通过状态API监控LDAP服务：
```http
GET /api/v1/ldap/status
```

返回信息包括：
- 配置状态
- 同步状态
- 用户统计
- 最后同步时间

### 定期维护
- 监控同步日志，及时发现问题
- 定期检查用户状态，清理无效用户
- 更新LDAP服务器证书（如使用SSL）
- 备份LDAP配置

## 扩展开发

### 自定义属性映射
可以扩展属性映射来支持更多字段：

```python
# 在 ldap_auth.py 中扩展
def _get_user_info(self, connection, user_dn):
    # 添加自定义属性
    custom_attrs = ['department', 'title', 'phone']
    attrs = list(config.attr_mapping.values()) + custom_attrs
    # ... 处理逻辑
```

### 自定义同步逻辑
可以扩展同步服务来支持特定需求：

```python
class CustomLDAPSyncService(LDAPSyncService):
    def _process_user(self, ldap_user_data):
        # 自定义用户处理逻辑
        pass
```

## 许可证

本模块遵循 Apache License 2.0 许可证。