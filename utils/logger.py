# -*- coding: utf-8 -*-
"""
12306 Ticket Bot - 日志工具（脱敏版）
日志管理器

功能：
- 敏感信息脱敏
- 多处理器输出
- 日志轮转

作者: OpenClaw
版本: v2.0
"""

import os
import sys
import re
import logging
import logging.handlers
from pathlib import Path
from typing import Optional, Dict, Any, List


class SensitiveFilter(logging.Filter):
    """敏感信息过滤"""
    
    # 敏感信息模式
    PATTERNS = [
        # Cookie
        (r'(cookie[s]?[=:]\s*)[^\s,;]+', r'\1***'),
        # Token
        (r'(token[s]?[=:]\s*)[^\s,;]+', r'\1***'),
        # 密码
        (r'(password[s]?[=:]\s*)[^\s,;]+', r'\1***'),
        # 手机号
        (r'(1[3-9]\d{9})', r'***\1[-4:]'),
        # 身份证号
        (r'([1-9]\d{5}(?:18|19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[0-9Xx])', r'***\1[-4:]'),
        # 银行卡号
        (r'([1-9]\d{15,18})', r'***\1[-4:]'),
        # 邮箱
        (r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', r'***\1'),
    ]
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        过滤日志记录
        
        Args:
            record: 日志记录
            
        Returns:
            是否保留
        """
        # 脱敏消息
        record.msg = self._desensitize(str(record.msg))
        
        # 脱敏参数
        if record.args:
            record.args = tuple(
                self._desensitize(str(arg))
                for arg in record.args
            )
        
        return True
    
    def _desensitize(self, text: str) -> str:
        """
        脱敏处理
        
        Args:
            text: 原始文本
            
        Returns:
            脱敏后的文本
        """
        result = text
        
        for pattern, replacement in self.PATTERNS:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        
        return result


class LoggerManager:
    """日志管理器"""
    
    def __init__(self, 
                 name: str = '12306_bot',
                 log_file: str = 'logs/app.log',
                 level: str = 'INFO',
                 max_size: int = 10 * 1024 * 1024,  # 10MB
                 backup_count: int = 5,
                 enable_console: bool = True,
                 desensitize: bool = True):
        """
        初始化日志管理器
        
        Args:
            name: 日志名称
            log_file: 日志文件路径
            level: 日志级别
            max_size: 单个日志文件最大大小
            backup_count: 保留的日志文件数量
            enable_console: 是否输出到控制台
            desensitize: 是否脱敏
        """
        self.logger = logging.getLogger(name)
        self.log_file = log_file
        self.desensitize = desensitize
        
        # 设置日志级别
        log_level = getattr(logging, level.upper(), logging.INFO)
        self.logger.setLevel(log_level)
        
        # 清除现有处理器
        self.logger.handlers.clear()
        
        # 创建目录
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 文件处理器（带轮转）
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(log_level)
        
        # 格式化
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        
        # 添加敏感信息过滤
        if desensitize:
            file_handler.addFilter(SensitiveFilter())
        
        self.logger.addHandler(file_handler)
        
        # 控制台处理器
        if enable_console:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(log_level)
            console_handler.setFormatter(formatter)
            
            if desensitize:
                console_handler.addFilter(SensitiveFilter())
            
            self.logger.addHandler(console_handler)
    
    def get_logger(self) -> logging.Logger:
        """获取日志记录器"""
        return self.logger
    
    def log_request(self, method: str, url: str, data: Dict = None, 
                    response: Any = None, level: str = 'debug'):
        """
        记录请求日志
        
        Args:
            method: 请求方法
            url: 请求 URL
            data: 请求数据
            response: 响应
            level: 日志级别
        """
        log_data = {
            'method': method,
            'url': url,
            'data': self._safe_data(data),
            'response': self._safe_data(response),
        }
        
        log_msg = f"[HTTP] {method} {url}"
        
        if level == 'debug':
            self.logger.debug(log_msg, extra={'data': log_data})
        elif level == 'info':
            self.logger.info(log_msg, extra={'data': log_data})
        elif level == 'warning':
            self.logger.warning(log_msg, extra={'data': log_data})
        elif level == 'error':
            self.logger.error(log_msg, extra={'data': log_data})
    
    def _safe_data(self, data: Any) -> Any:
        """
        安全数据处理
        
        Args:
            data: 原始数据
            
        Returns:
            脱敏后的数据
        """
        if data is None:
            return None
        
        if isinstance(data, dict):
            return {k: self._safe_data(v) for k, v in data.items()}
        
        if isinstance(data, (list, tuple)):
            return [self._safe_data(item) for item in data]
        
        return data


def setup_logger(name: str = '12306_bot',
                 log_file: str = 'logs/app.log',
                 level: str = 'INFO',
                 desensitize: bool = True) -> logging.Logger:
    """
    快速设置日志
    
    Args:
        name: 日志名称
        log_file: 日志文件
        level: 日志级别
        desensitize: 是否脱敏
        
    Returns:
        日志记录器
    """
    manager = LoggerManager(
        name=name,
        log_file=log_file,
        level=level,
        desensitize=desensitize
    )
    
    return manager.get_logger()


if __name__ == '__main__':
    # 测试日志
    print("=== 日志工具测试 ===")
    
    # 初始化日志
    logger = setup_logger(
        name='test_bot',
        log_file='logs/test_app.log',
        level='DEBUG',
        desensitize=True
    )
    
    # 测试日志
    logger.info("测试日志")
    logger.debug("调试信息")
    
    # 测试敏感信息脱敏
    logger.info(f"Cookie: cookie=test_cookie; token=secret_token_12345")
    logger.info(f"手机号: 13800138000")
    logger.info(f"身份证: 110101199001011234")
    
    print("\n日志已保存到 logs/test_app.log")
