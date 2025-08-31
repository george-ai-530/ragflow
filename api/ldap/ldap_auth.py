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
import ssl
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

try:
    import ldap3
    from ldap3 import Server, Connection, ALL, NTLM, SIMPLE
    from ldap3.core.exceptions import LDAPException, LDAPInvalidCredentialsError
except ImportError:
    ldap3 = None
    logging.warning("ldap3 library not installed. LDAP functionality will be disabled.")

from api.db.services.ldap_service import LDAPConfigService, LDAPUserService
from api.db.services.user_service import UserService
from api.utils import get_uuid, get_format_time


class LDAPConnectionManager:
    """Manages LDAP server connections and operations."""
    
    def __init__(self, config):
        self.config = config
        self.server = None
        self.connection = None
        
    def _create_server(self):
        """Create LDAP server instance."""
        if not ldap3:
            raise ImportError("ldap3 library is required for LDAP functionality")
            
        server_uri = f"{'ldaps' if self.config.use_ssl else 'ldap'}://{self.config.server_host}:{self.config.server_port}"
        
        tls_config = None
        if self.config.use_ssl:
            tls_config = ldap3.Tls(validate=ssl.CERT_NONE)  # For development, use proper cert validation in production
            
        self.server = Server(
            host=self.config.server_host,
            port=self.config.server_port,
            use_ssl=self.config.use_ssl,
            tls=tls_config,
            get_info=ALL
        )
        
    def connect(self, bind_dn=None, password=None):
        """Establish connection to LDAP server."""
        if not self.server:
            self._create_server()
            
        # Use service account for bind if provided, otherwise anonymous
        user_dn = bind_dn or self.config.bind_dn
        user_password = password or self.config.bind_password
        
        try:
            self.connection = Connection(
                self.server,
                user=user_dn,
                password=user_password,
                authentication=SIMPLE,
                auto_bind=True,
                raise_exceptions=True
            )
            return True
        except LDAPException as e:
            logging.error(f"Failed to connect to LDAP server: {e}")
            return False
            
    def disconnect(self):
        """Close LDAP connection."""
        if self.connection:
            self.connection.unbind()
            self.connection = None
            
    def __enter__(self):
        """Context manager entry."""
        if not self.connect():
            raise ConnectionError("Failed to connect to LDAP server")
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()


