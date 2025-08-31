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
import logging
from flask import request
from flask_login import login_required, current_user, login_user

from api import settings
from api.db.services.ldap_service import LDAPConfigService, LDAPUserService
from api.db.services.user_service import UserService
from api.ldap.ldap_auth import LDAPAuthenticator
from api.ldap.ldap_scheduler import force_ldap_sync
from api.utils import get_uuid, get_format_time, current_timestamp, decrypt
from api.utils.api_utils import (
    construct_response,
    get_data_error_result, 
    get_json_result,
    server_error_response,
    validate_request,
)
from datetime import datetime


@manager.route('/login', methods=['POST'])  # noqa: F821
def ldap_login():
    """
    LDAP用户登录接口
    ---
    tags:
      - LDAP
    parameters:
      - in: body
        name: body
        description: LDAP登录凭据
        required: true
        schema:
          type: object
          properties:
            username:
              type: string
              description: LDAP用户名
            password:
              type: string
              description: 用户密码（加密）
    responses:
      200:
        description: 登录成功
        schema:
          type: object
      401:
        description: 认证失败
        schema:
          type: object
    """
    if not request.json:
        return get_json_result(
            data=False, 
            code=settings.RetCode.AUTHENTICATION_ERROR, 
            message="Invalid request!"
        )

    username = request.json.get("username", "")
    password = request.json.get("password", "")
    
    if not username or not password:
        return get_json_result(
            data=False,
            code=settings.RetCode.AUTHENTICATION_ERROR,
            message="Username and password are required!"
        )

    try:
        # 解密密码
        password = decrypt(password)
    except Exception:
        return get_json_result(
            data=False,
            code=settings.RetCode.SERVER_ERROR,
            message="Failed to decrypt password"
        )

    try:
        # LDAP认证
        authenticator = LDAPAuthenticator()
        success, ldap_user_info = authenticator.authenticate_user(username, password)
        
        if not success or not ldap_user_info:
            return get_json_result(
                data=False,
                code=settings.RetCode.AUTHENTICATION_ERROR,
                message="Invalid LDAP credentials!"
            )

        # 获取或创建LDAP用户记录
        config = LDAPConfigService.get_active_config()
        if not config:
            return get_json_result(
                data=False,
                code=settings.RetCode.SERVER_ERROR,
                message="LDAP configuration not found!"
            )

        ldap_user, created = LDAPUserService.create_or_update_user(
            config.id, ldap_user_info
        )
        
        if not ldap_user:
            return get_json_result(
                data=False,
                code=settings.RetCode.SERVER_ERROR,
                message="Failed to create LDAP user record!"
            )

        # 更新登录时间
        LDAPUserService.update_login_time(ldap_user.id)

        # 获取或创建系统用户
        system_user = None
        if ldap_user.user_id:
            users = UserService.query(id=ldap_user.user_id)
            system_user = users[0] if users else None

        if not system_user and config.auto_create_user:
            # 自动创建系统用户
            user_data = {
                'id': get_uuid(),
                'email': ldap_user_info.get('email') or f"{username}@ldap.local",
                'nickname': ldap_user_info.get('nickname') or username,
                'password': '',  # LDAP用户不需要密码
                'login_channel': 'ldap',
                'last_login_time': get_format_time(),
                'is_superuser': False,
                'status': '1'
            }
            
            system_user = UserService.save(**user_data)
            if system_user:
                # 关联LDAP用户和系统用户
                LDAPUserService.model.update(
                    user_id=system_user.id
                ).where(
                    LDAPUserService.model.id == ldap_user.id
                ).execute()

        if not system_user:
            return get_json_result(
                data=False,
                code=settings.RetCode.AUTHENTICATION_ERROR,
                message="User account not found or disabled!"
            )

        # 登录用户
        system_user.access_token = get_uuid()
        login_user(system_user)
        system_user.update_time = current_timestamp()
        system_user.update_date = datetime.now()
        system_user.save()

        response_data = system_user.to_json()
        return construct_response(
            data=response_data,
            auth=system_user.get_id(),
            message="LDAP login successful!"
        )

    except Exception as e:
        logging.exception(f"LDAP login error: {e}")
        return server_error_response(e)


