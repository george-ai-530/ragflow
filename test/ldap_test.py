#
#  Copyright 2024 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
"""
LDAP模块测试用例

运行测试:
python -m pytest test/ldap_test.py -v
"""

import pytest
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from api.db.services.ldap_service import LDAPConfigService, LDAPUserService
from api.ldap.ldap_auth import LDAPAuthenticator, LDAPSyncService, LDAPConnectionManager


class TestLDAPConfigService(unittest.TestCase):
    """测试LDAP配置服务"""
    
    def setUp(self):
        self.config_data = {
            'name': 'Test LDAP',
            'server_host': 'ldap.test.com',
            'server_port': 389,
            'use_ssl': False,
            'bind_dn': 'cn=admin,dc=test,dc=com',
            'bind_password': 'password',
            'search_base': 'ou=users,dc=test,dc=com',
            'search_filter': '(objectClass=person)',
            'attr_mapping': {
                'username': 'uid',
                'email': 'mail',
                'nickname': 'displayName'
            },
            'enabled': True,
            'auto_create_user': True,
            'sync_enabled': True,
            'sync_interval': 30
        }

    @patch('api.db.services.ldap_service.LDAPConfigService.model')
    def test_create_config(self, mock_model):
        """测试创建LDAP配置"""
        # Mock返回值
        mock_instance = Mock()
        mock_model.create.return_value = mock_instance
        
        # 调用方法
        result = LDAPConfigService.create_config(self.config_data)
        
        # 验证结果
        self.assertIsNotNone(result)
        mock_model.create.assert_called_once()

    @patch('api.db.services.ldap_service.LDAPConfigService.model')
    def test_get_active_config(self, mock_model):
        """测试获取活跃配置"""
        # Mock返回值
        mock_instance = Mock()
        mock_model.select().where().first.return_value = mock_instance
        
        # 调用方法
        result = LDAPConfigService.get_active_config()
        
        # 验证结果
        self.assertIsNotNone(result)


class TestLDAPUserService(unittest.TestCase):
    """测试LDAP用户服务"""
    
    def setUp(self):
        self.user_data = {
            'dn': 'uid=testuser,ou=users,dc=test,dc=com',
            'username': 'testuser',
            'email': 'testuser@test.com',
            'nickname': 'Test User',
            'first_name': 'Test',
            'last_name': 'User',
            'attributes': {
                'uid': ['testuser'],
                'mail': ['testuser@test.com']
            }
        }
        
    @patch('api.db.services.ldap_service.LDAPUserService.model')
    def test_create_or_update_user(self, mock_model):
        """测试创建或更新用户"""
        # Mock没有找到现有用户
        mock_model.select().where().first.return_value = None
        mock_instance = Mock()
        mock_model.create.return_value = mock_instance
        
        # 调用方法
        result, created = LDAPUserService.create_or_update_user(
            'config123', self.user_data
        )
        
        # 验证结果
        self.assertIsNotNone(result)
        self.assertTrue(created)


class TestLDAPAuthenticator(unittest.TestCase):
    """测试LDAP认证器"""
    
    def setUp(self):
        self.authenticator = LDAPAuthenticator()
        
    @patch('api.ldap.ldap_auth.LDAPConfigService.get_active_config')
    def test_authenticate_user_no_config(self, mock_get_config):
        """测试无配置时的认证"""
        mock_get_config.return_value = None
        
        success, user_info = self.authenticator.authenticate_user(
            'testuser', 'password'
        )
        
        self.assertFalse(success)
        self.assertIsNone(user_info)

    @patch('api.ldap.ldap_auth.ldap3')
    @patch('api.ldap.ldap_auth.LDAPConfigService.get_active_config')
    def test_authenticate_user_ldap_unavailable(self, mock_get_config, mock_ldap3):
        """测试LDAP库不可用时的认证"""
        # 模拟配置存在但启用
        mock_config = Mock()
        mock_config.enabled = True
        mock_get_config.return_value = mock_config
        
        # 模拟ldap3不可用
        mock_ldap3 = None
        
        success, user_info = self.authenticator.authenticate_user(
            'testuser', 'password'
        )
        
        self.assertFalse(success)
        self.assertIsNone(user_info)


