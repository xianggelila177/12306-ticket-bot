# -*- coding: utf-8 -*-
"""
多渠道通知模块 - 支持多种通知方式
"""

import json
import requests
from typing import Optional, Dict, Any, List
from abc import ABC, abstractmethod

from utils.logger import get_logger

logger = get_logger("notification")


class BaseNotifier(ABC):
    """通知器基类"""
    
    @abstractmethod
    def send(self, title: str, content: str, **kwargs) -> bool:
        """
        发送通知
        
        Args:
            title: 标题
            content: 内容
        
        Returns:
            是否发送成功
        """
        pass


class PushPlusNotifier(BaseNotifier):
    """
    PushPlus 通知器
    
    使用说明：
    1. 访问 https://www.pushplus.plus 注册账号
    2. 获取 token
    3. 配置 channel（可选，默认为 wechat）
    """
    
    API_URL = "https://www.pushplus.plus/api/send"
    
    def __init__(self, token: str, channel: str = "wechat", topic: str = None):
        """
        初始化 PushPlus 通知器
        
        Args:
            token: PushPlus Token
            channel: 发送渠道 (wechat, email, webhook 等)
            topic: 群组编码（可选）
        """
        self.token = token
        self.channel = channel
        self.topic = topic
    
    def send(self, title: str, content: str, **kwargs) -> bool:
        """
        发送 PushPlus 通知
        
        Args:
            title: 标题
            content: 内容
            **kwargs: 其他参数
        
        Returns:
            是否发送成功
        """
        try:
            data = {
                'token': self.token,
                'title': title,
                'content': content,
                'channel': self.channel,
            }
            
            if self.topic:
                data['topic'] = self.topic
            
            # 支持 HTML 格式
            if kwargs.get('html', False):
                data['contentType'] = "text/html"
            
            response = requests.post(
                self.API_URL,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('code') == 200:
                    logger.info("PushPlus 通知发送成功")
                    return True
                else:
                    logger.error(f"PushPlus 发送失败: {result.get('msg')}")
                    return False
            else:
                logger.error(f"PushPlus 请求失败: {response.status_code}")
                return False
        
        except Exception as e:
            logger.error(f"PushPlus 通知异常: {e}")
            return False


class TelegramNotifier(BaseNotifier):
    """
    Telegram 通知器
    
    使用说明：
    1. 创建 Telegram Bot（@BotFather）
    2. 获取 Bot Token
    3. 获取 Chat ID
    """
    
    def __init__(self, bot_token: str, chat_id: str):
        """
        初始化 Telegram 通知器
        
        Args:
            bot_token: Bot Token
            chat_id: Chat ID
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    def send(self, title: str, content: str, **kwargs) -> bool:
        """
        发送 Telegram 通知
        
        Args:
            title: 标题（作为消息的一部分）
            content: 内容
            **kwargs: 其他参数
        
        Returns:
            是否发送成功
        """
        try:
            message = f"*{title}*\n\n{content}"
            
            data = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': 'Markdown',
            }
            
            # 支持 MarkdownV2
            if kwargs.get('markdown_v2', False):
                data['parse_mode'] = 'MarkdownV2'
            
            response = requests.post(
                self.api_url,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info("Telegram 通知发送成功")
                return True
            else:
                logger.error(f"Telegram 发送失败: {response.text}")
                return False
        
        except Exception as e:
            logger.error(f"Telegram 通知异常: {e}")
            return False


class EmailNotifier(BaseNotifier):
    """
    邮件通知器
    
    使用说明：
    - 支持 SMTP 发送邮件
    - 需要配置 SMTP 服务器信息
    """
    
    def __init__(
        self,
        smtp_server: str,
        smtp_port: int,
        sender_email: str,
        sender_password: str,
        receiver_email: str
    ):
        """
        初始化邮件通知器
        
        Args:
            smtp_server: SMTP 服务器
            smtp_port: SMTP 端口
            sender_email: 发件人邮箱
            sender_password: 发件人密码/授权码
            receiver_email: 收件人邮箱
        """
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender_email = sender_email
        self.sender_password = sender_password
        self.receiver_email = receiver_email
    
    def send(self, title: str, content: str, **kwargs) -> bool:
        """
        发送邮件通知
        
        Args:
            title: 邮件标题
            content: 邮件内容
            **kwargs: 其他参数
        
        Returns:
            是否发送成功
        """
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            # 构建邮件
            msg = MIMEMultipart('alternative')
            msg['Subject'] = title
            msg['From'] = self.sender_email
            msg['To'] = self.receiver_email
            
            # 添加 HTML 内容
            html_content = f"<html><body>{content}</body></html>"
            msg.attach(MIMEText(html_content, 'html', 'utf-8'))
            
            # 发送邮件
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
            
            logger.info("邮件发送成功")
            return True
        
        except Exception as e:
            logger.error(f"邮件发送异常: {e}")
            return False


class WebhookNotifier(BaseNotifier):
    """
    Webhook 通知器
    
    支持自定义 Webhook 回调
    """
    
    def __init__(self, webhook_url: str, headers: Dict = None):
        """
        初始化 Webhook 通知器
        
        Args:
            webhook_url: Webhook 地址
            headers: 请求头（可选）
        """
        self.webhook_url = webhook_url
        self.headers = headers or {}
    
    def send(self, title: str, content: str, **kwargs) -> bool:
        """
        发送 Webhook 通知
        
        Args:
            title: 标题
            content: 内容
            **kwargs: 其他参数
        
        Returns:
            是否发送成功
        """
        try:
            data = {
                'title': title,
                'content': content,
                'timestamp': kwargs.get('timestamp', ''),
                'type': kwargs.get('type', 'notification'),
            }
            
            # 添加额外数据
            if 'extra' in kwargs:
                data.update(kwargs['extra'])
            
            headers = {'Content-Type': 'application/json'}
            headers.update(self.headers)
            
            response = requests.post(
                self.webhook_url,
                json=data,
                headers=headers,
                timeout=30
            )
            
            if response.status_code in [200, 201, 204]:
                logger.info("Webhook 通知发送成功")
                return True
            else:
                logger.error(f"Webhook 发送失败: {response.status_code}")
                return False
        
        except Exception as e:
            logger.error(f"Webhook 通知异常: {e}")
            return False


class NotificationManager:
    """
    通知管理器
    
    功能：
    - 统一管理多种通知渠道
    - 支持通知模板
    - 失败重试
    """
    
    def __init__(self):
        """初始化通知管理器"""
        self.notifiers: List[BaseNotifier] = []
    
    def add_notifier(self, notifier: BaseNotifier):
        """
        添加通知器
        
        Args:
            notifier: 通知器实例
        """
        self.notifiers.append(notifier)
    
    def send_all(self, title: str, content: str, **kwargs) -> Dict[str, bool]:
        """
        发送通知到所有渠道
        
        Args:
            title: 标题
            content: 内容
            **kwargs: 其他参数
        
        Returns:
            各渠道发送结果
        """
        results = {}
        
        for notifier in self.notifiers:
            try:
                success = notifier.send(title, content, **kwargs)
                results[type(notifier).__name__] = success
            except Exception as e:
                logger.error(f"通知发送异常: {e}")
                results[type(notifier).__name__] = False
        
        return results
    
    def send_ticket_notification(
        self,
        train_code: str,
        departure_date: str,
        from_station: str,
        to_station: str,
        seat_type: str,
        success: bool,
        order_id: str = None,
        error_message: str = None
    ):
        """
        发送抢票结果通知
        
        Args:
            train_code: 车次
            departure_date: 日期
            from_station: 出发站
            to_station: 到达站
            seat_type: 座位类型
            success: 是否成功
            order_id: 订单号
            error_message: 错误信息
        """
        if success:
            title = "🎫 抢票成功！"
            content = (
                f"**车次**: {train_code}\n"
                f"**日期**: {departure_date}\n"
                f"**区间**: {from_station} → {to_station}\n"
                f"**座位**: {seat_type}\n"
                f"**订单号**: {order_id or 'N/A'}\n\n"
                f"请尽快在 30 分钟内完成支付！"
            )
        else:
            title = "❌ 抢票失败"
            content = (
                f"**车次**: {train_code}\n"
                f"**日期**: {departure_date}\n"
                f"**区间**: {from_station} → {to_station}\n"
                f"**座位**: {seat_type}\n"
                f"**原因**: {error_message or '未知错误'}\n\n"
                f"将继续监控..."
            )
        
        return self.send_all(title, content, type='ticket_result')
    
    def send_monitor_notification(self, changes: Dict):
        """
        发送余票监控变化通知
        
        Args:
            changes: 变化信息
        """
        title = "📊 余票监控变化"
        
        parts = []
        
        if changes.get('new_trains'):
            parts.append("**新增有票**:")
            for item in changes['new_trains'][:5]:  # 最多显示 5 条
                parts.append(f"- {item['train']} {item['seat_type']}: {item['count']}张")
        
        if changes.get('changes'):
            parts.append("\n**余票变化**:")
            for item in changes['changes'][:5]:
                parts.append(
                    f"- {item['train']} {item['seat_type']}: "
                    f"{item['previous']} → {item['current']}"
                )
        
        content = '\n'.join(parts) if parts else "暂无变化"
        
        return self.send_all(title, content, type='monitor_change')
    
    def send_error_notification(self, error_type: str, error_message: str):
        """
        发送错误通知
        
        Args:
            error_type: 错误类型
            error_message: 错误信息
        """
        title = "⚠️ 抢票错误"
        content = (
            f"**类型**: {error_type}\n"
            f"**信息**: {error_message}\n"
            f"**时间**: \n\n"
            f"请检查程序运行状态"
        )
        
        return self.send_all(title, content, type='error')


def create_notification_manager(config: Dict) -> NotificationManager:
    """
    创建通知管理器
    
    Args:
        config: 配置信息
    
    Returns:
        NotificationManager 实例
    """
    manager = NotificationManager()
    
    # 添加 PushPlus
    pushplus_config = config.get('pushplus', {})
    if pushplus_config.get('token'):
        manager.add_notifier(
            PushPlusNotifier(
                token=pushplus_config['token'],
                channel=pushplus_config.get('channel', 'wechat'),
                topic=pushplus_config.get('topic'),
            )
        )
        logger.info("已添加 PushPlus 通知器")
    
    # 添加 Telegram
    tg_config = config.get('telegram', {})
    if tg_config.get('bot_token') and tg_config.get('chat_id'):
        manager.add_notifier(
            TelegramNotifier(
                bot_token=tg_config['bot_token'],
                chat_id=tg_config['chat_id'],
            )
        )
        logger.info("已添加 Telegram 通知器")
    
    # 添加邮件
    email_config = config.get('email', {})
    if email_config.get('smtp_server') and email_config.get('receiver_email'):
        manager.add_notifier(
            EmailNotifier(
                smtp_server=email_config['smtp_server'],
                smtp_port=email_config.get('smtp_port', 587),
                sender_email=email_config['sender_email'],
                sender_password=email_config['sender_password'],
                receiver_email=email_config['receiver_email'],
            )
        )
        logger.info("已添加邮件通知器")
    
    return manager
