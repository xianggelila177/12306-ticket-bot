#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
12306 抢票 Agent - 本地持续化监控脚本

⚠️⚠️⚠️ 重要警告 ⚠️⚠️⚠️

1. 本工具仅供学习研究使用
2. 使用本工具存在账号被封禁的风险
3. 自动化操作可能违反12306服务条款
4. 请于24小时内删除本工具
5. 不保证抢票成功

使用即表示您已了解并同意以上声明

功能：
- 后台持续运行
- 系统守护进程
- 日志自动轮转
- 开机自启

用法：
    # 前台运行
    python3 local_monitor.py

    # 后台运行（Linux/Mac）
    python3 local_monitor.py --daemon

    # 安装开机自启
    python3 local_monitor.py --install-service

    # 查看状态
    python3 local_monitor.py --status

作者: OpenClaw
版本: v2.0
"""

import os
import sys
import time
import json
import logging
import signal
import argparse
import subprocess
from datetime import datetime
from pathlib import Path

# 项目路径
PROJECT_DIR = Path(__file__).parent
CONFIG_FILE = PROJECT_DIR / "config.yaml"
LOG_DIR = PROJECT_DIR / "logs"
PID_FILE = PROJECT_DIR / "monitor.pid"


class LocalMonitor:
    """本地监控器"""
    
    def __init__(self):
        self.is_running = False
        self.process = None
        self.logger = self._setup_logger()
    
    def _setup_logger(self) -> logging.Logger:
        """配置日志"""
        LOG_DIR.mkdir(exist_ok=True)
        
        logger = logging.getLogger('local_monitor')
        logger.setLevel(logging.DEBUG)
        
        # 文件日志（带日期轮转）
        file_handler = logging.FileHandler(
            LOG_DIR / f"monitor_{datetime.now().strftime('%Y%m%d')}.log",
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        
        # 控制台日志
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
    
    def check_config(self) -> bool:
        """检查配置文件"""
        if not CONFIG_FILE.exists():
            self.logger.error(f"配置文件不存在: {CONFIG_FILE}")
            self.logger.info("请复制 config.example.yaml 为 config.yaml 并配置")
            return False
        
        try:
            import yaml
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # 检查必要配置
            if not config.get('account', {}).get('cookie'):
                self.logger.error("未配置登录Cookie")
                return False
            
            if not config.get('notification', {}).get('pushplus', {}).get('token'):
                self.logger.warning("未配置PushPlus，将无法收到通知")
            
            self.logger.info("配置文件检查通过")
            return True
            
        except Exception as e:
            self.logger.error(f"配置文件读取失败: {e}")
            return False
    
    def start_foreground(self):
        """前台运行"""
        self.logger.info("🚀 启动 12306 抢票监控（前台模式）")
        
        # 检查配置
        if not self.check_config():
            return
        
        # 导入并启动主程序
        try:
            from main import main
            main()
        except KeyboardInterrupt:
            self.logger.info("收到停止信号，正在退出...")
        except Exception as e:
            self.logger.error(f"运行错误: {e}")
            sys.exit(1)
    
    def start_daemon(self):
        """后台运行（守护进程）"""
        self.logger.info("🚀 启动 12306 抢票监控（后台模式）")
        
        # 检查是否已在运行
        if self.is_running():
            self.logger.warning("监控已在运行中")
            return
        
        # 检查配置
        if not self.check_config():
            return
        
        try:
            # 启动子进程
            self.process = subprocess.Popen(
                [sys.executable, str(PROJECT_DIR / "main.py"), "--monitor"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.STDOUT,
                preexec_fn=os.setsid  # 创建新进程组
            )
            
            # 保存PID
            with open(PID_FILE, 'w') as f:
                f.write(str(self.process.pid))
            
            self.is_running = True
            self.logger.info(f"✅ 监控已启动 (PID: {self.process.pid})")
            self.logger.info(f"📁 日志位置: {LOG_DIR}")
            
            # 等待
            while self.is_running:
                time.sleep(5)
                if self.process.poll() is not None:
                    self.logger.warning("监控进程异常退出")
                    break
            
        except Exception as e:
            self.logger.error(f"启动失败: {e}")
    
    def stop(self):
        """停止监控"""
        if not self.is_running() and not PID_FILE.exists():
            self.logger.warning("监控未运行")
            return
        
        # 读取PID
        try:
            with open(PID_FILE, 'r') as f:
                pid = int(f.read().strip())
            
            # 发送SIGTERM
            try:
                os.kill(pid, signal.SIGTERM)
                self.logger.info(f"已发送停止信号 (PID: {pid})")
            except ProcessLookupError:
                self.logger.warning("进程已不存在")
            
            # 删除PID文件
            PID_FILE.unlink()
            self.logger.info("监控已停止")
            
        except Exception as e:
            self.logger.error(f"停止失败: {e}")
    
    def is_running(self) -> bool:
        """检查是否在运行"""
        if not PID_FILE.exists():
            return False
        
        try:
            with open(PID_FILE, 'r') as f:
                pid = int(f.read().strip())
            
            # 检查进程是否存在
            os.kill(pid, 0)
            return True
            
        except (ProcessLookupError, ValueError):
            PID_FILE.unlink(missing_ok=True)
            return False
    
    def status(self):
        """查看状态"""
        if self.is_running():
            with open(PID_FILE, 'r') as f:
                pid = f.read().strip()
            self.logger.info(f"🟢 运行中 (PID: {pid})")
        else:
            self.logger.info("🔴 未运行")
        
        # 日志统计
        if LOG_DIR.exists():
            log_files = list(LOG_DIR.glob("*.log"))
            self.logger.info(f"📁 日志文件: {len(log_files)} 个")
            
            total_size = sum(f.stat().st_size for f in log_files)
            self.logger.info(f"📦 日志大小: {total_size / 1024:.1f} KB")
    
    def install_service(self):
        """安装系统服务（Linux systemd）"""
        service_content = f"""[Unit]
