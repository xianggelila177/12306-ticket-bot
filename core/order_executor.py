# -*- coding: utf-8 -*-
"""
自动下单模块 - 自动下单（修复 API URL 版）
"""

import time
import requests
import json
from typing import Optional, Dict, List, Any
from datetime import datetime

from utils.logger import get_logger

logger = get_logger("order_executor")


class OrderExecutor:
    """
    12306 自动下单器
    
    功能：
    - 提交订单请求
    - 确认乘客信息
    - 提交验证码
    - 获取订单号
    """
    
    # ✅ 修复：正确的 API URL
    BASE_URL = "https://kyfw.12306.cn"
    
    # API 端点
    INIT_URL = f"{BASE_URL}/otn/confirmPassenger/confirmSingle"
    CHECK_ORDER_URL = f"{BASE_URL}/otn/confirmPassenger/checkOrderInfo"
    CONFIRM_URL = f"{BASE_URL}/otn/confirmPassenger/confirmSingle"
    GET_PASSENGER_URL = f"{BASE_URL}/otn/passengers/query"
    SUBMIT_ORDER_URL = f"{BASE_URL}/otn/leftTicket/submitOrderRequest"
    CHECK_CHAOSHI_URL = f"{BASE_URL}/otn/confirmPassenger/checkChaoshi"
    
    def __init__(self, session: requests.Session = None):
        """
        初始化下单器
        
        Args:
            session: requests Session 对象
        """
        if session is None:
            self.session = requests.Session()
        else:
            self.session = session
        
        # ✅ 完整的请求头配置
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Referer': 'https://kyfw.12306.cn/otn/leftTicket/init',
            'Origin': 'https://kyfw.12306.cn',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'Content-Type': 'application/json;charset=UTF-8',
        }
        self.session.headers.update(self.headers)
        
        self.current_order = None
    
    def submit_order(
        self,
        train_no: str,
        from_station: str,
        to_station: str,
        departure_date: str,
        seat_type: str,
        passengers: List[Dict],
        secret_str: str,
        train_type: str = None
    ) -> Dict:
        """
        提交订单请求
        
        Args:
            train_no: 车次编号
            from_station: 出发站代码
            to_station: 到达站代码
            departure_date: 出发日期
            seat_type: 座位类型
            passengers: 乘客信息列表
            secret_str: 加密字符串（来自余票查询）
            train_type: 车次类型
        
        Returns:
            提交结果
        """
        try:
            # 构建订单请求数据
            order_data = {
                'secretStr': secret_str,
                'train_date': departure_date,
                'backTrainDate': '',
                'tourFlag': 'dc',  # 单程
                'purpose_codes': 'ADULT',
                'query_from_station_name': from_station,
                'query_to_station_name': to_station,
                'undefined': '',
            }
            
            response = self.session.post(
                self.SUBMIT_ORDER_URL,
                data=json.dumps(order_data),
                headers=self.headers,
                timeout=15
            )
            
            if response.status_code != 200:
                logger.error(f"提交订单失败: {response.status_code}")
                return {'success': False, 'message': f'HTTP {response.status_code}'}
            
            result = response.json()
            
            if result.get('status') and result.get('httpstatus') == 200:
                logger.info("订单提交成功")
                self.current_order = {
                    'train_no': train_no,
                    'departure_date': departure_date,
                    'seat_type': seat_type,
                    'passengers': passengers,
                }
                return {'success': True, 'message': '订单提交成功'}
            else:
                error_msg = result.get('messages', ['未知错误'])[0]
                logger.error(f"提交订单失败: {error_msg}")
                return {'success': False, 'message': error_msg}
        
        except Exception as e:
            logger.error(f"提交订单异常: {e}")
            return {'success': False, 'message': str(e)}
    
    def get_passengers(self) -> List[Dict]:
        """
        获取常用乘客信息
        
        Returns:
            乘客列表
        """
        try:
            response = self.session.get(
                self.GET_PASSENGER_URL,
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code != 200:
                logger.error(f"获取乘客信息失败: {response.status_code}")
                return []
            
            result = response.json()
            
            if result.get('status'):
                return result.get('data', {}).get('normal_passengers', [])
            
            return []
        
        except Exception as e:
            logger.error(f"获取乘客信息异常: {e}")
            return []
    
    def check_order_info(
        self,
        passengers: List[Dict],
        seat_type: str,
        train_no: str,
        departure_date: str
    ) -> Dict:
        """
        检查订单信息（确认乘客和座位）
        
        Args:
            passengers: 乘客信息
            seat_type: 座位类型
            train_no: 车次编号
            departure_date: 出发日期
        
        Returns:
            检查结果
        """
        try:
            # 构建乘客信息
            passenger_str = ','.join([
                p.get('code', '') for p in passengers
            ])
            
            check_data = {
                'cancel_flag': '2',
                'bed_level_order_num': '000000000000000000000000',
                'passengerTicketStr': self._build_passenger_ticket(
                    passengers, seat_type
                ),
                'oldPassengerStr': passenger_str,
                'tour_flag': 'dc',
                'randCode': '',
                'whatselect': '1',
                'choose_seats': '',
                'seatDetailType': '000',
                'isShowWaitingTicket': None,
                'allowYoungMan': None,
                'priorityDown': None,
                'useLocalCache': 'true',  # ✅ 修复：添加必要参数
            }
            
            response = self.session.post(
                self.CHECK_ORDER_URL,
                data=json.dumps(check_data),
                headers=self.headers,
                timeout=15
            )
            
            if response.status_code != 200:
                return {'success': False, 'message': f'HTTP {response.status_code}'}
            
            result = response.json()
            
            if result.get('status') and result.get('httpstatus') == 200:
                return {
                    'success': True,
                    'data': result.get('data', {}),
                    'message': '订单信息检查通过'
                }
            else:
                error_msg = result.get('messages', ['检查失败'])[0]
                return {'success': False, 'message': error_msg}
        
        except Exception as e:
            logger.error(f"检查订单信息异常: {e}")
            return {'success': False, 'message': str(e)}
    
    def _build_passenger_ticket(self, passengers: List[Dict], seat_type: str) -> str:
        """
        构建乘客票务字符串
        
        Args:
            passengers: 乘客列表
            seat_type: 座位类型
        
        Returns:
            票务字符串
        """
        parts = []
        
        for p in passengers:
            # 格式: 座位类型,0,票种,乘客名,证件类型,证件号,手机号,保存常用联系人(Y/N)
            ticket_str = f"{seat_type},0,1,{p.get('name', '')},{p.get('passenger_id_type_code', '1')},{p.get('passenger_id_no', '')},{p.get('mobile', '')},N"
            parts.append(ticket_str)
        
        return ','.join(parts)
    
    def submit_captcha(self, captcha_result: List[str]) -> Dict:
        """
        ✅ 验证码提交（缺失的关键步骤）
        
        提交验证码验证请求
        
        Args:
            captcha_result: 验证码识别结果
        
        Returns:
            提交结果
        """
        try:
            # 构建验证码数据
            captcha_data = {
                'randCode': ','.join(captcha_result),
                'rand': 'sjrand',
                'type': 'login',
            }
            
            response = self.session.post(
                f"{self.BASE_URL}/passport/web/auth/qrcode/submit",  # ✅ 修复：正确的验证码提交 API
                data=json.dumps(captcha_data),
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code != 200:
                return {'success': False, 'message': f'HTTP {response.status_code}'}
            
            result = response.json()
            
            if result.get('result_code') == 0:
                return {'success': True, 'message': '验证码提交成功'}
            else:
                return {'success': False, 'message': result.get('result_message', '验证码验证失败')}
        
        except Exception as e:
            logger.error(f"验证码提交异常: {e}")
            return {'success': False, 'message': str(e)}
    
    def confirm_single(
        self,
        passengers: List[Dict],
        seat_type: str,
        captcha_result: List[str] = None,
        train_no: str = None,
        departure_date: str = None
    ) -> Dict:
        """
        确认下单（最终确认）
        
        Args:
            passengers: 乘客信息
            seat_type: 座位类型
            captcha_result: 验证码结果
            train_no: 车次编号
            departure_date: 出发日期
        
        Returns:
            下单结果
        """
        try:
            # 构建确认请求数据
            confirm_data = {
                'passengerTicketStr': self._build_passenger_ticket(passengers, seat_type),
                'oldPassengerStr': ','.join([
                    f"{p.get('passenger_name', '')},{p.get('passenger_id_type_code', '')},{p.get('passenger_id_no', '')},1"
                    for p in passengers
                ]),
                'randCode': ','.join(captcha_result) if captcha_result else '',
                'purpose_codes': '00',
                'key_check_isChange': self.current_order.get('key_check_isChange') if self.current_order else '',
                'leftTicketStr': self.current_order.get('left_ticket_str') if self.current_order else '',
                'train_location': self.current_order.get('train_location') if self.current_order else '',
                'choose_seats': '',
                'seatDetailType': '000',
                'whatselect': '1',
                'roomType': '00',
                'dwAll': 'N',
                'tying_ticket': '',
            }
            
            response = self.session.post(
                self.CONFIRM_URL,
                data=json.dumps(confirm_data),
                headers=self.headers,
                timeout=15
            )
            
            if response.status_code != 200:
                return {'success': False, 'message': f'HTTP {response.status_code}'}
            
            result = response.json()
            
            if result.get('status') and result.get('httpstatus') == 200:
                data = result.get('data', {})
                
                if data.get('submitStatus', False):
                    return {
                        'success': True,
                        'order_id': data.get('orderId'),
                        'message': '下单成功，请尽快支付'
                    }
                else:
                    # 获取失败原因
                    err_msg = data.get('errMsg', '下单失败')
                    logger.error(f"下单失败: {err_msg}")
                    return {'success': False, 'message': err_msg}
            else:
                error_msg = result.get('messages', ['下单失败'])[0]
                return {'success': False, 'message': error_msg}
        
        except Exception as e:
            logger.error(f"确认下单异常: {e}")
            return {'success': False, 'message': str(e)}
    
    def query_order(self, order_id: str) -> Dict:
        """
        查询订单状态
        
        Args:
            order_id: 订单 ID
        
        Returns:
            订单信息
        """
        try:
            response = self.session.get(
                f"{self.BASE_URL}/otn/queryOrder/queryMyOrder",
                params={
                    'orderId': order_id,
                    'come_from': 'scan',
                },
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code != 200:
                return {'success': False, 'message': '查询失败'}
            
            result = response.json()
            
            if result.get('status'):
                return {
                    'success': True,
                    'data': result.get('data', {}),
                }
            
            return {'success': False, 'message': result.get('messages', ['查询失败'])[0]}
        
        except Exception as e:
            logger.error(f"查询订单异常: {e}")
            return {'success': False, 'message': str(e)}
    
    def cancel_order(self, order_id: str) -> Dict:
        """
        取消订单
        
        Args:
            order_id: 订单 ID
        
        Returns:
            取消结果
        """
        try:
            response = self.session.post(
                f"{self.BASE_URL}/otn/queryOrder/cancelNoCompleteOrder",
                data=json.dumps({'orderId': order_id}),
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code != 200:
                return {'success': False, 'message': '取消失败'}
            
            result = response.json()
            
            if result.get('status'):
                return {'success': True, 'message': '订单已取消'}
            
            return {'success': False, 'message': result.get('messages', ['取消失败'])[0]}
        
        except Exception as e:
            logger.error(f"取消订单异常: {e}")
            return {'success': False, 'message': str(e)}
    
    def auto_order(
        self,
        train_info: Dict,
        passengers: List[Dict],
        seat_type: str,
        captcha_result: List[str]
    ) -> Dict:
        """
        自动完成下单流程
        
        Args:
            train_info: 车次信息（包含 secret_str 等）
            passengers: 乘客信息
            seat_type: 座位类型
            captcha_result: 验证码结果
        
        Returns:
            下单结果
        """
        logger.info("开始自动下单流程...")
        
        # 1. 提交订单
        submit_result = self.submit_order(
            train_no=train_info.get('train_no'),
            from_station=train_info.get('from_station'),
            to_station=train_info.get('to_station'),
            departure_date=train_info.get('departure_date'),
            seat_type=seat_type,
            passengers=passengers,
            secret_str=train_info.get('secret_str'),
            train_type=train_info.get('train_type'),
        )
        
        if not submit_result.get('success'):
            return submit_result
        
        # 2. 检查订单信息
        check_result = self.check_order_info(
            passengers=passengers,
            seat_type=seat_type,
            train_no=train_info.get('train_no'),
            departure_date=train_info.get('departure_date'),
        )
        
        if not check_result.get('success'):
            return check_result
        
        # 3. ✅ 验证码提交（缺失的关键步骤）
        captcha_result_submit = self.submit_captcha(captcha_result)
        if not captcha_result_submit.get('success'):
            return captcha_result_submit
        
        # 4. 确认下单
        confirm_result = self.confirm_single(
            passengers=passengers,
            seat_type=seat_type,
            captcha_result=captcha_result,
            train_no=train_info.get('train_no'),
            departure_date=train_info.get('departure_date'),
        )
        
        return confirm_result
