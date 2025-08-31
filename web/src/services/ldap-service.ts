import { request } from '@umijs/max';
import { message } from 'antd';

export interface LDAPConfig {
  id?: string;
  name: string;
  server_host: string;
  server_port: number;
  use_ssl: boolean;
  bind_dn?: string;
  bind_password?: string;
  search_base: string;
  search_filter: string;
  user_dn_template?: string;
  attr_mapping: {
    username: string;
    email: string;
    nickname: string;
    first_name: string;
    last_name: string;
  };
  enabled: boolean;
  auto_create_user: boolean;
  sync_enabled: boolean;
  sync_interval: number;
  last_sync_time?: string;
  sync_status?: string;
}

export interface LDAPUser {
  id: string;
  ldap_config_id: string;
  user_id?: string;
  ldap_dn: string;
  ldap_username: string;
  email?: string;
  nickname?: string;
  first_name?: string;
  last_name?: string;
  ldap_attributes: Record<string, any>;
  is_active: boolean;
  last_login_time?: string;
  last_sync_time?: string;
  sync_status: string;
  system_user?: {
    id: string;
    email: string;
    nickname: string;
    status: string;
  };
}

export interface LDAPStatus {
  configured: boolean;
  enabled: boolean;
  sync_enabled: boolean;
  sync_interval: number;
  last_sync_time?: string;
  sync_status: string;
  ldap3_available: boolean;
  user_stats?: {
    total_users: number;
    active_users: number;
    inactive_users: number;
  };
}

export interface LDAPSyncStats {
  total_found: number;
  created: number;
  updated: number;
  deactivated: number;
  errors: number;
}

class LDAPService {
  // Get LDAP configuration
  async getConfig(): Promise<{ data: LDAPConfig | null; code: number; message: string }> {
    return request('/api/v1/ldap/config', {
      method: 'GET',
    });
  }

  // Create or update LDAP configuration
  async saveConfig(config: Partial<LDAPConfig>): Promise<{ data: any; code: number; message: string }> {
    return request('/api/v1/ldap/config', {
      method: 'POST',
      data: config,
    });
  }

  // Test LDAP connection
  async testConnection(): Promise<{ data: boolean; code: number; message: string }> {
    return request('/api/v1/ldap/config/test', {
      method: 'POST',
    });
  }

  // Get LDAP service status
  async getStatus(): Promise<{ data: LDAPStatus; code: number; message: string }> {
    return request('/api/v1/ldap/status', {
      method: 'GET',
    });
  }

  // Force sync LDAP users
  async forceSync(): Promise<{ data: boolean; code: number; message: string }> {
    return request('/api/v1/ldap/sync', {
      method: 'POST',
    });
  }

  // Get LDAP users
  async getUsers(activeOnly: boolean = true): Promise<{ data: LDAPUser[]; code: number; message: string }> {
    return request('/api/v1/ldap/users', {
      method: 'GET',
      params: { active_only: activeOnly },
    });
  }

  // Update user status
  async updateUserStatus(userId: string, isActive: boolean): Promise<{ data: boolean; code: number; message: string }> {
    return request(`/api/v1/ldap/users/${userId}/status`, {
      method: 'PUT',
      data: { is_active: isActive },
    });
  }

  // LDAP login
  async ldapLogin(username: string, password: string): Promise<any> {
    return request('/api/v1/ldap/login', {
      method: 'POST',
      data: { username, password },
    });
  }
}

export default new LDAPService();