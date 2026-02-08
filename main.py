# -*- coding: utf-8 -*-
"""
12306 抢票 Agent 主入口

⚠️⚠️⚠️ 重要警告 ⚠️⚠️⚠️

1. 本工具仅供学习研究使用
2. 使用本工具存在账号被封禁的风险
3. 自动化操作可能违反12306服务条款
4. 请于24小时内删除本工具
5. 不保证抢票成功

使用即表示您已了解并同意以上声明

功能：
- 配置加载
- 模块协调
- 抢票流程控制
- 异常处理
"""

import os
import sys
import time
import signal
import argparse
from pathlib import Path
from typing import Optional, Dict, List

import yaml
import requests

from utils.logger import setup_logger
from core.auth_manager import AuthManager
from core.captcha_solver import CaptchaSolver, create_captcha_solver
from core.ticket_monitor import TicketMonitor
from core.order_executor import OrderExecutor
from core.notification import NotificationManager, create_notification_manager
from core.config_manager import SecureConfigManager, get_config_manager
from core.database import TicketDatabase
from core.risk_controller import RiskController
from core.proxy_manager import ProxyManager, create_proxy_manager

# 设置日志
logger = setup_logger(
    name="12306_bot",
    level=logging.INFO,
    log_file="12306_bot.log"
)


