#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RAGFlow LDAP模块使用示例

此脚本演示如何使用RAGFlow的LDAP功能进行用户认证和管理。
"""

import os
import sys
import json
import asyncio
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from api.db.services.ldap_service import LDAPConfigService, LDAPUserService
from api.ldap.ldap_auth import LDAPAuthenticator, LDAPSyncService
from api.ldap.ldap_scheduler import LDAPScheduler


def example_ldap_config():
    """示例：创建LDAP配置"""
    print("=== 创建LDAP配置示例 ===")
    
    config_data = {
        'name': '演示LDAP服务器',
        'server_host': 'ldap.example.com',
        'server_port': 389,
        'use_ssl': False,
        'bind_dn': 'cn=admin,dc=example,dc=com',
        'bind_password': 'admin_password',
        'search_base': 'ou=users,dc=example,dc=com',
        'search_filter': '(objectClass=person)',
        'user_dn_template': 'uid={username},ou=users,dc=example,dc=com',
        'attr_mapping': {
            'username': 'uid',
            'email': 'mail',
            'nickname': 'displayName',
            'first_name': 'givenName',
            'last_name': 'sn'
        },
        'enabled': True,
        'auto_create_user': True,
        'sync_enabled': True,
        'sync_interval': 30
    }
    
    # 注意：这只是示例，实际使用需要数据库连接
    print(f"配置数据: {json.dumps(config_data, indent=2, ensure_ascii=False)}")
    
    # config = LDAPConfigService.create_config(config_data)
    # if config:
    #     print(f"LDAP配置创建成功，ID: {config.id}")
    # else:
    #     print("LDAP配置创建失败")


def example_ldap_auth():
    """示例：LDAP用户认证"""
    print("\n=== LDAP用户认证示例 ===")
    
    authenticator = LDAPAuthenticator()
    
    # 模拟认证
    username = "testuser"
    password = "testpassword"
    
    print(f"尝试认证用户: {username}")
    
    # 注意：实际使用需要配置LDAP服务器
    # success, user_info = authenticator.authenticate_user(username, password)
    # if success:
    #     print(f"认证成功: {user_info}")
    # else:
    #     print("认证失败")
    
    print("认证流程:")
    print("1. 获取活跃的LDAP配置")
    print("2. 连接到LDAP服务器")
    print("3. 搜索或构建用户DN")
    print("4. 使用用户凭据进行认证")
    print("5. 获取用户属性信息")


def example_ldap_sync():
    """示例：LDAP用户同步"""
    print("\n=== LDAP用户同步示例 ===")
    
    sync_service = LDAPSyncService()
    
    print("同步流程:")
    print("1. 获取LDAP配置")
    print("2. 连接到LDAP服务器")
    print("3. 搜索所有用户")
    print("4. 创建或更新本地用户记录")
    print("5. 标记不存在的用户为非活跃")
    print("6. 更新同步状态")
    
    # 注意：实际使用需要LDAP服务器连接
    # success, stats = sync_service.sync_users()
    # if success:
    #     print(f"同步统计: {stats}")
    # else:
    #     print("同步失败")


def example_ldap_scheduler():
    """示例：LDAP调度器使用"""
    print("\n=== LDAP调度器示例 ===")
    
    scheduler = LDAPScheduler()
    
    print("调度器功能:")
    print("1. 自动检查LDAP配置")
    print("2. 根据同步间隔执行同步")
    print("3. 记录同步状态和统计")
    print("4. 支持强制同步")
    
    # 示例用法
    print("\n启动调度器:")
    print("scheduler.start()")
    
    print("\n强制执行同步:")
    print("success = scheduler.force_sync()")
    
    print("\n停止调度器:")
    print("scheduler.stop()")


def example_user_management():
    """示例：用户管理操作"""
    print("\n=== 用户管理示例 ===")
    
    # 模拟配置ID
    config_id = "config123"
    
    print("用户管理功能:")
    print("1. 获取用户列表")
    print("2. 更新用户状态")
    print("3. 查看用户详情")
    print("4. 清理过期用户")
    
    # 注意：实际使用需要数据库连接
    # users = LDAPUserService.get_users_by_config(config_id)
    # print(f"找到 {len(users)} 个用户")
    
    # # 更新用户状态
    # success = LDAPUserService.set_user_status("user123", False)
    # if success:
    #     print("用户状态更新成功")


def example_api_usage():
    """示例：API接口使用"""
    print("\n=== API接口使用示例 ===")
    
    print("LDAP登录API:")
    print("""
    POST /api/v1/ldap/login
    Content-Type: application/json
    
    {
        "username": "testuser",
        "password": "encrypted_password"
    }
    """)
    
    print("获取LDAP配置:")
    print("""
    GET /api/v1/ldap/config
    Authorization: Bearer <admin_token>
    """)
    
    print("强制同步用户:")
    print("""
    POST /api/v1/ldap/sync
    Authorization: Bearer <admin_token>
    """)
    
    print("获取用户列表:")
    print("""
    GET /api/v1/ldap/users?active_only=true
    Authorization: Bearer <admin_token>
    """)


def example_error_handling():
    """示例：错误处理"""
    print("\n=== 错误处理示例 ===")
    
    print("常见错误和处理:")
    
    print("\n1. LDAP连接失败:")
    print("   - 检查服务器地址和端口")
    print("   - 验证网络连接")
    print("   - 确认SSL设置")
    
    print("\n2. 认证失败:")
    print("   - 检查用户DN模板")
    print("   - 验证搜索配置")
    print("   - 确认用户凭据")
    
    print("\n3. 同步失败:")
    print("   - 检查绑定DN和密码")
    print("   - 验证搜索基础DN")
    print("   - 查看详细日志")


async def example_async_operations():
    """示例：异步操作"""
    print("\n=== 异步操作示例 ===")
    
    print("异步调度器:")
    from api.ldap.ldap_scheduler import AsyncLDAPScheduler
    
    scheduler = AsyncLDAPScheduler()
    
    print("启动异步调度器:")
    # await scheduler.start()
    
    print("异步同步检查每10秒执行一次")
    print("支持优雅停止和错误恢复")
    
    # 模拟运行一段时间
    print("运行调度器...")
    # await asyncio.sleep(5)
    
    print("停止调度器:")
    # await scheduler.stop()


def main():
    """主函数：运行所有示例"""
    print("RAGFlow LDAP模块使用示例")
    print("=" * 50)
    
    # 运行各种示例
    example_ldap_config()
    example_ldap_auth()
    example_ldap_sync()
    example_ldap_scheduler()
    example_user_management()
    example_api_usage()
    example_error_handling()
    
    # 异步示例
    print("\n运行异步示例...")
    # asyncio.run(example_async_operations())
    
    print("\n" + "=" * 50)
    print("示例完成！")
    print("\n注意：")
    print("- 这些只是演示代码，实际使用需要配置真实的LDAP服务器")
    print("- 需要安装 ldap3 依赖：pip install ldap3")
    print("- 确保RAGFlow数据库已正确初始化")
    print("- 管理员权限需要用于配置和管理操作")


if __name__ == "__main__":
    main()