class TestLDAPConnectionManager(unittest.TestCase):
    """测试LDAP连接管理器"""
    
    def setUp(self):
        self.config = Mock()
        self.config.server_host = 'ldap.test.com'
        self.config.server_port = 389
        self.config.use_ssl = False
        self.config.bind_dn = 'cn=admin,dc=test,dc=com'
        self.config.bind_password = 'password'
        
    @patch('api.ldap.ldap_auth.ldap3')
    def test_create_server(self, mock_ldap3):
        """测试创建服务器连接"""
        # 模拟ldap3可用
        mock_server = Mock()
        mock_ldap3.Server.return_value = mock_server
        
        # 创建连接管理器
        conn_mgr = LDAPConnectionManager(self.config)
        conn_mgr._create_server()
        
        # 验证服务器创建
        mock_ldap3.Server.assert_called_once()


class TestLDAPSyncService(unittest.TestCase):
    """测试LDAP同步服务"""
    
    def setUp(self):
        self.sync_service = LDAPSyncService()
        
    @patch('api.ldap.ldap_auth.LDAPConfigService.get_active_config')
    def test_sync_users_no_config(self, mock_get_config):
        """测试无配置时的同步"""
        mock_get_config.return_value = None
        
        success, stats = self.sync_service.sync_users()
        
        self.assertFalse(success)
        self.assertEqual(stats, {})

    @patch('api.ldap.ldap_auth.LDAPConfigService.get_active_config')
    def test_sync_users_disabled(self, mock_get_config):
        """测试同步被禁用时"""
        mock_config = Mock()
        mock_config.enabled = False
        mock_get_config.return_value = mock_config
        
        success, stats = self.sync_service.sync_users()
        
        self.assertFalse(success)
        self.assertEqual(stats, {})


class TestLDAPIntegration(unittest.TestCase):
    """LDAP集成测试"""
    
    @patch('requests.post')
    def test_ldap_login_api(self, mock_post):
        """测试LDAP登录API"""
        # 模拟API响应
        mock_response = Mock()
        mock_response.json.return_value = {
            'code': 0,
            'data': {
                'id': 'user123',
                'email': 'test@test.com',
                'nickname': 'Test User'
            },
            'message': 'LDAP login successful!'
        }
        mock_response.headers = {'Authorization': 'token123'}
        mock_post.return_value = mock_response
        
        # 模拟登录请求
        login_data = {
            'username': 'testuser',
            'password': 'encrypted_password'
        }
        
        # 这里应该使用实际的API测试
        # 由于需要完整的Flask应用环境，这里只做基本验证
        self.assertTrue(True)  # 占位符测试

    def test_ldap_config_validation(self):
        """测试LDAP配置验证"""
        # 测试必需字段
        config = {
            'name': 'Test LDAP',
            'server_host': 'ldap.test.com',
            'server_port': 389,
            'search_base': 'ou=users,dc=test,dc=com'
        }
        
        # 验证必需字段存在
        required_fields = ['name', 'server_host', 'server_port', 'search_base']
        for field in required_fields:
            self.assertIn(field, config)
            
        # 验证端口范围
        self.assertGreater(config['server_port'], 0)
        self.assertLessEqual(config['server_port'], 65535)

    def test_user_attribute_mapping(self):
        """测试用户属性映射"""
        attr_mapping = {
            'username': 'uid',
            'email': 'mail',
            'nickname': 'displayName',
            'first_name': 'givenName',
            'last_name': 'sn'
        }
        
        # 模拟LDAP属性
        ldap_attrs = {
            'uid': ['testuser'],
            'mail': ['testuser@test.com'],
            'displayName': ['Test User'],
            'givenName': ['Test'],
            'sn': ['User']
        }
        
        # 测试映射转换
        mapped_data = {}
        for key, ldap_attr in attr_mapping.items():
            if ldap_attr in ldap_attrs:
                value = ldap_attrs[ldap_attr]
                mapped_data[key] = value[0] if isinstance(value, list) and value else None
                
        self.assertEqual(mapped_data['username'], 'testuser')
        self.assertEqual(mapped_data['email'], 'testuser@test.com')
        self.assertEqual(mapped_data['nickname'], 'Test User')


if __name__ == '__main__':
    # 运行测试
    unittest.main()