class TicketBot:
    """
    12306 抢票机器人
    
    功能：
    - 扫码登录
    - 余票监控
    - 自动下单
    - 多渠道通知
    """
    
    def __init__(self, config_path: str = None):
        """
        初始化抢票机器人
        
        Args:
            config_path: 配置文件路径
        """
        # 加载配置
        self.config_manager = get_config_manager()
        self.config = self.config_manager.config
        
        # 初始化数据库
        self.db = TicketDatabase()
        
        # 初始化各模块
        self.session = requests.Session()
        self.auth_manager = AuthManager(self.session)
        self.ticket_monitor = TicketMonitor(self.session)
        self.order_executor = OrderExecutor(self.session)
        
        # 风控控制器
        risk_config = self.config_manager.risk_config
        self.risk_controller = RiskController(risk_config)
        
        # 代理管理
        proxy_config = self.config.get('proxy', {})
        self.proxy_manager = create_proxy_manager(proxy_config)
        
        # 通知管理
        notification_config = self.config_manager.notification_config
        self.notification_manager = create_notification_manager(notification_config)
        
        # 验证码识别
        captcha_config = self.config.get('captcha', {})
        self.captcha_solver = create_captcha_solver(captcha_config)
        
        # 运行状态
        self.is_running = False
        self.targets = self.config_manager.get_targets()
        
        # 信号处理
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logger.info("12306 抢票机器人初始化完成")
    
    def _signal_handler(self, signum, frame):
        """信号处理"""
        logger.info(f"接收到信号 {signum}，正在停止...")
        self.is_running = False
    
    def login(self, use_saved_cookies: bool = True) -> bool:
        """
        登录 12306
        
        Args:
            use_saved_cookies: 是否使用保存的 Cookie
        
        Returns:
            是否登录成功
        """
        # 尝试使用保存的 Cookie
        if use_saved_cookies:
            accounts = self.config_manager.get_active_accounts()
            if accounts:
                account_name = accounts[0].get('name')
                cookies = self.config_manager.get_cookies(account_name)
                
                if cookies:
                    self.auth_manager.set_cookies(cookies)
                    
                    # 验证登录状态
                    if self.auth_manager.verify_login_status():
                        logger.info(f"使用保存的 Cookie 登录成功: {account_name}")
                        return True
                    else:
                        logger.warning("保存的 Cookie 已过期，需要重新登录")
        
        # 扫码登录
        logger.info("开始扫码登录...")
        
        uuid, qrcode_base64 = self.auth_manager.generate_login_qrcode()
        
        if not uuid:
            logger.error("生成二维码失败")
            return False
        
        # 显示二维码
        logger.info(f"请扫描二维码登录 (UUID: {uuid})")
        
        # 等待扫码
        result = self.auth_manager.wait_for_scan(uuid, timeout=120)
        
        if result.get('status') == 'success':
            # 保存 Cookie
            cookies = self.auth_manager.get_cookies()
            account_name = "默认账号"
            self.config_manager.save_encrypted_cookies(account_name, cookies)
            
            logger.info("登录成功！")
            return True
        else:
            logger.error(f"登录失败: {result.get('message')}")
            return False
    
    def get_user_passengers(self) -> List[Dict]:
        """
        获取乘车人信息
        
        Returns:
            乘车人列表
        """
        # 从数据库获取
        passengers = self.db.get_passengers()
        
        if passengers:
            return passengers
        
        # 从 API 获取
        passengers = self.order_executor.get_passengers()
        
        if passengers:
            # 保存到数据库
            for p in passengers:
                self.db.add_passenger(
                    name=p.get('passenger_name'),
                    id_card=p.get('passenger_id_no'),
                    phone=p.get('mobile_no'),
                    id_type=p.get('passenger_id_type_code'),
                )
        
        return passengers
    
    def monitor_and_grab(self, target_index: int = 0) -> bool:
        """
        监控并抢票
        
        Args:
            target_index: 目标索引
        
        Returns:
            是否抢票成功
        """
        if not self.targets or target_index >= len(self.targets):
            logger.error("没有配置抢票目标")
            return False
        
        target = self.targets[target_index]
        
        logger.info(f"开始监控: {target}")
        
        # 获取乘车人
        passengers = self.get_user_passengers()
        if not passengers:
            logger.error("没有乘车人信息")
            return False
        
        passenger_names = target.get('passengers', [p.get('name') for p in passengers[:1]])
        selected_passengers = [p for p in passengers if p.get('name') in passenger_names]
        
        seat_types = target.get('seats', ['硬卧', '软卧', '硬座'])
        
        self.is_running = True
        last_trains = None
        
        while self.is_running:
            try:
                # 风控检查
                if self.risk_controller.should_stop():
                    logger.warning("触发风控，暂停监控")
                    time.sleep(60)
                    continue
                
                # 查询余票
                trains = self.ticket_monitor.query_tickets(
                    from_station=target['from_code'],
                    to_station=target['to_code'],
                    date=target['date'],
                )
                
                if not trains:
                    logger.debug("暂无可用车次")
                    self.risk_controller.wait_interval()
                    continue
                
                # 筛选目标车次
                filtered = self.ticket_monitor.filter_trains(
                    trains,
                    train_codes=target.get('trains'),
                    seat_types=seat_types,
                    min_available=1
                )
                
                if not filtered:
                    logger.debug("没有符合条件的车次")
                    self.risk_controller.wait_interval()
                    continue
                
                # 检测变化
                changes = self.ticket_monitor.detect_changes(filtered, last_trains)
                
                if changes.get('new_trains'):
                    logger.info(f"发现有余票: {changes['new_trains']}")
                    
                    # 通知余票变化
                    self.notification_manager.send_monitor_notification(changes)
                    
                    # 尝试下单
                    for train in filtered[:3]:  # 最多尝试前 3 个车次
                        if self._grab_ticket(train, selected_passengers, seat_types):
                            return True
                
                last_trains = filtered
                
                # 等待间隔
                self.risk_controller.wait_interval()
            
            except Exception as e:
                logger.error(f"监控异常: {e}")
                self.risk_controller.on_failure("monitor_error")
                time.sleep(5)
        
        return False
    
    def _grab_ticket(
        self,
        train: Dict,
        passengers: List[Dict],
        seat_types: List[str]
    ) -> bool:
        """
        尝试下单
        
        Args:
            train: 车次信息
            passengers: 乘车人
            seat_types: 座位类型列表
        
        Returns:
            是否下单成功
        """
        for seat_type in seat_types:
            try:
                logger.info(f"尝试下单: {train['train_code']} {seat_type}")
                
                # 获取验证码
                captcha_result = self._get_captcha()
                if not captcha_result:
                    logger.warning("验证码获取失败")
                    continue
                
                # 执行下单
                result = self.order_executor.auto_order(
                    train_info=train,
                    passengers=passengers,
                    seat_type=seat_type,
                    captcha_result=captcha_result,
                )
                
                if result.get('success'):
                    order_id = result.get('order_id')
                    
                    # 记录成功日志
                    self.db.add_ticket_log(
                        train_no=train['train_code'],
                        departure_date=train.get('departure_date', ''),
                        from_station=train.get('from_station', ''),
                        to_station=train.get('to_station', ''),
                        seat_type=seat_type,
                        status='success',
                        result=order_id,
                    )
                    
                    # 发送成功通知
                    self.notification_manager.send_ticket_notification(
                        train_code=train['train_code'],
                        departure_date=target.get('date', ''),
                        from_station=train.get('from_station_name', ''),
                        to_station=train.get('to_station_name', ''),
                        seat_type=seat_type,
                        success=True,
                        order_id=order_id,
                    )
                    
                    logger.info(f"抢票成功！订单号: {order_id}")
                    return True
                
                else:
                    error_msg = result.get('message', '未知错误')
                    
                    # 记录失败日志
                    self.db.add_ticket_log(
                        train_no=train['train_code'],
                        departure_date=target.get('date', ''),
                        from_station=train.get('from_station', ''),
                        to_station=train.get('to_station', ''),
                        seat_type=seat_type,
                        status='failed',
                        result=error_msg,
                    )
                    
                    logger.warning(f"下单失败: {error_msg}")
                    
                    # 发送失败通知
                    self.notification_manager.send_ticket_notification(
                        train_code=train['train_code'],
                        departure_date=target.get('date', ''),
                        from_station=train.get('from_station_name', ''),
                        to_station=train.get('to_station_name', ''),
                        seat_type=seat_type,
                        success=False,
                        error_message=error_msg,
                    )
                    
                    self.risk_controller.on_failure("order_failed")
            
            except Exception as e:
                logger.error(f"下单异常: {e}")
                self.risk_controller.on_failure("order_exception")
        
        return False
    
    def _get_captcha(self) -> Optional[List[str]]:
        """
        获取验证码识别结果
        
        Returns:
            验证码结果列表
        """
        try:
            # 获取验证码图片
            response = self.session.get(
                "https://kyfw.12306.cn/passport/captcha/captcha-image64",
                params={'login_site': 'E', 'module': 'login', 'type': '4'},
                timeout=10
            )
            
            if response.status_code != 200:
                logger.error("获取验证码图片失败")
                return None
            
            data = response.json()
            image_data = data.get('data', {}).get('image')
            
            if not image_data:
                return None
            
            # 解码 base64 图片
            import base64
            image_bytes = base64.b64decode(image_data)
            
            # 识别验证码
            success, result = self.captcha_solver.solve(image_bytes)
            
            if success:
                return result
            
            return None
        
        except Exception as e:
            logger.error(f"获取验证码异常: {e}")
            return None
    
    def run(self, target_index: int = 0):
        """
        运行抢票机器人
        
        Args:
            target_index: 目标索引
        """
        # 登录
        if not self.login():
            logger.error("登录失败，退出")
            return False
        
        # 监控并抢票
        success = self.monitor_and_grab(target_index)
        
        if success:
            logger.info("抢票任务完成")
        else:
            logger.info("抢票任务已停止")
        
        return success
    
    def stop(self):
        """停止抢票机器人"""
        self.is_running = False
        logger.info("正在停止抢票机器人...")
    
    def get_status(self) -> Dict:
        """
        获取运行状态
        
        Returns:
            状态信息
        """
        return {
            'is_running': self.is_running,
            'targets_count': len(self.targets),
            'risk_status': self.risk_controller.get_status(),
            'proxy_status': self.proxy_manager.get_stats(),
            'database_stats': self.db.get_statistics(),
        }


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='12306 抢票机器人')
    parser.add_argument('--config', '-c', default='config.yaml', help='配置文件路径')
    parser.add_argument('--target', '-t', type=int, default=0, help='目标索引')
    parser.add_argument('--login', '-l', action='store_true', help='仅登录')
    parser.add_argument('--status', '-s', action='store_true', help='查看状态')
    
    args = parser.parse_args()
    
    # 创建机器人实例
    bot = TicketBot(config_path=args.config)
    
    if args.login:
        # 仅登录
        success = bot.login()
        sys.exit(0 if success else 1)
    
    elif args.status:
        # 查看状态
        status = bot.get_status()
        print(status)
        sys.exit(0)
    
    else:
        # 运行抢票
        try:
            bot.run(target_index=args.target)
        except KeyboardInterrupt:
            logger.info("用户中断")
        finally:
            bot.stop()


if __name__ == '__main__':
    import logging
    main()
