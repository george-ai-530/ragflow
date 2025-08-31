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
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from api.db.db_models import DB, LDAPConfig, LDAPUser
from api.db.services.common_service import CommonService
from api.utils import get_uuid, current_timestamp, datetime_format


class LDAPConfigService(CommonService):
    """Service class for managing LDAP configuration operations."""
    model = LDAPConfig

    @classmethod
    @DB.connection_context()
    def get_active_config(cls) -> Optional[LDAPConfig]:
        """Get the first active LDAP configuration."""
        try:
            return cls.model.select().where(cls.model.enabled == True).first()
        except Exception as e:
            logging.exception(f"Failed to get active LDAP config: {e}")
            return None

    @classmethod
    @DB.connection_context()
    def create_config(cls, config_data: Dict) -> Optional[LDAPConfig]:
        """Create a new LDAP configuration."""
        try:
            config_id = get_uuid()
            config_data.update({
                'id': config_id,
                'create_time': current_timestamp(),
                'create_date': datetime.now(),
                'update_time': current_timestamp(),
                'update_date': datetime.now()
            })
            
            config = cls.model.create(**config_data)
            return config
        except Exception as e:
            logging.exception(f"Failed to create LDAP config: {e}")
            return None

    @classmethod
    @DB.connection_context()
    def update_config(cls, config_id: str, config_data: Dict) -> bool:
        """Update LDAP configuration."""
        try:
            config_data.update({
                'update_time': current_timestamp(),
                'update_date': datetime.now()
            })
            
            updated_rows = cls.model.update(**config_data).where(
                cls.model.id == config_id
            ).execute()
            return updated_rows > 0
        except Exception as e:
            logging.exception(f"Failed to update LDAP config {config_id}: {e}")
            return False

    @classmethod
    @DB.connection_context()
    def update_sync_status(cls, config_id: str, status: str, sync_time: Optional[datetime] = None) -> bool:
        """Update synchronization status."""
        try:
            update_data = {
                'sync_status': status,
                'update_time': current_timestamp(),
                'update_date': datetime.now()
            }
            
            if sync_time:
                update_data['last_sync_time'] = sync_time
            
            updated_rows = cls.model.update(**update_data).where(
                cls.model.id == config_id
            ).execute()
            return updated_rows > 0
        except Exception as e:
            logging.exception(f"Failed to update sync status for config {config_id}: {e}")
            return False


