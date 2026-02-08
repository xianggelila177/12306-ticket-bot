# -*- coding: utf-8 -*-
"""
风控检测模块 - 风控检测与自适应间隔
"""

import time
import random
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from utils.logger import get_logger

logger = get_logger("risk_controller")


@dataclass
class RiskState:
    """风控状态"""
    is_banned: bool = False              # 是否被封禁
    consecutive_failures: int = 0        # 连续失败次数
    current_interval: float = 5.0        # 当前查询间隔
    last_request_time: float = 0         # 上次请求时间
    daily_request_count: int = 0         # 今日请求次数
    last_reset_date: str = ""            # 上次重置日期
    
    # 封禁检测
    ban_detected_at: Optional[datetime] = None
    ban_release_time: Optional[datetime] = None


class RiskController:
    """
    风控控制器
    
    功能：
    - 频率控制
    - 封禁检测
    - 自适应间隔调整
    - 请求限流
    """
    
    def __init__(self, config: Dict = None):
        """
        初始化风控控制器
        
        Args:
            config: 风控配置
        """
        if config is None:
            config = {
                'min_query_interval': 5,     # 最小间隔 5 秒
                'max_query_interval': 15,    # 最大间隔 15 秒
                'daily_limit': 1000,         # 每日请求限制
                'failure_threshold': 5,       # 失败次数阈值
                'ban_threshold': 10,         # 封禁检测阈值
            }
        
        self.min_interval = config.get('min_query_interval', 5)
        self.max_interval = config.get('max_query_interval', 15)
        self.daily_limit = config.get('daily_limit', 1000)
        self.failure_threshold = config.get('failure_threshold', 5)
        self.ban_threshold = config.get('ban_threshold', 10)
        
        self.state = RiskState()
        self.state.current_interval = self.min_interval
        
        logger.info(f"风控控制器已启动: 间隔 [{self.min_interval}-{self.max_interval}] 秒")
    
    def get_interval(self) -> float:
        """
        获取当前请求间隔
        
        Returns:
            请求间隔时间（秒）
        """
        # 检查是否需要重置每日计数
        today = datetime.now().strftime('%Y-%m-%d')
        if self.state.last_reset_date != today:
            self.state.daily_request_count = 0
            self.state.last_reset_date = today
        
        # 检查是否在封禁期
        if self.state.is_banned:
            if self.state.ban_release_time and datetime.now() >= self.state.ban_release_time:
                self.state.is_banned = False
                logger.info("封禁已解除")
            else:
                remaining = (self.state.ban_release_time - datetime.now()).total_seconds()
                logger.warning(f"仍在封禁期，剩余 {remaining:.0f} 秒")
                return remaining
        
        return self.state.current_interval
    
    def wait_interval(self):
        """等待请求间隔"""
        interval = self.get_interval()
        
        # 添加随机抖动（±20%）
        jitter = interval * random.uniform(-0.2, 0.2)
        actual_wait = max(1, interval + jitter)
        
        logger.debug(f"等待 {actual_wait:.2f} 秒")
        time.sleep(actual_wait)
        
        self.state.last_request_time = time.time()
    
    def on_rate_limit(self, response_data: Dict = None):
        """
        触发限流响应
        
        Args:
            response_data: 响应数据
        """
        self.state.consecutive_failures += 1
        
        # 增加间隔
        self.state.current_interval = min(
            self.max_interval,
            self.state.current_interval * 1.5
        )
        
        logger.warning(
            f"触发限流，连续失败: {self.state.consecutive_failures}, "
            f"间隔调整为: {self.state.current_interval:.2f}秒"
        )
    
    def on_success(self):
        """成功响应处理"""
        if self.state.consecutive_failures > 0:
            # 成功一次，减少失败计数
            self.state.consecutive_failures = max(
                0,
                self.state.consecutive_failures - 1
            )
        
        # 尝试减小间隔
        if self.state.consecutive_failures == 0:
            self.state.current_interval = max(
                self.min_interval,
                self.state.current_interval * 0.9
            )
        
        # 重置为正常状态
        self.state.is_banned = False
        self.state.ban_detected_at = None
        self.state.ban_release_time = None
        
        self.state.daily_request_count += 1
    
    def on_failure(self, error_type: str = "unknown", response_data: Dict = None):
        """
        失败响应处理
        
        Args:
            error_type: 错误类型
            response_data: 响应数据
        """
        self.state.consecutive_failures += 1
        self.state.daily_request_count += 1
        
        # 检查是否触发限流
        if self.state.consecutive_failures >= self.failure_threshold:
            self.on_rate_limit(response_data)
        
        # 检查是否被封禁
        if self._detect_ban(response_data):
            self._handle_ban()
        
        logger.warning(
            f"请求失败: {error_type}, "
            f"连续失败: {self.state.consecutive_failures}, "
            f"今日请求: {self.state.daily_request_count}/{self.daily_limit}"
        )
    
    def _detect_ban(self, response_data: Dict = None) -> bool:
        """
        检测是否被封禁
        
        Args:
            response_data: 响应数据
        
        Returns:
            是否被封禁
        """
        if response_data is None:
            return False
        
        # 检查响应中的封禁标识
        ban_indicators = [
            'captcha login out',
            '登录超时',
            '用户已被锁定',
            '网络繁忙',
            '服务不可用',
            '系统繁忙',
            '操作失败',
        ]
        
        messages = response_data.get('messages', [])
        data_messages = response_data.get('data', {}).get('msg', [])
        
        all_messages = messages + data_messages
        
        for indicator in ban_indicators:
            for msg in all_messages:
                if indicator in msg:
                    return True
        
        # 检查 HTTP 状态码
        if response_data.get('httpstatus') in [403, 429, 503]:
            return True
        
        return False
    
    def _handle_ban(self):
        """处理封禁"""
        self.state.is_banned = True
        self.state.ban_detected_at = datetime.now()
        
        # 封禁时间递增
        ban_minutes = min(30, 2 ** (self.state.consecutive_failures - self.failure_threshold))
        self.state.ban_release_time = datetime.now() + timedelta(minutes=ban_minutes)
        
        logger.error(
            f"检测到封禁！解除时间: {self.state.ban_release_time.strftime('%H:%M:%S')}"
        )
    
    def check_daily_limit(self) -> bool:
        """
        检查是否达到每日请求限制
        
        Returns:
            是否超过限制
        """
        if self.state.daily_request_count >= self.daily_limit:
            logger.error(f"达到每日请求限制: {self.daily_limit}")
            return True
        return False
    
    def should_stop(self) -> bool:
        """
        检查是否应该停止请求
        
        Returns:
            是否应该停止
        """
        # 检查封禁状态
        if self.state.is_banned:
            return True
        
        # 检查每日限制
        if self.check_daily_limit():
            return True
        
        return False
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取风控状态
        
        Returns:
            状态信息字典
        """
        return {
            'is_banned': self.state.is_banned,
            'consecutive_failures': self.state.consecutive_failures,
            'current_interval': self.state.current_interval,
            'daily_request_count': self.state.daily_request_count,
            'daily_limit': self.daily_limit,
            'remaining_requests': max(0, self.daily_limit - self.state.daily_request_count),
            'ban_release_time': self.state.ban_release_time.isoformat() if self.state.ban_release_time else None,
        }
    
    def reset(self):
        """重置风控状态"""
        self.state = RiskState()
        self.state.current_interval = self.min_interval
        logger.info("风控状态已重置")
    
    def get_adaptive_interval(self) -> float:
        """
        获取自适应间隔
        
        基于连续失败次数和成功率动态调整
        
        Returns:
            推荐间隔时间
        """
        if self.state.consecutive_failures == 0:
            return self.min_interval
        elif self.state.consecutive_failures < 3:
            return self.min_interval * 1.2
        elif self.state.consecutive_failures < 5:
            return self.min_interval * 1.5
        else:
            return min(
                self.max_interval,
                self.min_interval * (2 ** (self.state.consecutive_failures - 3))
            )