Description=12306 Ticket Monitor
After=network.target

[Service]
Type=simple
User={os.getlogin()}
WorkingDirectory={PROJECT_DIR}
ExecStart={sys.executable} {PROJECT_DIR / "main.py"} --monitor
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""
        
        service_file = Path("/etc/systemd/system/12306-monitor.service")
        
        try:
            with open(service_file, 'w') as f:
                f.write(service_content)
            
            os.system("systemctl daemon-reload")
            os.system("systemctl enable 12306-monitor.service")
            
            self.logger.info(f"✅ 服务已安装: {service_file}")
            self.logger.info("可用命令:")
            self.logger.info("  systemctl start 12306-monitor")
            self.logger.info("  systemctl stop 12306-monitor")
            self.logger.info("  systemctl status 12306-monitor")
            
        except PermissionError:
            self.logger.error("需要 root 权限安装服务")
            self.logger.info("请运行: sudo python3 local_monitor.py --install-service")
    
    def uninstall_service(self):
        """卸载系统服务"""
        try:
            os.system("systemctl stop 12306-monitor.service")
            os.system("systemctl disable 12306-monitor.service")
            Path("/etc/systemd/system/12306-monitor.service").unlink()
            os.system("systemctl daemon-reload")
            self.logger.info("✅ 服务已卸载")
        except Exception as e:
            self.logger.error(f"卸载失败: {e}")


def signal_handler(signum, frame):
    """信号处理"""
    logger = logging.getLogger('local_monitor')
    logger.info(f"收到信号 {signum}，正在退出...")
    sys.exit(0)


def main():
    """主入口"""
    parser = argparse.ArgumentParser(
        description="12306 抢票监控 - 本地持续化运行"
    )
    parser.add_argument(
        '--daemon', 
        action='store_true',
        help='后台运行模式'
    )
    parser.add_argument(
        '--stop',
        action='store_true',
        help='停止监控'
    )
    parser.add_argument(
        '--status',
        action='store_true',
        help='查看运行状态'
    )
    parser.add_argument(
        '--install-service',
        action='store_true',
        help='安装系统服务（需要root）'
    )
    parser.add_argument(
        '--uninstall-service',
        action='store_true',
        help='卸载系统服务'
    )
    
    args = parser.parse_args()
    
    # 信号处理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    monitor = LocalMonitor()
    
    if args.stop:
        monitor.stop()
    elif args.status:
        monitor.status()
    elif args.install_service:
        monitor.install_service()
    elif args.uninstall_service:
        monitor.uninstall_service()
    elif args.daemon:
        monitor.start_daemon()
    else:
        monitor.start_foreground()


if __name__ == '__main__':
    main()
