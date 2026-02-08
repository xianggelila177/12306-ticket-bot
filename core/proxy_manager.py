# -*- coding: utf-8 -*-
"""
代理池管理模块 - 代理 IP 管理
"""

import random
import time
import requests
from typing import Optional, Dict, List
from dataclasses import dataclass
from datetime import datetime, timedelta

from utils.logger import get_logger

logger = get_logger("proxy_manager")


@dataclass
class Proxy:
    """代理信息"""
    host: str
    port: int
    protocol: str = "http"
    username: str = None
    password: str = None
    last_checked: datetime = None
    is_available: bool = True
    success_count: int = 0
    failure_count: int = 0
    
    @property
    def url(self) -> str:
        """生成代理 URL"""
        if self.username and self.password:
            return f"{self.protocol}://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"{self.protocol}://{self.host}:{self.port}"


class ProxyManager:
    """
    代理池管理器
    
    功能：
    - 代理池维护
    - 健康检查
    - 负载均衡
    - 故障转移
    """
    
    def __init__(self, config: Dict = None):
        """
        初始化代理管理器
        
        Args:
            config: 代理配置
        """
        if config is None:
            config = {
                'enabled': False,
                'proxies': [],
                'check_interval': 300,      # 检查间隔 5 分钟
                'min_available': 1,          # 最少可用代理数
                'failure_threshold': 3,      # 失败阈值
            }
        
        self.enabled = config.get('enabled', False)
        self.check_interval = config.get('check_interval', 300)
        self.min_available = config.get('min_available', 1)
        self.failure_threshold = config.get('failure_threshold', 3)
        
        # 初始化代理池
        self.proxies: List[Proxy] = []
        for p in config.get('proxies', []):
            self.proxies.append(Proxy(
                host=p.get('host'),
                port=p.get('port'),
                protocol=p.get('protocol', 'http'),
                username=p.get('username'),
                password=p.get('password'),
            ))
        
        # 当前使用的代理
        self.current_proxy: Optional[Proxy] = None
        
        # 上次检查时间
        self.last_check_time = None
        
        logger.info(f"代理池初始化完成: {len(self.proxies)} 个代理")
    
    def get_proxy(self) -> Optional[Dict[str, str]]:
        """
        获取可用代理
        
        Returns:
            代理配置字典 {host, port, protocol}
        """
        if not self.enabled:
            return None
        
        # 筛选可用代理
        available = [p for p in self.proxies if p.is_available]
        
        if not available:
            logger.warning("无可用代理，尝试恢复所有代理")
            self._recover_all()
            available = self.proxies
        
        if not available:
            logger.error("代理池无可用代理")
            return None
        
        # 负载均衡：随机选择
        proxy = random.choice(available)
        self.current_proxy = proxy
        
        logger.debug(f"选择代理: {proxy.host}:{proxy.port}")
        return {
            'http': proxy.url,
            'https': proxy.url,
        }
    
    def release_proxy(self, success: bool = True):
        """
        释放当前代理
        
        Args:
            success: 请求是否成功
        """
        if self.current_proxy:
            self.current_proxy.last_checked = datetime.now()
            
            if success:
                self.current_proxy.success_count += 1
            else:
                self.current_proxy.failure_count += 1
                
                # 连续失败达到阈值，标记为不可用
                if self.current_proxy.failure_count >= self.failure_threshold:
                    self.current_proxy.is_available = False
                    logger.warning(
                        f"代理 {self.current_proxy.host}:{self.current_proxy.port} "
                        f"连续 {self.failure_threshold} 次失败，标记为不可用"
                    )
            
            self.current_proxy = None
    
    def check_proxy_health(self, proxy: Proxy, timeout: int = 10) -> bool:
        """
        检查代理健康状态
        
        Args:
            proxy: 代理信息
            timeout: 超时时间
        
        Returns:
            是否可用
        """
        try:
            response = requests.get(
                "https://kyfw.12306.cn/",
                proxies={
                    'http': proxy.url,
                    'https': proxy.url,
                },
                timeout=timeout
            )
            
            if response.status_code == 200:
                return True
            return False
        
        except Exception as e:
            logger.debug(f"代理健康检查失败: {proxy.host}:{proxy.port} - {e}")
            return False
    
    def health_check(self) -> Dict[str, int]:
        """
        执行健康检查
        
        Returns:
            检查结果统计
        """
        results = {'available': 0, 'unavailable': 0}
        
        for proxy in self.proxies:
            if self.check_proxy_health(proxy):
                proxy.is_available = True
                results['available'] += 1
            else:
                proxy.is_available = False
                results['unavailable'] += 1
        
        logger.info(f"健康检查完成: 可用 {results['available']}, 不可用 {results['unavailable']}")
        self.last_check_time = datetime.now()
        
        return results
    
    def _recover_all(self):
        """恢复所有代理为可用状态"""
        for proxy in self.proxies:
            proxy.is_available = True
            proxy.failure_count = 0
        logger.info("已恢复所有代理")
    
    def add_proxy(self, host: str, port: int, protocol: str = "http",
                  username: str = None, password: str = None):
        """
        添加代理
        
        Args:
            host: 代理主机
            port: 代理端口
            protocol: 协议类型
            username: 用户名
            password: 密码
        """
        # 检查是否已存在
        for p in self.proxies:
            if p.host == host and p.port == port:
                logger.warning(f"代理已存在: {host}:{port}")
                return
        
        self.proxies.append(Proxy(
            host=host,
            port=port,
            protocol=protocol,
            username=username,
            password=password,
        ))
        logger.info(f"添加代理: {host}:{port}")
    
    def remove_proxy(self, host: str, port: int):
        """
        移除代理
        
        Args:
            host: 代理主机
            port: 代理端口
        """
        self.proxies = [
            p for p in self.proxies
            if not (p.host == host and p.port == port)
        ]
        logger.info(f"移除代理: {host}:{port}")
    
    def get_stats(self) -> Dict[str, any]:
        """
        获取代理池统计
        
        Returns:
            统计信息
        """
        available = sum(1 for p in self.proxies if p.is_available)
        total = len(self.proxies)
        
        return {
            'total_proxies': total,
            'available_proxies': available,
            'unavailable_proxies': total - available,
            'enabled': self.enabled,
            'current_proxy': {
                'host': self.current_proxy.host,
                'port': self.current_proxy.port,
            } if self.current_proxy else None,
            'last_check_time': self.last_check_time.isoformat() if self.last_check_time else None,
        }
    
    def auto_rotate(self) -> Optional[Dict[str, str]]:
        """
        自动轮换代理
        
        Returns:
            新的代理配置
        """
        if not self.enabled:
            return None
        
        # 检查是否需要健康检查
        if self.last_check_time is None or \
           (datetime.now() - self.last_check_time).seconds > self.check_interval:
            self.health_check()
        
        return self.get_proxy()


class DirectConnection:
    """
    直连连接（不使用代理）
    """
    
    def __init__(self):
        """初始化直连连接"""
        pass
    
    def get_session_config(self) -> Dict:
        """
        获取连接配置
        
        Returns:
            空配置（直连）
        """
        return {}
    
    def release(self, success: bool = True):
        """释放连接"""
        pass


def create_proxy_manager(config: Dict) -> ProxyManager:
    """
    创建代理管理器
    
    Args:
        config: 代理配置
    
    Returns:
        ProxyManager 实例
    """
    return ProxyManager(config)