class LDAPAuthenticator:
    """Handles LDAP authentication operations."""
    
    def __init__(self):
        self.config = None
        
    def get_config(self):
        """Get active LDAP configuration."""
        if not self.config:
            self.config = LDAPConfigService.get_active_config()
        return self.config
        
    def authenticate_user(self, username: str, password: str) -> Tuple[bool, Optional[Dict]]:
        """
        Authenticate user against LDAP.
        
        Returns:
            Tuple[bool, Optional[Dict]]: (success, user_info)
        """
        config = self.get_config()
        if not config or not config.enabled:
            return False, None
            
        if not ldap3:
            logging.error("LDAP authentication failed: ldap3 library not available")
            return False, None
            
        try:
            conn_mgr = LDAPConnectionManager(config)
            
            # First, connect with service account to search for user
            with conn_mgr:
                user_dn = self._find_user_dn(conn_mgr.connection, username)
                if not user_dn:
                    logging.warning(f"User {username} not found in LDAP")
                    return False, None
                    
            # Now authenticate with user credentials
            user_conn_mgr = LDAPConnectionManager(config)
            if not user_conn_mgr.connect(bind_dn=user_dn, password=password):
                return False, None
                
            try:
                # Get user information
                with conn_mgr:
                    user_info = self._get_user_info(conn_mgr.connection, user_dn)
                    if user_info:
                        return True, user_info
            finally:
                user_conn_mgr.disconnect()
                
        except LDAPInvalidCredentialsError:
            logging.warning(f"Invalid credentials for user {username}")
        except LDAPException as e:
            logging.error(f"LDAP authentication error for user {username}: {e}")
        except Exception as e:
            logging.exception(f"Unexpected error during LDAP authentication for user {username}: {e}")
            
        return False, None
        
    def _find_user_dn(self, connection: Connection, username: str) -> Optional[str]:
        """Find user DN by username."""
        config = self.get_config()
        if not config:
            return None
            
        # If user DN template is provided, use it directly
        if config.user_dn_template:
            return config.user_dn_template.format(username=username)
            
        # Otherwise search for the user
        search_filter = config.search_filter
        if '{}' in search_filter:
            search_filter = search_filter.format(username)
        elif '{username}' in search_filter:
            search_filter = search_filter.format(username=username)
        else:
            # Default search filter
            username_attr = config.attr_mapping.get('username', 'uid')
            search_filter = f"({username_attr}={username})"
            
        try:
            connection.search(
                search_base=config.search_base,
                search_filter=search_filter,
                attributes=['dn']
            )
            
            if connection.entries:
                return str(connection.entries[0].entry_dn)
                
        except LDAPException as e:
            logging.error(f"Error searching for user {username}: {e}")
            
        return None
        
    def _get_user_info(self, connection: Connection, user_dn: str) -> Optional[Dict]:
        """Get user information from LDAP."""
        config = self.get_config()
        if not config:
            return None
            
        try:
            # Get all mapped attributes
            attrs = list(config.attr_mapping.values()) + ['dn', 'cn']
            
            connection.search(
                search_base=user_dn,
                search_filter='(objectClass=*)',
                search_scope='BASE',
                attributes=attrs
            )
            
            if not connection.entries:
                return None
                
            entry = connection.entries[0]
            user_info = {
                'dn': str(entry.entry_dn),
                'username': self._get_attr_value(entry, config.attr_mapping.get('username', 'uid')),
                'email': self._get_attr_value(entry, config.attr_mapping.get('email', 'mail')),
                'nickname': self._get_attr_value(entry, config.attr_mapping.get('nickname', 'displayName')),
                'first_name': self._get_attr_value(entry, config.attr_mapping.get('first_name', 'givenName')),
                'last_name': self._get_attr_value(entry, config.attr_mapping.get('last_name', 'sn')),
                'attributes': {}
            }
            
            # Store all attributes for debugging/reference
            for attr in entry.entry_attributes:
                user_info['attributes'][attr] = self._get_attr_value(entry, attr)
                
            return user_info
            
        except LDAPException as e:
            logging.error(f"Error getting user info for {user_dn}: {e}")
            return None
            
    def _get_attr_value(self, entry, attr_name: str) -> Optional[str]:
        """Get attribute value from LDAP entry."""
        if not hasattr(entry, attr_name):
            return None
            
        attr = getattr(entry, attr_name)
        if attr and attr.value:
            # Handle multi-value attributes
            if isinstance(attr.value, list):
                return attr.value[0] if attr.value else None
            return str(attr.value)
        return None