@manager.route('/config', methods=['GET'])  # noqa: F821
@login_required
def get_config():
    """
    获取LDAP配置
    ---
    tags:
      - LDAP
    security:
      - ApiKeyAuth: []
    responses:
      200:
        description: 配置获取成功
        schema:
          type: object
    """
    try:
        if not current_user.is_superuser:
            return get_json_result(
                data=False,
                code=settings.RetCode.AUTHENTICATION_ERROR,
                message="Admin access required!"
            )

        config = LDAPConfigService.get_active_config()
        if not config:
            return get_json_result(data=None, message="No LDAP configuration found")

        config_data = config.to_dict()
        # 隐藏敏感信息
        config_data.pop('bind_password', None)
        
        return get_json_result(data=config_data)

    except Exception as e:
        return server_error_response(e)


@manager.route('/config', methods=['POST'])  # noqa: F821
@login_required
@validate_request("name", "server_host", "server_port", "search_base")
def create_or_update_config():
    """
    创建或更新LDAP配置
    ---
    tags:
      - LDAP
    security:
      - ApiKeyAuth: []
    parameters:
      - in: body
        name: body
        description: LDAP配置数据
        required: true
        schema:
          type: object
          properties:
            name:
              type: string
              description: 配置名称
            server_host:
              type: string
              description: LDAP服务器地址
            server_port:
              type: integer
              description: LDAP服务器端口
            use_ssl:
              type: boolean
              description: 使用SSL连接
            bind_dn:
              type: string
              description: 绑定DN
            bind_password:
              type: string
              description: 绑定密码
            search_base:
              type: string
              description: 搜索基础DN
            search_filter:
              type: string
              description: 搜索过滤器
            user_dn_template:
              type: string
              description: 用户DN模板
            attr_mapping:
              type: object
              description: 属性映射
            enabled:
              type: boolean
              description: 启用LDAP认证
            auto_create_user:
              type: boolean
              description: 自动创建用户
            sync_enabled:
              type: boolean
              description: 启用用户同步
            sync_interval:
              type: integer
              description: 同步间隔（秒）
    responses:
      200:
        description: 配置更新成功
        schema:
          type: object
    """
    try:
        if not current_user.is_superuser:
            return get_json_result(
                data=False,
                code=settings.RetCode.AUTHENTICATION_ERROR,
                message="Admin access required!"
            )

        req = request.json
        
        # 验证同步间隔
        sync_interval = req.get('sync_interval', 30)
        if sync_interval < 30:
            return get_data_error_result(message="Sync interval must be at least 30 seconds")

        # 获取现有配置
        existing_config = LDAPConfigService.get_active_config()
        
        if existing_config:
            # 更新现有配置
            success = LDAPConfigService.update_config(existing_config.id, req)
            if success:
                return get_json_result(data=True, message="LDAP configuration updated successfully")
            else:
                return server_error_response("Failed to update LDAP configuration")
        else:
            # 创建新配置
            config = LDAPConfigService.create_config(req)
            if config:
                return get_json_result(data=config.to_dict(), message="LDAP configuration created successfully")
            else:
                return server_error_response("Failed to create LDAP configuration")

    except Exception as e:
        return server_error_response(e)


@manager.route('/config/test', methods=['POST'])  # noqa: F821
@login_required
def test_connection():
    """
    测试LDAP连接
    ---
    tags:
      - LDAP
    security:
      - ApiKeyAuth: []
    responses:
      200:
        description: 连接测试结果
        schema:
          type: object
    """
    try:
        if not current_user.is_superuser:
            return get_json_result(
                data=False,
                code=settings.RetCode.AUTHENTICATION_ERROR,
                message="Admin access required!"
            )

        config = LDAPConfigService.get_active_config()
        if not config:
            return get_data_error_result(message="No LDAP configuration found")

        # TODO: 实现LDAP连接测试
        from api.ldap.ldap_auth import LDAPConnectionManager
        
        try:
            conn_mgr = LDAPConnectionManager(config)
            with conn_mgr:
                return get_json_result(
                    data=True,
                    message="LDAP connection successful"
                )
        except Exception as e:
            return get_json_result(
                data=False,
                message=f"LDAP connection failed: {str(e)}"
            )

    except Exception as e:
        return server_error_response(e)


