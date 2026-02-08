# -*- coding: utf-8 -*-
"""
扫码登录模块 - 12306 扫码登录（修复版）
"""

import time
import requests
from typing import Optional, Dict, Tuple
from urllib.parse import parse_qs

from utils.logger import get_logger
from utils.qrcode import generate_qrcode_base64

logger = get_logger("auth_manager")


class AuthManager:
    """
    12306 扫码登录管理器
    
    功能：
    - 生成登录二维码
    - 轮询检查扫码状态
    - Cookie 管理
    - 登录状态验证
    """
    
    # 12306 API 端点（✅ 修复：正确的 kyfw.12306.cn）
    BASE_URL = "https://kyfw.12306.cn"
    PASSPORT_URL = "https://passport.12306.cn"
    
    # API 端点配置
    QRCODE_URL = f"{PASSPORT_URL}/passport/web/auth/qrcode"
    CHECK_URL = f"{PASSPORT_URL}/passport/web/auth/qrcode/check"
    AUTH_URL = f"{PASSPORT_URL}/passport/web/auth/qrcode/{'login' if False else 'login'}"
    
    # 刷新 Cookie 的 API 列表
    COOKIE_REFRESH_APIS = [
        f"{BASE_URL}/otn/index/init",
        f"{BASE_URL}/otn/leftTicket/init",
        f"{BASE_URL}/otn/passengers/query",
    ]
    
    def __init__(self, session: requests.Session = None):
        """
        初始化登录管理器
        
        Args:
            session: requests Session 对象
        """
        if session is None:
            self.session = requests.Session()
        else:
            self.session = session
        
        # ✅ 完整的请求头配置
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://passport.12306.cn/',
            'Origin': 'https://passport.12306.cn',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'Content-Type': 'application/json;charset=UTF-8',
        }
        self.session.headers.update(self.headers)
        
        self.uuid: Optional[str] = None
        self.is_logged_in: bool = False
    
    def generate_login_qrcode(self) -> Tuple[str, str]:
        """
        生成登录二维码
        
        Returns:
            Tuple[uuid, base64_image]
        """
        try:
            # 生成 uuid
            response = self.session.get(
                f"{self.PASSPORT_URL}/passport/web/auth/qrcode/generate",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code != 200:
                logger.error(f"生成二维码失败: {response.status_code}")
                return None, ""
            
            data = response.json()
            
            if data.get('result_code') != 0:
                logger.error(f"生成二维码失败: {data}")
                return None, ""
            
            self.uuid = data['data']['uuid']
            qrcode_url = data['data']['image']
            
            # 生成 base64 图片
            base64_image = generate_qrcode_base64(qrcode_url)
            
            logger.info("二维码已生成，请在 12306 APP 中扫描")
            return self.uuid, base64_image
        
        except Exception as e:
            logger.error(f"生成二维码异常: {e}")
            return None, ""
    
    def check_qrcode_status(self, uuid: str = None) -> Dict:
        """
        检查二维码扫描状态
        
        Args:
            uuid: 二维码 UUID
        
        Returns:
            状态信息字典
        """
        if uuid is None:
            uuid = self.uuid
        
        if not uuid:
            return {'status': 'error', 'message': 'UUID 不存在'}
        
        try:
            response = self.session.get(
                f"{self.PASSPORT_URL}/passport/web/auth/qrcode/check",
                params={
                    'uuid': uuid,
                    '_csrf': '',
                },
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code != 200:
                return {'status': 'error', 'message': f'请求失败: {response.status_code}'}
            
            data = response.json()
            return self._parse_check_response(data)
        
        except Exception as e:
            logger.error(f"检查二维码状态异常: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def _parse_check_response(self, data: dict) -> Dict:
        """
        解析二维码检查响应
        
        Args:
            data: API 响应数据
        
        Returns:
            解析后的状态信息
        """
        result_code = data.get('result_code', -1)
        result_message = data.get('result_message', '')
        
        status_map = {
            0: {'status': 'waiting', 'message': '等待扫描'},
            1: {'status': 'scanned', 'message': '已扫描，请在 APP 中确认'},
            2: {'status': 'confirmed', 'message': '确认成功，正在登录...'},
            3: {'status': 'expired', 'message': '二维码已过期'},
            4: {'status': 'waiting', 'message': '等待扫描'},
        }
        
        if result_code in status_map:
            result = status_map[result_code]
            
            # 如果确认成功，提取登录信息
            if result_code == 2:
                result['data'] = data.get('data', {})
                result['apptk'] = data.get('data', {}).get('apptk')
            
            return result
        
        return {'status': 'unknown', 'message': result_message}
    
    def login_with_token(self, apptk: str) -> bool:
        """
        使用 token 完成登录
        
        Args:
            apptk: APP Token
        
        Returns:
            是否登录成功
        """
        try:
            response = self.session.post(
                f"{self.PASSPORT_URL}/passport/web/auth/qrcode/login",
                json={
                    'apptk': apptk,
                    '_struct_view': 'browser',
                },
                headers=self.headers,
                timeout=15
            )
            
            if response.status_code != 200:
                logger.error(f"登录请求失败: {response.status_code}")
                return False
            
            data = response.json()
            
            if data.get('result_code') != 0:
                logger.error(f"登录失败: {data.get('result_message')}")
                return False
            
            # 提取登录信息
            login_data = data.get('data', {})
            self.username = login_data.get('username', '')
            
            logger.info(f"登录成功: {self.username}")
            return True
        
        except Exception as e:
            logger.error(f"登录异常: {e}")
            return False
    
    def get_cookies(self) -> Dict[str, str]:
        """
        获取当前 Session 的 Cookie
        
        Returns:
            Cookie 字典
        """
        return self.session.cookies.get_dict()
    
    def set_cookies(self, cookies: Dict[str, str]):
        """
        设置 Cookie
        
        Args:
            cookies: Cookie 字典
        """
        self.session.cookies.update(cookies)
    
    def refresh_cookies(self, cookies: Dict[str, str] = None) -> Dict[str, str]:
        """
        多 API 刷新 Cookie（✅ 修复版）
        
        通过访问多个 12306 页面来刷新 Cookie
        以确保 Cookie 有效
        
        Args:
            cookies: 初始 Cookie（可选）
        
        Returns:
            更新后的 Cookie
        """
        if cookies:
            self.set_cookies(cookies)
        
        updated_cookies = {}
        
        for api in self.COOKIE_REFRESH_APIS:
            try:
                response = self.session.get(api, timeout=5)
                if response.status_code == 200:
                    updated_cookies.update(response.cookies.get_dict())
                    logger.debug(f"Cookie 刷新成功: {api}")
            except Exception as e:
                logger.warning(f"Cookie 刷新失败 {api}: {e}")
                continue
        
        # 合并更新后的 Cookie
        current_cookies = self.get_cookies()
        current_cookies.update(updated_cookies)
        
        logger.info(f"Cookie 刷新完成，当前 Cookie 数量: {len(current_cookies)}")
        return current_cookies
    
    def verify_login_status(self) -> bool:
        """
        验证登录状态
        
        Returns:
            是否已登录
        """
        try:
            response = self.session.get(
                f"{self.BASE_URL}/otn/index/init",
                timeout=10
            )
            
            if response.status_code != 200:
                return False
            
            # 检查响应中是否包含用户信息
            content = response.text
            
            # 检查登录状态标识
            if 'loginUserName' in content or 'currentUser' in content:
                self.is_logged_in = True
                return True
            
            # 检查 Cookie 中的登录标识
            cookies = self.get_cookies()
            if '_uab_collina' in cookies and '_passport_session' in cookies:
                self.is_logged_in = True
                return True
            
            self.is_logged_in = False
            return False
        
        except Exception as e:
            logger.error(f"验证登录状态异常: {e}")
            return False
    
    def logout(self):
        """退出登录"""
        try:
            response = self.session.get(
                f"{self.PASSPORT_URL}/passport/web/auth/logout",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info("已退出登录")
            else:
                logger.warning(f"退出登录请求失败: {response.status_code}")
        
        except Exception as e:
            logger.error(f"退出登录异常: {e}")
        
        finally:
            self.is_logged_in = False
            self.session.cookies.clear()
    
    def wait_for_scan(self, uuid: str, timeout: int = 120, interval: int = 2) -> Dict:
        """
        等待扫码并登录
        
        Args:
            uuid: 二维码 UUID
            timeout: 超时时间（秒）
            interval: 检查间隔（秒）
        
        Returns:
            最终登录结果
        """
        start_time = time.time()
        last_status = None
        
        while time.time() - start_time < timeout:
            result = self.check_qrcode_status(uuid)
            status = result.get('status')
            
            # 状态变化时打印日志
            if status != last_status:
                logger.info(f"扫码状态: {result.get('message', status)}")
                last_status = status
            
            # 扫码确认成功
            if status == 'confirmed':
                apptk = result.get('apptk')
                if apptk:
                    login_success = self.login_with_token(apptk)
                    if login_success:
                        # 刷新 Cookie
                        self.refresh_cookies()
                        return {'status': 'success', 'message': '登录成功'}
                    else:
                        return {'status': 'error', 'message': '登录失败'}
            
            # 二维码过期
            elif status == 'expired':
                return {'status': 'expired', 'message': '二维码已过期'}
            
            # 等待或扫描中
            elif status in ['waiting', 'scanned']:
                time.sleep(interval)
                continue
            
            # 错误
            else:
                return {'status': 'error', 'message': result.get('message', '未知错误')}
        
        return {'status': 'timeout', 'message': '扫码超时'}
