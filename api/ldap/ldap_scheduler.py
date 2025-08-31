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
import asyncio
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Optional

from api.db.services.ldap_service import LDAPConfigService
from api.ldap.ldap_auth import LDAPSyncService


class LDAPScheduler:
    """LDAP用户同步调度器，支持30秒自动同步"""
    
    def __init__(self):
        self.running = False
        self.thread = None
        self.sync_service = LDAPSyncService()
        self.last_sync_time = {}  # config_id -> last_sync_time
        
    def start(self):
        """启动调度器"""
        if self.running:
            logging.warning("LDAP scheduler is already running")
            return
            
        self.running = True
        self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.thread.start()
        logging.info("LDAP scheduler started")
        
    def stop(self):
        """停止调度器"""
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
        logging.info("LDAP scheduler stopped")
        
    def _run_scheduler(self):
        """运行调度器主循环"""
        while self.running:
            try:
                self._check_and_sync()
                time.sleep(10)  # 每10秒检查一次
            except Exception as e:
                logging.exception(f"Error in LDAP scheduler: {e}")
                time.sleep(30)  # 出错时等待30秒后重试
                
    def _check_and_sync(self):
        """检查并执行同步"""
        try:
            # 获取所有启用的LDAP配置
            config = LDAPConfigService.get_active_config()
            if not config or not config.enabled or not config.sync_enabled:
                return
                
            # 检查是否需要同步
            now = datetime.now()
            last_sync = self.last_sync_time.get(config.id)
            
            # 计算同步间隔
            sync_interval = max(config.sync_interval, 30)  # 最小30秒
            
            if (not last_sync or 
                (now - last_sync).total_seconds() >= sync_interval):
                
                logging.info(f"Starting LDAP sync for config {config.id}")
                
                # 更新同步状态
                self.last_sync_time[config.id] = now
                
                # 执行同步
                success, stats = self.sync_service.sync_users()
                
                if success:
                    logging.info(f"LDAP sync completed successfully: {stats}")
                else:
                    logging.error(f"LDAP sync failed: {stats}")
                    
        except Exception as e:
            logging.exception(f"Error during LDAP sync check: {e}")
            
    def force_sync(self) -> bool:
        """强制执行一次同步"""
        try:
            success, stats = self.sync_service.sync_users()
            if success:
                logging.info(f"Forced LDAP sync completed: {stats}")
                # 更新最后同步时间
                config = LDAPConfigService.get_active_config()
                if config:
                    self.last_sync_time[config.id] = datetime.now()
            return success
        except Exception as e:
            logging.exception(f"Error during forced LDAP sync: {e}")
            return False


# 全局调度器实例
ldap_scheduler = LDAPScheduler()


def start_ldap_scheduler():
    """启动LDAP调度器"""
    ldap_scheduler.start()
    

def stop_ldap_scheduler():
    """停止LDAP调度器"""
    ldap_scheduler.stop()
    

def force_ldap_sync():
    """强制执行LDAP同步"""
    return ldap_scheduler.force_sync()


class LDAPBackgroundTask:
    """LDAP后台任务管理器，与现有的task_executor集成"""
    
    @staticmethod
    def init_ldap_scheduler():
        """在应用启动时初始化LDAP调度器"""
        try:
            # 检查是否有启用的LDAP配置
            config = LDAPConfigService.get_active_config()
            if config and config.enabled and config.sync_enabled:
                start_ldap_scheduler()
                logging.info("LDAP scheduler initialized and started")
            else:
                logging.info("LDAP sync disabled, scheduler not started")
        except Exception as e:
            logging.exception(f"Failed to initialize LDAP scheduler: {e}")
            
    @staticmethod
    def shutdown_ldap_scheduler():
        """在应用关闭时停止LDAP调度器"""
        try:
            stop_ldap_scheduler()
            logging.info("LDAP scheduler shutdown completed")
        except Exception as e:
            logging.exception(f"Error during LDAP scheduler shutdown: {e}")


# 异步版本的调度器
class AsyncLDAPScheduler:
    """异步LDAP调度器"""
    
    def __init__(self):
        self.running = False
        self.task = None
        self.sync_service = LDAPSyncService()
        self.last_sync_time = {}
        
    async def start(self):
        """启动异步调度器"""
        if self.running:
            return
            
        self.running = True
        self.task = asyncio.create_task(self._run_scheduler())
        logging.info("Async LDAP scheduler started")
        
    async def stop(self):
        """停止异步调度器"""
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logging.info("Async LDAP scheduler stopped")
        
    async def _run_scheduler(self):
        """运行异步调度器主循环"""
        while self.running:
            try:
                await self._check_and_sync()
                await asyncio.sleep(10)  # 每10秒检查一次
            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.exception(f"Error in async LDAP scheduler: {e}")
                await asyncio.sleep(30)
                
    async def _check_and_sync(self):
        """异步检查并执行同步"""
        try:
            config = LDAPConfigService.get_active_config()
            if not config or not config.enabled or not config.sync_enabled:
                return
                
            now = datetime.now()
            last_sync = self.last_sync_time.get(config.id)
            sync_interval = max(config.sync_interval, 30)
            
            if (not last_sync or 
                (now - last_sync).total_seconds() >= sync_interval):
                
                logging.info(f"Starting async LDAP sync for config {config.id}")
                self.last_sync_time[config.id] = now
                
                # 在线程池中运行同步操作
                loop = asyncio.get_event_loop()
                success, stats = await loop.run_in_executor(
                    None, self.sync_service.sync_users
                )
                
                if success:
                    logging.info(f"Async LDAP sync completed: {stats}")
                else:
                    logging.error(f"Async LDAP sync failed: {stats}")
                    
        except Exception as e:
            logging.exception(f"Error during async LDAP sync: {e}")


# 全局异步调度器实例  
async_ldap_scheduler = AsyncLDAPScheduler()