@manager.route('/sync', methods=['POST'])  # noqa: F821
@login_required
def force_sync():
    """
    强制执行用户同步
    ---
    tags:
      - LDAP
    security:
      - ApiKeyAuth: []
    responses:
      200:
        description: 同步执行结果
        schema:
          type: object
    """
    try:
        if not current_user.is_superuser:
            return get_json_result(
                data=False,
                code=settings.RetCode.AUTHENTICATION_ERROR,
                message="Admin access required!"
            )

        success = force_ldap_sync()
        if success:
            return get_json_result(data=True, message="LDAP sync completed successfully")
        else:
            return get_json_result(data=False, message="LDAP sync failed")

    except Exception as e:
        return server_error_response(e)


@manager.route('/users', methods=['GET'])  # noqa: F821
@login_required
def get_ldap_users():
    """
    获取LDAP用户列表
    ---
    tags:
      - LDAP
    security:
      - ApiKeyAuth: []
    parameters:
      - in: query
        name: active_only
        type: boolean
        description: 仅显示活跃用户
    responses:
      200:
        description: 用户列表
        schema:
          type: object
    """
    try:
        if not current_user.is_superuser:
            return get_json_result(
                data=False,
                code=settings.RetCode.AUTHENTICATION_ERROR,
                message="Admin access required!"
            )

        config = LDAPConfigService.get_active_config()
        if not config:
            return get_data_error_result(message="No LDAP configuration found")

        active_only = request.args.get('active_only', 'true').lower() == 'true'
        users = LDAPUserService.get_users_by_config(config.id, active_only)
        
        user_list = []
        for user in users:
            user_data = user.to_dict()
            # 获取关联的系统用户信息
            if user.user_id:
                system_users = UserService.query(id=user.user_id)
                if system_users:
                    system_user = system_users[0]
                    user_data['system_user'] = {
                        'id': system_user.id,
                        'email': system_user.email,
                        'nickname': system_user.nickname,
                        'status': system_user.status
                    }
            user_list.append(user_data)

        return get_json_result(data=user_list)

    except Exception as e:
        return server_error_response(e)


@manager.route('/users/<user_id>/status', methods=['PUT'])  # noqa: F821
@login_required
def update_user_status(user_id):
    """
    更新LDAP用户状态
    ---
    tags:
      - LDAP
    security:
      - ApiKeyAuth: []
    parameters:
      - in: path
        name: user_id
        type: string
        required: true
        description: LDAP用户ID
      - in: body
        name: body
        description: 状态更新
        required: true
        schema:
          type: object
          properties:
            is_active:
              type: boolean
              description: 用户是否活跃
    responses:
      200:
        description: 状态更新成功
        schema:
          type: object
    """
    try:
        if not current_user.is_superuser:
            return get_json_result(
                data=False,
                code=settings.RetCode.AUTHENTICATION_ERROR,
                message="Admin access required!"
            )

        req = request.json
        is_active = req.get('is_active', True)
        
        success = LDAPUserService.set_user_status(user_id, is_active)
        if success:
            return get_json_result(data=True, message="User status updated successfully")
        else:
            return get_data_error_result(message="Failed to update user status")

    except Exception as e:
        return server_error_response(e)


@manager.route('/status', methods=['GET'])  # noqa: F821
@login_required
def get_ldap_status():
    """
    获取LDAP服务状态
    ---
    tags:
      - LDAP
    security:
      - ApiKeyAuth: []
    responses:
      200:
        description: LDAP服务状态
        schema:
          type: object
    """
    try:
        if not current_user.is_superuser:
            return get_json_result(
                data=False,
                code=settings.RetCode.AUTHENTICATION_ERROR,
                message="Admin access required!"
            )

        config = LDAPConfigService.get_active_config()
        
        status_data = {
            'configured': config is not None,
            'enabled': config.enabled if config else False,
            'sync_enabled': config.sync_enabled if config else False,
            'sync_interval': config.sync_interval if config else 30,
            'last_sync_time': config.last_sync_time.isoformat() if config and config.last_sync_time else None,
            'sync_status': config.sync_status if config else 'idle',
            'ldap3_available': True
        }
        
        # 检查ldap3库是否可用
        try:
            import ldap3
            status_data['ldap3_available'] = True
        except ImportError:
            status_data['ldap3_available'] = False

        # 获取用户统计
        if config:
            all_users = LDAPUserService.get_users_by_config(config.id, active_only=False)
            active_users = LDAPUserService.get_users_by_config(config.id, active_only=True)
            
            status_data['user_stats'] = {
                'total_users': len(all_users),
                'active_users': len(active_users),
                'inactive_users': len(all_users) - len(active_users)
            }

        return get_json_result(data=status_data)

    except Exception as e:
        return server_error_response(e)