class LDAPSyncService:
    """Handles LDAP user synchronization."""
    
    def __init__(self):
        self.config = None
        
    def get_config(self):
        """Get active LDAP configuration."""
        if not self.config:
            self.config = LDAPConfigService.get_active_config()
        return self.config
        
    def sync_users(self) -> Tuple[bool, Dict[str, int]]:
        """
        Synchronize users from LDAP.
        
        Returns:
            Tuple[bool, Dict[str, int]]: (success, stats)
        """
        config = self.get_config()
        if not config or not config.enabled or not config.sync_enabled:
            return False, {}
            
        if not ldap3:
            logging.error("LDAP sync failed: ldap3 library not available")
            return False, {}
            
        stats = {
            'total_found': 0,
            'created': 0,
            'updated': 0,
            'deactivated': 0,
            'errors': 0
        }
        
        try:
            # Update sync status to running
            LDAPConfigService.update_sync_status(config.id, 'running')
            
            conn_mgr = LDAPConnectionManager(config)
            with conn_mgr:
                # Get all users from LDAP
                ldap_users = self._get_all_ldap_users(conn_mgr.connection)
                stats['total_found'] = len(ldap_users)
                
                active_dns = []
                
                for ldap_user_data in ldap_users:
                    try:
                        ldap_user, created = LDAPUserService.create_or_update_user(
                            config.id, ldap_user_data
                        )
                        
                        if ldap_user:
                            active_dns.append(ldap_user_data['dn'])
                            if created:
                                stats['created'] += 1
                                # Auto-create system user if enabled
                                if config.auto_create_user:
                                    self._create_system_user(ldap_user)
                            else:
                                stats['updated'] += 1
                        else:
                            stats['errors'] += 1
                            
                    except Exception as e:
                        logging.exception(f"Error processing LDAP user: {e}")
                        stats['errors'] += 1
                
                # Mark inactive users
                stats['deactivated'] = LDAPUserService.mark_stale_users(
                    config.id, active_dns
                )
                
            # Update sync status to completed
            LDAPConfigService.update_sync_status(
                config.id, 'completed', datetime.now()
            )
            
            logging.info(f"LDAP sync completed: {stats}")
            return True, stats
            
        except Exception as e:
            logging.exception(f"LDAP sync failed: {e}")
            LDAPConfigService.update_sync_status(config.id, 'error')
            return False, stats
            
    def _get_all_ldap_users(self, connection: Connection) -> List[Dict]:
        """Get all users from LDAP directory."""
        config = self.get_config()
        if not config:
            return []
            
        users = []
        try:
            # Get all mapped attributes
            attrs = list(config.attr_mapping.values()) + ['dn', 'cn']
            
            connection.search(
                search_base=config.search_base,
                search_filter=config.search_filter,
                attributes=attrs
            )
            
            for entry in connection.entries:
                user_data = {
                    'dn': str(entry.entry_dn),
                    'username': self._get_attr_value(entry, config.attr_mapping.get('username', 'uid')),
                    'email': self._get_attr_value(entry, config.attr_mapping.get('email', 'mail')),
                    'nickname': self._get_attr_value(entry, config.attr_mapping.get('nickname', 'displayName')),
                    'first_name': self._get_attr_value(entry, config.attr_mapping.get('first_name', 'givenName')),
                    'last_name': self._get_attr_value(entry, config.attr_mapping.get('last_name', 'sn')),
                    'is_active': True,
                    'attributes': {}
                }
                
                # Store all attributes
                for attr in entry.entry_attributes:
                    user_data['attributes'][attr] = self._get_attr_value(entry, attr)
                    
                users.append(user_data)
                
        except LDAPException as e:
            logging.error(f"Error getting LDAP users: {e}")
            
        return users
        
    def _get_attr_value(self, entry, attr_name: str) -> Optional[str]:
        """Get attribute value from LDAP entry."""
        if not hasattr(entry, attr_name):
            return None
            
        attr = getattr(entry, attr_name)
        if attr and attr.value:
            # Handle multi-value attributes
            if isinstance(attr.value, list):
                return attr.value[0] if attr.value else None
            return str(attr.value)
        return None
        
    def _create_system_user(self, ldap_user) -> bool:
        """Create system user from LDAP user data."""
        try:
            # Check if system user already exists
            if ldap_user.email:
                existing_users = UserService.query(email=ldap_user.email)
                if existing_users:
                    # Link LDAP user to existing system user
                    LDAPUserService.model.update(
                        user_id=existing_users[0].id
                    ).where(
                        LDAPUserService.model.id == ldap_user.id
                    ).execute()
                    return True
                    
            # Create new system user
            user_data = {
                'id': get_uuid(),
                'email': ldap_user.email or f"{ldap_user.ldap_username}@ldap.local",
                'nickname': ldap_user.nickname or ldap_user.ldap_username,
                'password': '',  # No password for LDAP users
                'login_channel': 'ldap',
                'last_login_time': get_format_time(),
                'is_superuser': False,
                'status': '1'
            }
            
            system_user = UserService.save(**user_data)
            if system_user:
                # Link LDAP user to system user
                LDAPUserService.model.update(
                    user_id=system_user.id
                ).where(
                    LDAPUserService.model.id == ldap_user.id
                ).execute()
                return True
                
        except Exception as e:
            logging.exception(f"Failed to create system user for LDAP user {ldap_user.id}: {e}")
            
        return False