class LDAPUserService(CommonService):
    """Service class for managing LDAP user operations."""
    model = LDAPUser

    @classmethod
    @DB.connection_context()
    def get_by_ldap_username(cls, config_id: str, username: str) -> Optional[LDAPUser]:
        """Get LDAP user by username."""
        try:
            return cls.model.select().where(
                (cls.model.ldap_config_id == config_id) &
                (cls.model.ldap_username == username)
            ).first()
        except Exception as e:
            logging.exception(f"Failed to get LDAP user {username}: {e}")
            return None

    @classmethod
    @DB.connection_context()
    def get_by_dn(cls, config_id: str, dn: str) -> Optional[LDAPUser]:
        """Get LDAP user by DN."""
        try:
            return cls.model.select().where(
                (cls.model.ldap_config_id == config_id) &
                (cls.model.ldap_dn == dn)
            ).first()
        except Exception as e:
            logging.exception(f"Failed to get LDAP user by DN {dn}: {e}")
            return None

    @classmethod
    @DB.connection_context()
    def get_by_email(cls, config_id: str, email: str) -> Optional[LDAPUser]:
        """Get LDAP user by email."""
        try:
            return cls.model.select().where(
                (cls.model.ldap_config_id == config_id) &
                (cls.model.email == email)
            ).first()
        except Exception as e:
            logging.exception(f"Failed to get LDAP user by email {email}: {e}")
            return None

    @classmethod
    @DB.connection_context()
    def create_or_update_user(cls, config_id: str, ldap_data: Dict) -> Tuple[Optional[LDAPUser], bool]:
        """Create or update LDAP user. Returns (user, created)."""
        try:
            # Check if user already exists
            existing_user = None
            if 'dn' in ldap_data:
                existing_user = cls.get_by_dn(config_id, ldap_data['dn'])
            elif 'username' in ldap_data:
                existing_user = cls.get_by_ldap_username(config_id, ldap_data['username'])
            elif 'email' in ldap_data:
                existing_user = cls.get_by_email(config_id, ldap_data['email'])

            now = datetime.now()
            
            if existing_user:
                # Update existing user
                update_data = {
                    'email': ldap_data.get('email'),
                    'nickname': ldap_data.get('nickname'),
                    'first_name': ldap_data.get('first_name'),
                    'last_name': ldap_data.get('last_name'),
                    'ldap_attributes': ldap_data.get('attributes', {}),
                    'is_active': ldap_data.get('is_active', True),
                    'last_sync_time': now,
                    'sync_status': 'synced',
                    'update_time': current_timestamp(),
                    'update_date': now
                }
                
                cls.model.update(**update_data).where(
                    cls.model.id == existing_user.id
                ).execute()
                
                # Refresh the model instance
                existing_user = cls.get_by_id(existing_user.id)
                return existing_user, False
            else:
                # Create new user
                user_id = get_uuid()
                user_data = {
                    'id': user_id,
                    'ldap_config_id': config_id,
                    'ldap_dn': ldap_data.get('dn', ''),
                    'ldap_username': ldap_data.get('username', ''),
                    'email': ldap_data.get('email'),
                    'nickname': ldap_data.get('nickname'),
                    'first_name': ldap_data.get('first_name'),
                    'last_name': ldap_data.get('last_name'),
                    'ldap_attributes': ldap_data.get('attributes', {}),
                    'is_active': ldap_data.get('is_active', True),
                    'last_sync_time': now,
                    'sync_status': 'synced',
                    'create_time': current_timestamp(),
                    'create_date': now,
                    'update_time': current_timestamp(),
                    'update_date': now
                }
                
                user = cls.model.create(**user_data)
                return user, True
                
        except Exception as e:
            logging.exception(f"Failed to create/update LDAP user: {e}")
            return None, False

    @classmethod
    @DB.connection_context()
    def get_users_by_config(cls, config_id: str, active_only: bool = True) -> List[LDAPUser]:
        """Get all LDAP users for a configuration."""
        try:
            query = cls.model.select().where(cls.model.ldap_config_id == config_id)
            if active_only:
                query = query.where(cls.model.is_active == True)
            return list(query)
        except Exception as e:
            logging.exception(f"Failed to get LDAP users for config {config_id}: {e}")
            return []

    @classmethod
    @DB.connection_context()
    def set_user_status(cls, user_id: str, is_active: bool) -> bool:
        """Set user active status."""
        try:
            updated_rows = cls.model.update(
                is_active=is_active,
                update_time=current_timestamp(),
                update_date=datetime.now()
            ).where(cls.model.id == user_id).execute()
            return updated_rows > 0
        except Exception as e:
            logging.exception(f"Failed to set user status {user_id}: {e}")
            return False

    @classmethod
    @DB.connection_context()
    def update_login_time(cls, user_id: str) -> bool:
        """Update last login time."""
        try:
            now = datetime.now()
            updated_rows = cls.model.update(
                last_login_time=now,
                update_time=current_timestamp(),
                update_date=now
            ).where(cls.model.id == user_id).execute()
            return updated_rows > 0
        except Exception as e:
            logging.exception(f"Failed to update login time for user {user_id}: {e}")
            return False

    @classmethod
    @DB.connection_context()
    def mark_stale_users(cls, config_id: str, active_dns: List[str]) -> int:
        """Mark users as inactive if they are not in the active DN list."""
        try:
            updated_rows = cls.model.update(
                is_active=False,
                sync_status='stale',
                update_time=current_timestamp(),
                update_date=datetime.now()
            ).where(
                (cls.model.ldap_config_id == config_id) &
                (cls.model.ldap_dn.not_in(active_dns)) &
                (cls.model.is_active == True)
            ).execute()
            return updated_rows
        except Exception as e:
            logging.exception(f"Failed to mark stale users for config {config_id}: {e}")
            return 0

    @classmethod
    @DB.connection_context()
    def cleanup_stale_users(cls, config_id: str, days: int = 30) -> int:
        """Delete users that have been stale for more than specified days."""
        try:
            import peewee
            cutoff_date = datetime.now() - timedelta(days=days)
            
            deleted_rows = cls.model.delete().where(
                (cls.model.ldap_config_id == config_id) &
                (cls.model.sync_status == 'stale') &
                (cls.model.update_date < cutoff_date)
            ).execute()
            return deleted_rows
        except Exception as e:
            logging.exception(f"Failed to cleanup stale users for config {config_id}: {e}")
            return 0