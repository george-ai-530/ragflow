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
RAGFlow LDAP模块

提供LDAP用户认证和同步功能，支持：
- LDAP/LDAPS用户认证
- 30秒自动用户同步
- 用户有效性管理
- 灵活的属性映射配置
"""

__version__ = "1.0.0"
__author__ = "RAGFlow Team"

from .ldap_auth import LDAPAuthenticator, LDAPSyncService, LDAPConnectionManager
from .ldap_scheduler import LDAPScheduler, start_ldap_scheduler, stop_ldap_scheduler, force_ldap_sync

__all__ = [
    'LDAPAuthenticator',
    'LDAPSyncService', 
    'LDAPConnectionManager',
    'LDAPScheduler',
    'start_ldap_scheduler',
    'stop_ldap_scheduler',
    'force_ldap_sync'
]